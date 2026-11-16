use std::collections::{HashMap, HashSet, VecDeque};
use std::path::PathBuf;
use std::rc::Rc;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use rand::seq::SliceRandom;
use slint::{ComponentHandle, Image, Rgba8Pixel, SharedPixelBuffer};

use super::{ctx, model, post, Ctx};
use crate::media::{self, Backend, MediaCommand, MediaState};
use crate::music::bgm::{self, AssignedGame};
use crate::music::engine::{Engine, Input, Playback, State};
use crate::music::radio::{self, NowPlaying};
use crate::music::{pc98, titles, GameTrack, Source};
use crate::theme::{self, Rgb};
use crate::util::fmt_time;
use crate::{AppApi, MenuItem, MusicApi, TrackRow};

const COVER_PX: u32 = 800;
const METADATA_INTERVAL: Duration = Duration::from_secs(10);
const RECONNECT_MS: u64 = 2500;
const PREPARED_CACHE_BYTES: u64 = 256 * 1024 * 1024;
const TRACK_PREFIX: &str = "/com/github/Lyrilika/MukyuLauncher/track/";

#[derive(PartialEq, Clone, Copy)]
enum Mode {
    Game,
    Radio,
}

pub struct MusicState {
    engine: Option<Result<Engine, String>>,
    playback: Option<Playback>,
    mode: Mode,
    playing: bool,
    volume: f64,
    now: NowPlaying,
    metadata_gen: u64,
    metadata_in_flight: bool,
    metadata_failures: u32,
    last_metadata: Option<Instant>,
    poll_skip: u32,
    song_end_timer: Option<slint::Timer>,
    reconnect_timer: Option<slint::Timer>,
    art_gen: u64,
    last_art_url: Option<String>,
    local_art_key: Option<String>,
    art_rgb: Option<Rgb>,
    art_file: Option<PathBuf>,
    assigned: Vec<AssignedGame>,
    tracks: HashMap<String, Vec<GameTrack>>,
    selected_game: Option<String>,
    selected: Option<GameTrack>,
    favorites: HashSet<String>,
    favorites_view: bool,
    shuffle: bool,
    repeat: u8,
    language: String,
    scratch: PathBuf,
    prepared: Vec<(String, PathBuf)>,
    preparing: Option<String>,
    mode_gen: u64,
    scan_queue: Arc<Mutex<(VecDeque<AssignedGame>, bool)>>,
    scanning: HashSet<String>,
    shown_list: Vec<String>,
    intro_done: bool,
    status: String,
    media: Option<Box<dyn Backend>>,
    media_shared: media::SharedState,
    last_position: f64,
    loader_timer: Option<slint::Timer>,
    timers: Vec<slint::Timer>,
    closed: bool,
}

impl MusicState {
    pub fn new() -> Self {
        let scratch = private_temp_dir();
        MusicState {
            engine: None,
            playback: None,
            mode: Mode::Game,
            playing: false,
            volume: 1.0,
            now: NowPlaying::default(),
            metadata_gen: 0,
            metadata_in_flight: false,
            metadata_failures: 0,
            last_metadata: None,
            poll_skip: 0,
            song_end_timer: None,
            reconnect_timer: None,
            art_gen: 0,
            last_art_url: None,
            local_art_key: None,
            art_rgb: None,
            art_file: None,
            assigned: Vec::new(),
            tracks: HashMap::new(),
            selected_game: None,
            selected: None,
            favorites: load_favorites(),
            favorites_view: false,
            shuffle: false,
            repeat: 0,
            language: titles::load_title_language(),
            scratch,
            prepared: Vec::new(),
            preparing: None,
            mode_gen: 0,
            scan_queue: Arc::new(Mutex::new((VecDeque::new(), false))),
            scanning: HashSet::new(),
            shown_list: Vec::new(),
            intro_done: false,
            status: "Stopped".into(),
            media: None,
            media_shared: Arc::default(),
            last_position: 0.0,
            loader_timer: None,
            timers: Vec::new(),
            closed: false,
        }
    }
}

impl MusicState {
    pub fn debug_volume(&mut self, v: f64) {
        self.volume = v;
    }
}

fn private_temp_dir() -> PathBuf {
    for _ in 0..16 {
        let dir = std::env::temp_dir().join(format!("mukyulauncher-bgm-{:016x}", rand::random::<u64>()));
        let mut builder = std::fs::DirBuilder::new();
        #[cfg(unix)]
        std::os::unix::fs::DirBuilderExt::mode(&mut builder, 0o700);
        if builder.create(&dir).is_ok() {
            return dir;
        }
    }
    crate::paths::cache_dir().join("bgm-scratch")
}

fn favorites_file() -> PathBuf {
    crate::paths::config_dir().join("music_favorites.json")
}

fn load_favorites() -> HashSet<String> {
    match crate::util::read_json::<serde_json::Value>(&favorites_file()) {
        Some(serde_json::Value::Array(a)) => a.iter().map(|v| v.as_str().map(String::from).unwrap_or_else(|| v.to_string())).collect(),
        Some(serde_json::Value::Object(m)) => m.iter().filter(|(_, v)| v.as_bool().unwrap_or(!v.is_null())).map(|(k, _)| k.clone()).collect(),
        _ => HashSet::new(),
    }
}

fn save_favorites(f: &HashSet<String>) {
    let mut v: Vec<&String> = f.iter().collect();
    v.sort();
    let _ = crate::util::write_json_atomic(&favorites_file(), &v);
}

fn api(c: &Ctx) -> MusicApi<'_> {
    c.app.global::<MusicApi>()
}


pub fn setup(c: &Rc<Ctx>) {
    let a = api(c);
    a.set_language(if c.music.borrow().language == "ja" { 1 } else { 0 });
    set_game_defaults(c);
    refresh_palette(c);

    a.on_mode_changed(|i| mode_changed(&ctx(), if i == 0 { Mode::Game } else { Mode::Radio }));
    a.on_game_selected(|i| game_selected(&ctx(), i as usize));
    a.on_language_changed(|i| {
        let c = ctx();
        let lang = if i == 1 { "ja" } else { "en" };
        c.music.borrow_mut().language = lang.into();
        render_list(&c, true);
        let track = c.music.borrow().selected.clone();
        if let (Some(t), true) = (track, c.music.borrow().mode == Mode::Game) {
            api(&c).set_title(t.display_title(lang).into());
        }
        media_changed(&c);
        if titles::save_title_language(lang).is_err() {
            set_error(&c, "Could not save the song title language preference.");
        }
    });
    a.on_favorites_clicked(|| {
        let c = ctx();
        let view = !c.music.borrow().favorites_view;
        c.music.borrow_mut().favorites_view = view;
        api(&c).set_favorites_view(view);
        render_list(&c, false);
        api(&c).set_list_gen(api(&c).get_list_gen() + 1);
        media_changed(&c);
    });
    a.on_track_activated(|i| {
        let c = ctx();
        let list = current_list(&c);
        if let Some(t) = list.get(i as usize).cloned() {
            select_and_play(&c, t);
        }
    });
    a.on_favorite_toggled(|i, on| {
        let c = ctx();
        let list = current_list(&c);
        let Some(t) = list.get(i as usize) else { return };
        {
            let mut m = c.music.borrow_mut();
            if on {
                m.favorites.insert(t.id.clone());
            } else {
                m.favorites.remove(&t.id);
            }
            save_favorites(&m.favorites);
        }
        if c.music.borrow().favorites_view {
            render_list(&c, false);
        } else {
            super::update_row(&api(&c).get_tracks(), i as usize, |r| r.favorite = on);
        }
        update_favorites_nav(&c);
        media_changed(&c);
    });
    a.on_play_pause(|| play_pause(&ctx()));
    a.on_previous(|| previous(&ctx()));
    a.on_next(|| {
        let c = ctx();
        if c.music.borrow().mode == Mode::Game {
            advance(&c, false);
        }
    });
    a.on_shuffle_clicked(|| {
        let c = ctx();
        if c.music.borrow().mode != Mode::Game {
            return;
        }
        let on = !c.music.borrow().shuffle;
        c.music.borrow_mut().shuffle = on;
        api(&c).set_shuffle(on);
        media_changed(&c);
    });
    a.on_repeat_clicked(|| {
        let c = ctx();
        let r = c.music.borrow().repeat;
        set_repeat(&c, if r != 0 { 0 } else { 2 });
    });
    a.on_seek(|frac| {
        let c = ctx();
        let dur = c.music.borrow().selected.as_ref().map(|t| t.duration).unwrap_or(0.0);
        seek_to(&c, frac as f64 * dur, true);
    });

    let ticker = slint::Timer::default();
    ticker.start(slint::TimerMode::Repeated, Duration::from_millis(150), || tick(&ctx()));
    let meta = slint::Timer::default();
    meta.start(slint::TimerMode::Repeated, METADATA_INTERVAL, || poll_now_playing(&ctx(), false));
    c.music.borrow_mut().timers = vec![ticker, meta];
    refresh_assigned(c, false);
}

pub fn on_shown(c: &Rc<Ctx>) {
    let first = !c.music.borrow().intro_done;
    c.music.borrow_mut().intro_done = true;
    if first {
        super::after(30, || api(&ctx()).set_intro(true));
    }
    ensure_engine(c);
    refresh_assigned(c, false);
    if c.music.borrow().mode == Mode::Radio {
        let stale = c.music.borrow().last_metadata.map_or(true, |t| t.elapsed() >= METADATA_INTERVAL);
        if stale {
            c.music.borrow_mut().poll_skip = 0;
            poll_now_playing(c, true);
        }
    }
}

fn page_visible(c: &Ctx) -> bool {
    c.app.global::<AppApi>().get_tab() == 1
}

fn ensure_engine(c: &Rc<Ctx>) -> bool {
    let missing = c.music.borrow().engine.is_none();
    if missing {
        let engine = Engine::new().map_err(|e| e.to_string());
        if let Err(e) = &engine {
            set_error(c, &format!("Audio output is unavailable: {e}"));
        }
        c.music.borrow_mut().engine = Some(engine);
    }
    matches!(c.music.borrow().engine, Some(Ok(_)))
}


pub fn refresh_palette(c: &Ctx) {
    let rgb = c.music.borrow().art_rgb;
    let dark = c.is_dark();
    let p = match rgb {
        Some(rgb) => theme::music_palette(rgb, dark),
        None => theme::music_palette_from_hue(0.86, dark),
    };
    let t = c.app.global::<crate::Theme>();
    use super::color;
    t.set_mu_primary(color(p.primary));
    t.set_mu_on_primary(color(p.on_primary));
    t.set_mu_primary_container(color(p.primary_container));
    t.set_mu_on_primary_container(color(p.on_primary_container));
    t.set_mu_secondary_container(color(p.secondary_container));
    t.set_mu_surface(color(p.surface));
    t.set_mu_surface_container(color(p.surface_container));
    t.set_mu_surface_high(color(p.surface_high));
    t.set_mu_text(color(p.text));
    t.set_mu_text_dim(color(p.text_dim));
    t.set_mu_track(color(p.track));
}

fn prepare_art(img: image::DynamicImage) -> (SharedPixelBuffer<Rgba8Pixel>, Rgb) {
    let (w, h) = (img.width(), img.height());
    let side = w.min(h);
    let mut sq = img.crop_imm((w - side) / 2, (h - side) / 2, side, side);
    if side > COVER_PX {
        sq = sq.resize_exact(COVER_PX, COVER_PX, image::imageops::FilterType::Triangle);
    }
    let tiny = sq.resize_exact(32, 32, image::imageops::FilterType::Triangle).to_rgb8();
    let rgb = theme::dominant_rgb(tiny.as_raw(), 3);
    let rgba = sq.to_rgba8();
    (SharedPixelBuffer::clone_from_slice(rgba.as_raw(), rgba.width(), rgba.height()), rgb)
}

fn apply_art(c: &Rc<Ctx>, gen: u64, pixels: Option<SharedPixelBuffer<Rgba8Pixel>>, rgb: Option<Rgb>) {
    if c.music.borrow().art_gen != gen {
        return;
    }
    let a = api(c);
    match pixels {
        Some(p) => {
            a.set_art(Image::from_rgba8(p));
            a.set_has_art(true);
        }
        None => {
            a.set_art(Image::default());
            a.set_has_art(false);
            c.music.borrow_mut().local_art_key = None;
        }
    }
    c.music.borrow_mut().art_rgb = rgb;
    refresh_palette(c);
    a.set_art_gen(a.get_art_gen() + 1);
}

fn load_album_art(c: &Rc<Ctx>, album_art: &str) {
    let urls = radio::album_art_urls(album_art);
    {
        let mut m = c.music.borrow_mut();
        m.local_art_key = None;
        m.art_file = None;
        if m.last_art_url.as_deref() == Some(urls[0].as_str()) {
            return;
        }
        m.last_art_url = Some(urls[0].clone());
        m.art_gen += 1;
    }
    media_changed(c);
    let gen = c.music.borrow().art_gen;
    std::thread::spawn(move || {
        let mut all = urls;
        all.push(radio::LOGO_URL.into());
        for url in all {
            let Ok(bytes) = radio::fetch_bytes(&url) else { continue };
            let Ok(img) = image::load_from_memory(&bytes) else { continue };
            let (pixels, rgb) = prepare_art(img);
            post(move |c| apply_art(c, gen, Some(pixels), Some(rgb)));
            return;
        }
    });
}

fn load_local_art(c: &Rc<Ctx>, key: &str) {
    let path = crate::paths::cover_path(&format!("{}.jpg", key.replace('.', "")));
    let same = c.music.borrow().local_art_key.as_deref() == Some(key) && api(c).get_has_art();
    {
        let mut m = c.music.borrow_mut();
        m.last_art_url = None;
        m.art_file = path.is_file().then(|| path.clone());
        if same {
            drop(m);
            let a = api(c);
            a.set_art_gen(a.get_art_gen() + 1);
            return;
        }
        m.art_gen += 1;
        m.local_art_key = Some(key.to_string());
    }
    let gen = c.music.borrow().art_gen;
    std::thread::spawn(move || {
        match image::open(&path) {
            Ok(img) => {
                let (pixels, rgb) = prepare_art(img);
                post(move |c| apply_art(c, gen, Some(pixels), Some(rgb)));
            }
            Err(_) => post(move |c| apply_art(c, gen, None, None)),
        }
    });
}


fn set_error(c: &Rc<Ctx>, message: &str) {
    let a = api(c);
    if !message.is_empty() {
        a.set_source_text(message.into());
        a.set_source_error(true);
    } else if c.music.borrow().mode == Mode::Radio {
        a.set_source_text("Audio from Gensokyo Radio  ·  128 kbps MP3".into());
        a.set_source_error(false);
    } else {
        a.set_source_text("Audio from your provided game files  ·  local playback".into());
        a.set_source_error(false);
    }
}

fn set_playing_ui(c: &Rc<Ctx>, on: bool) {
    let radio = c.music.borrow().mode == Mode::Radio;
    c.music.borrow_mut().status = if on { "Playing".into() } else { "Paused".into() };
    let a = api(c);
    a.set_playing(on);
    if radio {
        a.set_progress_smooth(true);
        a.set_progress(if on { 1.0 } else { 0.0 });
    }
    media_changed(c);
}

fn set_controls(c: &Rc<Ctx>) {
    let m = c.music.borrow();
    let a = api(c);
    let game = m.mode == Mode::Game;
    let has_track = game && m.selected.is_some();
    a.set_controls_enabled(has_track);
    a.set_play_enabled(has_track || !game);
    a.set_progress_enabled(has_track);
}

fn set_game_defaults(c: &Rc<Ctx>) {
    c.music.borrow_mut().selected = None;
    let a = api(c);
    set_error(c, "");
    a.set_title("Game BGM".into());
    a.set_artist("Choose a game and track".into());
    a.set_album("Your assigned game files stay on your device".into());
    a.set_time_now("0:00".into());
    a.set_time_total("0:00".into());
    a.set_progress_smooth(false);
    a.set_progress(0.0);
    a.set_duration(0.0);
    set_controls(c);
}

fn set_station_defaults(c: &Rc<Ctx>) {
    let a = api(c);
    a.set_title("Gensokyo Radio".into());
    a.set_artist("Live radio".into());
    a.set_album("Connecting to the station…".into());
    a.set_time_now("LIVE".into());
    a.set_time_total("LIVE".into());
    c.music.borrow_mut().art_rgb = None;
    refresh_palette(c);
}

fn stop_playback(c: &Rc<Ctx>) {
    let pb = {
        let mut m = c.music.borrow_mut();
        m.preparing = None;
        m.playing = false;
        m.reconnect_timer = None;
        m.playback.take()
    };
    drop(pb);
    let a = api(c);
    a.set_connecting(false);
    set_playing_ui(c, false);
}


fn mode_changed(c: &Rc<Ctx>, mode: Mode) {
    if c.music.borrow().mode == mode {
        return;
    }
    {
        let mut m = c.music.borrow_mut();
        m.mode_gen += 1;
        m.mode = mode;
        m.status = "Stopped".into();
        m.favorites_view = false;
    }
    let a = api(c);
    a.set_favorites_view(false);
    a.set_info_gen(a.get_info_gen() + 1);
    a.set_art_gen(a.get_art_gen() + 1);
    media_changed(c);
    let gen = c.music.borrow().mode_gen;
    super::after(40, move || {
        let c = ctx();
        if c.music.borrow().mode_gen != gen {
            return;
        }
        stop_playback(&c);
        if c.music.borrow().mode == Mode::Radio {
            set_station_defaults(&c);
            {
                let mut m = c.music.borrow_mut();
                m.last_art_url = None;
                m.now = NowPlaying::default();
                m.selected = None;
            }
            set_error(&c, "");
            load_album_art(&c, "");
            let a = api(&c);
            a.set_progress_smooth(false);
            a.set_progress(0.0);
            set_controls(&c);
            poll_now_playing(&c, true);
        } else {
            set_game_defaults(&c);
            refresh_assigned(&c, true);
        }
        media_changed(&c);
    });
}


fn start_radio(c: &Rc<Ctx>) {
    if !ensure_engine(c) {
        return;
    }
    c.music.borrow_mut().reconnect_timer = None;
    c.music.borrow_mut().playing = true;
    api(c).set_connecting(true);
    set_playing_ui(c, true);
    set_error(c, "");
    super::after(60, || {
        let c = ctx();
        if c.music.borrow().mode == Mode::Radio && c.music.borrow().playing {
            open_stream(&c);
        }
    });
}

fn open_stream(c: &Rc<Ctx>) {
    let result = {
        let m = c.music.borrow();
        let Some(Ok(engine)) = &m.engine else { return };
        engine.play(Input::Stream { url: radio::RADIO_URL.into(), user_agent: radio::USER_AGENT.into() }, 0.0, None, m.volume as f32, false)
    };
    match result {
        Ok(pb) => c.music.borrow_mut().playback = Some(pb),
        Err(e) => {
            set_error(c, &format!("Gensokyo Radio may be temporarily down. Radio playback error: {e}"));
            restart_stream_later(c);
        }
    }
}

fn restart_stream_later(c: &Rc<Ctx>) {
    api(c).set_connecting(true);
    let t = slint::Timer::default();
    t.start(slint::TimerMode::SingleShot, Duration::from_millis(RECONNECT_MS), || {
        let c = ctx();
        c.music.borrow_mut().reconnect_timer = None;
        if c.music.borrow().mode == Mode::Radio && c.music.borrow().playing {
            c.music.borrow_mut().playback = None;
            open_stream(&c);
        }
    });
    c.music.borrow_mut().reconnect_timer = Some(t);
}

fn poll_now_playing(c: &Rc<Ctx>, force: bool) {
    {
        let mut m = c.music.borrow_mut();
        if m.mode != Mode::Radio || m.metadata_in_flight {
            return;
        }
        if !force && m.metadata_gen > 0 && !m.playing && !page_visible(c) {
            return;
        }
        if !force && m.poll_skip > 0 {
            m.poll_skip -= 1;
            return;
        }
        m.metadata_in_flight = true;
        m.metadata_gen += 1;
    }
    let gen = c.music.borrow().metadata_gen;
    std::thread::spawn(move || {
        let result = radio::fetch_now_playing().map_err(|e| e.to_string());
        post(move |c| now_playing_result(c, gen, result));
    });
}

fn now_playing_result(c: &Rc<Ctx>, gen: u64, result: Result<NowPlaying, String>) {
    c.music.borrow_mut().metadata_in_flight = false;
    if gen != c.music.borrow().metadata_gen || c.music.borrow().mode != Mode::Radio {
        return;
    }
    let np = match result {
        Ok(np) => np,
        Err(_) => {
            let failures = {
                let mut m = c.music.borrow_mut();
                m.metadata_failures += 1;
                m.poll_skip = (m.metadata_failures * 2).min(6);
                m.metadata_failures
            };
            if failures >= 4 && !c.music.borrow().playing {
                api(c).set_album("Unable to read live song information".into());
                set_error(c, "Gensokyo Radio may be temporarily down or busy. Retrying…");
            }
            return;
        }
    };
    let changed = {
        let m = c.music.borrow();
        (m.now.title.as_str(), m.now.artist.as_str()) != (np.title.as_str(), np.artist.as_str())
    };
    let a = api(c);
    a.set_title(np.title.clone().into());
    a.set_artist(np.artist.clone().into());
    let mut detail = np.album.clone();
    if !np.circle.is_empty() {
        detail += &format!("  ·  {}", np.circle);
    }
    if !np.year.is_empty() {
        detail += &format!("  ·  {}", np.year);
    }
    a.set_album(detail.into());
    a.set_time_now("LIVE".into());
    a.set_time_total("LIVE".into());
    set_error(c, "");
    if changed {
        a.set_info_gen(a.get_info_gen() + 1);
    }
    let art = np.album_art.clone();
    let remaining = np.remaining;
    {
        let mut m = c.music.borrow_mut();
        m.now = np;
        m.metadata_failures = 0;
        m.last_metadata = Some(Instant::now());
        m.poll_skip = 0;
        m.song_end_timer = None;
    }
    media_changed(c);
    load_album_art(c, &art);
    if let Some(rem) = remaining.filter(|r| (4.0..=900.0).contains(r)) {
        let t = slint::Timer::default();
        t.start(slint::TimerMode::SingleShot, Duration::from_millis(((rem + 1.5) * 1000.0) as u64), || {
            let c = ctx();
            if c.music.borrow().mode == Mode::Radio {
                c.music.borrow_mut().poll_skip = 0;
                poll_now_playing(&c, true);
            }
        });
        c.music.borrow_mut().song_end_timer = Some(t);
    }
}


pub fn config_changed(c: &Rc<Ctx>) {
    refresh_assigned(c, false);
}

fn refresh_assigned(c: &Rc<Ctx>, mut render: bool) {
    let config = crate::games::load_config();
    let assigned = bgm::assigned_games(&config);
    let changed = assigned != c.music.borrow().assigned;
    if changed {
        {
            let mut m = c.music.borrow_mut();
            let old = std::mem::replace(&mut m.assigned, assigned.clone());
            for g in &old {
                if !assigned.contains(g) {
                    m.tracks.remove(&g.key);
                }
            }
            if let Some(sel) = m.selected_game.clone() {
                if !assigned.iter().any(|g| g.key == sel) {
                    m.selected_game = None;
                }
            }
        }
        let orphan = c.music.borrow().selected.as_ref().map_or(false, |t| !assigned.iter().any(|g| g.key == t.game_key));
        if orphan && c.music.borrow().mode == Mode::Game {
            stop_playback(c);
            set_game_defaults(c);
        }
        rebuild_game_dropdown(c);
        render = true;
        let games = assigned.clone();
        super::after(1200, move || {
            let c = ctx();
            for g in &games {
                request_scan(&c, g.clone(), false);
            }
        });
    }
    update_favorites_nav(c);
    if render && c.music.borrow().mode == Mode::Game {
        if c.music.borrow().assigned.is_empty() {
            show_list_message(c, "Only music of provided games will be available");
        } else {
            let index = api(c).get_game_index().max(0) as usize;
            game_selected(c, index);
        }
    }
}

fn rebuild_game_dropdown(c: &Rc<Ctx>) {
    let m = c.music.borrow();
    let items: Vec<MenuItem> = if m.assigned.is_empty() {
        vec![MenuItem { text: "Only music of provided games will be available".into(), enabled: false }]
    } else {
        m.assigned.iter().map(|g| MenuItem { text: g.title.clone().into(), enabled: true }).collect()
    };
    let index = m
        .selected_game
        .as_ref()
        .and_then(|k| m.assigned.iter().position(|g| &g.key == k))
        .unwrap_or(0);
    drop(m);
    let a = api(c);
    a.set_games(model(items));
    a.set_game_index(index as i32);
}

fn request_scan(c: &Rc<Ctx>, game: AssignedGame, urgent: bool) {
    if c.music.borrow().tracks.contains_key(&game.key) {
        return;
    }
    let (queue, start) = {
        let mut m = c.music.borrow_mut();
        let queue = m.scan_queue.clone();
        let mut q = queue.lock().unwrap();
        if m.scanning.contains(&game.key) {
            if urgent {
                if let Some(pos) = q.0.iter().position(|g| g.key == game.key) {
                    let g = q.0.remove(pos).unwrap();
                    q.0.push_front(g);
                }
            }
            return;
        }
        m.scanning.insert(game.key.clone());
        if urgent {
            q.0.push_front(game);
        } else {
            q.0.push_back(game);
        }
        let start = !q.1;
        q.1 = true;
        drop(q);
        (queue, start)
    };
    if !start {
        return;
    }
    let scratch = c.music.borrow().scratch.clone();
    std::thread::Builder::new()
        .name("game-bgm-scan".into())
        .spawn(move || loop {
            let next = {
                let mut q = queue.lock().unwrap();
                match q.0.pop_front() {
                    Some(g) => g,
                    None => {
                        q.1 = false;
                        return;
                    }
                }
            };
            let (tracks, error) = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| bgm::discover_tracks(&next, &scratch)))
                .unwrap_or_else(|_| (Vec::new(), "The game's music files could not be read (they may be damaged).".into()));
            post(move |c| tracks_discovered(c, next, tracks, error));
        })
        .ok();
}

fn tracks_discovered(c: &Rc<Ctx>, game: AssignedGame, tracks: Vec<GameTrack>, error: String) {
    c.music.borrow_mut().scanning.remove(&game.key);
    let current = c.music.borrow().assigned.iter().find(|g| g.key == game.key).cloned();
    if current.as_ref() != Some(&game) {
        if let Some(g) = current {
            request_scan(c, g, true);
        }
        return;
    }
    if !tracks.is_empty() {
        c.music.borrow_mut().tracks.insert(game.key.clone(), tracks.clone());
    }
    let show = {
        let m = c.music.borrow();
        m.mode == Mode::Game && m.selected_game.as_deref() == Some(game.key.as_str()) && !m.favorites_view
    };
    if show {
        show_game_tracks(c, &game, &tracks, &error);
        let a = api(c);
        a.set_list_gen(a.get_list_gen() + 1);
    }
    update_favorites_nav(c);
    media_changed(c);
}

fn game_selected(c: &Rc<Ctx>, index: usize) {
    let game = {
        let m = c.music.borrow();
        if m.mode != Mode::Game {
            return;
        }
        let Some(g) = m.assigned.get(index).cloned() else { return };
        g
    };
    {
        let mut m = c.music.borrow_mut();
        m.favorites_view = false;
        m.selected_game = Some(game.key.clone());
    }
    api(c).set_favorites_view(false);
    let known = c.music.borrow().tracks.get(&game.key).cloned();
    match known {
        Some(tracks) => show_game_tracks(c, &game, &tracks, ""),
        None => {
            if c.music.borrow().selected.is_none() {
                let a = api(c);
                a.set_title("Game BGM".into());
                a.set_artist(game.title.clone().into());
                a.set_album("Reading game music…".into());
                set_controls(c);
                load_local_art(c, &game.key);
            }
            set_list_loading(c);
            let a = api(c);
            a.set_list_gen(a.get_list_gen() + 1);
            request_scan(c, game, true);
        }
    }
}

fn show_game_tracks(c: &Rc<Ctx>, game: &AssignedGame, tracks: &[GameTrack], error: &str) {
    let idle = c.music.borrow().selected.is_none();
    if !error.is_empty() && tracks.is_empty() {
        show_list_message(c, error);
        if idle {
            let a = api(c);
            a.set_title("Game BGM".into());
            a.set_artist(game.title.clone().into());
            a.set_album(error.into());
            set_controls(c);
            load_local_art(c, &game.key);
        }
        return;
    }
    render_list(c, false);
    if idle {
        let a = api(c);
        a.set_title("Game BGM".into());
        a.set_artist(game.title.clone().into());
        let n = tracks.len();
        a.set_album(format!("{n} track{} available", if n == 1 { "" } else { "s" }).into());
        load_local_art(c, &game.key);
        set_controls(c);
    }
}

fn set_list_loading(c: &Rc<Ctx>) {
    let a = api(c);
    a.set_list_state(1);
    c.music.borrow_mut().shown_list.clear();
    if c.music.borrow().loader_timer.is_none() {
        let start = Instant::now();
        let t = slint::Timer::default();
        t.start(slint::TimerMode::Repeated, Duration::from_millis(16), move || {
            let c = ctx();
            if api(&c).get_list_state() != 1 {
                let t = c.music.borrow_mut().loader_timer.take();
                super::after(0, move || drop(t));
                return;
            }
            api(&c).set_loader_path(blob_path(start.elapsed().as_secs_f64()).into());
        });
        c.music.borrow_mut().loader_timer = Some(t);
    }
}

fn blob_path(t: f64) -> String {
    const LOBES: [f64; 6] = [5.0, 8.0, 3.0, 6.0, 4.0, 7.0];
    let amp = |l: f64| (0.55 / l).min(0.2);
    let phase = t / 0.8;
    let index = phase.floor() as usize % LOBES.len();
    let f = phase.fract();
    let ease = f * f * (3.0 - 2.0 * f);
    let (a, b) = (LOBES[index], LOBES[(index + 1) % LOBES.len()]);
    let (amp_a, amp_b) = (amp(a) * (1.0 - ease), amp(b) * ease);
    let rotation = t * 2.0 + 0.5 * (t * 1.3).sin();
    let base = 29.0;
    let mut out = String::with_capacity(2400);
    for k in 0..=120 {
        let theta = std::f64::consts::TAU * k as f64 / 120.0;
        let r = base * (1.0 + amp_a * (a * theta).cos() + amp_b * (b * theta).cos());
        let (x, y) = (50.0 + r * (theta + rotation).cos(), 50.0 + r * (theta + rotation).sin());
        out.push_str(&format!("{} {x:.2} {y:.2} ", if k == 0 { "M" } else { "L" }));
    }
    out.push('Z');
    out
}

fn show_list_message(c: &Rc<Ctx>, message: &str) {
    let a = api(c);
    a.set_list_message(message.into());
    a.set_list_state(2);
    c.music.borrow_mut().shown_list.clear();
}

fn favorite_tracks(m: &MusicState) -> Vec<GameTrack> {
    m.assigned
        .iter()
        .flat_map(|g| m.tracks.get(&g.key).cloned().unwrap_or_default())
        .filter(|t| m.favorites.contains(&t.id))
        .collect()
}

fn current_list(c: &Ctx) -> Vec<GameTrack> {
    let m = c.music.borrow();
    if m.favorites_view {
        return favorite_tracks(&m);
    }
    m.selected_game.as_ref().and_then(|k| m.tracks.get(k).cloned()).unwrap_or_default()
}

fn playback_list(c: &Ctx) -> Vec<GameTrack> {
    let m = c.music.borrow();
    if m.favorites_view {
        return favorite_tracks(&m);
    }
    if let Some(t) = &m.selected {
        return m.tracks.get(&t.game_key).cloned().unwrap_or_default();
    }
    drop(m);
    current_list(c)
}

fn render_list(c: &Rc<Ctx>, force: bool) {
    let list = current_list(c);
    let (view, lang, selected) = {
        let m = c.music.borrow();
        (m.favorites_view, m.language.clone(), m.selected.as_ref().map(|t| t.id.clone()))
    };
    if list.is_empty() {
        show_list_message(c, if view { "Favorite songs from your assigned games" } else { "No game music is available" });
        return;
    }
    let ids: Vec<String> = list.iter().map(|t| t.id.clone()).collect();
    let a = api(c);
    let favs = c.music.borrow().favorites.clone();
    let rows: Vec<TrackRow> = list
        .iter()
        .enumerate()
        .map(|(i, t)| TrackRow {
            number: i as i32 + 1,
            title: t.display_title(&lang).into(),
            duration: fmt_time(t.duration).into(),
            favorite: favs.contains(&t.id),
            active: selected.as_deref() == Some(t.id.as_str()),
        })
        .collect();
    if !force && ids == c.music.borrow().shown_list && a.get_list_state() == 0 {
        let m = a.get_tracks();
        for (i, row) in rows.into_iter().enumerate() {
            super::update_row(&m, i, |r| {
                r.active = row.active;
                r.favorite = row.favorite;
            });
        }
        return;
    }
    a.set_tracks(model(rows));
    a.set_list_state(0);
    c.music.borrow_mut().shown_list = ids;
}

fn update_favorites_nav(c: &Rc<Ctx>) {
    let any = !favorite_tracks(&c.music.borrow()).is_empty();
    api(c).set_favorites_available(any);
    if !any && c.music.borrow().favorites_view {
        c.music.borrow_mut().favorites_view = false;
        api(c).set_favorites_view(false);
    }
}


fn loop_bounds(m: &MusicState) -> Option<(f64, f64)> {
    let t = m.selected.as_ref()?;
    if m.mode != Mode::Game || m.repeat != 2 {
        return None;
    }
    t.loop_region().or((t.duration > 0.0).then_some((0.0, t.duration)))
}

fn select_and_play(c: &Rc<Ctx>, track: GameTrack) {
    c.music.borrow_mut().selected = Some(track.clone());
    update_track_ui(c);
    load_local_art(c, &track.game_key);
    render_list(c, false);
    start_selected(c);
}

fn update_track_ui(c: &Rc<Ctx>) {
    media_changed(c);
    let (track, lang) = {
        let m = c.music.borrow();
        (m.selected.clone(), m.language.clone())
    };
    let Some(t) = track else {
        set_controls(c);
        return;
    };
    let a = api(c);
    a.set_title(t.display_title(&lang).into());
    a.set_artist(t.game_title.clone().into());
    a.set_album(t.filename.clone().into());
    a.set_progress_smooth(false);
    a.set_progress(0.0);
    a.set_duration(t.duration as f32);
    a.set_time_now("0:00".into());
    a.set_time_total(fmt_time(t.duration).into());
    set_error(c, "");
    set_controls(c);
    a.set_info_gen(a.get_info_gen() + 1);
}

fn input_for(track: &GameTrack, path: Option<PathBuf>) -> Option<Input> {
    Some(match &track.source {
        Source::Pcm { path, offset, length, channels, bits } => {
            Input::Pcm { path: path.clone(), offset: *offset, length: *length, channels: *channels, bits: *bits, rate: track.sample_rate }
        }
        Source::File(p) => Input::File(p.clone()),
        Source::Tasofro(m) => Input::Member(m.clone()),
        Source::Pc98 { .. } => Input::File(path?),
    })
}

fn start_selected(c: &Rc<Ctx>) {
    let Some(track) = c.music.borrow().selected.clone() else { return };
    if !ensure_engine(c) {
        return;
    }
    if let Source::Pc98 { .. } = track.source {
        let cached = c.music.borrow().prepared.iter().find(|(id, p)| *id == track.id && p.is_file()).map(|(_, p)| p.clone());
        if let Some(path) = cached {
            return track_ready(c, &track, path);
        }
        let (gen, scratch) = {
            let mut m = c.music.borrow_mut();
            m.preparing = Some(track.id.clone());
            m.playback = None;
            (m.mode_gen, m.scratch.join(crate::util::sanitize_component(&track.id)))
        };
        media_changed(c);
        api(c).set_connecting(true);
        api(c).set_source_text("Preparing selected track…".into());
        api(c).set_source_error(false);
        std::thread::spawn(move || {
            let result = pc98::render(&track, &scratch).map_err(|e| e.to_string());
            post(move |c| {
                let current = {
                    let m = c.music.borrow();
                    m.mode_gen == gen && m.mode == Mode::Game && m.selected.as_ref().map(|t| &t.id) == Some(&track.id)
                };
                if !current {
                    return;
                }
                match result {
                    Ok(path) => {
                        evict_prepared(c, &track.id, &path);
                        track_ready(c, &track, path);
                    }
                    Err(e) => {
                        {
                            let mut m = c.music.borrow_mut();
                            m.preparing = None;
                            m.playing = false;
                            m.status = "Stopped".into();
                        }
                        api(c).set_connecting(false);
                        set_playing_ui(c, false);
                        let lang = c.music.borrow().language.clone();
                        set_error(c, &format!("Could not prepare {}: {e}", track.display_title(&lang)));
                        c.music.borrow_mut().status = "Stopped".into();
                        media_changed(c);
                    }
                }
            });
        });
        return;
    }
    track_ready(c, &track, PathBuf::new());
}

fn evict_prepared(c: &Rc<Ctx>, id: &str, path: &PathBuf) {
    let mut m = c.music.borrow_mut();
    m.prepared.retain(|(i, _)| i != id);
    m.prepared.push((id.to_string(), path.clone()));
    let mut total: u64 = m.prepared.iter().map(|(_, p)| std::fs::metadata(p).map(|x| x.len()).unwrap_or(0)).sum();
    while total > PREPARED_CACHE_BYTES && m.prepared.len() > 1 {
        let (_, p) = m.prepared.remove(0);
        total = total.saturating_sub(std::fs::metadata(&p).map(|x| x.len()).unwrap_or(0));
        let _ = std::fs::remove_file(p);
    }
}

fn track_ready(c: &Rc<Ctx>, track: &GameTrack, path: PathBuf) {
    let Some(input) = input_for(track, Some(path)) else { return };
    let result = {
        let mut m = c.music.borrow_mut();
        m.preparing = None;
        m.playback = None;
        let bounds = loop_bounds(&m);
        let volume = m.volume as f32;
        let Some(Ok(engine)) = &m.engine else { return };
        engine.play(input, 0.0, bounds, volume, false)
    };
    match result {
        Ok(pb) => {
            {
                let mut m = c.music.borrow_mut();
                m.playback = Some(pb);
                m.playing = true;
                m.last_position = 0.0;
            }
            api(c).set_connecting(true);
            set_playing_ui(c, true);
            set_error(c, "");
        }
        Err(e) => {
            c.music.borrow_mut().playing = false;
            set_playing_ui(c, false);
            let lang = c.music.borrow().language.clone();
            set_error(c, &format!("Could not play {}: {e}", track.display_title(&lang)));
        }
    }
}

fn play_pause(c: &Rc<Ctx>) {
    let mode = c.music.borrow().mode;
    if mode == Mode::Radio {
        if c.music.borrow().playing {
            c.music.borrow_mut().reconnect_timer = None;
            stop_playback(c);
        } else {
            start_radio(c);
        }
        return;
    }
    if c.music.borrow().selected.is_none() {
        return;
    }
    let state = {
        let m = c.music.borrow();
        m.playback.as_ref().map(|p| (p.is_paused(), p.state()))
    };
    match state {
        Some((false, s)) if s != State::Ended && s != State::Failed && c.music.borrow().playing => {
            c.music.borrow().playback.as_ref().unwrap().pause();
            c.music.borrow_mut().playing = false;
            api(c).set_connecting(false);
            set_playing_ui(c, false);
        }
        Some((true, s)) if s != State::Ended && s != State::Failed => {
            c.music.borrow().playback.as_ref().unwrap().resume();
            c.music.borrow_mut().playing = true;
            set_playing_ui(c, true);
        }
        _ => {
            if c.music.borrow().preparing.is_none() {
                start_selected(c);
            }
        }
    }
}

fn seek_to(c: &Rc<Ctx>, seconds: f64, notify: bool) {
    let target = {
        let m = c.music.borrow();
        let (Some(pb), Some(t)) = (&m.playback, &m.selected) else { return };
        if m.mode != Mode::Game {
            return;
        }
        let mut target = seconds.clamp(0.0, (t.duration - 1.0 / t.sample_rate.max(1) as f64).max(0.0));
        if let Some((s, e)) = loop_bounds(&m) {
            if target >= e {
                target = s;
            }
        }
        pb.seek(target);
        target
    };
    c.music.borrow_mut().last_position = target;
    let a = api(c);
    let dur = c.music.borrow().selected.as_ref().map(|t| t.duration).unwrap_or(1.0).max(0.01);
    a.set_progress((target / dur) as f32);
    a.set_time_now(fmt_time(target).into());
    if notify {
        seeked(c, target);
    }
    media_changed(c);
}

fn previous(c: &Rc<Ctx>) {
    if c.music.borrow().mode != Mode::Game || c.music.borrow().selected.is_none() {
        return;
    }
    let pos = c.music.borrow().playback.as_ref().map(|p| p.position()).unwrap_or(0.0);
    if pos > 3.0 {
        return seek_to(c, 0.0, true);
    }
    let list = playback_list(c);
    if list.is_empty() {
        return;
    }
    let cur = c.music.borrow().selected.as_ref().and_then(|s| list.iter().position(|t| t.id == s.id)).unwrap_or(0);
    let prev = (cur + list.len() - 1) % list.len();
    select_and_play(c, list[prev].clone());
}

fn advance(c: &Rc<Ctx>, auto: bool) {
    if c.music.borrow().mode != Mode::Game {
        return;
    }
    let list = playback_list(c);
    if list.is_empty() {
        return stop_playback(c);
    }
    let (shuffle, repeat, selected) = {
        let m = c.music.borrow();
        (m.shuffle, m.repeat, m.selected.clone())
    };
    if auto && repeat == 2 {
        if let Some(t) = selected {
            select_and_play(c, t);
        }
        return;
    }
    let next = if shuffle && list.len() > 1 {
        let choices: Vec<&GameTrack> = list.iter().filter(|t| Some(&t.id) != selected.as_ref().map(|s| &s.id)).collect();
        choices.choose(&mut rand::thread_rng()).map(|t| (*t).clone())
    } else {
        let idx = selected.as_ref().and_then(|s| list.iter().position(|t| t.id == s.id)).map(|i| i as i64).unwrap_or(-1);
        let n = idx + 1;
        if n as usize >= list.len() {
            if repeat == 1 {
                list.first().cloned()
            } else {
                stop_playback(c);
                return;
            }
        } else {
            list.get(n as usize).cloned()
        }
    };
    if let Some(t) = next {
        select_and_play(c, t);
    }
}

fn set_repeat(c: &Rc<Ctx>, mode: u8) {
    if c.music.borrow().mode != Mode::Game || c.music.borrow().repeat == mode {
        return;
    }
    c.music.borrow_mut().repeat = mode;
    api(c).set_repeat(mode != 0);
    {
        let m = c.music.borrow();
        if let Some(pb) = &m.playback {
            pb.set_loop(loop_bounds(&m));
        }
    }
    media_changed(c);
}


fn tick(c: &Rc<Ctx>) {
    let (mode, playing) = {
        let m = c.music.borrow();
        (m.mode, m.playing)
    };
    let info = {
        let mut m = c.music.borrow_mut();
        m.playback.as_mut().map(|p| (p.state(), p.error(), p.position(), p.take_wrapped(), p.is_paused()))
    };
    let Some((state, error, position, wrapped, paused)) = info else { return };
    if state == State::Playing && api(c).get_connecting() && !paused {
        api(c).set_connecting(false);
        set_error(c, "");
    }
    match mode {
        Mode::Radio => match state {
            State::Failed => {
                c.music.borrow_mut().playback = None;
                set_error(c, &format!("Gensokyo Radio may be temporarily down. Radio playback error: {}", error.unwrap_or_default()));
                if playing {
                    restart_stream_later(c);
                }
            }
            State::Ended => {
                c.music.borrow_mut().playback = None;
                if playing {
                    restart_stream_later(c);
                }
            }
            _ => {}
        },
        Mode::Game => match state {
            State::Failed => {
                c.music.borrow_mut().playback = None;
                c.music.borrow_mut().playing = false;
                api(c).set_connecting(false);
                set_playing_ui(c, false);
                let title = {
                    let m = c.music.borrow();
                    m.selected.as_ref().map(|t| t.display_title(&m.language)).unwrap_or_else(|| "the selected track".into())
                };
                set_error(c, &format!("Could not play {title}: {}", error.unwrap_or_default()));
                c.music.borrow_mut().status = "Stopped".into();
                media_changed(c);
            }
            State::Ended => {
                c.music.borrow_mut().playback = None;
                if playing {
                    advance(c, true);
                }
            }
            _ => {
                if wrapped {
                    seeked(c, position);
                }
                let visible = page_visible(c);
                c.music.borrow_mut().last_position = position;
                c.music.borrow().media_shared.lock().unwrap().position_us = (position * 1e6) as i64;
                if visible && !paused {
                    let dur = c.music.borrow().selected.as_ref().map(|t| t.duration).unwrap_or(0.0);
                    let a = api(c);
                    a.set_progress((position / dur.max(0.01)).min(1.0) as f32);
                    a.set_time_now(fmt_time(position).into());
                    a.set_time_total(fmt_time(dur).into());
                }
            }
        },
    }
}


fn track_id(identity: &str) -> String {
    use sha2::Digest;
    format!("{TRACK_PREFIX}{}", hex::encode(sha2::Sha256::digest(identity.as_bytes())))
}

fn snapshot(c: &Ctx) -> MediaState {
    let m = c.music.borrow();
    let radio = m.mode == Mode::Radio;
    let track = if radio { None } else { m.selected.clone() };
    let available = radio || track.is_some();
    let (title, artist, album) = if radio {
        (m.now.title.clone(), m.now.artist.clone(), m.now.album.clone())
    } else if let Some(t) = &track {
        (t.display_title(&m.language), t.game_title.clone(), t.game_title.clone())
    } else {
        Default::default()
    };
    let identity = if radio {
        format!("radio:{title}\0{artist}\0{album}")
    } else {
        track.as_ref().map(|t| t.id.clone()).unwrap_or_default()
    };
    let mut art = if radio { m.last_art_url.clone().unwrap_or_default() } else { String::new() };
    if let Some(p) = m.art_file.as_ref().filter(|_| !radio) {
        if let Ok(u) = url::Url::from_file_path(p.canonicalize().unwrap_or_else(|_| p.clone())) {
            art = u.to_string();
        }
    }
    if available && art.is_empty() {
        if let Ok(u) = url::Url::from_file_path(crate::paths::icon_path().canonicalize().unwrap_or_default()) {
            art = u.to_string();
        }
    }
    let duration_us = track.as_ref().map(|t| (t.duration * 1e6).round() as i64).unwrap_or(0);
    let ready = track.is_some() && m.playback.is_some() && m.preparing.is_none();
    let list = if track.is_some() {
        drop(m);
        let l = playback_list(c);
        let m2 = c.music.borrow();
        let _ = &m2;
        l
    } else {
        drop(m);
        Vec::new()
    };
    let m = c.music.borrow();
    let index = track.as_ref().and_then(|t| list.iter().position(|x| x.id == t.id));
    MediaState {
        track_id: if identity.is_empty() { String::new() } else { track_id(&identity) },
        title,
        artist,
        album,
        art,
        duration_us,
        status: if available { m.status.clone() } else { "Stopped".into() },
        can_play: available,
        can_pause: available,
        can_seek: ready && duration_us > 0,
        can_next: !list.is_empty()
            && ((m.shuffle && list.len() > 1) || m.repeat == 1 || index.map_or(false, |i| i + 1 < list.len())),
        can_previous: !list.is_empty(),
        loop_status: if radio { "None".into() } else { ["None", "Playlist", "Track"][m.repeat as usize].into() },
        shuffle: m.shuffle && !radio,
        volume: m.volume,
    }
}

fn media_changed(c: &Rc<Ctx>) {
    if c.music.borrow().media.is_none() {
        return;
    }
    let state = snapshot(c);
    let shared = c.music.borrow().media_shared.clone();
    let position = (c.music.borrow().last_position * 1e6) as i64;
    {
        let mut s = shared.lock().unwrap();
        s.state = state.clone();
        s.position_us = position;
    }
    if let Some(b) = c.music.borrow_mut().media.as_mut() {
        b.update(&state, position);
    }
}

fn seeked(c: &Rc<Ctx>, position: f64) {
    if let Some(b) = c.music.borrow_mut().media.as_mut() {
        b.seeked((position * 1e6) as i64);
    }
}

pub fn attach_media(c: &Rc<Ctx>) {
    let shared = c.music.borrow().media_shared.clone();
    let sink: media::CommandSink = Arc::new(|cmd| post(move |c| media_command(c, cmd)));
    #[allow(unused_mut)]
    let mut window: Option<isize> = None;
    #[cfg(windows)]
    {
        use raw_window_handle::{HasWindowHandle, RawWindowHandle};
        if let Ok(h) = c.app.window().window_handle().window_handle() {
            if let RawWindowHandle::Win32(w) = h.as_raw() {
                window = Some(w.hwnd.get());
            }
        }
    }
    let backend = media::start(shared, sink, window);
    c.music.borrow_mut().media = backend;
    media_changed(c);
}

fn media_command(c: &Rc<Ctx>, cmd: MediaCommand) {
    if c.music.borrow().closed {
        return;
    }
    let state = snapshot(c);
    match cmd {
        MediaCommand::Raise => {
            let _ = c.app.show();
            c.app.window().set_minimized(false);
        }
        MediaCommand::Quit => {
            let _ = c.app.window().hide();
            shutdown(c);
            let _ = slint::quit_event_loop();
        }
        MediaCommand::PlayPause => {
            let busy = c.music.borrow().playing || c.music.borrow().preparing.is_some();
            media_command(c, if busy { MediaCommand::Pause } else { MediaCommand::Play });
            return;
        }
        MediaCommand::Play => {
            if state.can_play && !c.music.borrow().playing && c.music.borrow().preparing.is_none() {
                play_pause(c);
            }
        }
        MediaCommand::Pause => {
            if state.can_pause {
                if c.music.borrow().preparing.is_some() {
                    c.music.borrow_mut().mode_gen += 1;
                    stop_playback(c);
                    c.music.borrow_mut().status = "Paused".into();
                } else if c.music.borrow().playing {
                    play_pause(c);
                }
            }
        }
        MediaCommand::Stop => {
            c.music.borrow_mut().mode_gen += 1;
            stop_playback(c);
            c.music.borrow_mut().status = "Stopped".into();
        }
        MediaCommand::Next => {
            if state.can_next {
                advance(c, false);
            }
        }
        MediaCommand::Previous => {
            if state.can_previous {
                previous(c);
            }
        }
        MediaCommand::Seek(offset) => {
            if state.can_seek {
                let pos = (c.music.borrow().last_position * 1e6) as i64 + offset;
                if pos > state.duration_us {
                    advance(c, false);
                } else {
                    seek_to(c, pos.max(0) as f64 / 1e6, true);
                }
            }
        }
        MediaCommand::SetPosition(id, pos) => {
            if state.can_seek && (id.is_empty() || id == state.track_id) && (0..=state.duration_us).contains(&pos) {
                seek_to(c, pos as f64 / 1e6, true);
            }
        }
        MediaCommand::LoopStatus(s) => {
            if c.music.borrow().mode == Mode::Game {
                set_repeat(c, match s.as_str() { "Playlist" => 1, "Track" => 2, _ => 0 });
            }
        }
        MediaCommand::Shuffle(on) => {
            if c.music.borrow().mode == Mode::Game && c.music.borrow().shuffle != on {
                c.music.borrow_mut().shuffle = on;
                api(c).set_shuffle(on);
            }
        }
        MediaCommand::Volume(v) => {
            let v = v.clamp(0.0, 1.0);
            c.music.borrow_mut().volume = v;
            if let Some(pb) = c.music.borrow().playback.as_ref() {
                pb.set_volume(v as f32);
            }
        }
    }
    media_changed(c);
}

pub fn shutdown(c: &Rc<Ctx>) {
    let (pb, media, scratch) = {
        let mut m = c.music.borrow_mut();
        if m.closed {
            return;
        }
        m.closed = true;
        m.mode_gen += 1;
        m.timers.clear();
        (m.playback.take(), m.media.take(), m.scratch.clone())
    };
    drop(pb);
    drop(media);
    let _ = std::fs::remove_dir_all(scratch);
}
