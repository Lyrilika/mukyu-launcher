
use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;
use std::time::{Duration, Instant};

use slint::{ComponentHandle, Image, Rgb8Pixel, SharedPixelBuffer};

use super::{ctx, post, Ctx};
use crate::pdf::{PdfEvent, PdfWorker};
use crate::printworks as pw;
use crate::ReaderWindow;

const UI_HIDE: Duration = Duration::from_millis(2600);
const CACHE_RADIUS: i64 = 3;
const CACHE_BUDGET: u64 = 128 * 1024 * 1024;
const SCROLL_COOLDOWN: Duration = Duration::from_millis(160);
const EDGE_ZONE: f32 = 0.25;

struct Inner {
    id: u64,
    window: ReaderWindow,
    worker: PdfWorker,
    key: String,
    count: usize,
    cur: usize,
    cache: HashMap<usize, (Image, (u32, u32))>,
    bbox: (u32, u32),
    seen_box: (u32, u32),
    closed: bool,
    fullscreen: bool,
    scroll_acc: f32,
    scroll_time: Option<Instant>,
    last_poke: Instant,
    hide_timer: slint::Timer,
    toast_timer: slint::Timer,
    spinner_timer: slint::Timer,
    tick: slint::Timer,
}

pub struct Reader(Rc<RefCell<Inner>>);

thread_local! {
    static OPEN_READERS: std::cell::Cell<usize> = const { std::cell::Cell::new(0) };
}

#[cfg(windows)]
pub fn any_open() -> bool {
    OPEN_READERS.with(|n| n.get() > 0)
}

impl Reader {
    pub fn close_now(&self) {
        close(&self.0);
    }
}

fn find(c: &Ctx, id: u64) -> Option<Rc<RefCell<Inner>>> {
    c.readers.borrow().iter().find(|r| r.0.borrow().id == id).map(|r| r.0.clone())
}

fn set_fullscreen(window: &slint::Window, fullscreen: bool) {
    #[cfg(target_os = "linux")]
    {
        use slint::winit_030::{winit::window::Fullscreen, WinitWindowAccessor};

        if window.with_winit_window(|native| {
            native.set_fullscreen(fullscreen.then_some(Fullscreen::Borderless(None)));
        }).is_some() {
            return;
        }
    }
    window.set_fullscreen(fullscreen);
}

pub fn open(c: &Rc<Ctx>, name: &str) {
    static NEXT: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(1);
    let id = NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    let window = match ReaderWindow::new() {
        Ok(w) => w,
        Err(e) => return c.message("Reader unavailable", &e.to_string()),
    };
    let title = pw::folder_name(name);
    window.set_doc_title(title.clone().into());
    window.window().set_size(c.app.window().size());
    let worker = PdfWorker::spawn(pw::pdf_path(name), move |event| post(move |c| on_event(c, id, event)));
    let inner = Rc::new(RefCell::new(Inner {
        id,
        window: window.clone_strong(),
        worker,
        key: title,
        count: 0,
        cur: 0,
        cache: HashMap::new(),
        bbox: (0, 0),
        seen_box: (0, 0),
        closed: false,
        fullscreen: true,
        scroll_acc: 0.0,
        scroll_time: None,
        last_poke: Instant::now(),
        hide_timer: slint::Timer::default(),
        toast_timer: slint::Timer::default(),
        spinner_timer: slint::Timer::default(),
        tick: slint::Timer::default(),
    }));
    c.readers.borrow_mut().push(Reader(inner.clone()));
    OPEN_READERS.with(|n| n.set(n.get() + 1));

    let w = Rc::downgrade(&inner);
    let with = move |f: fn(&Rc<RefCell<Inner>>)| {
        let w = w.clone();
        move || {
            if let Some(i) = w.upgrade() {
                f(&i)
            }
        }
    };
    window.on_next(with(next_page));
    window.on_prev(with(prev_page));
    window.on_close_reader(with(close));
    window.on_poke(with(poke_ui));
    window.on_toggle_fullscreen(with(|i| {
        let fs = !i.borrow().fullscreen;
        i.borrow_mut().fullscreen = fs;
        set_fullscreen(i.borrow().window.window(), fs);
    }));
    let w2 = Rc::downgrade(&inner);
    window.on_go(move |index| {
        if let Some(i) = w2.upgrade() {
            go_to(&i, index.max(0) as usize);
        }
    });
    let w3 = Rc::downgrade(&inner);
    window.on_scrolled(move |dy| {
        if let Some(i) = w3.upgrade() {
            on_scroll(&i, dy);
        }
    });
    let w4 = Rc::downgrade(&inner);
    window.on_picture_clicked(move |x, width| {
        if let Some(i) = w4.upgrade() {
            on_click(&i, x, width);
        }
    });
    let w5 = Rc::downgrade(&inner);
    window.window().on_close_requested(move || {
        if let Some(i) = w5.upgrade() {
            close(&i);
        }
        slint::CloseRequestResponse::HideWindow
    });

    let w6 = Rc::downgrade(&inner);
    inner.borrow().tick.start(slint::TimerMode::Repeated, Duration::from_millis(120), move || {
        if let Some(i) = w6.upgrade() {
            measure(&i);
        }
    });

    let _ = window.show();
    let weak = Rc::downgrade(&inner);
    super::after(50, move || {
        if let Some(reader) = weak.upgrade() {
            let reader = reader.borrow();
            if !reader.closed && reader.fullscreen && !reader.window.window().is_fullscreen() {
                set_fullscreen(reader.window.window(), true);
            }
        }
    });
    poke_ui(&inner);
}

fn on_event(c: &Rc<Ctx>, id: u64, event: PdfEvent) {
    let Some(i) = find(c, id) else { return };
    if i.borrow().closed {
        return;
    }
    match event {
        PdfEvent::Opened(count) => {
            let saved = pw::load_progress(&i.borrow().key);
            {
                let mut s = i.borrow_mut();
                s.count = count;
                s.window.set_count(count as i32);
            }
            if let Some(p) = saved.filter(|&p| p > 1 && (p as usize) < count) {
                i.borrow_mut().cur = p as usize - 1;
                toast(&i, &format!("Continuing from page {p}   ·   Home for the start"));
            }
            update_ui(&i);
            schedule(&i);
            start_spinner_timer(&i);
        }
        PdfEvent::Rendered { index, bbox, page } => {
            let Some(page) = page else {
                if index == i.borrow().cur {
                    stop_spinner(&i);
                    toast(&i, "This page could not be displayed");
                }
                return;
            };
            {
                let s = i.borrow();
                if (index as i64 - s.cur as i64).abs() > cache_radius(&s) {
                    return;
                }
                if let Some((_, b)) = s.cache.get(&index) {
                    if *b == s.bbox && bbox != s.bbox {
                        return;
                    }
                }
            }
            let buffer = SharedPixelBuffer::<Rgb8Pixel>::clone_from_slice(&page.rgb, page.width, page.height);
            i.borrow_mut().cache.insert(index, (Image::from_rgb8(buffer), bbox));
            if index == i.borrow().cur {
                show_current(&i);
            }
        }
        PdfEvent::Error(message) => {
            stop_spinner(&i);
            i.borrow().window.set_error_text(message.into());
            set_ui(&i, true);
        }
    }
}

fn cache_radius(s: &Inner) -> i64 {
    let per_page = (s.bbox.0 as u64 * s.bbox.1 as u64 * 3).max(1);
    let pages = (CACHE_BUDGET / per_page).max(3) as i64;
    ((pages - 1) / 2).clamp(1, CACHE_RADIUS)
}

fn schedule(i: &Rc<RefCell<Inner>>) {
    let mut s = i.borrow_mut();
    if s.count < 1 || s.bbox.0 < 1 || s.bbox.1 < 1 {
        return;
    }
    let cur = s.cur as i64;
    let radius = cache_radius(&s);
    let mut wanted = Vec::new();
    for idx in [cur, cur + 1, cur - 1, cur + 2, cur - 2, cur + 3] {
        if (idx - cur).abs() <= radius && idx >= 0 && (idx as usize) < s.count && !wanted.contains(&(idx as usize)) {
            let stale = s.cache.get(&(idx as usize)).map_or(true, |(_, b)| *b != s.bbox);
            if stale {
                wanted.push(idx as usize);
            }
        }
    }
    s.cache.retain(|k, _| (*k as i64 - cur).abs() <= radius);
    let bbox = s.bbox;
    s.worker.request(wanted, bbox);
}

fn show_current(i: &Rc<RefCell<Inner>>) {
    let entry = {
        let s = i.borrow();
        s.cache.get(&s.cur).map(|(img, _)| img.clone())
    };
    match entry {
        Some(img) => {
            let s = i.borrow();
            s.window.set_page(img);
            s.window.set_has_page(true);
            drop(s);
            stop_spinner(i);
        }
        None => start_spinner_timer(i),
    }
}

fn start_spinner_timer(i: &Rc<RefCell<Inner>>) {
    let s = i.borrow();
    if s.spinner_timer.running() || !s.window.get_error_text().is_empty() {
        return;
    }
    let w = Rc::downgrade(i);
    s.spinner_timer.start(slint::TimerMode::SingleShot, Duration::from_millis(220), move || {
        if let Some(i) = w.upgrade() {
            let s = i.borrow();
            if !s.closed && !s.cache.contains_key(&s.cur) {
                s.window.set_spinner_on(true);
            }
        }
    });
}

fn stop_spinner(i: &Rc<RefCell<Inner>>) {
    let s = i.borrow();
    s.spinner_timer.stop();
    s.window.set_spinner_on(false);
}

fn measure(i: &Rc<RefCell<Inner>>) {
    let changed = {
        let mut s = i.borrow_mut();
        if s.closed {
            return;
        }
        let factor = s.window.window().scale_factor();
        let bbox = ((s.window.get_area_width() * factor) as u32, (s.window.get_area_height() * factor) as u32);
        let mut changed = false;
        if bbox.0 > 0 && bbox.1 > 0 && bbox != s.bbox && (s.bbox == (0, 0) || bbox == s.seen_box) {
            s.bbox = bbox;
            changed = true;
        }
        s.seen_box = bbox;
        changed
    };
    if changed {
        schedule(i);
    }
}

fn update_ui(i: &Rc<RefCell<Inner>>) {
    let s = i.borrow();
    s.window.set_current(s.cur as i32);
}

fn go_to(i: &Rc<RefCell<Inner>>, index: usize) {
    {
        let mut s = i.borrow_mut();
        if s.count < 1 {
            return;
        }
        let index = index.min(s.count - 1);
        if index == s.cur {
            return;
        }
        s.cur = index;
    }
    update_ui(i);
    show_current(i);
    schedule(i);
}

fn next_page(i: &Rc<RefCell<Inner>>) {
    let (count, cur) = (i.borrow().count, i.borrow().cur);
    if count < 1 {
        return;
    }
    if cur + 1 >= count {
        toast(i, "Last page");
    } else {
        go_to(i, cur + 1);
    }
}

fn prev_page(i: &Rc<RefCell<Inner>>) {
    let (count, cur) = (i.borrow().count, i.borrow().cur);
    if count < 1 {
        return;
    }
    if cur == 0 {
        toast(i, "First page");
    } else {
        go_to(i, cur - 1);
    }
}

fn set_ui(i: &Rc<RefCell<Inner>>, visible: bool) {
    i.borrow().window.set_ui_visible(visible);
}

fn poke_ui(i: &Rc<RefCell<Inner>>) {
    let (window, armed) = {
        let mut s = i.borrow_mut();
        s.last_poke = Instant::now();
        (s.window.clone_strong(), s.hide_timer.running())
    };
    if !window.get_ui_visible() {
        window.set_ui_visible(true);
    }
    if armed {
        return;
    }
    let w = Rc::downgrade(i);
    i.borrow().hide_timer.start(slint::TimerMode::Repeated, Duration::from_millis(250), move || {
        let Some(i) = w.upgrade() else { return };
        let (window, closed, idle) = {
            let s = i.borrow();
            (s.window.clone_strong(), s.closed, s.last_poke.elapsed() >= UI_HIDE)
        };
        if closed || idle {
            i.borrow().hide_timer.stop();
        }
        if !closed && idle && window.get_error_text().is_empty() {
            window.set_ui_visible(false);
        }
    });
}

fn toast(i: &Rc<RefCell<Inner>>, text: &str) {
    let s = i.borrow();
    s.window.set_toast_text(text.into());
    s.window.set_toast_on(true);
    let w = Rc::downgrade(i);
    s.toast_timer.start(slint::TimerMode::SingleShot, Duration::from_millis(2200), move || {
        if let Some(i) = w.upgrade() {
            i.borrow().window.set_toast_on(false);
        }
    });
}

fn on_scroll(i: &Rc<RefCell<Inner>>, dy: f32) {
    let action = {
        let mut s = i.borrow_mut();
        let now = Instant::now();
        if s.scroll_time.map_or(false, |t| now.duration_since(t) < SCROLL_COOLDOWN) {
            s.scroll_acc = 0.0;
            return;
        }
        s.scroll_acc += -dy / 40.0;
        if s.scroll_acc >= 1.0 {
            s.scroll_acc = 0.0;
            s.scroll_time = Some(now);
            1
        } else if s.scroll_acc <= -1.0 {
            s.scroll_acc = 0.0;
            s.scroll_time = Some(now);
            -1
        } else {
            0
        }
    };
    match action {
        1 => next_page(i),
        -1 => prev_page(i),
        _ => {}
    }
}

fn on_click(i: &Rc<RefCell<Inner>>, x: f32, width: f32) {
    if width <= 0.0 || i.borrow().count < 1 {
        return;
    }
    if x < width * EDGE_ZONE {
        prev_page(i);
    } else if x > width * (1.0 - EDGE_ZONE) {
        next_page(i);
    } else if i.borrow().window.get_ui_visible() {
        set_ui(i, false);
    } else {
        poke_ui(i);
    }
}

fn close(i: &Rc<RefCell<Inner>>) {
    let id = {
        let mut s = i.borrow_mut();
        if s.closed {
            return;
        }
        s.closed = true;
        if s.count > 0 {
            pw::save_progress(&s.key, s.cur as i64 + 1);
        }
        s.hide_timer.stop();
        s.toast_timer.stop();
        s.spinner_timer.stop();
        s.tick.stop();
        s.worker.stop();
        s.cache.clear();
        s.window.set_page(Image::default());
        let _ = s.window.hide();
        s.id
    };
    super::after(0, move || {
        let c = ctx();
        c.readers.borrow_mut().retain(|r| r.0.borrow().id != id);
        OPEN_READERS.with(|n| n.set(n.get().saturating_sub(1)));
    });
    super::after(1500, crate::platform::trim_memory);
}
