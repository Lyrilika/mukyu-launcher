
use std::collections::HashMap;
use std::io::{Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use std::sync::OnceLock;

use anyhow::{anyhow, bail, Result};
use num_bigint::BigUint;
use serde::Deserialize;

use super::metadata::{ogg_info, riff_loop, RandomRead};
use super::{GameTrack, Source};

const MODULI: [&str; 4] = [
    "c79a9e9bfbc20cb0c3e7ae274967628a78bbd12cb24df487c70935f701f82ee5493b836b8426aa429ae1ccee08a2151c42e748b19cce7ad9401a4dd436375c89",
    "ff657274616952202d2d20696f6b6e616c46207373656c4220646f472079614d088bf4755d78b1c8937f40ea34a585c11b8d631775982da817453131514f6e8d",
    "c643e09d355e981dbe636d3a5f840f49b8e853f54206373b3625cb65cedd688cf75d720ac047bdfa3b104cd22cfe7203104dd885153555a35aafc34a3bf3e237",
    "c44d6a2f05782c0fd75c8297176091dd6f836181d14e069b9437d2984de47bbf4260a78f88d6fdfee1f56a0b29cf0bed66f0ac4ed7ef96068bfa8e3348a3027d",
];

#[derive(Deserialize, Clone)]
pub struct CatalogEntry {
    pub file: String,
    pub title: String,
    #[serde(default)]
    #[allow(dead_code)]
    pub title_ja: String,
}

pub fn catalog() -> &'static HashMap<String, Vec<CatalogEntry>> {
    static C: OnceLock<HashMap<String, Vec<CatalogEntry>>> = OnceLock::new();
    C.get_or_init(|| {
        let path = crate::paths::assets_dir().join("catalogs/bgm_catalog.json");
        std::fs::read_to_string(path).ok().and_then(|t| serde_json::from_str(&t).ok()).unwrap_or_default()
    })
}

pub fn name_hash(name: &str, version: u8) -> u64 {
    let name = if version != 2 { name.to_lowercase().replace('/', "\\") } else { name.to_string() };
    let mut value: u32 = 0x811c9dc5;
    for b in crate::util::encode_cp932(&name) {
        value = if version == 0 {
            value.wrapping_mul(0x1000193) ^ b as u32
        } else {
            (value ^ b as u32).wrapping_mul(0x1000193)
        };
    }
    if version == 1 { value.wrapping_neg() as u64 } else { value as u64 }
}

fn cga_decode(data: &[u8], size: u64, offset: u64, start: u64) -> Vec<u8> {
    let mut out = vec![0u8; data.len()];
    let seed = (size ^ offset).wrapping_add(start / 4);
    for pos in (0..data.len()).step_by(4) {
        let mut k = seed.wrapping_add((pos / 4) as u64) as u32;
        let mut word: u32 = 0;
        for _ in 0..4 {
            let a = k as u64 * 0x5e47_89c9;
            let b = ((a >> 46) + (a >> 63)) as u32;
            k = k.wrapping_sub(b.wrapping_mul(0xadc8)).wrapping_mul(0xbc8f).wrapping_add(b.wrapping_mul(0xffff_f2b9));
            if k == 0 || k >= 0x8000_0000 {
                k = k.wrapping_add(0x7fff_ffff);
            }
            word = (word << 8) | (k & 255);
        }
        let end = (pos + 4).min(data.len());
        for i in pos..end {
            out[i] = data[i] ^ (word >> (8 * (i - pos))) as u8;
        }
    }
    out
}

#[derive(Clone, Debug)]
pub struct Member {
    pub archive: PathBuf,
    pub offset: u64,
    pub size: u64,
    pub version: u8,
    pub key: [u8; 16],
}

impl Member {
    pub fn read_with(&self, file: &mut std::fs::File, start: u64, length: Option<u64>) -> Result<Vec<u8>> {
        if start > self.size {
            bail!("Invalid archive member range");
        }
        let length = length.map_or(self.size - start, |l| l.min(self.size - start));
        let aligned = start - start % 16;
        let preceding = if self.version == 1 && aligned > 0 { aligned - 4 } else { aligned };
        file.seek(SeekFrom::Start(self.offset + preceding))?;
        let want = (start + length - preceding) as usize;
        let mut raw = vec![0u8; want];
        file.read_exact(&mut raw).map_err(|_| anyhow!("Truncated music archive"))?;
        let plain = if self.version == 2 {
            cga_decode(&raw, self.size, self.offset, aligned)
        } else {
            let skip = (aligned - preceding) as usize;
            let data = &raw[skip..];
            let mut plain: Vec<u8> = data.iter().enumerate().map(|(i, b)| b ^ self.key[i % 16]).collect();
            if self.version == 1 {
                for i in 0..plain.len() {
                    let fb = if i < 4 {
                        if aligned > 0 { raw[i] } else { self.key[i] }
                    } else {
                        data[i - 4]
                    };
                    plain[i] ^= fb;
                }
            }
            plain
        };
        let from = (start - aligned) as usize;
        Ok(plain[from..from + length as usize].to_vec())
    }
}

impl RandomRead for Member {
    fn size(&self) -> u64 {
        self.size
    }
    fn read_at(&self, start: u64, len: usize) -> Result<Vec<u8>> {
        let mut f = std::fs::File::open(&self.archive)?;
        self.read_with(&mut f, start, Some(len as u64))
    }
}

pub struct MemberReader {
    member: Member,
    file: std::fs::File,
    pos: u64,
    buf: Vec<u8>,
    buf_start: u64,
}

impl MemberReader {
    pub fn new(member: Member) -> Result<Self> {
        let file = std::fs::File::open(&member.archive)?;
        Ok(MemberReader { member, file, pos: 0, buf: Vec::new(), buf_start: 0 })
    }
}

impl MemberReader {
    pub fn len(&self) -> u64 {
        self.member.size
    }
}

impl Read for MemberReader {
    fn read(&mut self, out: &mut [u8]) -> std::io::Result<usize> {
        if self.pos >= self.member.size || out.is_empty() {
            return Ok(0);
        }
        let in_buf = self.pos >= self.buf_start && self.pos < self.buf_start + self.buf.len() as u64;
        if !in_buf {
            let start = self.pos - self.pos % 16;
            self.buf = self
                .member
                .read_with(&mut self.file, start, Some(128 * 1024))
                .map_err(std::io::Error::other)?;
            self.buf_start = start;
        }
        let off = (self.pos - self.buf_start) as usize;
        let n = out.len().min(self.buf.len() - off);
        out[..n].copy_from_slice(&self.buf[off..off + n]);
        self.pos += n as u64;
        Ok(n)
    }
}

impl Seek for MemberReader {
    fn seek(&mut self, pos: SeekFrom) -> std::io::Result<u64> {
        let new = match pos {
            SeekFrom::Start(p) => p as i64,
            SeekFrom::End(d) => self.member.size as i64 + d,
            SeekFrom::Current(d) => self.pos as i64 + d,
        };
        if new < 0 {
            return Err(std::io::Error::new(std::io::ErrorKind::InvalidInput, "negative seek"));
        }
        self.pos = new as u64;
        Ok(self.pos)
    }
}

struct RsaReader<'a> {
    file: &'a mut std::fs::File,
    modulus: Option<BigUint>,
}

impl RsaReader<'_> {
    fn read(&mut self, mut size: usize) -> Result<Vec<u8>> {
        let mut result = Vec::with_capacity(size);
        let e = BigUint::from(65537u32);
        while size > 0 {
            let n = size.min(32);
            let mut block = [0u8; 64];
            self.file.read_exact(&mut block).map_err(|_| anyhow!("Truncated music archive"))?;
            let payload: Vec<u8> = if block[32..].iter().all(|&b| b == 0) {
                block[..32].to_vec()
            } else {
                let candidates: Vec<BigUint> = match &self.modulus {
                    Some(m) => vec![m.clone()],
                    None => MODULI.iter().map(|s| BigUint::parse_bytes(s.as_bytes(), 16).unwrap()).collect(),
                };
                let value = BigUint::from_bytes_be(&block);
                let mut found = None;
                for modulus in candidates {
                    let decoded_raw = value.modpow(&e, &modulus).to_bytes_be();
                    let mut decoded = vec![0u8; 64usize.saturating_sub(decoded_raw.len())];
                    decoded.extend_from_slice(&decoded_raw);
                    if decoded.len() != 64 {
                        continue;
                    }
                    let mut pad = 2;
                    while pad < 63 && decoded[pad] == 255 {
                        pad += 1;
                    }
                    if decoded[0] == 0 && decoded[1] == 1 && pad >= 31 && decoded[pad] == 0 && 63 - pad >= n {
                        self.modulus = Some(modulus);
                        found = Some(decoded[pad + 1..].to_vec());
                        break;
                    }
                }
                found.ok_or_else(|| anyhow!("Unsupported TFPK header key or damaged archive"))?
            };
            result.extend_from_slice(&payload[..n]);
            size -= n;
        }
        Ok(result)
    }

    fn u32(&mut self) -> Result<u32> {
        Ok(u32::from_le_bytes(self.read(4)?.try_into().unwrap()))
    }
}

pub fn read_tfpk(path: &Path) -> Result<(u8, HashMap<u64, Member>)> {
    let path = path.canonicalize()?;
    let archive_size = std::fs::metadata(&path)?.len();
    let mut f = std::fs::File::open(&path)?;
    let mut magic = [0u8; 5];
    f.read_exact(&mut magic).map_err(|_| anyhow!("Truncated music archive"))?;
    if &magic[..4] != b"TFPK" || magic[4] > 1 {
        bail!("Unsupported TFPK archive");
    }
    let version = magic[4];
    let mut rsa = RsaReader { file: &mut f, modulus: None };
    let dirs = rsa.u32()? as u64;
    if dirs > archive_size / 64 {
        bail!("Invalid TFPK directory count");
    }
    for _ in 0..dirs {
        rsa.read(8)?;
    }
    if dirs > 0 {
        let head = rsa.read(12)?;
        let compressed = u32::from_le_bytes(head[0..4].try_into().unwrap()) as u64;
        let original = u32::from_le_bytes(head[4..8].try_into().unwrap()) as u64;
        let blocks = u32::from_le_bytes(head[8..12].try_into().unwrap()) as u64;
        if blocks > archive_size / 64 || original > 16 * 1024 * 1024 || compressed > blocks * 32 {
            bail!("Invalid TFPK name table");
        }
        let raw = rsa.read((blocks * 32) as usize)?;
        let mut decoded = Vec::new();
        flate2::read::ZlibDecoder::new(&raw[..compressed as usize])
            .take(original + 1)
            .read_to_end(&mut decoded)
            .map_err(|_| anyhow!("Invalid TFPK name table"))?;
        if decoded.len() as u64 != original {
            bail!("Invalid TFPK name table size");
        }
    }
    let count = rsa.u32()? as u64;
    if count > archive_size / 192 {
        bail!("Invalid TFPK member count");
    }
    let mut records = Vec::with_capacity(count as usize);
    for _ in 0..count {
        let so = rsa.read(8)?;
        let mut size = u32::from_le_bytes(so[0..4].try_into().unwrap());
        let mut offset = u32::from_le_bytes(so[4..8].try_into().unwrap());
        let mut hashed = u32::from_le_bytes(rsa.read(if version == 0 { 4 } else { 8 })?[..4].try_into().unwrap());
        let mut key: [u8; 16] = rsa.read(16)?.try_into().unwrap();
        if version == 1 {
            let w: Vec<u32> = key.chunks_exact(4).map(|c| u32::from_le_bytes(c.try_into().unwrap())).collect();
            size ^= w[0];
            offset ^= w[1];
            hashed ^= w[2];
            for (i, v) in w.iter().enumerate() {
                key[i * 4..i * 4 + 4].copy_from_slice(&v.wrapping_neg().to_le_bytes());
            }
        }
        records.push((hashed, offset, size, key));
    }
    let base = f.stream_position()?;
    let mut members = HashMap::new();
    for (hashed, offset, size, key) in records {
        if base + offset as u64 + size as u64 > archive_size {
            bail!("TFPK member extends beyond archive");
        }
        members.insert(
            hashed as u64,
            Member { archive: path.clone(), offset: base + offset as u64, size: size as u64, version, key },
        );
    }
    Ok((version, members))
}

pub fn read_cga(path: &Path) -> Result<(u8, HashMap<u64, Member>)> {
    let path = path.canonicalize()?;
    let size = std::fs::metadata(&path)?.len();
    if size < 32 {
        bail!("Truncated CGA archive");
    }
    let mut f = std::fs::File::open(&path)?;
    f.seek(SeekFrom::Start(size - 32))?;
    let mut raw = [0u8; 32];
    f.read_exact(&mut raw)?;
    let footer: Vec<u32> =
        cga_decode(&raw, 32, size - 32, 0).chunks_exact(4).map(|c| u32::from_le_bytes(c.try_into().unwrap())).collect();
    let count = footer[6] as u64;
    if footer[5] != 24 || footer[7] != 32 || count > (size - 32) / 24 {
        bail!("Unsupported CGA archive");
    }
    let offset = size - 32 - count * 24;
    f.seek(SeekFrom::Start(offset))?;
    let mut table = vec![0u8; (count * 24) as usize];
    f.read_exact(&mut table)?;
    let table = cga_decode(&table, count * 24, offset, 0);
    let mut members = HashMap::new();
    for rec in table.chunks_exact(24) {
        let hashed = u64::from_le_bytes(rec[0..8].try_into().unwrap());
        let pos = u64::from_le_bytes(rec[8..16].try_into().unwrap());
        let length = u64::from_le_bytes(rec[16..24].try_into().unwrap());
        if pos + length > offset {
            bail!("CGA member extends beyond archive");
        }
        members.insert(hashed, Member { archive: path.clone(), offset: pos, size: length, version: 2, key: [0; 16] });
    }
    Ok((2, members))
}

pub fn archive_tracks(key: &str, title: &str, exe_path: &Path, game_dir: &Path) -> (Vec<GameTrack>, String) {
    let compact = key.replace('.', "");
    let mut errors: Vec<String> = Vec::new();
    let (paths, cga): (Vec<PathBuf>, bool) = if key == "th17.5" {
        (["game.exe", "data.cga", "data.cgb"].iter().map(|p| game_dir.join(p)).collect(), true)
    } else {
        let mut p: Vec<PathBuf> = ["", "b", "c"].iter().map(|s| game_dir.join(format!("{compact}{s}.pak"))).collect();
        if exe_path.file_stem().map_or(false, |s| s.to_string_lossy().contains("_beta")) {
            p.push(game_dir.join(format!("{compact}b_beta.pak")));
        }
        (p, false)
    };
    let mut archives: Vec<(u8, HashMap<u64, Member>)> = Vec::new();
    for path in paths {
        if !path.is_file() {
            continue;
        }
        let result = if cga { read_cga(&path) } else { read_tfpk(&path) };
        match result {
            Ok(a) => archives.push(a),
            Err(e) => {
                if path.extension().map_or(true, |x| x != "exe") {
                    errors.push(format!("{}: {e}", path.file_name().unwrap_or_default().to_string_lossy()));
                }
            }
        }
    }
    if archives.is_empty() {
        let msg = if errors.is_empty() { "No supported Twilight Frontier music archive was found.".into() } else { errors.join("; ") };
        return (Vec::new(), msg);
    }
    let lookup = |name: &str| -> Option<Member> {
        archives.iter().rev().find_map(|(version, members)| members.get(&name_hash(name, *version)).cloned())
    };
    let mut tracks = Vec::new();
    let Some(entries) = catalog().get(key) else { return (tracks, "No catalogue for this game.".into()) };
    for entry in entries {
        let name = &entry.file;
        let Some(member) = lookup(name) else { continue };
        let probe = (|| -> Result<(f64, u32, u16, f64, f64)> {
            let (duration, rate, channels) = ogg_info(&member)?;
            let (mut start, mut end) = (0.0, 0.0);
            if let Some(sfl) = lookup(&format!("{}.sfl", &name[..name.len().saturating_sub(4)])) {
                (start, end) = riff_loop(&sfl, rate);
            }
            if let Some(ini) = lookup(&format!("{name}.ini")) {
                let text = String::from_utf8_lossy(&ini.read_at(0, ini.size as usize)?).to_string();
                let re = regex::Regex::new(r"(?m)^\s*(repeatstart|repeatend)\s*=\s*(\d+)").unwrap();
                let mut values = HashMap::new();
                for c in re.captures_iter(&text) {
                    values.insert(c[1].to_string(), c[2].parse::<f64>().unwrap_or(0.0));
                }
                if let (Some(s), Some(e)) = (values.get("repeatstart"), values.get("repeatend")) {
                    start = s / rate as f64;
                    end = e / rate as f64;
                }
            }
            if !(0.0 <= start && start < end && end <= duration + 0.05) {
                start = 0.0;
                end = 0.0;
            }
            Ok((duration, rate, channels, start, end))
        })();
        match probe {
            Ok((duration, rate, channels, start, end)) => {
                let filename = Path::new(name).file_name().unwrap_or_default().to_string_lossy().to_string();
                tracks.push(GameTrack {
                    id: format!("{key}:{}", name.to_lowercase()),
                    game_key: key.to_string(),
                    game_title: title.to_string(),
                    filename,
                    title: entry.title.clone(),
                    title_en: String::new(),
                    title_ja: String::new(),
                    source: Source::Tasofro(member),
                    sample_rate: rate,
                    channels,
                    duration,
                    loop_start: start,
                    loop_end: end,
                });
            }
            Err(e) => errors.push(format!("{}: {e}", Path::new(name).file_name().unwrap_or_default().to_string_lossy())),
        }
    }
    (tracks, errors.join("; "))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fnv_variants() {
        assert_eq!(name_hash("a", 0), ((0x811c9dc5u32.wrapping_mul(0x1000193)) ^ 0x61) as u64);
        assert_eq!(name_hash("a", 2), ((0x811c9dc5u32 ^ 0x61).wrapping_mul(0x1000193)) as u64);
    }

    #[test]
    fn cga_roundtrip() {
        let data: Vec<u8> = (0..37u8).collect();
        let enc = cga_decode(&data, 1000, 77, 0);
        assert_eq!(cga_decode(&enc, 1000, 77, 0), data);
    }
}

#[cfg(test)]
mod parity {
    use super::*;

    #[test]
    fn matches_python() {
        let data: Vec<u8> = (0..37u8).collect();
        assert_eq!(hex::encode(cga_decode(&data, 1000, 77, 16)), "c868836442b565f1ccff4f8e4e30291bd09218b029dffa25a308d4da254aae4f97bfb0fc11");
        assert_eq!(name_hash("bgm/ST00.ogg", 0), 3261736049);
        assert_eq!(name_hash("データ/曲.ogg", 0), 2275254973);
        assert_eq!(name_hash("bgm/ST00.ogg", 1), 625184027);
        assert_eq!(name_hash("データ/曲.ogg", 1), 2037317823);
        assert_eq!(name_hash("bgm/ST00.ogg", 2), 1815449456);
        assert_eq!(name_hash("データ/曲.ogg", 2), 4131841020);
    }
}
