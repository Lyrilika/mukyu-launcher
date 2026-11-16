
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::process::Command;

use anyhow::{anyhow, bail, Result};
use sha1::{Digest, Sha1};

use super::hdi::HdiFilesystem;
use super::{GameTrack, Source};
use crate::paths;
use crate::platform::no_window;

const CACHE_VERSION: &str = "6";
const RENDER_TAIL: f64 = 1.5;
const RHYTHM_NAMES: [&str; 6] = ["BD", "SD", "TOP", "HH", "TOM", "RIM"];
const PF_NONE: u16 = 0xF388;
const PF_RLE: u16 = 0x9595;

fn cache_dir() -> PathBuf {
    paths::cache_dir().join("pc98")
}

fn bin_dir() -> PathBuf {
    paths::tools_dir().join("pc98").join("bin")
}

fn rle_unpack(buf: &[u8], orgsize: usize) -> Vec<u8> {
    let mut out = Vec::with_capacity(orgsize);
    let mut prev: i32 = -1;
    let mut i = 0;
    while out.len() < orgsize && i < buf.len() {
        let b = buf[i];
        i += 1;
        if b as i32 == prev {
            let count = if i < buf.len() { buf[i] } else { 0 };
            i += 1;
            out.push(b);
            out.extend(std::iter::repeat(b).take(count as usize));
        } else {
            prev = b as i32;
            out.push(b);
        }
    }
    out.truncate(orgsize);
    out
}

#[derive(Clone)]
struct PfMember {
    kind: u16,
    aux: u8,
    psize: usize,
    osize: usize,
    offset: usize,
}

fn printable(name: &[u8]) -> bool {
    !name.is_empty() && name.iter().all(|&c| (0x20..0x7F).contains(&c))
}

fn parse_pf_th02(data: &[u8]) -> Option<Vec<(String, PfMember)>> {
    let mut members = Vec::new();
    let mut pos = 0;
    while pos + 32 <= data.len() {
        let kind = u16::from_le_bytes([data[pos], data[pos + 1]]);
        if kind == 0 {
            break;
        }
        if kind != PF_NONE && kind != PF_RLE {
            return None;
        }
        let raw: Vec<u8> = data[pos + 3..pos + 16].iter().map(|c| !c).collect();
        let name = raw.split(|&c| c == 0xFF).next().unwrap_or(&[]);
        if !printable(name) {
            return None;
        }
        let psize = u32::from_le_bytes(data[pos + 16..pos + 20].try_into().unwrap()) as usize;
        let osize = u32::from_le_bytes(data[pos + 20..pos + 24].try_into().unwrap()) as usize;
        let offset = u32::from_le_bytes(data[pos + 24..pos + 28].try_into().unwrap()) as usize;
        if offset + psize > data.len() {
            return None;
        }
        members.push((String::from_utf8_lossy(name).to_uppercase(), PfMember { kind, aux: 0x12, psize, osize, offset }));
        pos += 32;
    }
    (!members.is_empty()).then_some(members)
}

fn parse_pf_th03(data: &[u8]) -> Option<Vec<(String, PfMember)>> {
    if data.len() < 48 {
        return None;
    }
    let esize = u16::from_le_bytes([data[0], data[1]]) as usize;
    let key = u16::from_le_bytes([data[6], data[7]]);
    if esize < 32 || esize % 32 != 0 || 16 + esize > data.len() {
        return None;
    }
    let mut table = data[16..16 + esize].to_vec();
    let mut al = (key & 0xFF) as u8;
    for c in table.iter_mut() {
        let plain = *c ^ al;
        *c = plain;
        al = al.wrapping_sub(plain);
    }
    let mut members = Vec::new();
    for pos in (0..esize).step_by(32) {
        let kind = u16::from_le_bytes([table[pos], table[pos + 1]]);
        let aux = table[pos + 2];
        if kind == 0 {
            break;
        }
        if kind != PF_NONE && kind != PF_RLE {
            return None;
        }
        let name = table[pos + 3..pos + 16].split(|&c| c == 0).next().unwrap_or(&[]);
        if !printable(name) {
            return None;
        }
        let psize = u16::from_le_bytes([table[pos + 16], table[pos + 17]]) as usize;
        let osize = u16::from_le_bytes([table[pos + 18], table[pos + 19]]) as usize;
        let offset = u32::from_le_bytes(table[pos + 20..pos + 24].try_into().unwrap()) as usize;
        if offset + psize > data.len() {
            return None;
        }
        members.push((String::from_utf8_lossy(name).to_uppercase(), PfMember { kind, aux, psize, osize, offset }));
    }
    (!members.is_empty()).then_some(members)
}

struct PfArchive {
    data: Vec<u8>,
    members: HashMap<String, PfMember>,
    order: Vec<String>,
}

impl PfArchive {
    fn open(data: Vec<u8>) -> Option<PfArchive> {
        let members = parse_pf_th03(&data).or_else(|| parse_pf_th02(&data))?;
        let order = members.iter().map(|(n, _)| n.clone()).collect();
        Some(PfArchive { data, members: members.into_iter().collect(), order })
    }

    fn read(&self, name: &str) -> Vec<u8> {
        let m = &self.members[&name.to_uppercase()];
        let mut raw = self.data[m.offset..m.offset + m.psize].to_vec();
        if m.aux != 0 {
            raw.iter_mut().for_each(|b| *b ^= m.aux);
        }
        if m.kind == PF_RLE {
            rle_unpack(&raw, m.osize)
        } else {
            raw.truncate(m.osize);
            raw
        }
    }
}

type Catalog = Vec<(&'static str, Vec<&'static str>)>;

fn catalog(number: u32) -> Catalog {
    let c = |items: &[(&'static str, &[&'static str])]| items.iter().map(|(t, s)| (*t, s.to_vec())).collect::<Catalog>();
    match number {
        1 => c(&[
            ("A Sacred Lot", &["REIMU"]),
            ("Eternal Shrine Maiden (永遠の巫女)", &["ST0", "ST6"]),
            ("The Positive and Negative", &["POSITIVE"]),
            ("Highly Responsive to Prayers", &["ST1"]),
            ("Eastern Tale of Fancy (東方怪奇談)", &["ST2"]),
            ("Angel's Legend (天使伝説)", &["LEGEND"]),
            ("Oriental Magician", &["ST3"]),
            ("Small Evil-Crushing Blade (破邪の小太刀)", &["ST4"]),
            ("Magic Mirror (魔鏡)", &["KAMI", "KAMI2"]),
            ("The Legend of KAGE", &["ST5"]),
            ("Now, Until the Moment You Die (いざ、倒れ逝くその時まで)", &["TENSI"]),
            ("Civilization of Magic", &["SHUGEN", "SYUGEN"]),
            ("Angel of a Distant Star (星幽天使)", &["ALICE"]),
            ("Iris (アイリス)", &["IRIS"]),
            ("Shrine of the Wind", &["ZIPANGU"]),
        ]),
        2 => c(&[
            ("東方封魔録 ～ 浄土曼荼羅 (Pure Land Mandala)", &["OP"]),
            ("博麗 ～ Eastern Wind", &["STAGE0"]),
            ("She's in a temper!!", &["BOSS1"]),
            ("End of Daylight", &["STAGE1"]),
            ("やみのちから (Power of Darkness)", &["BOSS4"]),
            ("幻夢界 (Dream World)", &["STAGE2"]),
            ("死を賭して (Staking Your Life)", &["BOSS2"]),
            ("ひもろぎ、むらさきにもえ (Himorogi, Burning Purple)", &["STAGE3"]),
            ("恋色マジック (Love-Colored Magic)", &["BOSS3"]),
            ("東方封魔録 ～ 幽幻乱舞 (Phantom Dance)", &["STAGE4"]),
            ("Complete Darkness", &["MIMA"]),
            ("エキストララブ (Extra Love)", &["STAGE5"]),
            ("戦車むすめのみるゆめ (The Dream a Tank Girl Sees)", &["BOSS5"]),
            ("遠野の森 (Forest of Tōno)", &["END1"]),
            ("昔話わんだーらんど (Folktale Wonderland)", &["ENDING"]),
            ("Hakurei Shrine Grounds (博麗神社境内)", &["H_NG00"]),
            ("Sunfall (陽落ちて)", &["H_NG01"]),
            ("Demon-Sealing Finale (封魔終演)", &["H_NG02"]),
        ]),
        3 => c(&[
            ("A Dream Transcending Spacetime", &["OP"]),
            ("Selection", &["SELECT"]),
            ("Eastern Mystical Tale of Romance", &["00MM"]),
            ("Reincarnation", &["01MM"]),
            ("Dim. Dream", &["02MM"]),
            ("Tabula rasa ~ The Empty Girl", &["03MM"]),
            ("Maniacal Princess", &["04MM"]),
            ("Vanishing Dream ~ Lost Dream", &["05MM"]),
            ("Visionary Game ~ Dream War", &["06MM"]),
            ("Decisive Magic Battle! ~ Fight it out!", &["DEC"]),
            ("Sailor of Time", &["07MM"]),
            ("Strawberry Crisis!!", &["08MM"]),
            ("Disunified Field Theory of Magic", &["DEMO1"]),
            ("Adoration of Magic", &["DEMO2"]),
            ("Dream of Eternity", &["DEMO3"]),
            ("Eastern Blue Sky", &["DEMO4"]),
            ("Eternal Full Moon", &["DEMO5"]),
            ("Maple Dream...", &["ED"]),
            ("Ghostly Person's Holiday", &["SCORE"]),
            ("Victory Demonstration", &["WIN"]),
            ("Game Over", &["OVER"]),
            ("Winds of Time", &["Y_NG00"]),
            ("Starbow Dream", &["Y_NG01"]),
            ("Phantasmagoria", &["Y_NG02"]),
        ]),
        4 => c(&[
            ("幻想郷 ～ Lotus Land Story", &["OP"]),
            ("Witching Dream", &["ST00"]),
            ("Selene's light", &["ST10"]),
            ("装飾戦 ～ Decoration Battle", &["ST00B"]),
            ("Break the Sabbath", &["ST01"]),
            ("紅響曲 ～ Scarlet Phoneme", &["ST01B"]),
            ("Bad Apple!!", &["ST02"]),
            ("霊戦 ～ Perdition crisis", &["ST02B"]),
            ("アリスマエステラ (Alice Maestra)", &["ST03"]),
            ("少女綺想曲 ～ Capriccio", &["ST03C"]),
            ("星の器 ～ Casket of Star", &["ST03B"]),
            ("Lotus Love", &["ST04"]),
            ("眠れる恐怖 ～ Sleeping Terror", &["ST04B"]),
            ("Dream Land", &["ST05"]),
            ("幽夢 ～ Inanimate Dream", &["ST05B"]),
            ("禁じざるをえない遊戯 (A Game We Cannot Help Playing)", &["ST06"]),
            ("メイド幻想 ～ Icemilk Magic", &["ST06B"]),
            ("かわいい悪魔 ～ Innocence", &["ST06C"]),
            ("Days", &["END1"]),
            ("Peaceful", &["END2"]),
            ("Arcadian Dream", &["STAFF"]),
            ("幻想の住人 (Residents of Fantasy)", &["NAME"]),
            ("Lotus Road", &["G_NG00"]),
            ("Dreamy Pilot", &["G_NG01"]),
            ("Incomplete Plot", &["G_NG02"]),
            ("Border Land", &["G_NG03"]),
            ("Magic Shop of Raspberry", &["G_NG04"]),
            ("Crescent Dream", &["G_NG05"]),
        ]),
        5 => c(&[
            ("怪綺談 ～ Mystic Square", &["OP"]),
            ("Dream Express", &["ST00"]),
            ("魔法陣 ～ Magic Square", &["ST00B"]),
            ("夢想時空 (Dream Spacetime)", &["ST01"]),
            ("霊天 ～ Spiritual Heaven", &["ST01B"]),
            ("Romantic Children", &["ST02"]),
            ("プラスチックマインド (Plastic Mind)", &["ST02B"]),
            ("メイプルワイズ (Maple Wise)", &["ST03"]),
            ("禁断の魔法 ～ Forbidden Magic", &["ST03B"]),
            ("真紅の少女 ～ Crimson Dead!!", &["ST03C"]),
            ("裏切りの少女 ～ Judas Kiss", &["ST03D"]),
            ("the Last Judgement", &["ST04"]),
            ("悲しき人形 ～ Doll of Misery", &["ST04B"]),
            ("世界の果て ～ World's End", &["ST05"]),
            ("神話幻想 ～ Infinite Being", &["ST05B"]),
            ("不思議の国のアリス (Alice in Wonderland)", &["ST06"]),
            ("the Grimoire of Alice", &["ST06B"]),
            ("神社 (Shrine)", &["ED00"]),
            ("Endless", &["ED01"]),
            ("久遠の楽園 (Eternal Paradise)", &["ED02"]),
            ("Mystic Dream", &["STAFF"]),
            ("Peaceful Romancer", &["EXED"]),
            ("魂の休らむ所 (Where Souls Rest)", &["NAME"]),
        ]),
        _ => Vec::new(),
    }
}

const TH03_ORDER: [&str; 24] = [
    "OP", "SELECT", "00MM", "01MM", "02MM", "03MM", "04MM", "05MM", "06MM", "WIN", "DEC", "DEMO1", "07MM", "DEMO2",
    "08MM", "DEMO3", "DEMO4", "DEMO5", "ED", "OVER", "SCORE", "Y_NG00", "Y_NG01", "Y_NG02",
];

fn extensions(number: u32) -> &'static [&'static str] {
    match number {
        1 => &[".MDT"],
        2 | 3 => &[".M"],
        4 => &[".M86", ".M26"],
        5 => &[".M2", ".M"],
        _ => &[],
    }
}

fn tool(name: &str) -> Option<PathBuf> {
    let path = bin_dir().join(paths::exe_name(name));
    if paths::is_executable(&path) {
        Some(path)
    } else {
        paths::which(&paths::exe_name(name))
    }
}

fn renderer_missing_message(number: u32) -> String {
    let tool = if number == 1 { "mdt_render" } else { "pmd_render" };
    if cfg!(windows) {
        format!("The PC-98 music renderer ({tool}.exe) is not installed. Build it with packaging/windows (see README.md) and put it in tools/pc98/bin/.")
    } else {
        format!("The PC-98 music renderer ({tool}) is not installed or cannot run. Run scripts/install_pc98_music.sh in the launcher folder.")
    }
}

fn synthesize_rhythm(dir: &Path) -> Result<()> {
    use rand::{Rng, SeedableRng};
    let rate = 48000u32;
    let mut rng = rand::rngs::StdRng::seed_from_u64(98);
    let write = |name: &str, samples: Vec<f64>| -> Result<()> {
        let mut data = Vec::with_capacity(44 + samples.len() * 2);
        let len = (samples.len() * 2) as u32;
        data.extend_from_slice(b"RIFF");
        data.extend_from_slice(&(36 + len).to_le_bytes());
        data.extend_from_slice(b"WAVEfmt ");
        data.extend_from_slice(&16u32.to_le_bytes());
        data.extend_from_slice(&1u16.to_le_bytes());
        data.extend_from_slice(&1u16.to_le_bytes());
        data.extend_from_slice(&rate.to_le_bytes());
        data.extend_from_slice(&(rate * 2).to_le_bytes());
        data.extend_from_slice(&2u16.to_le_bytes());
        data.extend_from_slice(&16u16.to_le_bytes());
        data.extend_from_slice(b"data");
        data.extend_from_slice(&len.to_le_bytes());
        for s in samples {
            data.extend_from_slice(&(s.clamp(-32767.0, 32767.0) as i16).to_le_bytes());
        }
        std::fs::write(dir.join(format!("2608_{name}.WAV")), data)?;
        Ok(())
    };
    let sweep = |f0: f64, f1: f64, dur: f64, decay: f64, amp: f64| -> Vec<f64> {
        let n = (rate as f64 * dur) as usize;
        let mut phase = 0.0;
        (0..n)
            .map(|i| {
                let t = i as f64 / n as f64;
                phase += 2.0 * std::f64::consts::PI * (f1 + (f0 - f1) * (-t * 6.0).exp()) / rate as f64;
                amp * phase.sin() * (-t * decay).exp()
            })
            .collect()
    };
    let mut noise = |dur: f64, decay: f64, amp: f64, hp: f64| -> Vec<f64> {
        let n = (rate as f64 * dur) as usize;
        let mut prev = 0.0;
        (0..n)
            .map(|i| {
                let x: f64 = rng.gen_range(-1.0..1.0);
                let y = x - hp * prev;
                prev = x;
                amp * y * (-(i as f64) / n as f64 * decay).exp()
            })
            .collect()
    };
    write("BD", sweep(160.0, 45.0, 0.25, 7.0, 24000.0))?;
    let tone = sweep(260.0, 180.0, 0.2, 9.0, 9000.0);
    let sd_noise = noise(0.2, 8.0, 9000.0, 0.3);
    write("SD", tone.iter().zip(sd_noise).map(|(a, b)| a + b).collect())?;
    write("TOP", noise(0.7, 5.0, 9000.0, 0.9))?;
    write("HH", noise(0.08, 9.0, 8000.0, 0.95))?;
    write("TOM", sweep(220.0, 90.0, 0.3, 6.0, 22000.0))?;
    write("RIM", sweep(1700.0, 1500.0, 0.04, 20.0, 18000.0))?;
    Ok(())
}

pub fn rhythm_dir(image: &Path) -> PathBuf {
    let image = image.canonicalize().unwrap_or_else(|_| image.to_path_buf());
    let parent = image.parent().map(Path::to_path_buf).unwrap_or_default();
    let candidates = [
        parent.clone(),
        parent.parent().map(Path::to_path_buf).unwrap_or_default(),
        paths::tools_dir().join("pc98/rhythm"),
        cache_dir().join("rhythm_user"),
    ];
    let wanted: Vec<String> = RHYTHM_NAMES.iter().map(|n| format!("2608_{n}.WAV")).collect();
    for dir in candidates {
        let Ok(it) = std::fs::read_dir(&dir) else { continue };
        let files: Vec<(String, PathBuf)> = it.flatten().map(|e| (e.file_name().to_string_lossy().to_uppercase(), e.path())).collect();
        if wanted.iter().all(|w| files.iter().any(|(n, _)| n == w)) {
            let out = cache_dir().join("rhythm_real");
            let _ = std::fs::create_dir_all(&out);
            for (name, path) in files.iter().filter(|(n, _)| wanted.contains(n)) {
                let target = out.join(name);
                let same = std::fs::metadata(&target).ok().map(|m| m.len()) == std::fs::metadata(path).ok().map(|m| m.len());
                if !same {
                    let _ = std::fs::copy(path, &target);
                }
            }
            return out;
        }
    }
    let out = cache_dir().join("rhythm_synth");
    if !wanted.iter().all(|w| out.join(w).is_file()) {
        let _ = std::fs::create_dir_all(&out);
        let _ = synthesize_rhythm(&out);
    }
    out
}

enum Loader {
    Disk(String),
    Pf(usize, String),
}

struct Index {
    entries: HashMap<String, Loader>,
    archives: Vec<PfArchive>,
}

fn collect_members(fs: &HdiFilesystem, number: u32) -> Index {
    let mut entries = HashMap::new();
    let mut archives = Vec::new();
    for entry in fs.entries() {
        if entry.is_dir || entry.size < 32 {
            continue;
        }
        let base = entry.path.rsplit('/').next().unwrap_or(&entry.path).to_uppercase();
        let suffix = base.rfind('.').map(|i| base[i..].to_string()).unwrap_or_default();
        if number == 1 && base == "MDRV98.COM" {
            entries.insert(base, Loader::Disk(entry.path.clone()));
            continue;
        }
        if [".EXE", ".COM", ".SYS", ".BAT", ".TXT", ".URL", ".PI", ".GRP", ".GRZ", ".GRF"].contains(&suffix.as_str()) {
            continue;
        }
        if extensions(number).contains(&suffix.as_str()) {
            entries.entry(base).or_insert(Loader::Disk(entry.path.clone()));
            continue;
        }
        if number == 1 || entry.size > 4 * 1024 * 1024 {
            continue;
        }
        if let Ok(data) = fs.read_file(&entry.path) {
            if let Some(a) = PfArchive::open(data) {
                archives.push(a);
            }
        }
    }
    for (i, archive) in archives.iter().enumerate() {
        for name in &archive.order {
            entries.entry(name.clone()).or_insert(Loader::Pf(i, name.clone()));
        }
    }
    Index { entries, archives }
}

fn read_member(fs: &HdiFilesystem, index: &Index, name: &str) -> Result<Vec<u8>> {
    match index.entries.get(name).ok_or_else(|| anyhow!("missing {name}"))? {
        Loader::Disk(path) => fs.read_file(path),
        Loader::Pf(i, n) => Ok(index.archives[*i].read(n)),
    }
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Default)]
struct ProbeInfo {
    length_ms: u64,
    loop_ms: u64,
    title: String,
}

fn parse_kv(stdout: &[u8]) -> HashMap<String, Vec<u8>> {
    stdout
        .split(|&b| b == b'\n')
        .filter_map(|line| {
            let p = line.iter().position(|&b| b == b'=')?;
            let mut v = line[p + 1..].to_vec();
            if v.last() == Some(&b'\r') {
                v.pop();
            }
            Some((String::from_utf8_lossy(&line[..p]).to_string(), v))
        })
        .collect()
}

fn probe(tool: &Path, path: &Path, rhythm: &Path, driver: Option<&Path>) -> Option<ProbeInfo> {
    let mut cmd = Command::new(tool);
    cmd.arg("--info").arg(path);
    match driver {
        Some(d) => cmd.arg("--driver").arg(d),
        None => cmd.arg("--rhythm").arg(rhythm),
    };
    let out = no_window(&mut cmd).output().ok()?;
    if !out.status.success() {
        return None;
    }
    let v = parse_kv(&out.stdout);
    let num = |k: &str| -> Option<u64> { String::from_utf8_lossy(v.get(k).map(|x| x.as_slice()).unwrap_or(b"0")).trim().parse().ok() };
    if driver.is_some() {
        let length = num("LENGTH_MS")?;
        let looped = v.get("LOOPED").map(|x| x.as_slice()) == Some(b"1");
        let start = num("LOOP_START_MS")?;
        Some(ProbeInfo { length_ms: length, loop_ms: if looped { length.saturating_sub(start) } else { 0 }, title: String::new() })
    } else {
        Some(ProbeInfo {
            length_ms: num("LENGTH_MS")?,
            loop_ms: num("LOOP_MS")?,
            title: crate::util::decode_cp932(v.get("TITLE").map(|x| x.as_slice()).unwrap_or(b"")).trim().to_string(),
        })
    }
}

fn music_room_source(exe: &Path, configured: Option<&Path>, number: u32) -> Option<(HdiFilesystem, Index)> {
    if !(2..=4).contains(&number) {
        return None;
    }
    let mut candidates: Vec<PathBuf> = Vec::new();
    if let Some(c) = configured {
        candidates.push(c.to_path_buf());
    }
    if let Some(dir) = exe.parent() {
        let mut found: Vec<PathBuf> = std::fs::read_dir(dir)
            .map(|it| {
                it.flatten()
                    .map(|e| e.path())
                    .filter(|p| {
                        let n = p.file_name().unwrap_or_default().to_string_lossy().to_string();
                        (n.starts_with("th05") && n.ends_with(".hdi")) || (n.starts_with("TH05") && n.ends_with(".HDI"))
                    })
                    .collect()
            })
            .unwrap_or_default();
        found.sort();
        candidates.extend(found);
    }
    let own = exe.canonicalize().ok();
    let mut seen = Vec::new();
    for c in candidates {
        if seen.contains(&c) {
            continue;
        }
        seen.push(c.clone());
        if !c.is_file() || c.canonicalize().ok() == own {
            continue;
        }
        if let Ok(fs) = HdiFilesystem::open(&c) {
            let index = collect_members(&fs, 5);
            if index.entries.keys().any(|n| n.starts_with("H_NG") || n.starts_with("Y_NG") || n.starts_with("G_NG")) {
                return Some((fs, index));
            }
        }
    }
    None
}

fn file_sha1(path: &Path) -> Result<String> {
    let mut hasher = Sha1::new();
    std::io::copy(&mut std::fs::File::open(path)?, &mut hasher)?;
    Ok(hex::encode(hasher.finalize()))
}

pub fn discover(key: &str, title: &str, exe: &Path, music_room: Option<&Path>, scratch: &Path) -> (Vec<GameTrack>, String) {
    let number: u32 = key.trim_start_matches("th").parse().unwrap_or(0);
    let cat = catalog(number);
    if cat.is_empty() {
        return (Vec::new(), "This game's music format is not recognized.".into());
    }
    let fs = match HdiFilesystem::open(exe) {
        Ok(fs) => fs,
        Err(e) => return (Vec::new(), format!("The PC-98 disk image could not be read: {e}")),
    };
    let index = collect_members(&fs, number);
    if index.entries.is_empty() {
        return (Vec::new(), "No music files were found inside the PC-98 disk image.".into());
    }
    let work = scratch.join(format!("pc98-{key}"));
    let _ = std::fs::create_dir_all(&work);
    let renderer = tool(if number == 1 { "mdt_render" } else { "pmd_render" });
    let rhythm = rhythm_dir(exe);
    let image_id = file_sha1(exe).map(|h| h[..16].to_string()).unwrap_or_default();
    let cache_file = cache_dir().join(format!("{key}-{image_id}-v{CACHE_VERSION}.json"));
    let mut cache: HashMap<String, ProbeInfo> = crate::util::read_json(&cache_file).unwrap_or_default();

    let mut driver = None;
    if number == 1 {
        if !index.entries.contains_key("MDRV98.COM") {
            return (Vec::new(), "MDRV98.COM (the TH01 music driver) was not found on the disk image.".into());
        }
        let path = work.join("MDRV98.COM");
        match read_member(&fs, &index, "MDRV98.COM").and_then(|d| Ok(std::fs::write(&path, d)?)) {
            Ok(()) => driver = Some(path),
            Err(e) => return (Vec::new(), format!("The TH01 music driver could not be read: {e}")),
        }
    }

    let room = music_room_source(exe, music_room, number);
    let mut picks: Vec<(usize, &str, String, PathBuf)> = Vec::new();
    for (position, (track_title, stems)) in cat.iter().enumerate().map(|(i, x)| (i + 1, x)) {
        if number == 3 && !TH03_ORDER.contains(&stems[0]) {
            continue;
        }
        let mut chosen: Option<(String, Vec<u8>)> = None;
        'outer: for stem in stems {
            for ext in extensions(number) {
                let name = format!("{stem}{ext}");
                if index.entries.contains_key(&name) {
                    if let Ok(data) = read_member(&fs, &index, &name) {
                        chosen = Some((name, data));
                    }
                    break 'outer;
                }
            }
        }
        if chosen.is_none() {
            if let Some((room_fs, room_index)) = &room {
                'room: for stem in stems.iter().filter(|s| s.starts_with("H_NG") || s.starts_with("Y_NG") || s.starts_with("G_NG")) {
                    for ext in [".M2", ".M"] {
                        let name = format!("{stem}{ext}");
                        if room_index.entries.contains_key(&name) {
                            if let Ok(data) = read_member(room_fs, room_index, &name) {
                                chosen = Some((name, data));
                            }
                            break 'room;
                        }
                    }
                }
            }
        }
        let Some((name, data)) = chosen else { continue };
        let dest = work.join(format!("{position:02}_{name}"));
        if std::fs::write(&dest, data).is_ok() {
            picks.push((position, track_title, name, dest));
        }
    }
    if picks.is_empty() {
        return (Vec::new(), "None of this game's music files could be read from the disk image.".into());
    }

    let driver_data = driver.as_ref().and_then(|d| std::fs::read(d).ok()).unwrap_or_default();
    let mut infos: HashMap<usize, ProbeInfo> = HashMap::new();
    let mut todo = Vec::new();
    for (position, _, _, dest) in &picks {
        let mut hasher = Sha1::new();
        hasher.update(std::fs::read(dest).unwrap_or_default());
        hasher.update(&driver_data);
        let ck = hex::encode(hasher.finalize());
        match cache.get(&ck) {
            Some(info) => {
                infos.insert(*position, info.clone());
            }
            None => todo.push((*position, ck, dest.clone())),
        }
    }
    if let (false, Some(renderer)) = (todo.is_empty(), renderer.as_ref()) {
        let workers = std::thread::available_parallelism().map(|n| n.get()).unwrap_or(2).clamp(1, 4);
        let results = std::sync::Mutex::new(Vec::new());
        let queue = std::sync::Mutex::new(todo.into_iter());
        std::thread::scope(|s| {
            for _ in 0..workers {
                s.spawn(|| loop {
                    let Some((position, ck, dest)) = queue.lock().unwrap().next() else { break };
                    if let Some(info) = probe(renderer, &dest, &rhythm, driver.as_deref()) {
                        results.lock().unwrap().push((position, ck, info));
                    }
                });
            }
        });
        for (position, ck, info) in results.into_inner().unwrap() {
            cache.insert(ck, info.clone());
            infos.insert(position, info);
        }
        let _ = std::fs::create_dir_all(cache_dir());
        let _ = std::fs::write(&cache_file, serde_json::to_string(&cache).unwrap_or_default());
    }

    let mut tracks: Vec<GameTrack> = picks
        .into_iter()
        .map(|(position, track_title, name, dest)| {
            let info = infos.get(&position).cloned().unwrap_or_default();
            let length = info.length_ms as f64 / 1000.0;
            let lp = info.loop_ms as f64 / 1000.0;
            let mut track = GameTrack {
                id: format!("{key}:{position:02}:{}", name.to_lowercase()),
                game_key: key.to_string(),
                game_title: title.to_string(),
                filename: name,
                title: track_title.to_string(),
                title_en: String::new(),
                title_ja: String::new(),
                source: Source::Pc98 { path: dest, mdt: number == 1, rhythm: rhythm.clone() },
                sample_rate: 44100,
                channels: 2,
                duration: length,
                loop_start: 0.0,
                loop_end: 0.0,
            };
            if lp > 0.5 && length >= lp {
                track.loop_start = (length - lp).max(0.0);
                track.loop_end = length;
            } else if lp <= 0.0 {
                track.duration = length + RENDER_TAIL;
            }
            track
        })
        .collect();
    if number == 3 {
        let order = |t: &GameTrack| {
            let stem = t.filename.rsplit_once('.').map(|(s, _)| s).unwrap_or(&t.filename).to_uppercase();
            TH03_ORDER.iter().position(|s| *s == stem).unwrap_or(usize::MAX)
        };
        tracks.sort_by_key(order);
    }
    let error = if renderer.is_some() { String::new() } else { renderer_missing_message(number) };
    (tracks, error)
}

pub fn render(track: &GameTrack, scratch: &Path) -> Result<PathBuf> {
    let Source::Pc98 { path, mdt, rhythm } = &track.source else { bail!("not a PC-98 track") };
    let number = if *mdt { 1 } else { 2 };
    let renderer = tool(if *mdt { "mdt_render" } else { "pmd_render" }).ok_or_else(|| anyhow!(renderer_missing_message(number)))?;
    let out = scratch.join(format!("{}-v{CACHE_VERSION}.wav", crate::util::sanitize_component(&track.id)));
    if std::fs::metadata(&out).map(|m| m.len() > 44).unwrap_or(false) {
        return Ok(out);
    }
    let _ = std::fs::create_dir_all(scratch);
    let tmp = out.with_extension("part");
    let mut cmd = Command::new(&renderer);
    cmd.arg("--render").arg(path).arg(&tmp).arg("--rhythm").arg(rhythm);
    if *mdt {
        let driver = path.with_file_name("MDRV98.COM");
        if !driver.is_file() {
            bail!("The TH01 music driver (MDRV98.COM) has not been extracted yet.");
        }
        cmd.arg("--driver").arg(driver);
    }
    let result = no_window(&mut cmd).output()?;
    let ok = result.status.success() && std::fs::metadata(&tmp).map(|m| m.len() > 44).unwrap_or(false);
    if !ok {
        let _ = std::fs::remove_file(&tmp);
        let detail = String::from_utf8_lossy(if result.stderr.is_empty() { &result.stdout } else { &result.stderr }).trim().to_string();
        if detail.is_empty() {
            bail!("The renderer failed (exit code {:?}).", result.status.code());
        }
        bail!(detail);
    }
    std::fs::rename(&tmp, &out)?;
    Ok(out)
}
