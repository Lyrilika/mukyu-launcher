#![cfg_attr(windows, windows_subsystem = "windows")]

mod app;
#[cfg(target_os = "linux")]
mod dbus;
mod filepicker;
mod games;
mod media;
mod music;
mod paths;
mod pdf;
mod platform;
mod printworks;
mod printworks_data;
mod theme;
mod update;
mod util;

slint::include_modules!();

fn main() {
    #[cfg(all(target_os = "linux", target_env = "gnu"))]
    unsafe {
        libc::mallopt(libc::M_ARENA_MAX, 2);
    }
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--version") {
        println!("Mukyu Launcher {}", update::current_version());
        return;
    }
    if args.iter().any(|a| a == "--bgm-report" || a == "--decode-test") {
        dev_report(args.iter().any(|a| a == "--decode-test"));
        return;
    }
    let software = std::env::var_os(SOFTWARE_RENDERER_ENV).is_some();
    #[cfg(target_os = "linux")]
    if !software {
        platform::pick_egl_vendor();
    }
    let result = std::panic::catch_unwind(|| app::run(software));
    let failure = match result {
        Ok(Ok(())) => return,
        Ok(Err(e)) => format!("{e:#}"),
        Err(payload) => payload
            .downcast_ref::<&str>()
            .map(|s| s.to_string())
            .or_else(|| payload.downcast_ref::<String>().cloned())
            .unwrap_or_else(|| "unknown error".into()),
    };
    if !software && is_graphics_failure(&failure) && relaunch_with_software_renderer() {
        return;
    }
    eprintln!("Mukyu Launcher failed to start: {failure}");
    show_startup_error(&failure);
    std::process::exit(1);
}

const SOFTWARE_RENDERER_ENV: &str = "MUKYU_SOFTWARE_RENDERER";

fn is_graphics_failure(text: &str) -> bool {
    let text = text.to_ascii_lowercase();
    ["opengl", "gl configuration", "glutin", "egl", "wgl", "glx", "gl context"].iter().any(|k| text.contains(k))
}

fn relaunch_with_software_renderer() -> bool {
    let appimage = update::running_appimage();
    let program = match &appimage {
        Some(path) => path.clone(),
        None => match std::env::current_exe() {
            Ok(path) => path,
            Err(_) => return false,
        },
    };
    let mut cmd = std::process::Command::new(program);
    if appimage.is_some() {
        cmd.env_clear()
            .envs(platform::host_env().into_iter().filter(|(k, _)| !matches!(k.as_str(), "APPIMAGE" | "APPDIR" | "ARGV0" | "OWD" | "MUKYU_ROOT")));
    } else if std::env::var_os(platform::EGL_PICK_MARK).is_some() {
        if std::env::var(platform::EGL_PICK_MARK).as_deref() == Ok("mesa-pci") {
            cmd.env_remove("DRI_PRIME");
        }
        cmd.env_remove("__EGL_VENDOR_LIBRARY_FILENAMES").env_remove(platform::EGL_PICK_MARK);
    }
    cmd.args(std::env::args_os().skip(1)).env("MUKYU_WAIT_PID", std::process::id().to_string());
    cmd.env(SOFTWARE_RENDERER_ENV, "1");
    platform::detach(&mut cmd);
    cmd.spawn().is_ok()
}

fn show_startup_error(message: &str) {
    #[cfg(windows)]
    {
        use windows::core::{HSTRING, PCWSTR};
        use windows::Win32::UI::WindowsAndMessaging::{MessageBoxW, MB_ICONERROR, MB_OK};
        let text = HSTRING::from(format!("Mukyu Launcher could not start.\n\n{message}"));
        let title = HSTRING::from("Mukyu Launcher");
        unsafe {
            MessageBoxW(None, PCWSTR(text.as_ptr()), PCWSTR(title.as_ptr()), MB_OK | MB_ICONERROR);
        }
    }
    #[cfg(not(windows))]
    let _ = message;
}

fn dev_report(decode: bool) {
    let config = games::load_config();
    let scratch = std::env::temp_dir().join(format!("mukyu-bgm-report-{}", std::process::id()));
    let _ = std::fs::create_dir_all(&scratch);
    for game in music::bgm::assigned_games(&config) {
        let (tracks, error) = music::bgm::discover_tracks(&game, &scratch);
        println!("## {}\t{}\t{}", game.key, tracks.len(), error);
        for t in &tracks {
            println!("{}|{}|{}|{:.3}|{:.3}|{:.3}", t.id, t.title_en, t.title_ja, t.duration, t.loop_start, t.loop_end);
        }
        if decode {
            for t in tracks.iter().take(2) {
                let path = match &t.source {
                    music::Source::Pc98 { .. } => match music::pc98::render(t, &scratch) {
                        Ok(p) => Some(p),
                        Err(e) => {
                            println!("DECODE {} render error: {e}", t.id);
                            continue;
                        }
                    },
                    _ => None,
                };
                let input = match &t.source {
                    music::Source::Pcm { path, offset, length, channels, bits } => music::engine::Input::Pcm {
                        path: path.clone(), offset: *offset, length: *length, channels: *channels, bits: *bits, rate: t.sample_rate,
                    },
                    music::Source::File(p) => music::engine::Input::File(p.clone()),
                    music::Source::Tasofro(m) => music::engine::Input::Member(m.clone()),
                    music::Source::Pc98 { .. } => music::engine::Input::File(path.unwrap()),
                };
                let seek = t.loop_region().map(|(s, _)| s);
                match music::engine::probe_decode(&input, 0.0, 3.0, seek) {
                    Ok((frames, peak)) => println!("DECODE {} ok frames={frames} peak={peak:.3}", t.id),
                    Err(e) => println!("DECODE {} error: {e}", t.id),
                }
            }
        }
    }
    let _ = std::fs::remove_dir_all(&scratch);
}
