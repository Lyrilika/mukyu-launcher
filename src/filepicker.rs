
use std::path::{Path, PathBuf};

#[cfg_attr(windows, allow(dead_code))]
pub enum Picked {
    File(PathBuf),
    Cancelled,
    Unavailable,
}

#[cfg(windows)]
pub fn pick_blocking(title: &str, patterns: &[&str], filter_name: &str, start_dir: Option<&Path>) -> Picked {
    let exts: Vec<&str> = patterns.iter().filter_map(|p| p.strip_prefix("*.")).collect();
    let mut dialog = rfd::FileDialog::new().set_title(title).add_filter(filter_name, &exts);
    if let Some(dir) = start_dir.filter(|d| d.is_dir()) {
        dialog = dialog.set_directory(dir);
    }
    match dialog.pick_file() {
        Some(p) => Picked::File(p),
        None => Picked::Cancelled,
    }
}

#[cfg(not(windows))]
pub fn pick_blocking(title: &str, patterns: &[&str], filter_name: &str, start_dir: Option<&Path>) -> Picked {
    for backend in backend_order() {
        let result = if backend == "portal" {
            #[cfg(target_os = "linux")]
            {
                portal_pick(title, patterns, filter_name, start_dir)
            }
            #[cfg(not(target_os = "linux"))]
            {
                None
            }
        } else {
            external_pick(backend, title, patterns, filter_name, start_dir)
        };
        match result {
            Some(Picked::Unavailable) | None => continue,
            Some(other) => return other,
        }
    }
    Picked::Unavailable
}

#[cfg(not(windows))]
fn default_file_manager() -> String {
    let out = std::process::Command::new("xdg-mime")
        .args(["query", "default", "inode/directory"])
        .envs(crate::platform::host_env())
        .output();
    out.map(|o| String::from_utf8_lossy(&o.stdout).trim().to_lowercase()).unwrap_or_default()
}

#[cfg(not(windows))]
fn backend_order() -> Vec<&'static str> {
    let fm = default_file_manager();
    let desktop = std::env::var("XDG_CURRENT_DESKTOP").unwrap_or_default().to_lowercase();
    let kde = ["dolphin", "konqueror", "krusader", "kde", "plasma"].iter().any(|h| fm.contains(h)) || desktop.contains("kde");
    let order = if kde {
        vec!["kdialog", "portal", "zenity", "qarma", "yad"]
    } else {
        vec!["portal", "zenity", "qarma", "yad", "kdialog"]
    };
    order.into_iter().filter(|b| *b == "portal" || crate::paths::which(b).is_some()).collect()
}

#[cfg(not(windows))]
fn external_pick(tool: &str, title: &str, patterns: &[&str], filter_name: &str, start_dir: Option<&Path>) -> Option<Picked> {
    let exe = crate::paths::which(tool)?;
    let start = match start_dir.filter(|d| d.is_dir()) {
        Some(d) => format!("{}/", d.display().to_string().trim_end_matches('/')),
        None => format!("{}/", dirs::home_dir().unwrap_or_default().display()),
    };
    let mut globs: Vec<String> = Vec::new();
    for p in patterns {
        globs.push(p.to_string());
        if p.starts_with("*.") {
            globs.push(p.to_uppercase());
        }
    }
    let mut cmd = std::process::Command::new(exe);
    cmd.envs(crate::platform::host_env());
    if tool == "kdialog" {
        cmd.args(["--title", title, "--getopenfilename", &start]);
        if !globs.is_empty() {
            cmd.arg(format!("{}|{filter_name}", globs.join(" ")));
        }
    } else {
        cmd.arg(if tool == "yad" { "--file" } else { "--file-selection" });
        cmd.args(["--title", title, "--filename", &start]);
        if !globs.is_empty() {
            cmd.args(["--file-filter", &format!("{filter_name} | {}", globs.join(" "))]);
        }
    }
    let out = cmd.output().ok()?;
    let text = String::from_utf8_lossy(&out.stdout);
    let path = text.lines().next().unwrap_or("").trim().to_string();
    let code = out.status.code().unwrap_or(-1);
    Some(if code == 0 && !path.is_empty() && Path::new(&path).is_file() {
        Picked::File(PathBuf::from(path))
    } else if code == 1 && path.is_empty() {
        Picked::Cancelled
    } else {
        Picked::Unavailable
    })
}

#[cfg(target_os = "linux")]
fn portal_pick(title: &str, patterns: &[&str], filter_name: &str, start_dir: Option<&Path>) -> Option<Picked> {
    use std::collections::HashMap;
    use zbus::zvariant::{OwnedObjectPath, OwnedValue, Value};

    let conn = crate::dbus::session()?;
    let unique = conn.unique_name()?.to_string();
    let sender = unique.trim_start_matches(':').replace('.', "_");
    let token = format!(
        "mukyu{}x{}",
        std::process::id(),
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).ok()?.as_millis()
    );
    let handle = format!("/org/freedesktop/portal/desktop/request/{sender}/{token}");
    let rule = zbus::MatchRule::builder()
        .msg_type(zbus::message::Type::Signal)
        .interface("org.freedesktop.portal.Request")
        .ok()?
        .member("Response")
        .ok()?
        .path(handle.as_str())
        .ok()?
        .build();
    let mut iter = zbus::blocking::MessageIterator::for_match_rule(rule, &conn, Some(4)).ok()?;

    let mut options: HashMap<&str, Value> = HashMap::new();
    options.insert("handle_token", Value::from(token.as_str()));
    options.insert("modal", Value::from(true));
    if !patterns.is_empty() {
        let mut globs: Vec<(u32, String)> = Vec::new();
        for p in patterns {
            globs.push((0, p.to_string()));
            if let Some(ext) = p.strip_prefix("*.") {
                let ci: String = ext
                    .chars()
                    .map(|c| if c.is_alphabetic() { format!("[{}{}]", c.to_lowercase(), c.to_uppercase()) } else { c.to_string() })
                    .collect();
                globs.push((0, format!("*.{ci}")));
            }
        }
        options.insert("filters", Value::from(vec![(filter_name.to_string(), globs)]));
    }
    if let Some(dir) = start_dir.filter(|d| d.is_dir()) {
        use std::os::unix::ffi::OsStrExt;
        let mut bytes = dir.as_os_str().as_bytes().to_vec();
        bytes.push(0);
        options.insert("current_folder", Value::from(bytes));
    }
    let reply = conn.call_method(
        Some("org.freedesktop.portal.Desktop"),
        "/org/freedesktop/portal/desktop",
        Some("org.freedesktop.portal.FileChooser"),
        "OpenFile",
        &("", title, options),
    );
    let reply = match reply {
        Ok(r) => r,
        Err(_) => return Some(Picked::Unavailable),
    };
    let _path: OwnedObjectPath = reply.body().deserialize().ok()?;
    for msg in iter.by_ref() {
        let Ok(msg) = msg else { break };
        let Ok((code, results)) = msg.body().deserialize::<(u32, HashMap<String, OwnedValue>)>() else {
            return Some(Picked::Unavailable);
        };
        return Some(match code {
            0 => {
                let uris: Vec<String> = results.get("uris").and_then(|v| Vec::<String>::try_from(v.try_clone().ok()?).ok()).unwrap_or_default();
                match uris.first().and_then(|u| url::Url::parse(u).ok()).and_then(|u| u.to_file_path().ok()) {
                    Some(p) => Picked::File(p),
                    None => Picked::Unavailable,
                }
            }
            1 => Picked::Cancelled,
            _ => Picked::Unavailable,
        });
    }
    Some(Picked::Unavailable)
}

