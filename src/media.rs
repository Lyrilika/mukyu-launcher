
use std::sync::{Arc, Mutex};

#[derive(Clone, Debug, PartialEq, Default)]
pub struct MediaState {
    pub track_id: String,
    pub title: String,
    pub artist: String,
    pub album: String,
    pub art: String,
    pub duration_us: i64,
    pub status: String,
    pub can_play: bool,
    pub can_pause: bool,
    pub can_seek: bool,
    pub can_next: bool,
    pub can_previous: bool,
    pub loop_status: String,
    pub shuffle: bool,
    pub volume: f64,
}

#[derive(Clone, Debug)]
#[cfg_attr(not(target_os = "linux"), allow(dead_code))]
pub enum MediaCommand {
    Raise,
    Quit,
    Play,
    Pause,
    PlayPause,
    Stop,
    Next,
    Previous,
    Seek(i64),
    SetPosition(String, i64),
    LoopStatus(String),
    Shuffle(bool),
    Volume(f64),
}

pub type CommandSink = Arc<dyn Fn(MediaCommand) + Send + Sync>;

#[derive(Default)]
pub struct Shared {
    pub state: MediaState,
    pub position_us: i64,
}

pub type SharedState = Arc<Mutex<Shared>>;

pub trait Backend {
    fn update(&mut self, state: &MediaState, position_us: i64);
    fn seeked(&mut self, position_us: i64);
}

#[cfg(target_os = "linux")]
pub use mpris::start;

#[cfg(windows)]
pub use smtc::start;

#[cfg(not(any(target_os = "linux", windows)))]
pub fn start(_: SharedState, _: CommandSink, _: Option<isize>) -> Option<Box<dyn Backend>> {
    None
}

#[cfg(target_os = "linux")]
mod mpris {
    use std::collections::HashMap;

    use zbus::object_server::SignalEmitter;
    use zbus::zvariant::{ObjectPath, OwnedValue, Value};

    use super::*;

    const PATH: &str = "/org/mpris/MediaPlayer2";
    const PLAYER: &str = "org.mpris.MediaPlayer2.Player";

    struct Root {
        cmd: CommandSink,
    }

    #[zbus::interface(name = "org.mpris.MediaPlayer2")]
    impl Root {
        fn raise(&self) {
            (self.cmd)(MediaCommand::Raise)
        }
        fn quit(&self) {
            (self.cmd)(MediaCommand::Quit)
        }
        #[zbus(property)]
        fn can_quit(&self) -> bool {
            true
        }
        #[zbus(property)]
        fn can_raise(&self) -> bool {
            true
        }
        #[zbus(property)]
        fn has_track_list(&self) -> bool {
            false
        }
        #[zbus(property)]
        fn identity(&self) -> String {
            "Mukyu Launcher".into()
        }
        #[zbus(property)]
        fn desktop_entry(&self) -> String {
            "mukyulauncher".into()
        }
        #[zbus(property)]
        fn supported_uri_schemes(&self) -> Vec<String> {
            Vec::new()
        }
        #[zbus(property)]
        fn supported_mime_types(&self) -> Vec<String> {
            Vec::new()
        }
    }

    struct Player {
        cmd: CommandSink,
        shared: SharedState,
    }

    fn metadata(s: &MediaState) -> HashMap<String, OwnedValue> {
        let mut m: HashMap<String, OwnedValue> = HashMap::new();
        if s.track_id.is_empty() {
            return m;
        }
        let ov = |v: Value| OwnedValue::try_from(v).unwrap();
        if let Ok(p) = ObjectPath::try_from(s.track_id.as_str()) {
            m.insert("mpris:trackid".into(), ov(Value::from(p)));
        }
        m.insert("xesam:title".into(), ov(Value::from(s.title.as_str())));
        let artists: Vec<&str> = if s.artist.is_empty() { vec![] } else { vec![s.artist.as_str()] };
        m.insert("xesam:artist".into(), ov(Value::from(artists)));
        m.insert("xesam:album".into(), ov(Value::from(s.album.as_str())));
        if s.duration_us > 0 {
            m.insert("mpris:length".into(), ov(Value::from(s.duration_us)));
        }
        if !s.art.is_empty() {
            m.insert("mpris:artUrl".into(), ov(Value::from(s.art.as_str())));
        }
        m
    }

    #[zbus::interface(name = "org.mpris.MediaPlayer2.Player")]
    impl Player {
        fn next(&self) {
            (self.cmd)(MediaCommand::Next)
        }
        fn previous(&self) {
            (self.cmd)(MediaCommand::Previous)
        }
        fn pause(&self) {
            (self.cmd)(MediaCommand::Pause)
        }
        fn play_pause(&self) {
            (self.cmd)(MediaCommand::PlayPause)
        }
        fn stop(&self) {
            (self.cmd)(MediaCommand::Stop)
        }
        fn play(&self) {
            (self.cmd)(MediaCommand::Play)
        }
        fn seek(&self, offset: i64) {
            (self.cmd)(MediaCommand::Seek(offset))
        }
        fn set_position(&self, track_id: ObjectPath<'_>, position: i64) {
            (self.cmd)(MediaCommand::SetPosition(track_id.to_string(), position))
        }
        fn open_uri(&self, _uri: &str) -> zbus::fdo::Result<()> {
            Err(zbus::fdo::Error::NotSupported("Open a track in Mukyu Launcher".into()))
        }
        #[zbus(signal)]
        async fn seeked(emitter: &SignalEmitter<'_>, position: i64) -> zbus::Result<()>;

        #[zbus(property)]
        fn playback_status(&self) -> String {
            self.shared.lock().unwrap().state.status.clone()
        }
        #[zbus(property)]
        fn loop_status(&self) -> String {
            self.shared.lock().unwrap().state.loop_status.clone()
        }
        #[zbus(property)]
        fn set_loop_status(&mut self, value: String) -> zbus::fdo::Result<()> {
            if !matches!(value.as_str(), "None" | "Track" | "Playlist") {
                return Err(zbus::fdo::Error::InvalidArgs("Invalid loop status".into()));
            }
            (self.cmd)(MediaCommand::LoopStatus(value));
            Ok(())
        }
        #[zbus(property)]
        fn rate(&self) -> f64 {
            1.0
        }
        #[zbus(property)]
        fn set_rate(&mut self, value: f64) {
            if value == 0.0 {
                (self.cmd)(MediaCommand::Pause)
            }
        }
        #[zbus(property)]
        fn shuffle(&self) -> bool {
            self.shared.lock().unwrap().state.shuffle
        }
        #[zbus(property)]
        fn set_shuffle(&mut self, value: bool) {
            (self.cmd)(MediaCommand::Shuffle(value))
        }
        #[zbus(property)]
        fn metadata(&self) -> HashMap<String, OwnedValue> {
            metadata(&self.shared.lock().unwrap().state)
        }
        #[zbus(property)]
        fn volume(&self) -> f64 {
            self.shared.lock().unwrap().state.volume
        }
        #[zbus(property)]
        fn set_volume(&mut self, value: f64) -> zbus::fdo::Result<()> {
            if !value.is_finite() {
                return Err(zbus::fdo::Error::InvalidArgs("Volume must be finite".into()));
            }
            (self.cmd)(MediaCommand::Volume(value));
            Ok(())
        }
        #[zbus(property(emits_changed_signal = "false"))]
        fn position(&self) -> i64 {
            self.shared.lock().unwrap().position_us
        }
        #[zbus(property)]
        fn minimum_rate(&self) -> f64 {
            1.0
        }
        #[zbus(property)]
        fn maximum_rate(&self) -> f64 {
            1.0
        }
        #[zbus(property)]
        fn can_go_next(&self) -> bool {
            self.shared.lock().unwrap().state.can_next
        }
        #[zbus(property)]
        fn can_go_previous(&self) -> bool {
            self.shared.lock().unwrap().state.can_previous
        }
        #[zbus(property)]
        fn can_play(&self) -> bool {
            self.shared.lock().unwrap().state.can_play
        }
        #[zbus(property)]
        fn can_pause(&self) -> bool {
            self.shared.lock().unwrap().state.can_pause
        }
        #[zbus(property)]
        fn can_seek(&self) -> bool {
            self.shared.lock().unwrap().state.can_seek
        }
        #[zbus(property(emits_changed_signal = "const"))]
        fn can_control(&self) -> bool {
            true
        }
    }

    pub struct Mpris {
        conn: zbus::blocking::Connection,
        last: Option<MediaState>,
    }

    pub fn start(shared: SharedState, cmd: CommandSink, _window: Option<isize>) -> Option<Box<dyn Backend>> {
        let build = |name: String| -> zbus::Result<zbus::blocking::Connection> {
            zbus::blocking::connection::Builder::session()?
                .name(name)?
                .serve_at(PATH, Root { cmd: cmd.clone() })?
                .serve_at(PATH, Player { cmd: cmd.clone(), shared: shared.clone() })?
                .build()
        };
        let conn = build("org.mpris.MediaPlayer2.mukyulauncher".into())
            .or_else(|_| build(format!("org.mpris.MediaPlayer2.mukyulauncher.instance{}", std::process::id())))
            .ok()?;
        Some(Box::new(Mpris { conn, last: None }))
    }

    impl Backend for Mpris {
        fn update(&mut self, s: &MediaState, _position: i64) {
            let mut changed: HashMap<&str, Value> = HashMap::new();
            let last = self.last.clone().unwrap_or_else(|| MediaState { status: String::from("\u{0}"), ..Default::default() });
            if s.status != last.status {
                changed.insert("PlaybackStatus", Value::from(s.status.clone()));
            }
            if s.loop_status != last.loop_status {
                changed.insert("LoopStatus", Value::from(s.loop_status.clone()));
            }
            if s.shuffle != last.shuffle || self.last.is_none() {
                changed.insert("Shuffle", Value::from(s.shuffle));
            }
            let meta_changed = s.track_id != last.track_id
                || s.title != last.title
                || s.artist != last.artist
                || s.album != last.album
                || s.art != last.art
                || s.duration_us != last.duration_us;
            if meta_changed || self.last.is_none() {
                let m: HashMap<String, Value> = metadata(s).into_iter().map(|(k, v)| (k, Value::from(v))).collect();
                changed.insert("Metadata", Value::from(m));
            }
            if s.volume != last.volume || self.last.is_none() {
                changed.insert("Volume", Value::from(s.volume));
            }
            for (key, now, before) in [
                ("CanGoNext", s.can_next, last.can_next),
                ("CanGoPrevious", s.can_previous, last.can_previous),
                ("CanPlay", s.can_play, last.can_play),
                ("CanPause", s.can_pause, last.can_pause),
                ("CanSeek", s.can_seek, last.can_seek),
            ] {
                if now != before || self.last.is_none() {
                    changed.insert(key, Value::from(now));
                }
            }
            self.last = Some(s.clone());
            if !changed.is_empty() {
                let _ = self.conn.emit_signal(
                    None::<&str>,
                    PATH,
                    "org.freedesktop.DBus.Properties",
                    "PropertiesChanged",
                    &(PLAYER, changed, Vec::<String>::new()),
                );
            }
        }

        fn seeked(&mut self, position: i64) {
            let _ = self.conn.emit_signal(None::<&str>, PATH, PLAYER, "Seeked", &(position,));
        }
    }
}

#[cfg(windows)]
mod smtc {
    use windows::core::HSTRING;
    use windows::Foundation::{TimeSpan, TypedEventHandler, Uri};
    use windows::Media::*;
    use windows::Storage::StorageFile;
    use windows::Storage::Streams::RandomAccessStreamReference;
    use windows::Win32::Foundation::HWND;
    use windows::Win32::System::WinRT::ISystemMediaTransportControlsInterop;

    use super::*;

    pub struct Smtc {
        controls: SystemMediaTransportControls,
        last: Option<MediaState>,
    }

    pub fn start(shared: SharedState, cmd: CommandSink, window: Option<isize>) -> Option<Box<dyn Backend>> {
        let hwnd = window?;
        let _ = shared;
        let controls: SystemMediaTransportControls = unsafe {
            let interop: ISystemMediaTransportControlsInterop =
                windows::core::factory::<SystemMediaTransportControls, ISystemMediaTransportControlsInterop>().ok()?;
            interop.GetForWindow(HWND(hwnd as _)).ok()?
        };
        controls.SetIsEnabled(true).ok()?;
        controls.SetIsStopEnabled(true).ok()?;
        let c = cmd.clone();
        controls
            .ButtonPressed(&TypedEventHandler::new(move |_, args: &Option<SystemMediaTransportControlsButtonPressedEventArgs>| {
                if let Some(args) = args {
                    let command = match args.Button()? {
                        SystemMediaTransportControlsButton::Play => Some(MediaCommand::Play),
                        SystemMediaTransportControlsButton::Pause => Some(MediaCommand::Pause),
                        SystemMediaTransportControlsButton::Stop => Some(MediaCommand::Stop),
                        SystemMediaTransportControlsButton::Next => Some(MediaCommand::Next),
                        SystemMediaTransportControlsButton::Previous => Some(MediaCommand::Previous),
                        _ => None,
                    };
                    if let Some(command) = command {
                        c(command);
                    }
                }
                Ok(())
            }))
            .ok()?;
        let c = cmd.clone();
        let _ = controls.PlaybackPositionChangeRequested(&TypedEventHandler::new(
            move |_, args: &Option<PlaybackPositionChangeRequestedEventArgs>| {
                if let Some(args) = args {
                    let pos = args.RequestedPlaybackPosition()?.Duration / 10;
                    c(MediaCommand::SetPosition(String::new(), pos));
                }
                Ok(())
            },
        ));
        let c = cmd.clone();
        let _ = controls.ShuffleEnabledChangeRequested(&TypedEventHandler::new(
            move |_, args: &Option<ShuffleEnabledChangeRequestedEventArgs>| {
                if let Some(args) = args {
                    c(MediaCommand::Shuffle(args.RequestedShuffleEnabled()?));
                }
                Ok(())
            },
        ));
        let c = cmd;
        let _ = controls.AutoRepeatModeChangeRequested(&TypedEventHandler::new(
            move |_, args: &Option<AutoRepeatModeChangeRequestedEventArgs>| {
                if let Some(args) = args {
                    let mode = match args.RequestedAutoRepeatMode()? {
                        MediaPlaybackAutoRepeatMode::Track => "Track",
                        MediaPlaybackAutoRepeatMode::List => "Playlist",
                        _ => "None",
                    };
                    c(MediaCommand::LoopStatus(mode.into()));
                }
                Ok(())
            },
        ));
        Some(Box::new(Smtc { controls, last: None }))
    }

    fn thumbnail(art: &str) -> Option<RandomAccessStreamReference> {
        if art.starts_with("http://") || art.starts_with("https://") {
            let uri = Uri::CreateUri(&HSTRING::from(art)).ok()?;
            return RandomAccessStreamReference::CreateFromUri(&uri).ok();
        }
        let path = url::Url::parse(art).ok()?.to_file_path().ok()?;
        let file = StorageFile::GetFileFromPathAsync(&HSTRING::from(path.as_os_str())).ok()?.get().ok()?;
        RandomAccessStreamReference::CreateFromFile(&file).ok()
    }

    impl Backend for Smtc {
        fn update(&mut self, s: &MediaState, position: i64) {
            let c = &self.controls;
            let _ = c.SetIsPlayEnabled(s.can_play);
            let _ = c.SetIsPauseEnabled(s.can_pause);
            let _ = c.SetIsNextEnabled(s.can_next);
            let _ = c.SetIsPreviousEnabled(s.can_previous);
            let _ = c.SetPlaybackStatus(match s.status.as_str() {
                "Playing" => MediaPlaybackStatus::Playing,
                "Paused" => MediaPlaybackStatus::Paused,
                _ => MediaPlaybackStatus::Stopped,
            });
            let _ = c.SetShuffleEnabled(s.shuffle);
            let _ = c.SetAutoRepeatMode(match s.loop_status.as_str() {
                "Track" => MediaPlaybackAutoRepeatMode::Track,
                "Playlist" => MediaPlaybackAutoRepeatMode::List,
                _ => MediaPlaybackAutoRepeatMode::None,
            });
            let meta_changed = self.last.as_ref().map_or(true, |l| {
                l.title != s.title || l.artist != s.artist || l.album != s.album || l.art != s.art
            });
            if meta_changed {
                if let Ok(updater) = c.DisplayUpdater() {
                    let _ = updater.SetType(MediaPlaybackType::Music);
                    if let Ok(props) = updater.MusicProperties() {
                        let _ = props.SetTitle(&HSTRING::from(s.title.as_str()));
                        let _ = props.SetArtist(&HSTRING::from(s.artist.as_str()));
                        let _ = props.SetAlbumTitle(&HSTRING::from(s.album.as_str()));
                    }
                    if let Some(thumb) = thumbnail(&s.art) {
                        let _ = updater.SetThumbnail(&thumb);
                    }
                    let _ = updater.Update();
                }
            }
            if let Ok(tl) = SystemMediaTransportControlsTimelineProperties::new() {
                let end = if s.can_seek { s.duration_us * 10 } else { 0 };
                let pos = if s.can_seek { position * 10 } else { 0 };
                let _ = tl.SetStartTime(TimeSpan { Duration: 0 });
                let _ = tl.SetMinSeekTime(TimeSpan { Duration: 0 });
                let _ = tl.SetEndTime(TimeSpan { Duration: end });
                let _ = tl.SetMaxSeekTime(TimeSpan { Duration: end });
                let _ = tl.SetPosition(TimeSpan { Duration: pos });
                let _ = c.UpdateTimelineProperties(&tl);
            }
            self.last = Some(s.clone());
        }

        fn seeked(&mut self, position: i64) {
            if let Some(s) = self.last.clone() {
                self.update(&s, position);
            }
        }
    }

    impl Drop for Smtc {
        fn drop(&mut self) {
            let _ = self.controls.SetIsEnabled(false);
        }
    }
}
