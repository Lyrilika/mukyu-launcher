use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

use anyhow::{anyhow, bail, Context, Result};
use serde_json::Value;
use sha2::{Digest, Sha256};

use crate::paths;

pub const REPO: &str = "Lyrilika/mukyu-launcher";
pub const APPIMAGE_ASSET: &str =
    if cfg!(target_arch = "aarch64") { "Mukyu_Launcher-aarch64.AppImage" } else { "Mukyu_Launcher-x86_64.AppImage" };
pub const INSTALLER_ASSET: &str =
    if cfg!(target_arch = "aarch64") { "Mukyu_Launcher_Setup_arm64.exe" } else { "Mukyu_Launcher_Setup.exe" };
const USER_AGENT: &str = "Mukyu-Launcher-Updater";
const MAX_JSON_BYTES: u64 = 4 * 1024 * 1024;
const MAX_ASSET_BYTES: u64 = 1024 * 1024 * 1024;

#[derive(Clone, Debug, PartialEq)]
pub struct Release {
    pub version: String,
    pub page_url: String,
    pub asset_url: Option<String>,
    pub asset_size: u64,
    pub asset_sha256: Option<String>,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Method {
    ReplaceAppImage,
    WindowsInstaller,
    SaveInstaller,
    OpenPage,
}

pub fn current_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[derive(Debug, PartialEq, Eq, PartialOrd, Ord)]
struct Version {
    core: (u64, u64, u64),
    stable: bool,
    pre: String,
}

fn parse_version(text: &str) -> Option<Version> {
    let text = text.trim().trim_start_matches(['v', 'V']);
    let text = text.split('+').next()?;
    let (core, pre) = match text.split_once('-') {
        Some((c, p)) => (c, p.to_string()),
        None => (text, String::new()),
    };
    let mut parts = core.split('.').map(|p| p.parse::<u64>().ok());
    let major = parts.next()??;
    let minor = parts.next().unwrap_or(Some(0))?;
    let patch = parts.next().unwrap_or(Some(0))?;
    if parts.next().is_some() {
        return None;
    }
    Some(Version { core: (major, minor, patch), stable: pre.is_empty(), pre })
}

pub fn is_newer(candidate: &str, current: &str) -> bool {
    match (parse_version(candidate), parse_version(current)) {
        (Some(a), Some(b)) => a > b,
        _ => false,
    }
}

fn test_api() -> Option<String> {
    if !cfg!(debug_assertions) {
        return None;
    }
    std::env::var("MUKYU_RELEASES_API").ok().map(|s| s.trim_end_matches('/').to_string())
}

fn releases_api() -> String {
    test_api().unwrap_or_else(|| format!("https://api.github.com/repos/{REPO}/releases"))
}

fn trusted_url(url: &str) -> bool {
    let Ok(u) = url::Url::parse(url) else { return false };
    if test_api().is_some() && u.scheme() == "http" && u.host_str() == Some("127.0.0.1") {
        return true;
    }
    if u.scheme() != "https" || !u.username().is_empty() || u.password().is_some() || u.port().is_some() {
        return false;
    }
    match u.host_str() {
        Some(h) => h == "github.com" || h == "api.github.com" || h.ends_with(".githubusercontent.com"),
        None => false,
    }
}

fn safe_page(url: Option<&str>, fallback: String) -> String {
    match url {
        Some(u) if u.starts_with(&format!("https://github.com/{REPO}/")) && !u.chars().any(char::is_whitespace) => u.to_string(),
        _ => fallback,
    }
}

fn valid_version_text(v: &str) -> bool {
    !v.is_empty() && v.len() <= 40 && v.chars().all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '-' | '+'))
}

fn api_url() -> String {
    format!("{}/latest", releases_api())
}

fn get_json(url: &str) -> Result<Value> {
    if !trusted_url(url) {
        bail!("Refusing to contact an untrusted update server.");
    }
    let resp = agent()
        .get(url)
        .set("Accept", "application/vnd.github+json")
        .set("User-Agent", USER_AGENT)
        .call()?;
    if !trusted_url(resp.get_url()) {
        bail!("The update server redirected to an untrusted address.");
    }
    let mut body = Vec::new();
    resp.into_reader().take(MAX_JSON_BYTES + 1).read_to_end(&mut body)?;
    if body.len() as u64 > MAX_JSON_BYTES {
        bail!("The update server sent too much data.");
    }
    Ok(serde_json::from_slice(&body)?)
}

fn agent() -> ureq::Agent {
    ureq::AgentBuilder::new()
        .timeout_connect(std::time::Duration::from_secs(15))
        .timeout_read(std::time::Duration::from_secs(60))
        .redirects(10)
        .build()
}

pub fn asset_name() -> &'static str {
    if cfg!(windows) {
        INSTALLER_ASSET
    } else {
        APPIMAGE_ASSET
    }
}

pub fn parse_release(json: &Value, asset: &str) -> Option<Release> {
    if json.get("draft").and_then(Value::as_bool) == Some(true) || json.get("prerelease").and_then(Value::as_bool) == Some(true) {
        return None;
    }
    let tag = json.get("tag_name")?.as_str()?;
    parse_version(tag)?;
    let version = tag.trim_start_matches(['v', 'V']).to_string();
    if !valid_version_text(&version) {
        return None;
    }
    let page_url = safe_page(json.get("html_url").and_then(Value::as_str), format!("https://github.com/{REPO}/releases/latest"));
    let found = json.get("assets").and_then(Value::as_array).and_then(|assets| {
        assets.iter().find(|a| a.get("name").and_then(Value::as_str) == Some(asset))
    });
    let asset_url = found
        .and_then(|a| a.get("browser_download_url"))
        .and_then(Value::as_str)
        .filter(|u| trusted_url(u))
        .map(String::from);
    let asset_size = found.and_then(|a| a.get("size")).and_then(Value::as_u64).unwrap_or(0);
    let asset_sha256 = found
        .and_then(|a| a.get("digest"))
        .and_then(Value::as_str)
        .and_then(|d| d.strip_prefix("sha256:"))
        .filter(|h| h.len() == 64 && h.chars().all(|c| c.is_ascii_hexdigit()))
        .map(|h| h.to_ascii_lowercase());
    Some(Release { version, page_url, asset_url, asset_size, asset_sha256 })
}

pub fn check() -> Result<Option<Release>> {
    if !prefs().auto_check {
        return Ok(None);
    }
    let release = check_now()?;
    if release.as_ref().is_some_and(|r| prefs().ignored_version.as_deref() == Some(r.version.as_str())) {
        return Ok(None);
    }
    Ok(release)
}

pub fn check_now() -> Result<Option<Release>> {
    let json = get_json(&api_url())?;
    let Some(release) = parse_release(&json, asset_name()) else { return Ok(None) };
    Ok(is_newer(&release.version, current_version()).then_some(release))
}

#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Prefs {
    #[serde(default = "default_true")]
    pub auto_check: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub ignored_version: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub updated_from: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub updated_to: Option<String>,
    #[serde(default = "default_true")]
    pub show_changelog: bool,
}

fn default_true() -> bool {
    true
}

impl Default for Prefs {
    fn default() -> Self {
        Prefs { auto_check: true, ignored_version: None, updated_from: None, updated_to: None, show_changelog: true }
    }
}

fn state_file() -> PathBuf {
    paths::config_dir().join("update.json")
}

pub fn prefs() -> Prefs {
    crate::util::read_json(&state_file()).unwrap_or_default()
}

fn edit_prefs(f: impl FnOnce(&mut Prefs)) {
    let mut p = prefs();
    f(&mut p);
    let _ = crate::util::write_json_atomic(&state_file(), &p);
}

pub fn ignore_version(version: &str) {
    edit_prefs(|p| p.ignored_version = Some(version.to_string()));
}

pub fn set_auto_check(enabled: bool) {
    edit_prefs(|p| p.auto_check = enabled);
}

pub fn set_show_changelog(enabled: bool) {
    edit_prefs(|p| p.show_changelog = enabled);
}

pub fn mark_updated(to: &str) {
    let from = current_version().to_string();
    let to = to.to_string();
    edit_prefs(|p| {
        p.updated_from = Some(from);
        p.updated_to = Some(to);
    });
}

pub fn take_update_record() -> Option<String> {
    let p = prefs();
    let to = p.updated_to?;
    let current = current_version();
    if is_newer(&to, current) {
        return None;
    }
    edit_prefs(|p| {
        p.updated_from = None;
        p.updated_to = None;
    });
    (to == current).then(|| p.updated_from.unwrap_or_default())
}

pub struct ReleaseNotes {
    pub text: String,
    pub page_url: String,
}

pub fn release_notes(version: &str) -> Result<ReleaseNotes> {
    let json = get_json(&format!("{}/tags/v{version}", releases_api()))?;
    let body = json.get("body").and_then(Value::as_str).unwrap_or("");
    let page_url = safe_page(json.get("html_url").and_then(Value::as_str), format!("https://github.com/{REPO}/releases/tag/v{version}"));
    Ok(ReleaseNotes { text: markdown_to_text(body), page_url })
}

pub fn markdown_to_text(md: &str) -> String {
    let link = regex::Regex::new(r"!?\[([^\]]*)\]\([^)]*\)").unwrap();
    let emphasis = regex::Regex::new(r"(\*\*|__|\*|_|~~|`)([^*_~`]+)(\*\*|__|\*|_|~~|`)").unwrap();
    let html = regex::Regex::new(r"<[^>]+>").unwrap();
    let mut out: Vec<String> = Vec::new();
    let mut in_code = false;
    for raw in md.replace("\r\n", "\n").lines() {
        let trimmed = raw.trim_end();
        if trimmed.trim_start().starts_with("```") {
            in_code = !in_code;
            continue;
        }
        if in_code {
            out.push(format!("    {trimmed}"));
            continue;
        }
        let indent = trimmed.len() - trimmed.trim_start().len();
        let mut line = trimmed.trim_start().to_string();
        let mut prefix = String::new();
        if let Some(rest) = line.strip_prefix('#') {
            line = rest.trim_start_matches('#').trim().to_string();
            if !out.last().map_or(true, |l| l.is_empty()) {
                out.push(String::new());
            }
        } else if let Some(rest) = line.strip_prefix("- ").or_else(|| line.strip_prefix("* ")).or_else(|| line.strip_prefix("+ ")) {
            prefix = format!("{}•  ", "    ".repeat(indent / 2));
            line = rest.to_string();
        } else if let Some(rest) = line.strip_prefix("> ") {
            line = rest.to_string();
        } else if line.chars().all(|c| c == '-' || c == '*' || c == '_') && line.len() >= 3 {
            line = String::new();
        }
        let line = link.replace_all(&line, "$1");
        let line = html.replace_all(&line, "");
        let mut line = line.into_owned();
        loop {
            let next = emphasis.replace_all(&line, "$2").into_owned();
            if next == line {
                break;
            }
            line = next;
        }
        out.push(format!("{prefix}{line}"));
    }
    let mut text = out.join("\n");
    while text.contains("\n\n\n") {
        text = text.replace("\n\n\n", "\n\n");
    }
    text.trim().to_string()
}

pub fn running_appimage() -> Option<PathBuf> {
    if !cfg!(target_os = "linux") {
        return None;
    }
    let path = PathBuf::from(std::env::var_os("APPIMAGE")?);
    path.is_file().then_some(path)
}

fn windows_install_dir() -> Option<PathBuf> {
    if !cfg!(windows) {
        return None;
    }
    let dir = std::env::current_exe().ok()?.parent()?.to_path_buf();
    let installed = std::fs::read_dir(&dir).ok()?.flatten().any(|e| {
        let name = e.file_name().to_string_lossy().to_ascii_lowercase();
        name.starts_with("unins") && name.ends_with(".exe")
    });
    installed.then_some(dir)
}

pub fn method(release: &Release) -> Method {
    if release.asset_url.is_none() || release.asset_sha256.is_none() || release.asset_size == 0 || release.asset_size > MAX_ASSET_BYTES {
        return Method::OpenPage;
    }
    if running_appimage().is_some() {
        return Method::ReplaceAppImage;
    }
    if cfg!(windows) {
        return if windows_install_dir().is_some() { Method::WindowsInstaller } else { Method::SaveInstaller };
    }
    Method::OpenPage
}

pub struct Progress {
    pub done: u64,
    pub total: u64,
}

fn download(release: &Release, dest: &Path, cancel: &AtomicBool, on_progress: &dyn Fn(Progress)) -> Result<()> {
    let url = release.asset_url.as_deref().filter(|u| trusted_url(u)).ok_or_else(|| anyhow!("This release has no download for your system."))?;
    let expected = release
        .asset_sha256
        .as_deref()
        .ok_or_else(|| anyhow!("This release can't be verified, so it wasn't downloaded. Get it from the release page instead."))?;
    let total = release.asset_size;
    if total == 0 || total > MAX_ASSET_BYTES {
        bail!("This release has an invalid download size.");
    }
    let resp = agent().get(url).set("User-Agent", USER_AGENT).call().map_err(|e| match e {
        ureq::Error::Status(code, _) => anyhow!("The download server answered with an error (HTTP {code})."),
        ureq::Error::Transport(_) => anyhow!("Could not reach the download server. Check your internet connection."),
    })?;
    if !trusted_url(resp.get_url()) {
        bail!("The download was redirected to an untrusted address.");
    }
    let mut reader = resp.into_reader().take(total + 1);
    let mut options = std::fs::OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut file = options.open(dest).with_context(|| format!("Could not write {}", dest.display()))?;
    let mut hasher = Sha256::new();
    let mut buf = vec![0u8; 128 * 1024];
    let mut done = 0u64;
    let mut last_report = std::time::Instant::now() - std::time::Duration::from_secs(1);
    loop {
        if cancel.load(Ordering::Relaxed) {
            bail!("cancelled");
        }
        let n = reader.read(&mut buf).context("The download was interrupted.")?;
        if n == 0 {
            break;
        }
        file.write_all(&buf[..n]).context("Could not save the download.")?;
        hasher.update(&buf[..n]);
        done += n as u64;
        if done > total {
            bail!("The download is larger than expected. Please try again.");
        }
        if last_report.elapsed() >= std::time::Duration::from_millis(100) {
            last_report = std::time::Instant::now();
            on_progress(Progress { done, total });
        }
    }
    file.sync_all().ok();
    drop(file);
    on_progress(Progress { done, total });
    if done != total {
        bail!("The download is incomplete. Please try again.");
    }
    if hex::encode(hasher.finalize()) != expected {
        bail!("The downloaded file is damaged (checksum mismatch). Please try again.");
    }
    Ok(())
}

fn file_sha256(path: &Path) -> Option<String> {
    let mut f = std::fs::File::open(path).ok()?;
    let mut hasher = Sha256::new();
    let mut buf = vec![0u8; 128 * 1024];
    loop {
        let n = f.read(&mut buf).ok()?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Some(hex::encode(hasher.finalize()))
}

fn still_verified(path: &Path, sha256: &str) -> bool {
    std::fs::symlink_metadata(path).map_or(false, |m| m.is_file()) && file_sha256(path).as_deref() == Some(sha256)
}

fn check_header(path: &Path, appimage: bool) -> Result<()> {
    let mut head = [0u8; 16];
    let mut f = std::fs::File::open(path)?;
    let n = f.read(&mut head)?;
    let ok = if appimage {
        n >= 11 && &head[..4] == b"\x7fELF" && &head[8..11] == b"AI\x02"
    } else {
        n >= 2 && &head[..2] == b"MZ"
    };
    if !ok {
        bail!("The downloaded file is not a valid {}.", if appimage { "AppImage" } else { "installer" });
    }
    Ok(())
}

pub fn short_path(path: &Path) -> String {
    let home = dirs::home_dir();
    let text = match home.as_deref().and_then(|h| path.strip_prefix(h).ok()) {
        Some(rest) if rest.as_os_str().is_empty() => "~".to_string(),
        Some(rest) => format!("~/{}", rest.display()),
        None => path.display().to_string(),
    };
    if text.chars().count() <= 48 {
        return text;
    }
    let parts: Vec<String> = path.components().map(|c| c.as_os_str().to_string_lossy().to_string()).collect();
    let tail = parts[parts.len().saturating_sub(2)..].join(std::path::MAIN_SEPARATOR_STR);
    format!("…{}{tail}", std::path::MAIN_SEPARATOR)
}

pub enum Applied {
    Replaced(PathBuf),
    InstallerStaged(PathBuf),
    InstallerSaved(PathBuf),
}

pub fn apply(release: &Release, method: Method, save_dir: Option<&Path>, cancel: &AtomicBool, on_progress: &dyn Fn(Progress)) -> Result<Applied> {
    match method {
        Method::ReplaceAppImage => {
            let target = running_appimage().ok_or_else(|| anyhow!("Mukyu Launcher is not running from an AppImage."))?;
            let target = target.canonicalize().unwrap_or(target);
            let dir = target.parent().ok_or_else(|| anyhow!("Invalid AppImage location."))?.to_path_buf();
            let name = target.file_name().ok_or_else(|| anyhow!("Invalid AppImage location."))?.to_string_lossy().to_string();
            let prefix = format!(".{name}.update-");
            if let Ok(entries) = std::fs::read_dir(&dir) {
                for entry in entries.flatten() {
                    let stale = entry.file_name().to_string_lossy().starts_with(&prefix)
                        && entry.file_type().map_or(false, |t| t.is_file());
                    if stale {
                        let _ = std::fs::remove_file(entry.path());
                    }
                }
            }
            let temp = dir.join(format!("{prefix}{}", std::process::id()));
            let result = (|| -> Result<()> {
                download(release, &temp, cancel, on_progress).map_err(|e| {
                    if e.chain().any(|c| c.downcast_ref::<std::io::Error>().map_or(false, |io| io.kind() == std::io::ErrorKind::PermissionDenied)) {
                        anyhow!("Mukyu Launcher can't write to {}. Move the AppImage to a folder you own and try again.", short_path(&dir))
                    } else {
                        e
                    }
                })?;
                check_header(&temp, true)?;
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    let mode = std::fs::metadata(&target).map(|m| m.permissions().mode()).unwrap_or(0o755) | 0o111;
                    std::fs::set_permissions(&temp, std::fs::Permissions::from_mode(mode & 0o7777))?;
                }
                std::fs::rename(&temp, &target).with_context(|| format!("Could not replace {}", target.display()))?;
                Ok(())
            })();
            if result.is_err() {
                let _ = std::fs::remove_file(&temp);
            }
            result.map(|_| Applied::Replaced(target))
        }
        Method::WindowsInstaller | Method::SaveInstaller => {
            let dir = match (method, save_dir) {
                (Method::SaveInstaller, Some(d)) => d.to_path_buf(),
                (Method::SaveInstaller, None) => bail!("Choose a folder for the installer."),
                _ => std::env::temp_dir().join("mukyulauncher-update"),
            };
            std::fs::create_dir_all(&dir).with_context(|| format!("Could not create {}", dir.display()))?;
            let file_name = if method == Method::SaveInstaller {
                INSTALLER_ASSET.to_string()
            } else {
                format!("{}-{}.exe", INSTALLER_ASSET.trim_end_matches(".exe"), release.version)
            };
            let dest = dir.join(file_name);
            let temp = dest.with_extension("exe.part");
            let _ = std::fs::remove_file(&temp);
            let result = (|| -> Result<()> {
                download(release, &temp, cancel, on_progress)?;
                check_header(&temp, false)?;
                let _ = std::fs::remove_file(&dest);
                std::fs::rename(&temp, &dest)?;
                Ok(())
            })();
            if result.is_err() {
                let _ = std::fs::remove_file(&temp);
            }
            result?;
            Ok(if method == Method::SaveInstaller { Applied::InstallerSaved(dest) } else { Applied::InstallerStaged(dest) })
        }
        Method::OpenPage => bail!("Automatic updates are not available for this build."),
    }
}

static PENDING_INSTALLER: Mutex<Option<(PathBuf, String)>> = Mutex::new(None);

pub fn set_pending_installer(path: PathBuf, sha256: String) {
    *PENDING_INSTALLER.lock().unwrap() = Some((path, sha256));
}

pub fn has_pending_installer() -> bool {
    PENDING_INSTALLER.lock().unwrap().is_some()
}

pub fn run_pending_installer(relaunch: bool) {
    let Some((installer, sha256)) = PENDING_INSTALLER.lock().unwrap().take() else { return };
    if !still_verified(&installer, &sha256) {
        let _ = std::fs::remove_file(&installer);
        return;
    }
    #[cfg(windows)]
    {
        let all_users = windows_install_dir()
            .and_then(|d| {
                let pf = std::env::var_os("ProgramFiles").map(PathBuf::from)?;
                Some(d.starts_with(pf))
            })
            .unwrap_or(false);
        let mut params = String::from("/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-");
        params.push_str(if all_users { " /ALLUSERS" } else { " /CURRENTUSER" });
        if relaunch {
            params.push_str(" /RELAUNCH");
        }
        windows_launch(&installer, &params, all_users);
    }
    #[cfg(not(windows))]
    {
        let _ = (installer, relaunch);
    }
}

#[cfg(windows)]
fn windows_launch(program: &Path, params: &str, elevate: bool) {
    use windows::core::{HSTRING, PCWSTR};
    use windows::Win32::UI::Shell::ShellExecuteW;
    use windows::Win32::UI::WindowsAndMessaging::SW_SHOWNORMAL;
    let verb = HSTRING::from(if elevate { "runas" } else { "open" });
    let file = HSTRING::from(program.as_os_str());
    let args = HSTRING::from(params);
    unsafe {
        ShellExecuteW(None, PCWSTR(verb.as_ptr()), PCWSTR(file.as_ptr()), PCWSTR(args.as_ptr()), PCWSTR::null(), SW_SHOWNORMAL);
    }
}

pub fn open_installer(path: &Path, sha256: &str) -> Result<()> {
    if !still_verified(path, sha256) {
        bail!("The saved installer was changed or removed. Download the update again.");
    }
    #[cfg(windows)]
    windows_launch(path, "", false);
    #[cfg(not(windows))]
    {
        let _ = open::that_detached(path);
    }
    Ok(())
}

pub fn relaunch_appimage(path: &Path) -> Result<()> {
    let mut cmd = std::process::Command::new("/bin/sh");
    cmd.arg("-c")
        .arg("while kill -0 \"$1\" 2>/dev/null; do sleep 0.2; done; exec \"$2\"")
        .arg("sh")
        .arg(std::process::id().to_string())
        .arg(path)
        .env_clear()
        .envs(crate::platform::host_env().into_iter().filter(|(k, _)| !matches!(k.as_str(), "APPIMAGE" | "APPDIR" | "ARGV0" | "OWD" | "MUKYU_ROOT")))
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null());
    crate::platform::detach(&mut cmd);
    cmd.spawn().context("Could not restart Mukyu Launcher")?;
    Ok(())
}

#[cfg(windows)]
pub fn hold_instance_mutex() {
    use windows::core::w;
    use windows::Win32::System::Threading::CreateMutexW;
    unsafe {
        let _ = CreateMutexW(None, false, w!("MukyuLauncherRunning"));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_order() {
        assert!(is_newer("1.0.1", "1.0.0"));
        assert!(is_newer("v2.0.0", "1.9.9"));
        assert!(is_newer("1.10.0", "1.9.0"));
        assert!(is_newer("1.0.0", "1.0.0-beta.1"));
        assert!(!is_newer("1.0.0-beta.1", "1.0.0"));
        assert!(!is_newer("1.0.0", "1.0.0"));
        assert!(!is_newer("0.9.0", "1.0.0"));
        assert!(!is_newer("garbage", "1.0.0"));
    }

    #[test]
    fn release_parsing() {
        let json = serde_json::json!({
            "tag_name": "v1.2.0",
            "html_url": "https://example.invalid/r",
            "draft": false,
            "prerelease": false,
            "assets": [
                {"name": "Mukyu_Launcher-x86_64.AppImage", "browser_download_url": "https://github.com/Lyrilika/mukyu-launcher/releases/download/v1.2.0/a", "size": 10,
                 "digest": "sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"},
                {"name": "Mukyu_Launcher_Setup.exe", "browser_download_url": "https://github.com/Lyrilika/mukyu-launcher/releases/download/v1.2.0/b", "size": 20}
            ]
        });
        let r = parse_release(&json, "Mukyu_Launcher-x86_64.AppImage").unwrap();
        assert_eq!(r.version, "1.2.0");
        assert_eq!(r.asset_url.as_deref(), Some("https://github.com/Lyrilika/mukyu-launcher/releases/download/v1.2.0/a"));
        assert_eq!(r.asset_size, 10);
        assert_eq!(r.asset_sha256.as_deref(), Some("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"));
        let w = parse_release(&json, "Mukyu_Launcher_Setup.exe").unwrap();
        assert_eq!(w.asset_url.as_deref(), Some("https://github.com/Lyrilika/mukyu-launcher/releases/download/v1.2.0/b"));
        assert_eq!(w.asset_sha256, None);
        let mut bad = json.clone();
        bad["tag_name"] = "v1.2.0-a/../../x".into();
        assert!(parse_release(&bad, "Mukyu_Launcher-x86_64.AppImage").is_none());
        let mut evil = json.clone();
        evil["assets"][0]["browser_download_url"] = "http://evil.example/a".into();
        evil["html_url"] = "file:///etc/passwd".into();
        let e = parse_release(&evil, "Mukyu_Launcher-x86_64.AppImage").unwrap();
        assert_eq!(e.asset_url, None);
        assert_eq!(e.page_url, format!("https://github.com/{REPO}/releases/latest"));
        let mut pre = json.clone();
        pre["prerelease"] = true.into();
        assert!(parse_release(&pre, "Mukyu_Launcher-x86_64.AppImage").is_none());
    }

    #[test]
    fn markdown_cleanup() {
        let md = "## What's new\r\n\r\n- **Faster** scrolling\n- See [the docs](https://x)\n  - nested `code`\n\n---\nPlain <b>text</b>";
        assert_eq!(markdown_to_text(md), "What's new\n\n•  Faster scrolling\n•  See the docs\n    •  nested code\n\n\nPlain text".replace("\n\n\n", "\n\n"));
    }
}
