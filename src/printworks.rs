
use std::io::{Read, Write};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

pub use crate::printworks_data::*;
use crate::paths;

pub const ONGOING_SUFFIX: &str = " (Ongoing)";
const ARCHIVE_BASE: &str = "https://archive.org/download/touhouprintworks/";
const USER_AGENT: &str = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0";

pub fn folder_name(name: &str) -> String {
    name.strip_suffix(ONGOING_SUFFIX).unwrap_or(name).replace('/', "-").replace('\0', "").trim().to_string()
}

pub fn download_root() -> PathBuf {
    paths::data_dir().join("PrintWorks")
}

pub fn pdf_dir(name: &str) -> PathBuf {
    download_root().join(folder_name(name))
}

pub fn pdf_path(name: &str) -> PathBuf {
    pdf_dir(name).join(format!("{}.pdf", folder_name(name)))
}

pub fn is_downloaded(name: &str) -> bool {
    pdf_path(name).is_file()
}

pub fn pdf_url(name: &str) -> Option<String> {
    let file = archive_file(name)?;
    let quoted: String = file
        .bytes()
        .map(|b| match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' | b'/' => (b as char).to_string(),
            _ => format!("%{b:02X}"),
        })
        .collect();
    Some(format!("{ARCHIVE_BASE}{quoted}"))
}

pub fn thumb_path(cover: &str) -> PathBuf {
    paths::assets_dir().join("print_thumbnails").join(cover)
}

fn agent() -> ureq::Agent {
    ureq::AgentBuilder::new()
        .timeout_connect(std::time::Duration::from_secs(30))
        .timeout_read(std::time::Duration::from_secs(30))
        .redirects(10)
        .build()
}

fn request(method: &str, url: &str) -> Result<ureq::Response, ureq::Error> {
    agent()
        .request(method, url)
        .set("User-Agent", USER_AGENT)
        .set("Accept", "application/pdf,*/*")
        .set("Accept-Encoding", "identity")
        .call()
}

fn is_web_page(resp: &ureq::Response) -> bool {
    matches!(resp.content_type(), "text/html" | "application/xhtml+xml")
}

fn host(resp: &ureq::Response) -> String {
    url::Url::parse(resp.get_url()).ok().and_then(|u| u.host_str().map(String::from)).unwrap_or_else(|| "the server".into())
}

pub fn fetch_size(url: &str) -> Option<u64> {
    static CACHE: Mutex<Vec<(String, Option<u64>)>> = Mutex::new(Vec::new());
    if let Some((_, size)) = CACHE.lock().unwrap().iter().find(|(u, _)| u == url) {
        return *size;
    }
    let mut result = None;
    for method in ["HEAD", "GET"] {
        if let Ok(resp) = request(method, url) {
            if is_web_page(&resp) {
                break;
            }
            if let Some(n) = resp.header("Content-Length").and_then(|v| v.trim().parse::<u64>().ok()).filter(|&n| n > 0) {
                result = Some(n);
                break;
            }
        }
    }
    CACHE.lock().unwrap().push((url.to_string(), result));
    result
}

pub enum DownloadError {
    Cancelled,
    Failed(String),
}

fn describe(e: ureq::Error) -> String {
    match e {
        ureq::Error::Status(code, _) => format!("The server answered with an error (HTTP {code})."),
        ureq::Error::Transport(t) => {
            if t.kind() == ureq::ErrorKind::Io && t.to_string().to_lowercase().contains("timed out") {
                "The connection timed out. Please try again.".into()
            } else {
                "Could not reach the download server. Check your internet connection.".into()
            }
        }
    }
}

fn free_space_ok(_dir: &std::path::Path, _needed: u64) -> bool {
    #[cfg(unix)]
    unsafe {
        use std::os::unix::ffi::OsStrExt;
        let c = std::ffi::CString::new(_dir.as_os_str().as_bytes()).unwrap_or_default();
        let mut st: libc::statvfs = std::mem::zeroed();
        if libc::statvfs(c.as_ptr(), &mut st) == 0 {
            return (st.f_bavail as u64) * (st.f_frsize as u64) >= _needed;
        }
    }
    true
}

pub static ACTIVE: Mutex<Vec<String>> = Mutex::new(Vec::new());

pub fn download_pdf(name: &str, url: &str, cancel: Arc<AtomicBool>, mut progress: impl FnMut(u64, Option<u64>)) -> Result<(), DownloadError> {
    let dir = pdf_dir(name);
    let fin = pdf_path(name);
    let part = fin.with_extension("pdf.part");
    let cleanup = || {
        let _ = std::fs::remove_file(&part);
        if !fin.is_file() {
            let _ = std::fs::remove_dir(&dir);
        }
    };
    let result = (|| -> Result<(), DownloadError> {
        std::fs::create_dir_all(&dir).map_err(|e| DownloadError::Failed(format!("Download failed: {e}")))?;
        let _ = std::fs::remove_file(&part);
        let resp = request("GET", url).map_err(|e| DownloadError::Failed(describe(e)))?;
        if is_web_page(&resp) {
            return Err(DownloadError::Failed(format!(
                "This link opens a web page ({}), not the PDF itself. It needs to be a direct download URL.",
                host(&resp)
            )));
        }
        let total = resp.header("Content-Length").and_then(|v| v.trim().parse::<u64>().ok()).filter(|&n| n > 0);
        if let Some(t) = total {
            if !free_space_ok(&dir, t + (1 << 20)) {
                return Err(DownloadError::Failed("Not enough free disk space for this download.".into()));
            }
        }
        let content_type = resp.content_type().to_string();
        let host = host(&resp);
        let mut reader = resp.into_reader();
        let mut out = std::fs::File::create(&part).map_err(|e| DownloadError::Failed(format!("Download failed: {e}")))?;
        let mut buf = vec![0u8; 64 * 1024];
        let mut done = 0u64;
        let mut first = true;
        loop {
            if cancel.load(Ordering::Relaxed) {
                return Err(DownloadError::Cancelled);
            }
            let n = reader.read(&mut buf).map_err(|e| {
                if e.kind() == std::io::ErrorKind::TimedOut {
                    DownloadError::Failed("The connection timed out. Please try again.".into())
                } else {
                    DownloadError::Failed(format!("Download failed: {e}"))
                }
            })?;
            if n == 0 {
                break;
            }
            if first {
                if !buf[..n].starts_with(b"%PDF") {
                    return Err(DownloadError::Failed(format!("The server did not send a PDF file (got {content_type} from {host}).")));
                }
                first = false;
            }
            out.write_all(&buf[..n]).map_err(|e| {
                if e.raw_os_error() == Some(28) {
                    DownloadError::Failed("Not enough free disk space for this download.".into())
                } else {
                    DownloadError::Failed(format!("Download failed: {e}"))
                }
            })?;
            done += n as u64;
            progress(done, total);
        }
        out.sync_all().ok();
        if first {
            return Err(DownloadError::Failed("The downloaded file was empty.".into()));
        }
        if total.map_or(false, |t| t != done) {
            return Err(DownloadError::Failed("The download ended early. Please try again.".into()));
        }
        if cancel.load(Ordering::Relaxed) {
            return Err(DownloadError::Cancelled);
        }
        std::fs::rename(&part, &fin).map_err(|e| DownloadError::Failed(format!("Download failed: {e}")))?;
        Ok(())
    })();
    if result.is_err() {
        cleanup();
    }
    result
}

pub fn delete_download(name: &str) {
    let _ = std::fs::remove_file(pdf_path(name));
    if !ACTIVE.lock().unwrap().iter().any(|n| n == name) {
        let _ = std::fs::remove_file(pdf_path(name).with_extension("pdf.part"));
        let _ = std::fs::remove_dir(pdf_dir(name));
    }
}


fn progress_file() -> PathBuf {
    paths::data_dir().join("reading_progress.json")
}

pub fn load_progress(key: &str) -> Option<i64> {
    let data: serde_json::Map<String, serde_json::Value> = crate::util::read_json(&progress_file())?;
    data.get(key)?.as_i64()
}

pub fn save_progress(key: &str, page: i64) {
    let mut data: serde_json::Map<String, serde_json::Value> = crate::util::read_json(&progress_file()).unwrap_or_default();
    data.insert(key.into(), page.into());
    let _ = crate::util::write_json_atomic(&progress_file(), &data);
}
