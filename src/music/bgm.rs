
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::process::Command;

use super::metadata::{ogg_info, riff_loop, wav_info, FileRead};
use super::{pc98, tasofro, titles, GameTrack, Source};
use crate::games::{GameConfig, GAMES};
use crate::paths;
use crate::platform::no_window;

#[derive(Clone, Debug, PartialEq)]
pub struct AssignedGame {
    pub key: String,
    pub title: String,
    pub path: PathBuf,
    pub music_room: Option<PathBuf>,
}

pub fn assigned_games(config: &GameConfig) -> Vec<AssignedGame> {
    let mut result: Vec<AssignedGame> = GAMES
        .iter()
        .filter_map(|g| {
            let exe = config.get(g.key)?.exe.clone()?;
            let p = Path::new(&exe);
            p.exists().then(|| AssignedGame {
                key: g.key.into(),
                title: g.title.into(),
                path: std::path::absolute(p).unwrap_or_else(|_| p.to_path_buf()),
                music_room: None,
            })
        })
        .collect();
    if let Some(room) = config.get("th5").and_then(|e| e.exe.clone()).filter(|p| Path::new(p).is_file()) {
        let room = std::path::absolute(&room).unwrap_or_else(|_| PathBuf::from(&room));
        for g in result.iter_mut().filter(|g| matches!(g.key.as_str(), "th2" | "th3" | "th4")) {
            g.music_room = Some(room.clone());
        }
    }
    result
}

fn game_number(key: &str) -> Option<(u32, String)> {
    let re = regex::Regex::new(r"^th(\d+)(?:\.(\d+))?$").unwrap();
    let c = re.captures(key)?;
    Some((c[1].parse().ok()?, c.get(2).map(|m| m.as_str().to_string()).unwrap_or_default()))
}

fn thtk_game_id(key: &str) -> Option<String> {
    game_number(key).map(|(w, d)| format!("{w}{d}"))
}

fn tool_path(name: &str) -> Option<PathBuf> {
    let name = paths::exe_name(name);
    let base = paths::tools_dir().join("thtk");
    for p in [base.join("bin").join(&name), base.join(&name)] {
        if p.is_file() {
            return Some(p);
        }
    }
    paths::which(&name)
}

fn tool_command(tool: &Path) -> Command {
    let mut cmd = Command::new(tool);
    if let Some(lib) = tool.canonicalize().ok().and_then(|p| p.parent()?.parent().map(|d| d.join("lib64"))) {
        if lib.is_dir() {
            let current = std::env::var("LD_LIBRARY_PATH").unwrap_or_default();
            let value = if current.is_empty() { lib.display().to_string() } else { format!("{}:{current}", lib.display()) };
            cmd.env("LD_LIBRARY_PATH", value);
        }
    }
    no_window(&mut cmd);
    cmd
}

fn run_with_timeout(mut cmd: Command, secs: u64) -> Option<std::process::Output> {
    use std::process::Stdio;
    let child = cmd.stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::null()).spawn().ok()?;
    let id = child.id();
    let (tx, rx) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        let _ = tx.send(child.wait_with_output());
    });
    match rx.recv_timeout(std::time::Duration::from_secs(secs)) {
        Ok(Ok(out)) => Some(out),
        _ => {
            #[cfg(unix)]
            unsafe {
                libc::kill(id as i32, libc::SIGKILL);
            }
            #[cfg(not(unix))]
            let _ = id;
            None
        }
    }
}

fn run_thdat(args: &[String], cwd: &Path, timeout: u64, key: Option<&str>) -> bool {
    let Some(thdat) = tool_path("thdat") else { return false };
    let mut commands: Vec<Vec<String>> = Vec::new();
    if let Some(id) = key.and_then(thtk_game_id) {
        if args.len() >= 2 && (args[0] == "-x" || args[0] == "-l") && args[1] == "d" {
            let mut c = vec![args[0].clone(), id];
            c.extend_from_slice(&args[2..]);
            commands.push(c);
        }
    }
    commands.push(args.to_vec());
    if args.len() >= 2 && args[1] == "d" && (args[0] == "-x" || args[0] == "-l") {
        let mut c = vec![format!("{}d", args[0])];
        c.extend_from_slice(&args[2..]);
        commands.push(c);
    }
    let mut seen = Vec::new();
    for c in commands {
        if seen.contains(&c) {
            continue;
        }
        seen.push(c.clone());
        let mut cmd = tool_command(&thdat);
        cmd.args(&c).current_dir(cwd);
        if let Some(out) = run_with_timeout(cmd, timeout) {
            if out.status.success() {
                return true;
            }
        }
    }
    false
}

fn list_members(archive: &Path, key: &str) -> Vec<String> {
    let Some(thdat) = tool_path("thdat") else { return Vec::new() };
    let mut variants: Vec<Vec<String>> = Vec::new();
    if let Some(id) = thtk_game_id(key) {
        variants.push(vec!["-l".into(), id, archive.display().to_string()]);
    }
    variants.push(vec!["-l".into(), "d".into(), archive.display().to_string()]);
    variants.push(vec!["-ld".into(), archive.display().to_string()]);
    for v in variants {
        let mut cmd = tool_command(&thdat);
        cmd.args(&v);
        if let Some(out) = run_with_timeout(cmd, 20) {
            if out.status.success() {
                return String::from_utf8_lossy(&out.stdout).lines().map(str::trim).filter(|l| !l.is_empty()).map(String::from).collect();
            }
        }
    }
    Vec::new()
}

fn candidate_dat_files(dir: &Path, key: &str) -> Vec<PathBuf> {
    let Some((whole, decimal)) = game_number(key) else { return Vec::new() };
    let mut stems: Vec<String> = Vec::new();
    for v in [format!("{whole}{decimal}"), format!("{whole:02}{decimal}")] {
        if !stems.contains(&v) {
            stems.push(v);
        }
    }
    if decimal.is_empty() {
        let padded = format!("{whole:02}");
        if !stems.contains(&padded) {
            stems.insert(0, padded);
        }
    }
    let listing: Vec<PathBuf> = {
        let mut v: Vec<PathBuf> = std::fs::read_dir(dir).map(|it| it.flatten().map(|e| e.path()).collect()).unwrap_or_default();
        v.sort();
        v
    };
    let mut out: Vec<PathBuf> = Vec::new();
    for stem in &stems {
        for suffix in [".dat", "_tr.dat", "tr.dat", "b.dat", "a.dat", "bgm.dat"] {
            let p = dir.join(format!("th{stem}{suffix}"));
            if p.is_file() {
                out.push(p);
            }
        }
        let prefix = format!("th{stem}");
        for p in &listing {
            let name = p.file_name().unwrap_or_default().to_string_lossy();
            if name.starts_with(&prefix) && name.ends_with(".dat") {
                out.push(p.clone());
            }
        }
    }
    let mut seen = Vec::new();
    out.retain(|p| {
        let k = p.canonicalize().unwrap_or_else(|_| p.clone());
        if seen.contains(&k) {
            false
        } else {
            seen.push(k);
            true
        }
    });
    out
}

fn find_recursive(root: &Path, name: &str) -> Option<PathBuf> {
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        for e in std::fs::read_dir(&dir).ok()?.flatten() {
            let p = e.path();
            if p.is_dir() {
                stack.push(p);
            } else if e.file_name().to_string_lossy() == name {
                return Some(p);
            }
        }
    }
    None
}

fn extract_members(archive: &Path, out: &Path, key: &str) -> Option<PathBuf> {
    let _ = std::fs::create_dir_all(out);
    let members = list_members(archive, key);
    for wanted in ["thbgm.fmt", "thbgm_tr.fmt", "musiccmt.txt", "musiccmt_tr.txt"] {
        let norm = |m: &str| m.replace('\\', "/").trim_matches('/').to_lowercase();
        let member = members
            .iter()
            .find(|m| norm(m) == wanted)
            .or_else(|| members.iter().find(|m| norm(m).rsplit('/').next() == Some(wanted)))
            .cloned()
            .unwrap_or_else(|| wanted.to_string());
        run_thdat(&["-x".into(), "d".into(), archive.display().to_string(), member], out, 20, Some(key));
    }
    ["thbgm.fmt", "thbgm_tr.fmt"].iter().find_map(|n| find_recursive(out, n))
}

fn find_or_extract_fmt(dir: &Path, key: &str, scratch: &Path) -> Option<PathBuf> {
    for n in ["thbgm.fmt", "thbgm_tr.fmt"] {
        if dir.join(n).is_file() {
            return Some(dir.join(n));
        }
    }
    for archive in candidate_dat_files(dir, key) {
        let stem = archive.file_stem().unwrap_or_default().to_string_lossy().to_string();
        if let Some(fmt) = extract_members(&archive, &scratch.join(stem), key) {
            return Some(fmt);
        }
    }
    None
}

fn parse_musiccmt(path: &Path) -> HashMap<String, String> {
    let Ok(raw) = std::fs::read(path) else { return HashMap::new() };
    let text = crate::util::decode_cp932(&raw);
    let lines: Vec<&str> = text.lines().map(str::trim).collect();
    let no = regex::Regex::new(r"^No\.\s*\d+\s*").unwrap();
    let mut result = HashMap::new();
    for (i, line) in lines.iter().enumerate() {
        if !line.to_lowercase().starts_with("@bgm/") {
            continue;
        }
        let filename = line.split_once('/').map(|x| x.1.trim()).unwrap_or("");
        let mut title = String::new();
        for cand in lines.iter().skip(i + 1).take(7) {
            if cand.is_empty() || cand.starts_with('#') || cand.starts_with('@') {
                continue;
            }
            let cleaned = no.replace(cand, "").trim().to_string();
            if !cleaned.is_empty() && !cleaned.starts_with('♪') {
                title = cleaned;
                break;
            }
        }
        if !title.is_empty() {
            result.insert(filename.to_lowercase(), title.clone());
            let stem = Path::new(filename).file_stem().unwrap_or_default().to_string_lossy().to_lowercase();
            result.insert(stem, title);
        }
    }
    result
}

const TH06_TITLES: [(&str, &str); 17] = [
    ("th06_01.wav", "A Dream More Scarlet than Red"),
    ("th06_02.wav", "A Soul as Scarlet as a Ground Cherry"),
    ("th06_03.wav", "Apparitions Stalk the Night"),
    ("th06_04.wav", "Lunate Elf"),
    ("th06_05.wav", "Tomboyish Girl in Love"),
    ("th06_06.wav", "Shanghai Teahouse ~ Chinese Tea"),
    ("th06_07.wav", "Shanghai Alice of Meiji 17"),
    ("th06_08.wav", "Voile, the Magic Library"),
    ("th06_09.wav", "Locked Girl ~ The Girl's Sealed Room"),
    ("th06_10.wav", "The Maid and the Pocket Watch of Blood"),
    ("th06_11.wav", "Lunar Clock ~ Luna Dial"),
    ("th06_12.wav", "The Young Descendant of Tepes"),
    ("th06_13.wav", "Septette for a Dead Princess"),
    ("th06_14.wav", "The Centennial Festival for Magical Girls"),
    ("th06_15.wav", "U.N. Owen Was Her?"),
    ("th06_16.wav", "An Eternity More Transient than Scarlet"),
    ("th06_17.wav", "Scarlet Chamber ~ Eastern Dream..."),
];

fn stem_of(name: &str) -> String {
    Path::new(name).file_stem().unwrap_or_default().to_string_lossy().to_lowercase()
}

fn title_from_filename(filename: &str, key: &str, titles: &HashMap<String, String>) -> String {
    let lower = filename.to_lowercase();
    if key == "th6" {
        if let Some((_, t)) = TH06_TITLES.iter().find(|(f, _)| *f == lower) {
            return t.to_string();
        }
    }
    if let Some(t) = titles.get(&lower) {
        return t.clone();
    }
    let stem = stem_of(filename);
    titles
        .iter()
        .find(|(k, _)| stem_of(k) == stem)
        .map(|(_, t)| t.clone())
        .unwrap_or_else(|| Path::new(filename).file_stem().unwrap_or_default().to_string_lossy().to_string())
}

fn parse_fmt(fmt: &Path, key: &str, title: &str, dir: &Path) -> Vec<GameTrack> {
    let Ok(data) = std::fs::read(fmt) else { return Vec::new() };
    let mut musiccmt = fmt.with_file_name("musiccmt.txt");
    if !musiccmt.exists() {
        musiccmt = fmt.with_file_name("musiccmt_tr.txt");
    }
    let titles = parse_musiccmt(&musiccmt);
    let mut source = dir.join("thbgm.dat");
    if !source.is_file() && dir.join("thbgm_tr.dat").is_file() {
        source = dir.join("thbgm_tr.dat");
    }
    let mut tracks = Vec::new();
    for block in data.chunks_exact(52) {
        let name_end = block[..16].iter().position(|&b| b == 0).unwrap_or(16);
        let filename: String = String::from_utf8_lossy(&block[..name_end]).chars().filter(char::is_ascii).collect::<String>().trim().to_string();
        if filename.is_empty() {
            continue;
        }
        let u32_at = |o: usize| u32::from_le_bytes(block[o..o + 4].try_into().unwrap());
        let i32_at = |o: usize| i32::from_le_bytes(block[o..o + 4].try_into().unwrap());
        let u16_at = |o: usize| u16::from_le_bytes([block[o], block[o + 1]]);
        let start = u32_at(16) as u64;
        let intro = i32_at(24);
        let total = i32_at(28);
        let (tag, channels, rate, byte_rate, bits) = (u16_at(32), u16_at(34), u32_at(36), u32_at(40), u16_at(46));
        if tag != 1 || channels < 1 || rate == 0 || bits == 0 || byte_rate == 0 || total <= 0 {
            continue;
        }
        let br = byte_rate as f64;
        let loop_start = intro.max(0) as f64 / br;
        let loop_end = if intro >= 0 && intro < total { total as f64 / br } else { 0.0 };
        tracks.push(GameTrack {
            id: format!("{key}:{}", filename.to_lowercase()),
            game_key: key.into(),
            game_title: title.into(),
            title: title_from_filename(&filename, key, &titles),
            filename,
            title_en: String::new(),
            title_ja: String::new(),
            source: Source::Pcm { path: source.clone(), offset: start, length: total as u64, channels, bits },
            sample_rate: rate,
            channels,
            duration: total as f64 / br,
            loop_start,
            loop_end,
        });
    }
    tracks
}

fn wav_track(path: &Path, key: &str, title: &str) -> Option<GameTrack> {
    let src = FileRead::open(path).ok()?;
    let (channels, rate, bits, _off, len) = wav_info(&src).ok()?;
    let frame = (channels as u64 * (bits as u64 / 8)).max(1);
    let duration = if rate > 0 { (len / frame) as f64 / rate as f64 } else { 0.0 };
    let (mut loop_start, mut loop_end) = (0.0, 0.0);
    if let Some(grand) = path.parent().and_then(Path::parent) {
        if let Ok(it) = std::fs::read_dir(grand) {
            for e in it.flatten() {
                let p = e.path();
                if p.is_dir() && e.file_name().to_string_lossy().to_lowercase().ends_with("md.dat") {
                    let pos = p.join(format!("{}.pos", path.file_stem().unwrap_or_default().to_string_lossy()));
                    if let Ok(b) = std::fs::read(&pos) {
                        if b.len() >= 8 {
                            loop_start = u32::from_le_bytes(b[0..4].try_into().unwrap()) as f64 / rate as f64;
                            loop_end = u32::from_le_bytes(b[4..8].try_into().unwrap()) as f64 / rate as f64;
                        }
                    }
                    break;
                }
            }
        }
    }
    let name = path.file_name()?.to_string_lossy().to_string();
    Some(GameTrack {
        id: format!("{key}:{}", name.to_lowercase()),
        game_key: key.into(),
        game_title: title.into(),
        title: title_from_filename(&name, key, &HashMap::new()),
        filename: name,
        title_en: String::new(),
        title_ja: String::new(),
        source: Source::File(path.to_path_buf()),
        sample_rate: rate,
        channels,
        duration,
        loop_start,
        loop_end,
    })
}

fn th06_loop_points(dir: &Path, tracks: &mut [GameTrack], scratch: &Path) {
    let missing: Vec<usize> = (0..tracks.len()).filter(|&i| tracks[i].loop_region().is_none()).collect();
    if missing.is_empty() {
        return;
    }
    let out = scratch.join("th6-loop-points");
    let _ = std::fs::create_dir_all(&out);
    let names: Vec<String> = missing.iter().map(|&i| format!("{}.pos", stem_of(&tracks[i].filename))).collect();
    let mut archives: Vec<PathBuf> = std::fs::read_dir(dir).map(|it| it.flatten().map(|e| e.path()).collect()).unwrap_or_default();
    archives.sort();
    for archive in archives {
        if archive.is_file() && archive.file_name().unwrap_or_default().to_string_lossy().to_lowercase().ends_with("md.dat") {
            let mut args = vec!["-x".to_string(), "d".into(), archive.display().to_string()];
            args.extend(names.iter().cloned());
            run_thdat(&args, &out, 20, Some("th6"));
        }
    }
    let mut points = HashMap::new();
    let mut stack = vec![out];
    while let Some(d) = stack.pop() {
        for e in std::fs::read_dir(&d).into_iter().flatten().flatten() {
            let p = e.path();
            if p.is_dir() {
                stack.push(p);
            } else if p.extension().map_or(false, |x| x.eq_ignore_ascii_case("pos")) {
                points.insert(e.file_name().to_string_lossy().to_lowercase(), p);
            }
        }
    }
    for i in missing {
        let t = &mut tracks[i];
        let Some(pos) = points.get(&format!("{}.pos", stem_of(&t.filename))) else { continue };
        if let Ok(b) = std::fs::read(pos) {
            if b.len() >= 8 {
                let s = u32::from_le_bytes(b[0..4].try_into().unwrap()) as f64 / t.sample_rate as f64;
                let e = u32::from_le_bytes(b[4..8].try_into().unwrap()) as f64 / t.sample_rate as f64;
                if 0.0 <= s && s < e && e <= t.duration + 0.05 {
                    t.loop_start = s;
                    t.loop_end = e;
                }
            }
        }
    }
}

fn archive_audio_tracks(archive: &Path, key: &str, title: &str, scratch: &Path) -> Vec<GameTrack> {
    use sha2::Digest;
    let meta = std::fs::metadata(archive).ok();
    let stamp = format!(
        "{}:{}:{}",
        archive.canonicalize().unwrap_or_else(|_| archive.to_path_buf()).display(),
        meta.as_ref().map(|m| m.len()).unwrap_or(0),
        meta.and_then(|m| m.modified().ok()).and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok()).map(|d| d.as_nanos()).unwrap_or(0)
    );
    let digest = hex::encode(sha2::Sha256::digest(stamp.as_bytes()));
    let stem = archive.file_stem().unwrap_or_default().to_string_lossy().to_string();
    let extract = scratch.join(format!("{stem}-{}", &digest[..16]));
    let Some(rows) = tasofro::catalog().get(key) else { return Vec::new() };
    let _ = std::fs::create_dir_all(&extract);
    if !extract.join(".complete").exists() {
        let mut wanted: Vec<String> = rows.iter().map(|r| r.file.clone()).collect();
        let extra: Vec<String> = wanted.iter().filter(|n| n.ends_with(".ogg")).map(|n| format!("{}.sfl", &n[..n.len() - 4])).collect();
        wanted.extend(extra);
        wanted.sort();
        wanted.dedup();
        let mut args = vec!["-x".to_string(), "d".into(), archive.display().to_string()];
        args.extend(wanted);
        run_thdat(&args, &extract, 90, Some(key));
        if rows.iter().all(|r| extract.join(&r.file).is_file()) {
            let _ = std::fs::write(extract.join(".complete"), b"");
        }
    }
    let mut tracks = Vec::new();
    for row in rows {
        let path = extract.join(&row.file);
        if !path.is_file() {
            continue;
        }
        let is_wav = path.extension().map_or(false, |x| x == "wav");
        let mut track = if is_wav {
            match wav_track(&path, key, title) {
                Some(t) => t,
                None => continue,
            }
        } else {
            let Ok(src) = FileRead::open(&path) else { continue };
            let Ok((duration, rate, channels)) = ogg_info(&src) else { continue };
            GameTrack {
                id: String::new(),
                game_key: key.into(),
                game_title: title.into(),
                filename: path.file_name().unwrap_or_default().to_string_lossy().to_string(),
                title: row.title.clone(),
                title_en: String::new(),
                title_ja: String::new(),
                source: Source::File(path.clone()),
                sample_rate: rate,
                channels,
                duration,
                loop_start: 0.0,
                loop_end: 0.0,
            }
        };
        track.id = format!("{key}:{}", row.file.to_lowercase());
        track.title = row.title.clone();
        let loop_file = if is_wav { path.clone() } else { path.with_extension("sfl") };
        if loop_file.is_file() {
            if let Ok(src) = FileRead::open(&loop_file) {
                let (s, e) = riff_loop(&src, track.sample_rate);
                if 0.0 <= s && s < e && e <= track.duration + 0.05 {
                    track.loop_start = s;
                    track.loop_end = e;
                }
            }
        }
        tracks.push(track);
    }
    tracks
}

pub fn discover_tracks(game: &AssignedGame, scratch: &Path) -> (Vec<GameTrack>, String) {
    let (mut tracks, error) = discover_inner(game, scratch);
    for t in tracks.iter_mut() {
        titles::apply_titles(t);
    }
    (tracks, error)
}

fn discover_inner(game: &AssignedGame, scratch: &Path) -> (Vec<GameTrack>, String) {
    let key = game.key.as_str();
    let title = game.title.as_str();
    let dir = game.path.canonicalize().unwrap_or_else(|_| game.path.clone()).parent().map(Path::to_path_buf).unwrap_or_default();
    if key == "th6" {
        let bgm = dir.join("bgm");
        if !bgm.is_dir() {
            return (Vec::new(), "No bgm folder was found in the assigned game.".into());
        }
        let num = regex::Regex::new(r"_(\d+)").unwrap();
        let mut wavs: Vec<PathBuf> = std::fs::read_dir(&bgm)
            .map(|it| it.flatten().map(|e| e.path()).filter(|p| p.extension().map_or(false, |x| x == "wav")).collect())
            .unwrap_or_default();
        wavs.sort_by_key(|p| {
            let stem = p.file_stem().unwrap_or_default().to_string_lossy().to_string();
            let n = num.captures(&stem).and_then(|c| c[1].parse::<u32>().ok()).unwrap_or(9999);
            (n, p.file_name().unwrap_or_default().to_string_lossy().to_lowercase())
        });
        let mut tracks: Vec<GameTrack> = wavs.iter().filter_map(|p| wav_track(p, key, title)).collect();
        th06_loop_points(&dir, &mut tracks, scratch);
        let err = if tracks.is_empty() { "No playable WAV tracks were found in the game's bgm folder." } else { "" };
        return (tracks, err.into());
    }
    let Some((whole, decimal)) = game_number(key) else {
        return (Vec::new(), "This game's music format is not recognized yet.".into());
    };
    if decimal.is_empty() && (1..=5).contains(&whole) {
        return pc98::discover(key, title, &game.path, game.music_room.as_deref(), scratch);
    }
    if matches!(key, "th13.5" | "th14.5" | "th15.5" | "th17.5") {
        return tasofro::archive_tracks(key, title, &game.path, &dir);
    }
    let compact = format!("{whole}{decimal}");
    let special = match compact.as_str() {
        "75" => Some(dir.join("th075bgm.dat")),
        "105" | "123" => Some(dir.join(format!("th{compact}b.dat"))),
        _ => None,
    };
    if let Some(special) = special.filter(|p| p.is_file()) {
        let tracks = archive_audio_tracks(&special, key, title, scratch);
        if !tracks.is_empty() {
            return (tracks, String::new());
        }
        return (
            Vec::new(),
            format!(
                "The BGM archive {} could not be read. This archive uses the Twilight Frontier BGM format rather than the standard Team Shanghai Alice format.",
                special.file_name().unwrap_or_default().to_string_lossy()
            ),
        );
    }
    if !dir.join("thbgm.dat").is_file() && !dir.join("thbgm_tr.dat").is_file() {
        return (Vec::new(), "This game does not contain a supported BGM archive.".into());
    }
    let Some(fmt) = find_or_extract_fmt(&dir, key, scratch) else {
        if tool_path("thdat").is_none() {
            let msg = if cfg!(windows) {
                "BGM metadata is packed inside the game's .dat archive. Put thdat.exe in tools/thtk/bin/ (see README.md) to enable Game BGM for this game."
            } else {
                "BGM metadata is packed inside the game's .dat archive. Run scripts/install_thtk.sh in the launcher folder once to enable Game BGM for this game."
            };
            return (Vec::new(), msg.into());
        }
        return (Vec::new(), "The game's BGM metadata could not be extracted from its .dat archive.".into());
    };
    let tracks = parse_fmt(&fmt, key, title, &dir);
    if tracks.is_empty() {
        return (Vec::new(), "The game's BGM metadata could not be read.".into());
    }
    (tracks, String::new())
}
