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
    #[cfg(target_os = "linux")]
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
    if let Err(e) = app::run() {
        eprintln!("Mukyu Launcher failed to start: {e:#}");
        std::process::exit(1);
    }
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
