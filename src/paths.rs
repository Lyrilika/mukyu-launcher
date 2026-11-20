
use std::path::{Path, PathBuf};
use std::sync::OnceLock;

pub const APP_ID: &str = "mukyulauncher";

fn looks_like_root(dir: &Path) -> bool {
    dir.join("assets").join("covers").is_dir()
}

pub fn root_dir() -> &'static Path {
    static ROOT: OnceLock<PathBuf> = OnceLock::new();
    ROOT.get_or_init(|| {
        if let Ok(dir) = std::env::var("MUKYU_ROOT") {
            let dir = PathBuf::from(dir);
            if looks_like_root(&dir) {
                return dir;
            }
        }
        if let Ok(exe) = std::env::current_exe() {
            let exe = exe.canonicalize().unwrap_or(exe);
            if let Some(bin) = exe.parent() {
                let candidates = [
                    bin.to_path_buf(),
                    bin.join(".."),
                    bin.join("../share").join(APP_ID),
                    bin.join("../../"),
                    bin.join("../../../"),
                ];
                for candidate in candidates {
                    if looks_like_root(&candidate) {
                        return candidate.canonicalize().unwrap_or(candidate);
                    }
                }
            }
        }
        let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        if looks_like_root(&manifest) {
            return manifest;
        }
        std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
    })
}

pub fn assets_dir() -> PathBuf {
    root_dir().join("assets")
}

pub fn tools_dir() -> PathBuf {
    root_dir().join("tools")
}

pub fn icon_path() -> PathBuf {
    assets_dir().join("icons/hicolor/scalable/apps/mukyulauncher.png")
}

pub fn cover_path(file: &str) -> PathBuf {
    assets_dir().join("covers").join(file)
}

pub fn home() -> PathBuf {
    dirs::home_dir().unwrap_or_else(|| PathBuf::from("."))
}

pub fn config_home() -> PathBuf {
    dirs::config_dir().unwrap_or_else(|| home().join(".config"))
}

pub fn data_home() -> PathBuf {
    dirs::data_local_dir().unwrap_or_else(|| home().join(".local/share"))
}

pub fn cache_home() -> PathBuf {
    dirs::cache_dir().unwrap_or_else(|| home().join(".cache"))
}

pub fn config_dir() -> PathBuf {
    config_home().join(APP_ID)
}

pub fn data_dir() -> PathBuf {
    data_home().join(APP_ID)
}

pub fn cache_dir() -> PathBuf {
    cache_home().join(APP_ID)
}

pub fn exe_name(name: &str) -> String {
    if cfg!(windows) && !name.to_ascii_lowercase().ends_with(".exe") {
        format!("{name}.exe")
    } else {
        name.to_string()
    }
}

pub fn which(name: &str) -> Option<PathBuf> {
    let path = crate::platform::host_env_var("PATH")?;
    let exts: Vec<String> = if cfg!(windows) {
        std::env::var("PATHEXT")
            .unwrap_or_else(|_| ".EXE;.BAT;.CMD".into())
            .split(';')
            .map(|e| e.to_ascii_lowercase())
            .collect()
    } else {
        vec![String::new()]
    };
    for dir in std::env::split_paths(&path) {
        for ext in &exts {
            let candidate = if ext.is_empty() || name.to_ascii_lowercase().ends_with(ext.as_str()) {
                dir.join(name)
            } else {
                dir.join(format!("{name}{ext}"))
            };
            if is_executable(&candidate) {
                return Some(candidate);
            }
        }
    }
    None
}

pub fn is_executable(path: &Path) -> bool {
    match std::fs::metadata(path) {
        Ok(meta) if meta.is_file() => {
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                meta.permissions().mode() & 0o111 != 0
            }
            #[cfg(not(unix))]
            {
                true
            }
        }
        _ => false,
    }
}
