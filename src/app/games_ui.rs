use std::io::BufRead;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::rc::Rc;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use slint::{ComponentHandle, Image, Model, ModelRc, Rgba8Pixel, SharedPixelBuffer, VecModel};

use super::{ctx, post, Ctx, ACCENT, NEUTRAL};
use crate::filepicker::{self, Picked};
use crate::games::{self, GameConfig, GameEntry, LaunchError, GAMES};
use crate::platform::{self, GameProcess};
use crate::{GameCardData, GamesApi};

pub struct Running {
    proc: GameProcess,
    key: String,
    title: String,
    start: Instant,
    proton: bool,
    lines: Arc<Mutex<Vec<String>>>,
    reported: bool,
}

#[derive(Default)]
pub struct GamesState {
    pub config: GameConfig,
    last_picker_dir: Option<PathBuf>,
    running: Option<Running>,
    cards: Option<ModelRc<GameCardData>>,
    timers: Vec<slint::Timer>,
    runner_ids: Vec<String>,
}

impl GamesState {
    fn picker_start_dir(&self, key: &str) -> Option<&Path> {
        self.config
            .get(key)
            .and_then(|entry| entry.exe.as_deref())
            .and_then(|exe| Path::new(exe).parent())
            .filter(|dir| dir.is_dir())
            .or_else(|| self.last_picker_dir.as_deref().filter(|dir| dir.is_dir()))
    }
}

fn picker_directory_file() -> PathBuf {
    crate::paths::config_dir().join("game_picker_directory.json")
}

const COVER_PX: u32 = 350;

pub type Pixels = SharedPixelBuffer<Rgba8Pixel>;

pub fn decode_scaled(path: &Path, max_short: u32) -> Option<image::RgbaImage> {
    let img = image::open(path).ok()?;
    let (w, h) = (img.width(), img.height());
    let ratio = (max_short as f64 / w.min(h) as f64).min(1.0);
    let img = if ratio < 1.0 {
        img.resize_exact(((w as f64 * ratio).round() as u32).max(1), ((h as f64 * ratio).round() as u32).max(1), image::imageops::FilterType::Triangle)
    } else {
        img
    };
    Some(img.to_rgba8())
}

pub fn to_pixels(img: &image::RgbaImage) -> Pixels {
    SharedPixelBuffer::clone_from_slice(img.as_raw(), img.width(), img.height())
}

fn grayscale(img: &image::RgbaImage) -> image::RgbaImage {
    let mut out = img.clone();
    for p in out.pixels_mut() {
        let [r, g, b, a] = p.0;
        let l = 0.2126 * r as f32 + 0.7152 * g as f32 + 0.0722 * b as f32;
        let m = |c: u8| ((c as f32 * 0.15 + l * 0.85) * 0.8).round().clamp(0.0, 255.0) as u8;
        p.0 = [m(r), m(g), m(b), a];
    }
    out
}

fn refresh_any_unset(c: &Ctx) {
    let m = cards(c);
    let any = (0..m.row_count()).any(|i| m.row_data(i).map_or(false, |r| !r.has_exe));
    c.app.global::<GamesApi>().set_any_unset(any);
}

fn cards(c: &Ctx) -> ModelRc<GameCardData> {
    c.games.borrow().cards.clone().expect("cards model")
}

fn index_of(key: &str) -> Option<usize> {
    GAMES.iter().position(|g| g.key == key)
}

pub fn setup(c: &Rc<Ctx>) {
    let config = games::load_config();
    let data: Vec<GameCardData> = GAMES
        .iter()
        .map(|g| GameCardData {
            key: g.key.into(),
            title: g.title.into(),
            cover: Image::default(),
            gray: Image::default(),
            loaded: false,
            has_exe: config.get(g.key).map_or(false, GameEntry::exe_exists),
        })
        .collect();
    let model = ModelRc::new(VecModel::from(data));
    {
        let mut g = c.games.borrow_mut();
        g.config = config;
        g.last_picker_dir = crate::util::read_json(&picker_directory_file());
        g.cards = Some(model.clone());
    }
    let api = c.app.global::<GamesApi>();
    api.set_cards(model);
    api.set_windows(cfg!(windows));
    if cfg!(target_os = "linux") && !games::NO_GE_PROTON {
        let _ = std::fs::create_dir_all(games::runner_directory());
    }
    api.set_ge_available(games::MANAGED_AVAILABLE);
    api.set_managed_runner(games::MANAGED_NAME.into());
    refresh_any_unset(c);

    let next = Arc::new(std::sync::atomic::AtomicUsize::new(0));
    for _ in 0..4 {
        let next = next.clone();
        std::thread::Builder::new()
            .name("cover-loader".into())
            .spawn(move || loop {
                let i = next.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                let Some(g) = GAMES.get(i) else { break };
                let Some(img) = decode_scaled(&crate::paths::cover_path(g.cover), COVER_PX) else { continue };
                let (color, gray) = (to_pixels(&img), to_pixels(&grayscale(&img)));
                post(move |c| {
                    super::update_row(&cards(c), i, |row| {
                        row.cover = Image::from_rgba8(color);
                        row.gray = Image::from_rgba8(gray);
                        row.loaded = true;
                    });
                });
            })
            .ok();
    }

    api.on_card_clicked(|i| {
        let c = ctx();
        let key = GAMES[i as usize].key;
        let entry = c.games.borrow().config.get(key).cloned().unwrap_or_default();
        if entry.exe_exists() {
            launch(&c, i as usize);
        } else {
            prompt_for_exe(&c, i as usize);
        }
    });
    api.on_open_settings(|i| open_settings(&ctx(), i as usize));
    api.on_close_settings(|| close_settings(&ctx()));
    api.on_runner_changed(|i| {
        let c = ctx();
        persist(&c);
        let picked = c.games.borrow().runner_ids.get(i as usize).cloned().unwrap_or_default();
        if picked == games::MANAGED_RUNNER && !games::managed_installed() {
            c.app.global::<GamesApi>().set_ge_status(format!("{} is not installed yet.", games::MANAGED_NAME).into());
        }
    });
    api.on_options_committed(|_| persist(&ctx()));
    api.on_change_exe(|| {
        let c = ctx();
        let i = c.app.global::<GamesApi>().get_settings_index();
        if i < 0 {
            return;
        }
        persist(&c);
        close_settings(&c);
        prompt_for_exe(&c, i as usize);
    });
    api.on_remove_exe(|| {
        let c = ctx();
        let i = c.app.global::<GamesApi>().get_settings_index();
        if i < 0 {
            return;
        }
        let key = GAMES[i as usize].key;
        {
            let mut g = c.games.borrow_mut();
            let entry = g.config.entry(key.to_string()).or_default();
            entry.exe = None;
            if games::is_pc98(key) {
                entry.runner = "dosbox-x".into();
            }
            games::save_config(&g.config);
        }
        super::update_row(&cards(&c), i as usize, |r| r.has_exe = false);
        refresh_any_unset(&c);
        let api = c.app.global::<GamesApi>();
        api.set_settings_open(false);
        super::music_ui::config_changed(&c);
    });
    api.on_download_ge(|| download_ge(&ctx()));
    api.on_download_dosbox(|| {
        let c = ctx();
        c.app.global::<GamesApi>().set_dosbox_status("Downloading DOSBox-X...".into());
        std::thread::spawn(|| {
            let result = games::install_dosbox(|text| post(move |c| c.app.global::<GamesApi>().set_dosbox_status(text.into())));
            if let Err(e) = result {
                let text = format!("Install failed: {e}");
                post(move |c| c.app.global::<GamesApi>().set_dosbox_status(text.into()));
            }
        });
    });
    api.on_stop_game(|| stop_game(&ctx()));
}

fn ge_status_text() -> String {
    if games::managed_installed() {
        format!("{}: installed", games::MANAGED_NAME)
    } else {
        format!("{}: not downloaded", games::MANAGED_NAME)
    }
}

fn open_settings(c: &Rc<Ctx>, i: usize) {
    let info = &GAMES[i];
    let entry = c.games.borrow().config.get(info.key).cloned().unwrap_or_default();
    let api = c.app.global::<GamesApi>();
    api.set_settings_index(i as i32);
    api.set_settings_title(info.title.into());
    api.set_playtime(games::playtime_text(info.key).into());
    let pc98 = entry.runner == "dosbox-x" || games::is_pc98(info.key);
    api.set_pc98(pc98);
    let options = games::runner_options();
    let current = games::effective_runner(&entry.runner);
    let index = options.iter().position(|(id, _)| *id == current).unwrap_or(0);
    let mut items: Vec<crate::MenuItem> = options.iter().map(|(_, label)| crate::MenuItem { text: label.into(), enabled: true }).collect();
    if items.is_empty() {
        items.push(crate::MenuItem { text: "No runners installed".into(), enabled: false });
    }
    api.set_runner_items(ModelRc::new(VecModel::from(items)));
    api.set_runner(index as i32);
    c.games.borrow_mut().runner_ids = options.into_iter().map(|(id, _)| id).collect();
    if !api.get_ge_busy() {
        api.set_ge_status(ge_status_text().into());
        api.set_ge_progress_visible(false);
    }
    api.set_exe_set(entry.exe.as_deref().map_or(false, |e| !e.is_empty()));
    api.set_exe_exists(entry.exe_exists());
    api.set_launch_options(entry.launch_options.clone().into());
    api.set_dosbox_status(
        if games::dosbox_path().is_some() { "DOSBox-X installed" } else { "DOSBox-X not installed" }.into(),
    );
    api.set_settings_open(true);
}

fn persist(c: &Rc<Ctx>) {
    let api = c.app.global::<GamesApi>();
    let i = api.get_settings_index();
    if i < 0 || api.get_pc98() {
        return;
    }
    let key = GAMES[i as usize].key;
    let mut g = c.games.borrow_mut();
    let runner = g.runner_ids.get(api.get_runner().max(0) as usize).cloned().unwrap_or_else(games::default_runner);
    let entry = g.config.entry(key.to_string()).or_default();
    entry.launch_options = api.get_launch_options().to_string();
    entry.runner = runner;
    games::save_config(&g.config);
}

pub fn close_settings(c: &Rc<Ctx>) {
    let api = c.app.global::<GamesApi>();
    if !api.get_settings_open() {
        return;
    }
    persist(c);
    api.set_settings_open(false);
}

fn download_ge(c: &Rc<Ctx>) {
    let api = c.app.global::<GamesApi>();
    api.set_ge_busy(true);
    api.set_ge_status(format!("{}: checking for latest release…", games::MANAGED_NAME).into());
    api.set_ge_progress(0.0);
    api.set_ge_progress_text("0%".into());
    api.set_ge_progress_failed(false);
    api.set_ge_progress_visible(true);
    std::thread::spawn(|| {
        let last = Arc::new(Mutex::new(Instant::now() - Duration::from_secs(1)));
        let result = games::install_latest_managed(move |pct| {
            let mut l = last.lock().unwrap();
            if pct != Some(100) && pct != Some(0) && l.elapsed() < Duration::from_millis(80) {
                return;
            }
            *l = Instant::now();
            post(move |c| {
                let api = c.app.global::<GamesApi>();
                match pct {
                    None => {
                        api.set_ge_status(format!("{}: downloading…", games::MANAGED_NAME).into());
                        api.set_ge_progress_text("Downloading…".into());
                    }
                    Some(p) => {
                        api.set_ge_status(format!("{}: downloading… {p}%", games::MANAGED_NAME).into());
                        api.set_ge_progress(p as f32 / 100.0);
                        api.set_ge_progress_text(format!("{p}%").into());
                    }
                }
            });
        });
        post(move |c| {
            let api = c.app.global::<GamesApi>();
            api.set_ge_busy(false);
            match result {
                Ok(()) => {
                    api.set_ge_progress(1.0);
                    api.set_ge_progress_text("100%".into());
                    api.set_ge_status(ge_status_text().into());
                }
                Err(e) => {
                    api.set_ge_progress_text("Failed".into());
                    api.set_ge_progress_failed(true);
                    api.set_ge_status(format!("{}: download failed — {e}", games::MANAGED_NAME).into());
                }
            }
        });
    });
}

fn prompt_for_exe(c: &Rc<Ctx>, i: usize) {
    let info = &GAMES[i];
    let pc98 = games::is_pc98(info.key);
    let start_dir = c.games.borrow().picker_start_dir(info.key).map(Path::to_path_buf);
    let title = if pc98 { format!("Select ROM for {}", info.title) } else { format!("Select EXE for {}", info.title) };
    std::thread::spawn(move || {
        let (patterns, filter): (&[&str], &str) = if pc98 {
            (&["*.hdi", "*.nhd", "*.fdi", "*.img", "*.d88"], "PC-98 ROM images")
        } else {
            (&["*.exe"], "Executable files")
        };
        let picked = filepicker::pick_blocking(&title, patterns, filter, start_dir.as_deref());
        post(move |c| match picked {
            Picked::File(path) => exe_picked(c, i, path),
            Picked::Cancelled => {}
            Picked::Unavailable => c.message(
                "No file chooser available",
                if cfg!(windows) {
                    "The Windows file dialog could not be opened."
                } else {
                    "Mukyu Launcher uses your desktop's file chooser. Install xdg-desktop-portal (with a backend for your desktop), or zenity / kdialog, and try again."
                },
            ),
        });
    });
}

fn exe_picked(c: &Rc<Ctx>, i: usize, path: PathBuf) {
    let key = GAMES[i].key;
    {
        let mut g = c.games.borrow_mut();
        let entry = g.config.entry(key.to_string()).or_default();
        entry.exe = Some(path.display().to_string());
        if games::is_pc98(key) {
            entry.runner = "dosbox-x".into();
        }
        games::save_config(&g.config);
        if let Some(dir) = path.parent().filter(|dir| dir.is_dir()) {
            g.last_picker_dir = Some(dir.to_path_buf());
            let _ = crate::util::write_json_atomic(&picker_directory_file(), dir);
        }
    }
    super::update_row(&cards(c), i, |r| r.has_exe = true);
    refresh_any_unset(c);
    super::music_ui::config_changed(c);
}


fn running_alive(c: &Rc<Ctx>) -> bool {
    c.games.borrow_mut().running.as_mut().map_or(false, |r| r.proc.alive())
}

fn launch(c: &Rc<Ctx>, i: usize) {
    let info = &GAMES[i];
    let entry = c.games.borrow().config.get(info.key).cloned().unwrap_or_default();
    let Some(exe) = entry.exe.clone() else { return };
    let runner = if games::is_pc98(info.key) {
        "dosbox-x".to_string()
    } else if cfg!(windows) {
        "wine".to_string()
    } else {
        games::effective_runner(&entry.runner)
    };

    if running_alive(c) {
        let (current_title, same) = {
            let g = c.games.borrow();
            let r = g.running.as_ref().unwrap();
            (r.title.clone(), r.key == info.key)
        };
        let (heading, message, confirm) = if same {
            ("This game is already running".to_string(), format!("{} is already running.", info.title), "Close & Relaunch")
        } else {
            ("A game is already running".to_string(), format!("Close {current_title} first and then launch {}?", info.title), "Close Current Game")
        };
        c.dialog(
            &heading,
            &message,
            &[(confirm, ACCENT), ("Cancel", NEUTRAL)],
            1,
            Some(Box::new(move |choice| {
                if choice == 0 {
                    stop_then(&ctx(), Box::new(move || launch(&ctx(), i)));
                }
            })),
        );
        return;
    }
    let proton_missing = |c: &Rc<Ctx>| {
        c.dialog(
            &format!("{} is not installed", games::MANAGED_NAME),
            &format!("Download {0} from the settings for {1} before launching this game with {0}.", games::MANAGED_NAME, info.title),
            &[("OK", ACCENT)],
            0,
            None,
        )
    };
    let dosbox_missing = |c: &Rc<Ctx>| {
        c.dialog(
            "DOSBox-X is not installed",
            "Use the Download DOSBox-X button in the settings, or manually install DOSBox-X and restart the app.",
            &[("OK", ACCENT)],
            0,
            None,
        )
    };
    let steam_app = if games::is_pc98(info.key) { None } else { games::steam_app_id(Path::new(&exe)) };
    if steam_app.is_none() && runner == games::MANAGED_RUNNER && !games::managed_installed() {
        return proton_missing(c);
    }
    let plan = if let Some(app_id) = steam_app {
        games::LaunchPlan { command: games::steam_launch_command(app_id), env: vec![] }
    } else {
        match games::build_launch_command(&exe, &entry.launch_options, &runner, info.key) {
        Ok(p) => p,
        Err(LaunchError::DosboxMissing) => return dosbox_missing(c),
        Err(LaunchError::ProtonMissing) => return proton_missing(c),
        Err(LaunchError::BadPath) => {
            return c.message("Unsupported file name", "Rename the disk image so its path contains no double quotes (\"), then select it again.")
        }
        }
    };
    if plan.command.is_empty() {
        return;
    }
    let session = format!("{:016x}", rand::random::<u64>());
    let game_dir = Path::new(&exe).parent().map(Path::to_path_buf).unwrap_or_default();
    let proton = steam_app.is_none() && games::is_proton_runner(&runner);
    let mut cmd = Command::new(&plan.command[0]);
    cmd.args(&plan.command[1..]);
    cmd.env_clear().envs(platform::host_env()).envs(plan.env.iter().cloned());
    cmd.env(platform::SESSION_ENV_VAR, &session);
    if game_dir.is_dir() {
        cmd.current_dir(&game_dir);
    }
    cmd.stdin(Stdio::null());
    if proton {
        cmd.stdout(Stdio::piped()).stderr(Stdio::piped());
    } else if cfg!(windows) {
        cmd.stdout(Stdio::null()).stderr(Stdio::null());
    } else if let Some(log) = games::open_launch_log(&plan.command, &runner, info.key) {
        match log.try_clone() {
            Ok(err) => {
                cmd.stdout(log).stderr(err);
            }
            Err(_) => {
                cmd.stdout(log);
            }
        }
    }
    if steam_app.is_some() {
        platform::no_window(&mut cmd);
    }
    platform::detach(&mut cmd);
    let mut child = match cmd.spawn() {
        Ok(child) => child,
        Err(e) => {
            let mut detail = e.to_string();
            if e.raw_os_error() == Some(740) {
                detail = "This game needs administrator rights. Start the launcher as administrator, or turn off \"Run this program as an administrator\" in the game's .exe Properties > Compatibility.".into();
            }
            if !cfg!(windows) {
                if let Some(mut log) = games::open_launch_log(&plan.command, &runner, info.key) {
                    use std::io::Write;
                    let _ = writeln!(log, "Could not start: {e}");
                }
            }
            c.dialog(&format!("Could not start {}", info.title), &detail, &[("OK", ACCENT)], 0, None);
            return;
        }
    };
    let lines = Arc::new(Mutex::new(Vec::new()));
    if proton {
        let mut log = games::open_launch_log(&plan.command, &runner, info.key);
        let (out, err) = (child.stdout.take(), child.stderr.take());
        let (tx, rx) = std::sync::mpsc::channel::<String>();
        for stream in [out.map(|s| Box::new(s) as Box<dyn std::io::Read + Send>), err.map(|s| Box::new(s) as Box<dyn std::io::Read + Send>)]
            .into_iter()
            .flatten()
        {
            let tx = tx.clone();
            std::thread::spawn(move || {
                for line in std::io::BufReader::new(stream).lines().map_while(Result::ok) {
                    if tx.send(line).is_err() {
                        break;
                    }
                }
            });
        }
        drop(tx);
        let lines = lines.clone();
        std::thread::spawn(move || {
            let ansi = regex::Regex::new(r"\x1b\[[0-9;]*m").unwrap();
            for raw in rx {
                if let Some(log) = log.as_mut() {
                    use std::io::Write;
                    let _ = writeln!(log, "{raw}");
                }
                let clean = ansi.replace_all(&raw, "").trim().to_string();
                if !clean.is_empty() {
                    let mut l = lines.lock().unwrap();
                    l.push(clean);
                    let n = l.len();
                    if n > 6 {
                        l.drain(..n - 6);
                    }
                }
            }
        });
    }
    let running = Running {
        proc: match steam_app {
            Some(app_id) => GameProcess::new(child, session)
                .watching(Path::new(&exe).parent().map(Path::to_path_buf).unwrap_or_default(), app_id),
            None => GameProcess::new(child, session),
        },
        key: info.key.into(),
        title: info.title.into(),
        start: Instant::now(),
        proton,
        lines,
        reported: false,
    };
    c.games.borrow_mut().running = Some(running);
    let api = c.app.global::<GamesApi>();
    api.set_running_key(info.key.into());
    api.set_running_title(info.title.into());
    api.set_running_time("0:00".into());
    api.set_running_visible(true);

    let poll = slint::Timer::default();
    poll.start(slint::TimerMode::Repeated, Duration::from_millis(250), || poll_running(&ctx()));
    let tick = slint::Timer::default();
    tick.start(slint::TimerMode::Repeated, Duration::from_secs(1), || {
        let c = ctx();
        let secs = c.games.borrow().running.as_ref().map(|r| r.start.elapsed().as_secs());
        if let Some(s) = secs {
            c.app.global::<GamesApi>().set_running_time(crate::util::fmt_session(s).into());
        }
    });
    c.games.borrow_mut().timers = vec![poll, tick];
}

fn check_proton_error(c: &Rc<Ctx>) {
    let report = {
        let mut g = c.games.borrow_mut();
        let Some(r) = g.running.as_mut() else { return };
        match (r.proton, r.proc.exit_status, r.proc.stopping, r.reported) {
            (true, Some(code), false, false) if code != 0 => {
                r.reported = true;
                Some((code, r.lines.lock().unwrap().join("\n")))
            }
            _ => None,
        }
    };
    if let Some((code, details)) = report {
        let details: String = details.chars().rev().take(2000).collect::<Vec<_>>().into_iter().rev().collect();
        c.dialog(
            "GE-Proton error",
            &format!("GE-Proton exited with code {code}.\n\n{details}\n\nFull log: {}", games::launch_log_path().display()),
            &[("OK", ACCENT)],
            0,
            None,
        );
    }
}

fn poll_running(c: &Rc<Ctx>) {
    let alive = running_alive(c);
    check_proton_error(c);
    if !alive {
        finish_running(c);
    }
}

fn finish_running(c: &Rc<Ctx>) {
    let (finished, timers) = {
        let mut g = c.games.borrow_mut();
        (g.running.take(), std::mem::take(&mut g.timers))
    };
    super::after(0, move || drop(timers));
    if let Some(r) = finished {
        games::add_playtime(&r.key, r.start.elapsed().as_secs());
    }
    let api = c.app.global::<GamesApi>();
    api.set_running_visible(false);
    super::after(400, || {
        let c = ctx();
        if c.games.borrow().running.is_none() {
            c.app.global::<GamesApi>().set_running_key("".into());
        }
    });
}

fn stop_game(c: &Rc<Ctx>) {
    {
        let mut g = c.games.borrow_mut();
        let Some(r) = g.running.as_mut() else { return };
        r.proc.snapshot_tree();
        r.proc.signal(false);
    }
    let started = Instant::now();
    let t = slint::Timer::default();
    t.start(slint::TimerMode::Repeated, Duration::from_millis(100), move || {
        let c = ctx();
        if c.games.borrow().running.is_none() {
            return;
        }
        if !running_alive(&c) {
            finish_running(&c);
        } else if started.elapsed() >= Duration::from_millis(1000) {
            if let Some(r) = c.games.borrow_mut().running.as_mut() {
                r.proc.signal(true);
            }
            finish_running(&c);
        }
    });
    c.games.borrow_mut().timers.push(t);
}

fn stop_then(c: &Rc<Ctx>, then: Box<dyn FnOnce()>) {
    if c.games.borrow().running.is_none() {
        return then();
    }
    if let Some(r) = c.games.borrow_mut().running.as_mut() {
        r.proc.signal(false);
    }
    let started = Instant::now();
    let then = std::cell::RefCell::new(Some(then));
    let t = slint::Timer::default();
    t.start(slint::TimerMode::Repeated, Duration::from_millis(100), move || {
        let c = ctx();
        let done = !running_alive(&c) || started.elapsed() >= Duration::from_millis(1500);
        if !done {
            return;
        }
        if running_alive(&c) {
            if let Some(r) = c.games.borrow_mut().running.as_mut() {
                r.proc.signal(true);
            }
        }
        finish_running(&c);
        if let Some(f) = then.borrow_mut().take() {
            super::after(0, f);
        }
    });
    c.games.borrow_mut().timers.push(t);
}

#[allow(dead_code)]
fn card_index(key: &str) -> Option<usize> {
    index_of(key)
}

#[allow(dead_code)]
fn cards_len(c: &Ctx) -> usize {
    cards(c).row_count()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unassigned_game_uses_the_last_picker_directory() {
        let dir = std::env::current_dir().unwrap();
        let state = GamesState {
            last_picker_dir: Some(dir.clone()),
            ..Default::default()
        };

        assert_eq!(state.picker_start_dir("th06"), Some(dir.as_path()));
    }
}
