use std::rc::Rc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Instant;

use slint::{ComponentHandle, Image, ModelRc, VecModel};

use super::{ctx, post, Ctx, DANGER, NEUTRAL};
use crate::printworks::{self as pw, DownloadError, PRINTWORKS};
use crate::{DownloadApi, PrintApi, PrintWorkData};

#[derive(Default)]
pub struct PrintState {
    items: Option<ModelRc<PrintWorkData>>,
    download: Option<Download>,
}

struct Download {
    name: String,
    url: String,
    cancel: Arc<AtomicBool>,
    closed: Arc<AtomicBool>,
}

fn items(c: &Ctx) -> ModelRc<PrintWorkData> {
    c.print.borrow().items.clone().expect("print model")
}

pub fn setup(c: &Rc<Ctx>) {
    let data: Vec<PrintWorkData> = PRINTWORKS
        .iter()
        .map(|w| {
            let ongoing = w.name.ends_with(pw::ONGOING_SUFFIX);
            let chapters = pw::chapters(w.name).map(|n| if ongoing { format!("{n}-ongoing") } else { n.to_string() }).unwrap_or_default();
            PrintWorkData {
                name: w.name.into(),
                title: w.name.strip_suffix(pw::ONGOING_SUFFIX).unwrap_or(w.name).into(),
                ongoing,
                cover: Image::default(),
                loaded: false,
                year: w.year.into(),
                author: w.author.into(),
                chapters: chapters.into(),
                description: pw::description(w.name).into(),
                artist: w.artist.into(),
                downloaded: pw::is_downloaded(w.name),
            }
        })
        .collect();
    let model = ModelRc::new(VecModel::from(data));
    c.print.borrow_mut().items = Some(model.clone());
    let api = c.app.global::<PrintApi>();
    api.set_items(model);

    std::thread::Builder::new()
        .name("pw-thumbs".into())
        .spawn(|| {
            for (i, w) in PRINTWORKS.iter().enumerate() {
                let Ok(img) = image::open(pw::thumb_path(w.cover)) else { continue };
                let img = if img.width() > 360 || img.height() > 500 { img.resize(360, 500, image::imageops::FilterType::Triangle) } else { img };
                let pixels = super::games_ui::to_pixels(&img.to_rgba8());
                post(move |c| super::update_row(&items(c), i, |r| {
                    r.cover = Image::from_rgba8(pixels);
                    r.loaded = true;
                }));
            }
        })
        .ok();

    api.on_read(|i| {
        let c = ctx();
        let name = PRINTWORKS[i as usize].name;
        if pw::is_downloaded(name) {
            super::reader_ui::open(&c, name);
            return;
        }
        match pw::pdf_url(name) {
            Some(url) => open_download(&c, name, url),
            None => c.message("Not available", "This print work is not available to download yet."),
        }
    });
    api.on_delete(|i| {
        let c = ctx();
        let name = PRINTWORKS[i as usize].name;
        c.dialog(
            "Are you sure you want to delete this?",
            &format!("\"{}\" will be removed from this computer. You can download it again later.", pw::folder_name(name)),
            &[("Cancel", NEUTRAL), ("Delete", DANGER)],
            0,
            Some(Box::new(move |choice| {
                if choice == 1 {
                    pw::delete_download(name);
                    refresh_rows(&ctx());
                }
            })),
        );
    });

    let d = c.app.global::<DownloadApi>();
    d.on_cancel(|| cancel_download(&ctx()));
    d.on_action(|| {
        let c = ctx();
        let state = c.app.global::<DownloadApi>().get_state();
        match state {
            0 | 3 => start_download(&c),
            2 => {
                let name = c.print.borrow().download.as_ref().map(|d| d.name.clone());
                close_dialog(&c);
                if let Some(name) = name {
                    super::after(0, move || super::reader_ui::open(&ctx(), &name));
                }
            }
            _ => {}
        }
    });
}

pub fn refresh_rows(c: &Rc<Ctx>) {
    let m = items(c);
    for (i, w) in PRINTWORKS.iter().enumerate() {
        let d = pw::is_downloaded(w.name);
        super::update_row(&m, i, |r| r.downloaded = d);
    }
}

pub fn download_open(c: &Ctx) -> bool {
    c.app.global::<DownloadApi>().get_open()
}

fn open_download(c: &Rc<Ctx>, name: &str, url: String) {
    let closed = Arc::new(AtomicBool::new(false));
    c.print.borrow_mut().download = Some(Download {
        name: name.into(),
        url: url.clone(),
        cancel: Arc::new(AtomicBool::new(false)),
        closed: closed.clone(),
    });
    let d = c.app.global::<DownloadApi>();
    d.set_name(pw::folder_name(name).into());
    d.set_state(0);
    d.set_size_text("File size: checking…".into());
    d.set_open(true);
    std::thread::spawn(move || {
        let size = pw::fetch_size(&url);
        if !closed.load(Ordering::Relaxed) {
            post(move |c| c.app.global::<DownloadApi>().set_size_text(format!("File size: {}", crate::util::fmt_size(size)).into()));
        }
    });
}

fn close_dialog(c: &Rc<Ctx>) {
    c.app.global::<DownloadApi>().set_open(false);
    if let Some(d) = c.print.borrow().download.as_ref() {
        d.closed.store(true, Ordering::Relaxed);
    }
}

pub fn cancel_download(c: &Rc<Ctx>) {
    if let Some(d) = c.print.borrow().download.as_ref() {
        d.cancel.store(true, Ordering::Relaxed);
    }
    close_dialog(c);
}

fn start_download(c: &Rc<Ctx>) {
    let Some((name, url, closed)) = c.print.borrow().download.as_ref().map(|d| (d.name.clone(), d.url.clone(), d.closed.clone())) else {
        return;
    };
    let api = c.app.global::<DownloadApi>();
    if pw::ACTIVE.lock().unwrap().contains(&name) {
        api.set_error_text("The previous attempt is still stopping. Please try again in a moment.".into());
        api.set_state(3);
        return;
    }
    pw::ACTIVE.lock().unwrap().push(name.clone());
    let cancel = Arc::new(AtomicBool::new(false));
    if let Some(d) = c.print.borrow_mut().download.as_mut() {
        d.cancel = cancel.clone();
    }
    api.set_fraction(0.0);
    api.set_pulse(false);
    api.set_progress_text("Starting…".into());
    api.set_state(1);
    std::thread::spawn(move || {
        struct Stats {
            speed: Option<f64>,
            win_t: Option<Instant>,
            win_b: u64,
            last_ui: Option<Instant>,
        }
        let stats = Mutex::new(Stats { speed: None, win_t: None, win_b: 0, last_ui: None });
        let closed2 = closed.clone();
        let result = pw::download_pdf(&name, &url, cancel, |done, total| {
            let mut s = stats.lock().unwrap();
            let now = Instant::now();
            if s.win_t.is_none() {
                s.win_t = Some(now);
                s.win_b = 0;
            }
            let elapsed = now.duration_since(s.win_t.unwrap()).as_secs_f64();
            if elapsed >= 0.5 {
                let current = (done - s.win_b) as f64 / elapsed;
                s.speed = Some(s.speed.map_or(current, |sp| 0.6 * sp + 0.4 * current));
                s.win_t = Some(now);
                s.win_b = done;
            }
            let due = s.last_ui.map_or(true, |t| now.duration_since(t).as_secs_f64() >= 0.1) || total.map_or(false, |t| done >= t);
            if !due || closed2.load(Ordering::Relaxed) {
                return;
            }
            s.last_ui = Some(now);
            let speed = s.speed;
            post(move |c| {
                let api = c.app.global::<DownloadApi>();
                if api.get_state() != 1 {
                    return;
                }
                let speed_text = speed.map(|v| format!("{}/s", crate::util::fmt_size(Some(v as u64)))).unwrap_or_else(|| "calculating speed…".into());
                match total {
                    Some(t) => {
                        api.set_pulse(false);
                        api.set_fraction((done as f64 / t as f64).min(1.0) as f32);
                        api.set_progress_text(
                            format!(
                                "{} of {}  ({}%)  ·  {speed_text}",
                                crate::util::fmt_size(Some(done)),
                                crate::util::fmt_size(Some(t)),
                                done * 100 / t.max(1)
                            )
                            .into(),
                        );
                    }
                    None => {
                        api.set_pulse(true);
                        api.set_progress_text(format!("{}  ·  {speed_text}", crate::util::fmt_size(Some(done))).into());
                    }
                }
            });
        });
        pw::ACTIVE.lock().unwrap().retain(|n| n != &name);
        post(move |c| {
            match result {
                Ok(()) => {
                    refresh_rows(c);
                    if !closed.load(Ordering::Relaxed) {
                        c.app.global::<DownloadApi>().set_state(2);
                    }
                }
                Err(DownloadError::Cancelled) => {}
                Err(DownloadError::Failed(msg)) => {
                    if !closed.load(Ordering::Relaxed) {
                        let api = c.app.global::<DownloadApi>();
                        api.set_error_text(msg.into());
                        api.set_state(3);
                    }
                }
            }
        });
    });
}
