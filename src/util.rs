use std::io::Write;
use std::path::{Path, PathBuf};

use serde::de::DeserializeOwned;
use serde::Serialize;

pub fn write_json_atomic<T: Serialize + ?Sized>(path: &Path, value: &T) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let mut tmp = path.as_os_str().to_owned();
    tmp.push(".tmp");
    let tmp = PathBuf::from(tmp);
    {
        let mut file = std::fs::File::create(&tmp)?;
        let text = serde_json::to_string_pretty(value).map_err(std::io::Error::other)?;
        file.write_all(text.as_bytes())?;
        file.write_all(b"\n")?;
        file.sync_all().ok();
    }
    std::fs::rename(&tmp, path)
}

pub fn read_json<T: DeserializeOwned>(path: &Path) -> Option<T> {
    let text = std::fs::read_to_string(path).ok()?;
    let text = text.trim();
    if text.is_empty() {
        return None;
    }
    serde_json::from_str(text).ok()
}

pub fn fmt_size(n: Option<u64>) -> String {
    let Some(n) = n else { return "Unknown".into() };
    let mut value = n as f64;
    for unit in ["B", "KB", "MB", "GB"] {
        if value < 1024.0 || unit == "GB" {
            return if unit == "B" { format!("{} B", value as u64) } else { format!("{value:.1} {unit}") };
        }
        value /= 1024.0;
    }
    unreachable!()
}

pub fn fmt_time(seconds: f64) -> String {
    let s = seconds.max(0.0) as u64;
    format!("{}:{:02}", s / 60, s % 60)
}

pub fn fmt_session(seconds: u64) -> String {
    let (h, rest) = (seconds / 3600, seconds % 3600);
    let (m, s) = (rest / 60, rest % 60);
    if h > 0 { format!("{h}:{m:02}:{s:02}") } else { format!("{m}:{s:02}") }
}

pub fn sanitize_component(text: &str) -> String {
    let re = regex::Regex::new(r"[^A-Za-z0-9._-]+").unwrap();
    re.replace_all(text, "_").into_owned()
}

pub fn decode_cp932(raw: &[u8]) -> String {
    let (text, _, had_errors) = encoding_rs::SHIFT_JIS.decode(raw);
    if !had_errors {
        return text.into_owned();
    }
    if let Ok(text) = std::str::from_utf8(raw) {
        return text.to_string();
    }
    raw.iter().map(|&b| b as char).collect()
}

pub fn encode_cp932(text: &str) -> Vec<u8> {
    let (bytes, _, _) = encoding_rs::SHIFT_JIS.encode(text);
    bytes.into_owned()
}

pub fn http_agent() -> ureq::Agent {
    ureq::AgentBuilder::new()
        .timeout_connect(std::time::Duration::from_secs(20))
        .timeout_read(std::time::Duration::from_secs(30))
        .build()
}
