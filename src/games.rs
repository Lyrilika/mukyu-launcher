
use std::collections::BTreeMap;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

use anyhow::{anyhow, bail, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::paths;
use crate::platform;

pub struct GameInfo {
    pub title: &'static str,
    pub key: &'static str,
    pub cover: &'static str,
}

macro_rules! games {
    ($(($t:expr, $k:expr, $c:expr)),* $(,)?) => { &[$(GameInfo { title: $t, key: $k, cover: $c }),*] };
}

pub const GAMES: &[GameInfo] = games![
    ("Touhou 1: The Highly Responsive to Prayers", "th1", "th1.jpg"),
    ("Touhou 2: Story of Eastern Wonderland", "th2", "th2.jpg"),
    ("Touhou 3: Phantasmagoria of Dim.Dream", "th3", "th3.jpg"),
    ("Touhou 4: Lotus Land Story", "th4", "th4.jpg"),
    ("Touhou 5: Mystic Square", "th5", "th5.jpg"),
    ("Touhou 6: The Embodiment of Scarlet Devil", "th6", "th6.jpg"),
    ("Touhou 7: Perfect Cherry Blossom", "th7", "th7.jpg"),
    ("Touhou 7.5: Immaterial and Missing Power", "th7.5", "th75.jpg"),
    ("Touhou 8: Imperishable Night", "th8", "th8.jpg"),
    ("Touhou 9: Phantasmagoria of Flower View", "th9", "th9.jpg"),
    ("Touhou 9.5: Shoot the Bullet", "th9.5", "th95.jpg"),
    ("Touhou 10: Mountain of Faith", "th10", "th10.jpg"),
    ("Touhou 10.5: Scarlet Weather Rhapsody", "th10.5", "th105.jpg"),
    ("Touhou 11: Subterranean Animism", "th11", "th11.jpg"),
    ("Touhou 12: Undefined Fantastic Object", "th12", "th12.jpg"),
    ("Touhou 12.3: Hisoutensoku", "th12.3", "th123.jpg"),
    ("Touhou 12.5: Double Spoiler", "th12.5", "th125.jpg"),
    ("Touhou 12.8: Great Fairy Wars", "th12.8", "th128.jpg"),
    ("Touhou 13: Ten Desires", "th13", "th13.jpg"),
    ("Touhou 13.5: Hopeless Masquerade", "th13.5", "th135.jpg"),
    ("Touhou 14: Double Dealing Character", "th14", "th14.jpg"),
    ("Touhou 14.3: Impossible Spell Card", "th14.3", "th143.jpg"),
    ("Touhou 14.5: Urban Legend in Limbo", "th14.5", "th145.jpg"),
    ("Touhou 15: Legacy of Lunatic Kingdom", "th15", "th15.jpg"),
    ("Touhou 15.5: Antinomy of Common Flowers", "th15.5", "th155.jpg"),
    ("Touhou 16: Hidden Star in Four Seasons", "th16", "th16.jpg"),
    ("Touhou 16.5: Violet Detector", "th16.5", "th165.jpg"),
    ("Touhou 17: Wily Beast and Weakest Creature", "th17", "th17.jpg"),
    ("Touhou 17.5: Sunken Fossil World", "th17.5", "th175.jpg"),
    ("Touhou 18: Unconnected Marketeers", "th18", "th18.jpg"),
    ("Touhou 18.5: 100th Black Market", "th18.5", "th185.jpg"),
    ("Touhou 19: Unfinished Dream of All Living Ghost", "th19", "th19.jpg"),
    ("Touhou 20: Fossilized Wonders", "th20", "th20.jpg"),
];

pub fn is_pc98(key: &str) -> bool {
    matches!(key, "th1" | "th2" | "th3" | "th4" | "th5")
}


#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct GameEntry {
    pub exe: Option<String>,
    #[serde(default)]
    pub launch_options: String,
    #[serde(default = "default_runner")]
    pub runner: String,
}

pub const NO_GE_PROTON: bool = cfg!(any(target_env = "musl", all(target_os = "linux", any(target_arch = "x86", target_arch = "arm"))));
pub const WINE_LATEST: bool = cfg!(all(target_os = "linux", target_env = "gnu", any(target_arch = "x86", target_arch = "arm")));
pub const PROTON_ONLY: bool = cfg!(all(target_os = "linux", target_arch = "aarch64", not(target_env = "musl")));
pub const MANAGED_AVAILABLE: bool = WINE_LATEST || !NO_GE_PROTON;
pub const MANAGED_RUNNER: &str = if WINE_LATEST { "wine-latest" } else { "ge-proton" };
pub const MANAGED_NAME: &str = if WINE_LATEST { "Wine" } else { "GE-Proton" };

pub fn default_runner() -> String {
    if MANAGED_AVAILABLE { MANAGED_RUNNER.into() } else { "wine".into() }
}

pub fn managed_installed() -> bool {
    if WINE_LATEST { managed_wine_path().is_some() } else { ge_proton_installed() }
}

pub enum InstallStep {
    Checking,
    UpToDate,
    Downloading { percent: Option<u32>, bytes_per_sec: u64 },
    Extracting,
}

pub fn install_latest_managed(progress: impl FnMut(InstallStep)) -> Result<()> {
    if WINE_LATEST { install_latest_wine(progress) } else { install_latest_ge_proton(progress) }
}

pub fn managed_wine_path() -> Option<PathBuf> {
    let mut best: Option<(Vec<u64>, PathBuf)> = None;
    for entry in std::fs::read_dir(runner_directory()).ok()?.flatten() {
        let name = entry.file_name().to_string_lossy().to_string();
        let path = entry.path();
        if !name.starts_with("wine-") || !paths::is_executable(&path.join("bin/wine")) {
            continue;
        }
        let key = version_key(&name);
        if best.as_ref().map_or(true, |b| key > b.0) {
            best = Some((key, path));
        }
    }
    best.map(|(_, p)| p)
}

pub fn wine_installed() -> bool {
    let path = platform::host_env_var("PATH").unwrap_or_default();
    std::env::split_paths(&path).any(|dir| paths::is_executable(&dir.join("wine")))
}

fn is_proton_dir(dir: &Path) -> bool {
    dir.join("proton").is_file() && dir.join("toolmanifest.vdf").is_file()
}

pub fn runner_directory() -> PathBuf {
    paths::data_dir().join("compatibilitytools.d")
}

pub fn installed_protons() -> Vec<(String, PathBuf)> {
    let home = paths::home();
    let steam_roots = [
        paths::data_home().join("Steam"),
        home.join(".steam/root"),
        home.join(".steam/steam"),
        home.join(".var/app/com.valvesoftware.Steam/data/Steam"),
    ];
    let mut seen = std::collections::HashSet::new();
    let mut found = Vec::new();
    let tool_dirs = [
        runner_directory(),
        PathBuf::from("/usr/share/steam/compatibilitytools.d"),
        PathBuf::from("/usr/local/share/steam/compatibilitytools.d"),
    ];
    for entries in tool_dirs.iter().filter_map(|d| std::fs::read_dir(d).ok()) {
        for entry in entries.flatten() {
            let path = entry.path();
            if !is_proton_dir(&path) {
                continue;
            }
            let real = path.canonicalize().unwrap_or(path);
            if seen.insert(real.clone()) {
                found.push((entry.file_name().to_string_lossy().to_string(), real));
            }
        }
    }
    for root in &steam_roots {
        for (dir, only_proton) in [(root.join("compatibilitytools.d"), false), (root.join("steamapps/common"), true)] {
            let Ok(entries) = std::fs::read_dir(&dir) else { continue };
            for entry in entries.flatten() {
                let name = entry.file_name().to_string_lossy().to_string();
                if only_proton && !name.starts_with("Proton") {
                    continue;
                }
                let path = entry.path();
                if !is_proton_dir(&path) {
                    continue;
                }
                let real = path.canonicalize().unwrap_or(path);
                if seen.insert(real.clone()) {
                    found.push((name, real));
                }
            }
        }
    }
    found.sort_by(|a, b| (version_key(&b.0), &b.0).cmp(&(version_key(&a.0), &a.0)));
    found
}

pub fn runner_options() -> Vec<(String, String)> {
    let mut options = Vec::new();
    if MANAGED_AVAILABLE {
        options.push((MANAGED_RUNNER.to_string(), format!("{MANAGED_NAME} (latest)")));
    }
    if !PROTON_ONLY && wine_installed() {
        options.push(("wine".into(), "Wine".into()));
    }
    for (name, path) in installed_protons() {
        options.push((format!("proton:{}", path.display()), name));
    }
    options
}

pub fn effective_runner(runner: &str) -> String {
    match runner {
        "ge-proton" if NO_GE_PROTON => default_runner(),
        "wine-latest" if !WINE_LATEST => default_runner(),
        "wine" if PROTON_ONLY || !wine_installed() => default_runner(),
        r if r.strip_prefix("proton:").is_some_and(|p| !is_proton_dir(Path::new(p))) => default_runner(),
        r => r.to_string(),
    }
}

pub fn is_proton_runner(runner: &str) -> bool {
    runner == "ge-proton" || runner.starts_with("proton:")
}

impl Default for GameEntry {
    fn default() -> Self {
        GameEntry { exe: None, launch_options: String::new(), runner: default_runner() }
    }
}

impl GameEntry {
    pub fn exe_exists(&self) -> bool {
        self.exe.as_deref().map_or(false, |p| !p.is_empty() && Path::new(p).exists())
    }
}

pub type GameConfig = BTreeMap<String, GameEntry>;

pub fn config_file() -> PathBuf {
    paths::config_dir().join("games_config.json")
}

pub fn load_config() -> GameConfig {
    let _ = std::fs::create_dir_all(paths::config_dir());
    let raw: BTreeMap<String, Value> = crate::util::read_json(&config_file()).unwrap_or_default();
    raw.into_iter()
        .filter_map(|(key, value)| {
            let entry = match value {
                Value::String(s) => GameEntry { exe: Some(s), ..Default::default() },
                Value::Object(map) => {
                    let mut runner = map.get("runner").and_then(Value::as_str).map(String::from).unwrap_or_else(default_runner);
                    if !matches!(runner.as_str(), "wine" | "ge-proton" | "wine-latest" | "dosbox-x") && !runner.starts_with("proton:") {
                        runner = default_runner();
                    }
                    GameEntry {
                        exe: map.get("exe").and_then(Value::as_str).map(String::from),
                        launch_options: map.get("launch_options").and_then(Value::as_str).unwrap_or("").to_string(),
                        runner,
                    }
                }
                _ => return None,
            };
            Some((key, entry))
        })
        .collect()
}

pub fn save_config(config: &GameConfig) {
    let _ = crate::util::write_json_atomic(&config_file(), config);
}


fn playtime_file() -> PathBuf {
    paths::data_dir().join("playtime.json")
}

pub fn add_playtime(key: &str, seconds: u64) {
    if key.is_empty() {
        return;
    }
    let mut data: BTreeMap<String, Value> = crate::util::read_json(&playtime_file()).unwrap_or_default();
    let entry = data.entry(key.to_string()).or_insert_with(|| serde_json::json!({"seconds": 0}));
    let current = entry.get("seconds").and_then(Value::as_u64).unwrap_or(0);
    *entry = serde_json::json!({"seconds": current + seconds});
    let _ = crate::util::write_json_atomic(&playtime_file(), &data);
}

pub fn playtime_text(key: &str) -> String {
    let data: BTreeMap<String, Value> = crate::util::read_json(&playtime_file()).unwrap_or_default();
    let seconds = data.get(key).and_then(|v| v.get("seconds")).and_then(Value::as_u64).unwrap_or(0);
    if seconds == 0 {
        return String::new();
    }
    format!("Playtime: {}h {}m {}s", seconds / 3600, (seconds % 3600) / 60, seconds % 60)
}


const UA: &str = "Mukyu-Launcher";

fn github_latest(repo: &str) -> Result<Value> {
    let url = format!("https://api.github.com/repos/{repo}/releases/latest");
    let resp = crate::util::http_agent()
        .get(&url)
        .set("Accept", "application/vnd.github+json")
        .set("User-Agent", UA)
        .call()
        .with_context(|| format!("Could not reach GitHub ({repo})"))?;
    Ok(resp.into_json()?)
}

fn download_to(url: &str, dest: &Path, mut progress: impl FnMut(Option<u32>)) -> Result<()> {
    download_with_speed(url, dest, |p, _| progress(p))
}

fn download_with_speed(url: &str, dest: &Path, mut progress: impl FnMut(Option<u32>, u64)) -> Result<()> {
    let resp = crate::util::http_agent().get(url).set("User-Agent", UA).call()?;
    let total: u64 = resp.header("Content-Length").and_then(|v| v.trim().parse().ok()).unwrap_or(0);
    let mut reader = resp.into_reader();
    let mut out = std::fs::File::create(dest)?;
    let mut buf = vec![0u8; 256 * 1024];
    let mut done: u64 = 0;
    let mut last = u32::MAX;
    let mut window_start = std::time::Instant::now();
    let mut window_bytes: u64 = 0;
    let mut speed: u64 = 0;
    loop {
        let n = reader.read(&mut buf)?;
        if n == 0 {
            break;
        }
        out.write_all(&buf[..n])?;
        done += n as u64;
        window_bytes += n as u64;
        let elapsed = window_start.elapsed();
        let speed_changed = elapsed >= std::time::Duration::from_millis(500);
        if speed_changed {
            speed = (window_bytes as f64 / elapsed.as_secs_f64()) as u64;
            window_start = std::time::Instant::now();
            window_bytes = 0;
        }
        if total > 0 {
            let pct = ((done * 100) / total).min(100) as u32;
            if pct != last || speed_changed {
                last = pct;
                progress(Some(pct), speed);
            }
        } else {
            progress(None, speed);
        }
    }
    out.flush()?;
    Ok(())
}

fn assets(release: &Value) -> Vec<(String, String)> {
    release
        .get("assets")
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(|x| {
                    Some((x.get("name")?.as_str()?.to_string(), x.get("browser_download_url")?.as_str()?.to_string()))
                })
                .collect()
        })
        .unwrap_or_default()
}

fn temp_dir(prefix: &str, parent: Option<&Path>) -> Result<PathBuf> {
    let base = parent.map(Path::to_path_buf).unwrap_or_else(std::env::temp_dir);
    std::fs::create_dir_all(&base)?;
    for i in 0..1000u32 {
        let dir = base.join(format!("{prefix}{}-{i}", std::process::id()));
        if std::fs::create_dir(&dir).is_ok() {
            return Ok(dir);
        }
    }
    bail!("Could not create a temporary folder")
}


pub fn ge_proton_directory() -> PathBuf {
    paths::data_home().join("Steam").join("compatibilitytools.d")
}

fn version_key(name: &str) -> Vec<u64> {
    regex::Regex::new(r"\d+").unwrap().find_iter(name).filter_map(|m| m.as_str().parse().ok()).collect()
}

pub fn ge_proton_path() -> Option<PathBuf> {
    let mut best: Option<(Vec<u64>, String, PathBuf)> = None;
    let dirs = [runner_directory(), ge_proton_directory()];
    for entry in dirs.iter().filter_map(|d| std::fs::read_dir(d).ok()).flat_map(|e| e.flatten()) {
        let path = entry.path();
        let name = entry.file_name().to_string_lossy().to_string();
        if !name.starts_with("GE-Proton") || !path.is_dir() {
            continue;
        }
        if !path.join("proton").is_file() || !path.join("toolmanifest.vdf").is_file() {
            continue;
        }
        if !paths::is_executable(&path.join("files/bin/wine")) {
            continue;
        }
        let key = (version_key(&name), name.clone(), path);
        if best.as_ref().map_or(true, |b| (&key.0, &key.1) > (&b.0, &b.1)) {
            best = Some(key);
        }
    }
    best.map(|(_, _, p)| p.canonicalize().unwrap_or(p))
}

pub fn ge_proton_installed() -> bool {
    ge_proton_path().is_some()
}

fn read_sha512sum(text: &str, tarball: &str) -> Option<String> {
    for line in text.lines() {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() >= 2 && parts[1].trim_start_matches('*') == tarball {
            return Some(parts[0].to_string());
        }
    }
    text.lines()
        .filter_map(|l| l.split_whitespace().next())
        .find(|v| v.len() == 128 && v.chars().all(|c| c.is_ascii_hexdigit()))
        .map(String::from)
}

pub fn install_latest_ge_proton(mut progress: impl FnMut(InstallStep)) -> Result<()> {
    use sha2::Digest;
    progress(InstallStep::Checking);
    let release = github_latest("GloriousEggroll/proton-ge-custom")?;
    let suffix = match std::env::consts::ARCH {
        "x86_64" => "-x86_64.tar.gz",
        "aarch64" => "-aarch64.tar.gz",
        other => bail!("Unsupported architecture: {other}"),
    };
    let all = assets(&release);
    let (tar_name, tar_url) = all
        .iter()
        .rev()
        .find(|(n, _)| n.ends_with(suffix))
        .cloned()
        .ok_or_else(|| anyhow!("Could not find the latest GE-Proton release for this architecture"))?;
    let stem = tar_name.trim_end_matches(".tar.gz").to_string();
    let checksum_url = all.iter().find(|(n, _)| *n == format!("{stem}.sha512sum")).map(|(_, u)| u.clone());
    let install_dir = runner_directory();
    let target = install_dir.join(&stem);
    if target.is_dir() {
        progress(InstallStep::UpToDate);
        return Ok(());
    }
    std::fs::create_dir_all(&install_dir)?;
    let temp = temp_dir("mukyu-ge-proton-", None)?;
    let result = (|| -> Result<()> {
        let tar_path = temp.join(&tar_name);
        progress(InstallStep::Downloading { percent: Some(0), bytes_per_sec: 0 });
        download_with_speed(&tar_url, &tar_path, |percent, bytes_per_sec| progress(InstallStep::Downloading { percent, bytes_per_sec }))?;
        progress(InstallStep::Extracting);
        if let Some(url) = checksum_url {
            let sum_path = temp.join(format!("{tar_name}.sha512sum"));
            download_to(&url, &sum_path, |_| {})?;
            if let Some(expected) = read_sha512sum(&std::fs::read_to_string(&sum_path)?, &tar_name) {
                let mut hasher = sha2::Sha512::new();
                let mut file = std::fs::File::open(&tar_path)?;
                std::io::copy(&mut file, &mut hasher)?;
                if hex::encode(hasher.finalize()) != expected.to_lowercase() {
                    bail!("GE-Proton checksum verification failed");
                }
            }
        }
        let staging = temp_dir("ge-proton-install-", Some(&install_dir))?;
        let unpack = (|| -> Result<()> {
            let file = std::fs::File::open(&tar_path)?;
            let mut archive = tar::Archive::new(flate2::read::GzDecoder::new(file));
            archive.set_preserve_permissions(true);
            for entry in archive.entries()? {
                let mut entry = entry?;
                let path = entry.path()?.into_owned();
                if path.is_absolute() || path.components().any(|c| matches!(c, std::path::Component::ParentDir)) {
                    bail!("Unsafe path found in GE-Proton archive");
                }
                entry.unpack_in(&staging)?;
            }
            let extracted = staging.join(&stem);
            if !extracted.is_dir() {
                bail!("GE-Proton archive did not contain the expected directory");
            }
            std::fs::rename(&extracted, &target)?;
            Ok(())
        })();
        let _ = std::fs::remove_dir_all(&staging);
        unpack
    })();
    let _ = std::fs::remove_dir_all(&temp);
    result?;
    Ok(())
}

fn install_latest_wine(mut progress: impl FnMut(InstallStep)) -> Result<()> {
    use sha2::Digest;
    progress(InstallStep::Checking);
    let release = github_latest("Kron4ek/Wine-Builds")?;
    let all = assets(&release);
    let pattern = regex::Regex::new(r"^wine-[0-9.]+-x86\.tar\.xz$").unwrap();
    let (tar_name, tar_url) = all
        .iter()
        .find(|(n, _)| pattern.is_match(n))
        .cloned()
        .ok_or_else(|| anyhow!("Could not find the latest Wine release"))?;
    let stem = tar_name.trim_end_matches(".tar.xz").to_string();
    let checksum_url = all.iter().find(|(n, _)| n == "sha256sums.txt").map(|(_, u)| u.clone());
    let install_dir = runner_directory();
    let target = install_dir.join(&stem);
    if target.is_dir() {
        progress(InstallStep::UpToDate);
        return Ok(());
    }
    std::fs::create_dir_all(&install_dir)?;
    let temp = temp_dir("mukyu-wine-", None)?;
    let result = (|| -> Result<()> {
        let tar_path = temp.join(&tar_name);
        progress(InstallStep::Downloading { percent: Some(0), bytes_per_sec: 0 });
        download_with_speed(&tar_url, &tar_path, |percent, bytes_per_sec| progress(InstallStep::Downloading { percent, bytes_per_sec }))?;
        progress(InstallStep::Extracting);
        let url = checksum_url.ok_or_else(|| anyhow!("The Wine release has no checksums"))?;
        let sum_path = temp.join("sha256sums.txt");
        download_to(&url, &sum_path, |_| {})?;
        let expected = read_sha512sum(&std::fs::read_to_string(&sum_path)?, &tar_name)
            .ok_or_else(|| anyhow!("The Wine release has no checksum for {tar_name}"))?;
        let mut hasher = sha2::Sha256::new();
        let mut file = std::fs::File::open(&tar_path)?;
        std::io::copy(&mut file, &mut hasher)?;
        if hex::encode(hasher.finalize()) != expected.to_lowercase() {
            bail!("Wine checksum verification failed");
        }
        let staging = temp_dir("wine-install-", Some(&install_dir))?;
        let unpack = (|| -> Result<()> {
            let mut xz = std::process::Command::new("xz")
                .arg("-dc")
                .arg(&tar_path)
                .stdout(std::process::Stdio::piped())
                .spawn()
                .context("xz is required to unpack Wine")?;
            let stdout = xz.stdout.take().ok_or_else(|| anyhow!("Could not read the Wine archive"))?;
            let mut archive = tar::Archive::new(stdout);
            archive.set_preserve_permissions(true);
            for entry in archive.entries()? {
                let mut entry = entry?;
                let path = entry.path()?.into_owned();
                if path.is_absolute() || path.components().any(|c| matches!(c, std::path::Component::ParentDir)) {
                    bail!("Unsafe path found in Wine archive");
                }
                entry.unpack_in(&staging)?;
            }
            if !xz.wait()?.success() {
                bail!("The Wine archive could not be unpacked");
            }
            let extracted = staging.join(&stem);
            if !paths::is_executable(&extracted.join("bin/wine")) {
                bail!("Wine archive did not contain the expected directory");
            }
            std::fs::rename(&extracted, &target)?;
            Ok(())
        })();
        let _ = std::fs::remove_dir_all(&staging);
        unpack
    })();
    let _ = std::fs::remove_dir_all(&temp);
    result?;
    Ok(())
}

pub fn dosbox_root() -> PathBuf {
    paths::data_dir().join("dosbox-x")
}

fn dosbox_binary() -> PathBuf {
    dosbox_root().join(paths::exe_name("dosbox-x"))
}

#[cfg(windows)]
fn find_windows_dosbox() -> Option<PathBuf> {
    let root = dosbox_root();
    let mut best: Option<((u8, usize), PathBuf)> = None;
    let mut stack = vec![(root.clone(), 0usize)];
    while let Some((dir, depth)) = stack.pop() {
        let Ok(it) = std::fs::read_dir(&dir) else { continue };
        for e in it.flatten() {
            let p = e.path();
            if p.is_dir() {
                if depth < 4 {
                    stack.push((p, depth + 1));
                }
            } else if e.file_name().to_string_lossy().eq_ignore_ascii_case("dosbox-x.exe") {
                let s = p.display().to_string().to_lowercase();
                let rank = (if s.contains("sdl2") { 0 } else { 1 }, s.len());
                if best.as_ref().map_or(true, |b| rank < b.0) {
                    best = Some((rank, p));
                }
            }
        }
    }
    if let Some((_, p)) = best {
        return Some(p);
    }
    for root in [std::env::var("ProgramFiles").ok(), std::env::var("ProgramFiles(x86)").ok(), Some("C:\\".into())]
        .into_iter()
        .flatten()
    {
        for sub in ["DOSBox-X", "DOSBox-X-Windows"] {
            let c = Path::new(&root).join(sub).join("dosbox-x.exe");
            if c.is_file() {
                return Some(c);
            }
        }
    }
    paths::which("dosbox-x")
}

pub fn dosbox_path() -> Option<PathBuf> {
    #[cfg(windows)]
    {
        return find_windows_dosbox();
    }
    #[allow(unreachable_code)]
    {
        for c in [dosbox_binary(), dosbox_root().join("dosbox-x.AppImage"), dosbox_root().join("dosbox-x")] {
            if paths::is_executable(&c) {
                return Some(c);
            }
        }
        paths::which("dosbox-x")
    }
}

pub fn install_dosbox(mut status: impl FnMut(String)) -> Result<()> {
    status("Downloading DOSBox-X...".into());
    let root = dosbox_root();
    std::fs::create_dir_all(&root)?;
    if cfg!(windows) {
        let release = github_latest("joncampbell123/dosbox-x")?;
        let mut candidates: Vec<(String, String)> = assets(&release)
            .into_iter()
            .filter(|(n, _)| {
                let n = n.to_lowercase();
                n.ends_with(".zip") && n.contains("win64") && !n.contains("arm") && !n.contains("lowend")
            })
            .collect();
        candidates.sort_by_key(|(n, _)| if n.to_lowercase().contains("mingw") { 0 } else { 1 });
        let (_, url) = candidates.into_iter().next().ok_or_else(|| anyhow!("No compatible DOSBox-X build found"))?;
        let temp = temp_dir("mukyu-dosbox-", None)?;
        let result = (|| -> Result<()> {
            let archive_path = temp.join("dosbox-x.zip");
            download_to(&url, &archive_path, |p| {
                if let Some(p) = p {
                    status(format!("Downloading DOSBox-X... {p}%"))
                }
            })?;
            status("Unpacking DOSBox-X...".into());
            let staging = temp_dir("unpack-", Some(&root))?;
            let inner = (|| -> Result<()> {
                let mut zip = zip::ZipArchive::new(std::fs::File::open(&archive_path)?)?;
                for i in 0..zip.len() {
                    let mut file = zip.by_index(i)?;
                    let Some(rel) = file.enclosed_name() else { bail!("Unsafe path found in DOSBox-X archive") };
                    let out = staging.join(rel);
                    if file.is_dir() {
                        std::fs::create_dir_all(&out)?;
                    } else {
                        if let Some(parent) = out.parent() {
                            std::fs::create_dir_all(parent)?;
                        }
                        std::io::copy(&mut file, &mut std::fs::File::create(&out)?)?;
                    }
                }
                Ok(())
            })();
            if let Err(e) = inner {
                let _ = std::fs::remove_dir_all(&staging);
                return Err(e);
            }
            for entry in std::fs::read_dir(&root)?.flatten() {
                let p = entry.path();
                if p != staging && p.is_dir() && !entry.file_type().map(|t| t.is_symlink()).unwrap_or(false) {
                    let _ = std::fs::remove_dir_all(&p);
                }
            }
            std::fs::rename(&staging, root.join("windows-build"))?;
            Ok(())
        })();
        let _ = std::fs::remove_dir_all(&temp);
        result?;
    } else {
        let release = github_latest("pkgforge-dev/DOSBox-X-AppImage")?;
        let url = assets(&release)
            .into_iter()
            .find(|(n, _)| {
                let n = n.to_lowercase();
                n.contains("appimage") && (n.contains("x86_64") || n.contains("amd64"))
            })
            .map(|(_, u)| u)
            .ok_or_else(|| anyhow!("No compatible DOSBox-X build found"))?;
        let out = root.join("dosbox-x.AppImage");
        download_to(&url, &out, |p| {
            if let Some(p) = p {
                status(format!("Downloading DOSBox-X... {p}%"))
            }
        })?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(&out, std::fs::Permissions::from_mode(0o755))?;
            let link = dosbox_binary();
            let _ = std::fs::remove_file(&link);
            let _ = std::os::unix::fs::symlink(&out, &link);
        }
    }
    status("Installed".into());
    Ok(())
}

fn dosbox_args(rom: &Path) -> Vec<String> {
    let rom = std::path::absolute(rom).unwrap_or_else(|_| rom.to_path_buf());
    [
        "-set", "machine=pc98",
        "-set", "sdl output=opengl",
        "-set", "sdl fullscreen=true",
        "-set", "sdl fullresolution=desktop",
        "-set", "render aspect=true",
        "-set", "render aspect_ratio=4:3",
        "-set", "cpu cycles=max",
        "-c",
    ]
    .iter()
    .map(|s| s.to_string())
    .chain([format!("IMGMOUNT C \"{}\"", rom.display()), "-c".into(), "C:".into(), "-c".into(), "GAME".into()])
    .collect()
}


pub fn umu_path() -> PathBuf {
    let bundled = paths::tools_dir().join("umu").join("umu-run");
    if paths::is_executable(&bundled) {
        bundled
    } else {
        PathBuf::from("umu-run")
    }
}

pub enum LaunchError {
    DosboxMissing,
    ProtonMissing,
    BadPath,
}

pub struct LaunchPlan {
    pub command: Vec<String>,
    pub env: Vec<(String, String)>,
}

fn wrap(options: &str, base: Vec<String>, split: fn(&str) -> Vec<String>) -> Vec<String> {
    if let Some((before, after)) = options.split_once("%command%") {
        let mut cmd = split(before);
        cmd.extend(base);
        cmd.extend(split(after));
        cmd
    } else {
        let mut cmd = base;
        cmd.extend(split(options));
        cmd
    }
}

pub fn build_launch_command(exe: &str, options: &str, runner: &str, key: &str) -> std::result::Result<LaunchPlan, LaunchError> {
    let options = options.trim();
    if runner == "dosbox-x" {
        if exe.contains('"') {
            return Err(LaunchError::BadPath);
        }
        let db = dosbox_path().ok_or(LaunchError::DosboxMissing)?;
        let mut command = vec![db.display().to_string()];
        command.extend(dosbox_args(Path::new(exe)));
        return Ok(LaunchPlan { command, env: vec![] });
    }
    if cfg!(windows) {
        return Ok(LaunchPlan { command: wrap(options, vec![exe.to_string()], platform::split_launch_options), env: vec![] });
    }
    let game_dir = std::path::absolute(exe)
        .ok()
        .and_then(|p| p.parent().map(Path::to_path_buf))
        .unwrap_or_default();
    if runner == "wine-latest" {
        let prefix = paths::data_dir().join("prefixes").join(key);
        let _ = std::fs::create_dir_all(&prefix);
        let wine = managed_wine_path().ok_or(LaunchError::ProtonMissing)?.join("bin/wine").display().to_string();
        let base = if cfg!(target_arch = "arm") { vec!["box86".into(), wine, exe.to_string()] } else { vec![wine, exe.to_string()] };
        let env = vec![("WINEPREFIX".into(), prefix.display().to_string())];
        return Ok(LaunchPlan { command: wrap(options, base, platform::shell_split), env });
    }
    if is_proton_runner(runner) {
        let prefix = paths::data_dir().join("prefixes").join(key);
        let _ = std::fs::create_dir_all(&prefix);
        let proton = match runner.strip_prefix("proton:") {
            Some(dir) if is_proton_dir(Path::new(dir)) => PathBuf::from(dir),
            Some(_) => return Err(LaunchError::ProtonMissing),
            None => ge_proton_path().ok_or(LaunchError::ProtonMissing)?,
        };
        let env = vec![
            ("WINEPREFIX".into(), prefix.display().to_string()),
            ("GAMEID".into(), "0".into()),
            ("PROTONPATH".into(), proton.display().to_string()),
            ("PYTHONNOUSERSITE".into(), "1".into()),
            ("STEAM_COMPAT_INSTALL_PATH".into(), game_dir.display().to_string()),
        ];
        let base = vec![umu_path().display().to_string(), exe.to_string()];
        return Ok(LaunchPlan { command: wrap(options, base, platform::shell_split), env });
    }
    Ok(LaunchPlan { command: wrap(options, vec!["wine".into(), exe.to_string()], platform::shell_split), env: vec![] })
}

pub fn launch_log_path() -> PathBuf {
    let dir = paths::cache_dir();
    let _ = std::fs::create_dir_all(&dir);
    dir.join("launch.log")
}

pub fn open_launch_log(command: &[String], runner: &str, key: &str) -> Option<std::fs::File> {
    let path = launch_log_path();
    if std::fs::metadata(&path).map(|m| m.len() > 2_000_000).unwrap_or(false) {
        let mut old = path.as_os_str().to_owned();
        old.push(".old");
        let _ = std::fs::rename(&path, old);
    }
    let mut file = std::fs::OpenOptions::new().create(true).append(true).open(&path).ok()?;
    let now = chrono::Local::now().format("%Y-%m-%d %H:%M:%S");
    let _ = write!(file, "\n===== {now}  {key}  runner={runner} =====\n$ {}\n", platform::shell_join(command));
    Some(file)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn wraps_command_token() {
        let cmd = wrap("mangohud %command% -fast", vec!["wine".into(), "a.exe".into()], platform::shell_split);
        assert_eq!(cmd, vec!["mangohud", "wine", "a.exe", "-fast"]);
    }

    #[test]
    fn sha512_lookup() {
        let text = format!("{}  GE-Proton9-1.tar.gz\n", "a".repeat(128));
        assert_eq!(read_sha512sum(&text, "GE-Proton9-1.tar.gz"), Some("a".repeat(128)));
    }
}

pub fn steam_app_id(exe: &Path) -> Option<u32> {
    let mut dir = exe.parent()?;
    loop {
        let parent = dir.parent()?;
        let is_common = parent.file_name().is_some_and(|n| n.eq_ignore_ascii_case("common"));
        let steamapps = parent.parent()?;
        if is_common && steamapps.file_name().is_some_and(|n| n.eq_ignore_ascii_case("steamapps")) {
            let install = dir.file_name()?.to_string_lossy().to_string();
            for entry in std::fs::read_dir(steamapps).ok()?.flatten() {
                let name = entry.file_name().to_string_lossy().to_string();
                let Some(id) = name.strip_prefix("appmanifest_").and_then(|n| n.strip_suffix(".acf")) else { continue };
                let Ok(text) = std::fs::read_to_string(entry.path()) else { continue };
                let matches = text.lines().any(|line| {
                    let mut parts = line.split('"').map(str::trim).filter(|s| !s.is_empty());
                    parts.next().is_some_and(|k| k.eq_ignore_ascii_case("installdir")) && parts.next().is_some_and(|v| v.eq_ignore_ascii_case(&install))
                });
                if matches {
                    return id.parse().ok();
                }
            }
            return None;
        }
        dir = parent;
    }
}

pub fn steam_launch_command(app_id: u32) -> Vec<String> {
    let url = format!("steam://rungameid/{app_id}");
    if cfg!(windows) {
        vec!["cmd".into(), "/C".into(), "start".into(), String::new(), url]
    } else {
        vec!["xdg-open".into(), url]
    }
}
