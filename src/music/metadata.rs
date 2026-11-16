
use anyhow::{bail, Result};

pub trait RandomRead {
    fn size(&self) -> u64;
    fn read_at(&self, start: u64, len: usize) -> Result<Vec<u8>>;
}

pub struct FileRead {
    pub path: std::path::PathBuf,
    size: u64,
}

impl FileRead {
    pub fn open(path: &std::path::Path) -> Result<Self> {
        Ok(FileRead { path: path.to_path_buf(), size: std::fs::metadata(path)?.len() })
    }
}

impl RandomRead for FileRead {
    fn size(&self) -> u64 {
        self.size
    }
    fn read_at(&self, start: u64, len: usize) -> Result<Vec<u8>> {
        use std::io::{Read, Seek, SeekFrom};
        let mut f = std::fs::File::open(&self.path)?;
        f.seek(SeekFrom::Start(start))?;
        let mut buf = Vec::with_capacity(len);
        f.take(len as u64).read_to_end(&mut buf)?;
        Ok(buf)
    }
}

fn find_last(hay: &[u8], needle: &[u8], end: usize) -> Option<usize> {
    let end = end.min(hay.len());
    if end < needle.len() {
        return None;
    }
    (0..=end - needle.len()).rev().find(|&i| &hay[i..i + needle.len()] == needle)
}

pub fn ogg_info(src: &dyn RandomRead) -> Result<(f64, u32, u16)> {
    let size = src.size();
    let header = src.read_at(0, size.min(4096) as usize)?;
    if header.len() < 28 || &header[..5] != b"OggS\0" {
        bail!("Invalid Ogg header");
    }
    let serial = header[14..18].to_vec();
    let start = 27 + header[26] as usize;
    if header.len() < start + 30 || &header[start..start + 7] != b"\x01vorbis" {
        bail!("Expected Vorbis identification packet");
    }
    let channels = header[start + 11] as u16;
    let rate = u32::from_le_bytes(header[start + 12..start + 16].try_into().unwrap());
    if rate == 0 || channels == 0 {
        bail!("Invalid Vorbis audio format");
    }
    let tail_len = size.min(131072);
    let tail = src.read_at(size - tail_len, tail_len as usize)?;
    let mut pos = tail.len();
    loop {
        let Some(p) = find_last(&tail, b"OggS\0", pos) else { bail!("Missing final Ogg page") };
        pos = p;
        if p + 27 > tail.len() || tail[p + 14..p + 18] != serial[..] || tail[p + 5] & 4 == 0 {
            continue;
        }
        let segments = tail[p + 26] as usize;
        let end_header = p + 27 + segments;
        if end_header > tail.len() {
            continue;
        }
        let end = end_header + tail[p + 27..end_header].iter().map(|&b| b as usize).sum::<usize>();
        if end != tail.len() {
            continue;
        }
        let samples = i64::from_le_bytes(tail[p + 6..p + 14].try_into().unwrap());
        if samples <= 0 {
            bail!("Invalid Ogg sample count");
        }
        return Ok((samples as f64 / rate as f64, rate, channels));
    }
}

pub fn riff_loop(src: &dyn RandomRead, rate: u32) -> (f64, f64) {
    riff_loop_inner(src, rate).unwrap_or((0.0, 0.0))
}

fn riff_loop_inner(src: &dyn RandomRead, rate: u32) -> Result<(f64, f64)> {
    let size = src.size();
    if src.read_at(0, 4)? != b"RIFF" {
        return Ok((0.0, 0.0));
    }
    let mut cues: Vec<(u32, u32)> = Vec::new();
    let mut lengths = std::collections::HashMap::new();
    let mut pos: u64 = 12;
    while pos + 8 <= size {
        let header = src.read_at(pos, 8)?;
        if header.len() != 8 {
            break;
        }
        let tag = &header[..4];
        let length = u32::from_le_bytes(header[4..8].try_into().unwrap()) as u64;
        if pos + 8 + length > size {
            break;
        }
        if tag == b"cue " && (4..=65536).contains(&length) {
            let chunk = src.read_at(pos + 8, length as usize)?;
            let count = u32::from_le_bytes(chunk[..4].try_into().unwrap()) as usize;
            for i in 0..count.min((length as usize - 4) / 24) {
                let o = 4 + i * 24;
                let ident = u32::from_le_bytes(chunk[o..o + 4].try_into().unwrap());
                let sample = u32::from_le_bytes(chunk[o + 20..o + 24].try_into().unwrap());
                cues.push((ident, sample));
            }
        } else if tag == b"LIST" && length <= 65536 {
            let chunk = src.read_at(pos + 8, length as usize)?;
            if chunk.len() >= 4 && &chunk[..4] == b"adtl" {
                let mut p = 4;
                while p + 8 <= chunk.len() {
                    let kind = &chunk[p..p + 4];
                    let n = u32::from_le_bytes(chunk[p + 4..p + 8].try_into().unwrap()) as usize;
                    if p + 8 + n > chunk.len() {
                        break;
                    }
                    if kind == b"ltxt" && n >= 8 {
                        let ident = u32::from_le_bytes(chunk[p + 8..p + 12].try_into().unwrap());
                        let samples = u32::from_le_bytes(chunk[p + 12..p + 16].try_into().unwrap());
                        lengths.insert(ident, samples);
                    }
                    p += 8 + n + n % 2;
                }
            }
        }
        pos += 8 + length + length % 2;
    }
    for (ident, start) in cues {
        if let Some(&len) = lengths.get(&ident) {
            if len > 0 {
                return Ok((start as f64 / rate as f64, (start as f64 + len as f64) / rate as f64));
            }
        }
    }
    Ok((0.0, 0.0))
}

pub fn wav_info(src: &dyn RandomRead) -> Result<(u16, u32, u16, u64, u64)> {
    let size = src.size();
    let head = src.read_at(0, 12)?;
    if head.len() < 12 || &head[..4] != b"RIFF" || &head[8..12] != b"WAVE" {
        bail!("Not a WAV file");
    }
    let mut pos = 12u64;
    let mut fmt = None;
    while pos + 8 <= size {
        let h = src.read_at(pos, 8)?;
        let len = u32::from_le_bytes(h[4..8].try_into().unwrap()) as u64;
        if &h[..4] == b"fmt " {
            let c = src.read_at(pos + 8, len.min(64) as usize)?;
            if c.len() >= 16 {
                let tag = u16::from_le_bytes([c[0], c[1]]);
                let ch = u16::from_le_bytes([c[2], c[3]]);
                let rate = u32::from_le_bytes(c[4..8].try_into().unwrap());
                let bits = u16::from_le_bytes([c[14], c[15]]);
                if tag != 1 && tag != 0xFFFE {
                    bail!("Unsupported WAV encoding");
                }
                fmt = Some((ch, rate, bits));
            }
        } else if &h[..4] == b"data" {
            let (ch, rate, bits) = fmt.ok_or_else(|| anyhow::anyhow!("WAV data before format"))?;
            let len = len.min(size - pos - 8);
            return Ok((ch, rate, bits, pos + 8, len));
        }
        pos += 8 + len + len % 2;
    }
    bail!("WAV file has no audio data")
}
