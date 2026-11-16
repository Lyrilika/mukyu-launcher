
use anyhow::Result;
use serde_json::Value;

pub const RADIO_URL: &str = "https://stream.gensokyoradio.net/1";
pub const NOW_PLAYING_URL: &str = "https://gensokyoradio.net/api/station/playing/";
pub const LOGO_URL: &str = "https://gensokyoradio.net/images/assets/gr-logo-placeholder.png";
pub const USER_AGENT: &str = concat!(
    "MukyuLauncher/",
    env!("CARGO_PKG_VERSION"),
    " (Gensokyo Radio integration)"
);

#[derive(Clone, Debug, Default, PartialEq)]
pub struct NowPlaying {
    pub title: String,
    pub artist: String,
    pub album: String,
    pub circle: String,
    pub year: String,
    pub album_art: String,
    pub remaining: Option<f64>,
}

fn agent() -> ureq::Agent {
    ureq::AgentBuilder::new()
        .timeout_connect(std::time::Duration::from_secs(12))
        .timeout_read(std::time::Duration::from_secs(12))
        .build()
}

pub fn fetch_bytes(url: &str) -> Result<Vec<u8>> {
    let resp = agent().get(url).set("User-Agent", USER_AGENT).call()?;
    let mut data = Vec::new();
    std::io::Read::read_to_end(&mut resp.into_reader().take_limit(32 * 1024 * 1024), &mut data)?;
    Ok(data)
}

trait TakeLimit: std::io::Read + Sized {
    fn take_limit(self, n: u64) -> std::io::Take<Self> {
        std::io::Read::take(self, n)
    }
}
impl<R: std::io::Read> TakeLimit for R {}

fn first(map: Option<&Value>, keys: &[&str]) -> Option<String> {
    let map = map?.as_object()?;
    keys.iter().find_map(|k| match map.get(*k)? {
        Value::Null => None,
        Value::String(s) if s.is_empty() => None,
        Value::String(s) => Some(s.clone()),
        other => Some(other.to_string()),
    })
}

pub fn fetch_now_playing() -> Result<NowPlaying> {
    let payload: Value = agent().get(NOW_PLAYING_URL).set("User-Agent", USER_AGENT).call()?.into_json()?;
    let song = payload.get("SONGINFO");
    let misc = payload.get("MISC");
    let times = payload.get("SONGTIMES");
    Ok(NowPlaying {
        title: first(song, &["TITLE", "title"]).unwrap_or_else(|| "Gensokyo Radio".into()),
        artist: first(song, &["ARTIST", "artist"]).unwrap_or_else(|| "Live radio".into()),
        album: first(song, &["ALBUM", "album"]).unwrap_or_else(|| "Gensokyo Radio".into()),
        circle: first(song, &["CIRCLE", "circle"]).unwrap_or_default(),
        year: first(song, &["YEAR", "year"]).unwrap_or_default(),
        album_art: first(misc, &["ALBUMART", "album_art", "albumart"]).unwrap_or_default(),
        remaining: first(times, &["REMAINING", "remaining"]).and_then(|v| v.trim_matches('"').parse().ok()),
    })
}

pub fn album_art_urls(album_art: &str) -> Vec<String> {
    if album_art.is_empty() {
        return vec![LOGO_URL.into()];
    }
    if album_art.starts_with("http://") || album_art.starts_with("https://") {
        return vec![album_art.into()];
    }
    let name: String = album_art
        .trim_start_matches('/')
        .bytes()
        .map(|b| match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' | b'/' => (b as char).to_string(),
            _ => format!("%{b:02X}"),
        })
        .collect();
    let base = "https://gensokyoradio.net/images/albums/";
    vec![format!("{base}original/{name}"), format!("{base}500/{name}")]
}
