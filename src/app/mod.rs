
pub mod games_ui;
pub mod music_ui;
pub mod print_ui;
pub mod reader_ui;

use std::cell::RefCell;
use std::collections::VecDeque;
use std::rc::Rc;

use slint::{ComponentHandle, Model, ModelRc, VecModel};

use crate::theme::{self, Rgb, ThemeSettings};
use crate::{AppApi, AppWindow, DialogApi, DialogButton, SettingsApi, Theme};

pub const ACCENT: i32 = 0;
pub const DANGER: i32 = 1;
pub const NEUTRAL: i32 = 2;

type Response = Box<dyn FnOnce(usize)>;

struct PendingDialog {
    heading: String,
    message: String,
    buttons: Vec<(String, i32)>,
    cancel: usize,
    on_response: Option<Response>,
}

pub struct Ctx {
    pub app: AppWindow,
    theme: RefCell<ThemeSettings>,
    dark: RefCell<bool>,
    dialogs: RefCell<VecDeque<PendingDialog>>,
    active_dialog: RefCell<Option<PendingDialog>>,
    pub games: RefCell<games_ui::GamesState>,
    pub music: RefCell<music_ui::MusicState>,
    pub print: RefCell<print_ui::PrintState>,
    pub readers: RefCell<Vec<reader_ui::Reader>>,
    timers: RefCell<Vec<slint::Timer>>,
}

thread_local! {
    static CTX: RefCell<Option<Rc<Ctx>>> = const { RefCell::new(None) };
}

pub fn ctx() -> Rc<Ctx> {
    CTX.with(|c| c.borrow().clone().expect("UI context"))
}

pub fn post(f: impl FnOnce(&Rc<Ctx>) + Send + 'static) {
    let _ = slint::invoke_from_event_loop(move || {
        if let Some(c) = CTX.with(|c| c.borrow().clone()) {
            f(&c);
        }
    });
}

pub fn after(ms: u64, f: impl FnOnce() + 'static) {
    slint::Timer::single_shot(std::time::Duration::from_millis(ms), f);
}

pub fn color(rgb: Rgb) -> slint::Color {
    let c = |v: f64| v.round().clamp(0.0, 255.0) as u8;
    slint::Color::from_rgb_u8(c(rgb[0]), c(rgb[1]), c(rgb[2]))
}

pub fn model<T: Clone + 'static>(items: Vec<T>) -> ModelRc<T> {
    ModelRc::new(VecModel::from(items))
}


impl Ctx {
    pub fn dialog(&self, heading: &str, message: &str, buttons: &[(&str, i32)], cancel: usize, on_response: Option<Response>) {
        self.dialogs.borrow_mut().push_back(PendingDialog {
            heading: heading.into(),
            message: message.into(),
            buttons: buttons.iter().map(|(t, r)| (t.to_string(), *r)).collect(),
            cancel,
            on_response,
        });
        if self.active_dialog.borrow().is_none() {
            self.next_dialog();
        }
    }

    pub fn message(&self, heading: &str, message: &str) {
        self.dialog(heading, message, &[("OK", ACCENT)], 0, None);
    }

    fn next_dialog(&self) {
        let next = self.dialogs.borrow_mut().pop_front();
        let api = self.app.global::<DialogApi>();
        match next {
            Some(d) => {
                api.set_heading(d.heading.clone().into());
                api.set_message(d.message.clone().into());
                api.set_buttons(model(
                    d.buttons.iter().map(|(t, r)| DialogButton { text: t.into(), role: *r }).collect(),
                ));
                api.set_cancel_index(d.cancel as i32);
                api.set_open(true);
                *self.active_dialog.borrow_mut() = Some(d);
            }
            None => api.set_open(false),
        }
    }

    fn respond(&self, index: usize) {
        let Some(mut d) = self.active_dialog.borrow_mut().take() else { return };
        let callback = d.on_response.take();
        self.next_dialog();
        if let Some(cb) = callback {
            after(0, move || cb(index));
        }
    }

    pub fn dialog_open(&self) -> bool {
        self.active_dialog.borrow().is_some()
    }
}


pub fn hsv_to_rgb(h: f64, s: f64, v: f64) -> Rgb {
    let h = h.rem_euclid(1.0) * 6.0;
    let (s, v) = (s.clamp(0.0, 1.0), v.clamp(0.0, 1.0));
    let i = h.floor();
    let f = h - i;
    let (p, q, t) = (v * (1.0 - s), v * (1.0 - s * f), v * (1.0 - s * (1.0 - f)));
    let (r, g, b) = match i as i32 % 6 {
        0 => (v, t, p),
        1 => (q, v, p),
        2 => (p, v, t),
        3 => (p, q, v),
        4 => (t, p, v),
        _ => (v, p, q),
    };
    [r * 255.0, g * 255.0, b * 255.0]
}

pub fn hex_to_hsv(hex: &str) -> Option<(f64, f64, f64)> {
    let hex = theme::normalize_hex(hex)?;
    if hex.len() != 7 {
        return None;
    }
    let [r, g, b] = theme::hex_rgb(&hex).map(|c| c / 255.0);
    let max = r.max(g).max(b);
    let min = r.min(g).min(b);
    let v = max;
    if max == min {
        return Some((0.0, 0.0, v));
    }
    let s = (max - min) / max;
    let rc = (max - r) / (max - min);
    let gc = (max - g) / (max - min);
    let bc = (max - b) / (max - min);
    let h = if r == max { bc - gc } else if g == max { 2.0 + rc - bc } else { 4.0 + gc - rc };
    Some(((h / 6.0).rem_euclid(1.0), s, v))
}

impl Ctx {
    pub fn is_dark(&self) -> bool {
        *self.dark.borrow()
    }

    pub fn apply_theme(&self, save: bool) {
        let settings = self.theme.borrow().clone();
        let palette = theme::manual_palette(&settings.mode, &settings.accent_color);
        let t = self.app.global::<Theme>();
        t.set_bg(color(palette.bg));
        t.set_surface(color(palette.surface));
        t.set_surface_alt(color(palette.surface_alt));
        t.set_surface_high(color(palette.surface_high));
        t.set_popover(color(palette.popover));
        t.set_fg(color(palette.fg));
        t.set_fg_dim(color(palette.fg_dim));
        t.set_fg_disabled(color(palette.fg_disabled));
        t.set_accent(color(palette.accent));
        t.set_accent_hover(color(palette.accent_hover));
        t.set_on_accent(color(palette.on_accent));
        let dark = palette.is_dark();
        t.set_dark(dark);
        *self.dark.borrow_mut() = dark;
        let s = self.app.global::<SettingsApi>();
        s.set_dark(dark);
        s.set_accent(settings.accent_color.clone().into());
        if save {
            settings.save();
        }
        music_ui::refresh_palette(self);
    }

    fn set_accent(&self, hex: &str, save: bool) {
        let Some(hex) = theme::normalize_hex(hex) else { return };
        self.theme.borrow_mut().accent_color = hex;
        self.apply_theme(save);
    }

    fn sync_picker(&self) {
        let accent = self.theme.borrow().accent_color.clone();
        let s = self.app.global::<SettingsApi>();
        if let Some((h, sat, v)) = hex_to_hsv(&accent) {
            if sat > 0.02 && v > 0.02 {
                s.set_hue(h as f32);
            }
            s.set_sat(sat as f32);
            s.set_val(v as f32);
        }
        s.set_hex_text(accent.into());
    }
}

fn setup_settings(c: &Rc<Ctx>) {
    let s = c.app.global::<SettingsApi>();
    if cfg!(windows) {
        s.set_build_title("Windows build".into());
    } else {
        let os = if cfg!(target_os = "linux") { "Linux" } else { std::env::consts::OS };
        s.set_build_title(format!("{os} build").into());
    }
    s.set_build_arch(std::env::consts::ARCH.into());
    s.set_version(env!("CARGO_PKG_VERSION").into());
    c.sync_picker();

    s.on_hsv_color(|h, sat, v| color(hsv_to_rgb(h as f64, sat as f64, v as f64)));
    s.on_close(|| {
        let c = ctx();
        let s = c.app.global::<SettingsApi>();
        s.set_picker_open(false);
        s.set_open(false);
    });
    s.on_set_dark(|dark| {
        let c = ctx();
        {
            let mut t = c.theme.borrow_mut();
            t.mode = if dark { "dark".into() } else { "light".into() };
        }
        c.apply_theme(true);
    });
    s.on_pick_preset(|hex| {
        let c = ctx();
        c.set_accent(&hex, true);
        c.sync_picker();
    });
    s.on_picker_changed(|h, sat, v, fin| {
        let c = ctx();
        let hex = theme::rgb_hex(hsv_to_rgb(h as f64, sat as f64, v as f64));
        c.app.global::<SettingsApi>().set_hex_text(hex.clone().into());
        c.set_accent(&hex, fin);
    });
    s.on_hex_entered(|text| {
        let c = ctx();
        let t = text.trim();
        let re = regex::Regex::new(r"^#?[0-9a-fA-F]{6}$").unwrap();
        if !re.is_match(t) {
            return;
        }
        c.set_accent(t, true);
        let s = c.app.global::<SettingsApi>();
        if let Some((h, sat, v)) = hex_to_hsv(t) {
            if sat > 0.02 && v > 0.02 {
                s.set_hue(h as f32);
            }
            s.set_sat(sat as f32);
            s.set_val(v as f32);
        }
    });
    s.on_open_github(|| {
        let _ = open::that_detached("https://github.com/Lyrilika/mukyu-launcher");
    });
}

fn setup_app_api(c: &Rc<Ctx>) {
    let a = c.app.global::<AppApi>();
    a.on_tab_changed(|tab| {
        let c = ctx();
        if tab == 1 {
            music_ui::on_shown(&c);
        }
    });
    a.on_escape(|| {
        let c = ctx();
        if c.dialog_open() {
            let cancel = c.active_dialog.borrow().as_ref().map(|d| d.cancel).unwrap_or(0);
            c.respond(cancel);
        } else if print_ui::download_open(&c) {
            print_ui::cancel_download(&c);
        } else if c.app.global::<SettingsApi>().get_picker_open() {
            c.app.global::<SettingsApi>().set_picker_open(false);
        } else if c.app.global::<SettingsApi>().get_open() {
            c.app.global::<SettingsApi>().invoke_close();
        } else if c.app.global::<crate::GamesApi>().get_settings_open() {
            games_ui::close_settings(&c);
        }
    });
    a.on_scrim_clicked(|| {
        let c = ctx();
        if c.dialog_open() || print_ui::download_open(&c) {
            return;
        }
        if c.app.global::<SettingsApi>().get_open() {
            c.app.global::<SettingsApi>().invoke_close();
        } else {
            games_ui::close_settings(&c);
        }
    });
    let d = c.app.global::<DialogApi>();
    d.on_response(|i| ctx().respond(i as usize));
}

#[cfg(target_os = "linux")]
fn raise_existing_instance() -> bool {
    let Some(conn) = crate::dbus::session() else { return false };
    let name = "org.mpris.MediaPlayer2.mukyulauncher";
    let owned = conn
        .call_method(Some("org.freedesktop.DBus"), "/org/freedesktop/DBus", Some("org.freedesktop.DBus"), "NameHasOwner", &(name,))
        .ok()
        .and_then(|r| r.body().deserialize::<bool>().ok())
        .unwrap_or(false);
    if !owned {
        return false;
    }
    conn.call_method(Some(name), "/org/mpris/MediaPlayer2", Some("org.mpris.MediaPlayer2"), "Raise", &()).is_ok()
}

pub fn run() -> anyhow::Result<()> {
    #[cfg(target_os = "linux")]
    if std::env::var_os("MUKYU_ALLOW_MULTIPLE").is_none() && raise_existing_instance() {
        return Ok(());
    }

    let _ = slint::BackendSelector::new()
        .with_winit_window_attributes_hook(|attrs| {
            #[cfg(target_os = "linux")]
            {
                use slint::winit_030::winit::platform::{wayland::WindowAttributesExtWayland, x11::WindowAttributesExtX11};
                let attrs = WindowAttributesExtWayland::with_name(attrs, crate::paths::APP_ID, "");
                return WindowAttributesExtX11::with_name(attrs, crate::paths::APP_ID, crate::paths::APP_ID);
            }
            #[allow(unreachable_code)]
            attrs
        })
        .select();
    let app = AppWindow::new()?;
    let settings = ThemeSettings::load();
    let c = Rc::new(Ctx {
        app,
        theme: RefCell::new(settings),
        dark: RefCell::new(true),
        dialogs: RefCell::new(VecDeque::new()),
        active_dialog: RefCell::new(None),
        games: RefCell::new(games_ui::GamesState::default()),
        music: RefCell::new(music_ui::MusicState::new()),
        print: RefCell::new(print_ui::PrintState::default()),
        readers: RefCell::new(Vec::new()),
        timers: RefCell::new(Vec::new()),
    });
    CTX.with(|cell| *cell.borrow_mut() = Some(c.clone()));

    c.apply_theme(false);
    setup_settings(&c);
    setup_app_api(&c);
    games_ui::setup(&c);
    music_ui::setup(&c);
    print_ui::setup(&c);

    after(60, || {
        let c = ctx();
        c.app.global::<crate::GamesApi>().set_appeared(true);
        c.app.global::<crate::PrintApi>().set_appeared(true);
        c.app.global::<AppApi>().set_ready(true);
    });
    #[cfg(target_os = "linux")]
    {
        let t = slint::Timer::default();
        t.start(slint::TimerMode::Repeated, std::time::Duration::from_secs(45), crate::platform::trim_memory);
        c.timers.borrow_mut().push(t);
    }

    c.app.window().on_close_requested(|| {
        let c = ctx();
        music_ui::shutdown(&c);
        for r in c.readers.borrow_mut().drain(..) {
            r.close_now();
        }
        let _ = slint::quit_event_loop();
        slint::CloseRequestResponse::HideWindow
    });

    c.app.show()?;
    music_ui::attach_media(&c);
    debug_hooks();
    slint::run_event_loop_until_quit()?;
    music_ui::shutdown(&ctx());
    Ok(())
}

fn debug_hooks() {
    let Ok(spec) = std::env::var("MUKYU_DEBUG") else { return };
    after(400, move || {
        let c = ctx();
        for item in spec.split(',') {
            let (k, v) = item.split_once(':').unwrap_or((item, ""));
            match k {
                "tab" => {
                    let t: i32 = v.parse().unwrap_or(0);
                    c.app.global::<AppApi>().set_tab(t);
                    c.app.global::<AppApi>().invoke_tab_changed(t);
                }
                "settings" => c.app.global::<SettingsApi>().set_open(true),
                "about" => {
                    c.app.global::<SettingsApi>().set_open(true);
                    c.app.global::<SettingsApi>().set_page(1);
                }
                "picker" => c.app.global::<SettingsApi>().set_picker_open(true),
                "light" => c.app.global::<SettingsApi>().invoke_set_dark(false),
                "game-settings" => {
                    let g = c.app.global::<crate::GamesApi>();
                    g.set_anchor_x(30.0);
                    g.set_anchor_y(80.0);
                    g.invoke_open_settings(v.parse().unwrap_or(5));
                }
                "dialog" => c.message("A game is already running", "Close Touhou 6 first and then launch Touhou 7?"),
                "launch" => c.app.global::<crate::GamesApi>().invoke_card_clicked(v.parse().unwrap_or(11)),
                "stop" => after(4000, || ctx().app.global::<crate::GamesApi>().invoke_stop_game()),
                "read" => c.app.global::<crate::PrintApi>().invoke_read(v.parse().unwrap_or(1)),
                "volume" => c.music.borrow_mut().debug_volume(v.parse().unwrap_or(0.0)),
                "play" => c.app.global::<crate::MusicApi>().invoke_play_pause(),
                "game" => {
                    let m = c.app.global::<crate::MusicApi>();
                    m.set_game_index(v.parse().unwrap_or(0));
                    m.invoke_game_selected(m.get_game_index());
                }
                "track" => {
                    let i: i32 = v.parse().unwrap_or(0);
                    after(2500, move || ctx().app.global::<crate::MusicApi>().invoke_track_activated(i));
                }
                "mode" => {
                    let m = c.app.global::<crate::MusicApi>();
                    m.set_mode(v.parse().unwrap_or(1));
                    m.invoke_mode_changed(m.get_mode());
                }
                _ => {}
            }
        }
    });
}

pub fn update_row<T: Clone + 'static>(m: &ModelRc<T>, index: usize, f: impl FnOnce(&mut T)) {
    if let Some(mut row) = m.row_data(index) {
        f(&mut row);
        m.set_row_data(index, row);
    }
}
