
use std::path::Path;

use anyhow::{anyhow, bail, Result};

#[derive(Clone, Debug)]
pub struct HdiEntry {
    pub path: String,
    pub is_dir: bool,
    pub size: u32,
    pub first_cluster: u16,
}

pub struct HdiFilesystem {
    data: Vec<u8>,
    header_size: usize,
    data_size: usize,
    physical_bps: usize,
    spt: usize,
    heads: usize,
    volume_bps: usize,
    spc: usize,
    fat_offset: usize,
    root_offset: usize,
    root_sectors: usize,
    data_offset: usize,
    volume_end: usize,
    fat16: bool,
    entries: Vec<HdiEntry>,
}

const PHYS: [usize; 6] = [128, 256, 512, 1024, 2048, 4096];
const FAT_MEDIA: [u8; 9] = [0xF0, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF];

fn u16le(b: &[u8], o: usize) -> u16 {
    u16::from_le_bytes([b[o], b[o + 1]])
}
fn u32le(b: &[u8], o: usize) -> u32 {
    u32::from_le_bytes(b[o..o + 4].try_into().unwrap())
}

struct Bpb {
    bps: usize,
    spc: usize,
    reserved: usize,
    fats: usize,
    root_entries: usize,
    spf: usize,
    total: usize,
}

fn parse_bpb(boot: &[u8]) -> Option<Bpb> {
    if boot.len() < 0x24 {
        return None;
    }
    let total16 = u16le(boot, 0x13) as usize;
    let total32 = u32le(boot, 0x20) as usize;
    Some(Bpb {
        bps: u16le(boot, 0x0B) as usize,
        spc: boot[0x0D] as usize,
        reserved: u16le(boot, 0x0E) as usize,
        fats: boot[0x10] as usize,
        root_entries: u16le(boot, 0x11) as usize,
        spf: u16le(boot, 0x16) as usize,
        total: if total16 != 0 { total16 } else { total32 },
    })
}

fn bpb_sane(f: &Bpb, available: usize) -> bool {
    if !PHYS.contains(&f.bps) {
        return false;
    }
    if f.spc == 0 || f.spc > 128 || f.spc & (f.spc - 1) != 0 {
        return false;
    }
    if f.reserved == 0 || f.reserved > 128 || f.fats == 0 || f.fats > 4 {
        return false;
    }
    if f.root_entries == 0 || f.root_entries > 4096 || f.spf == 0 || f.spf > 512 || f.total == 0 {
        return false;
    }
    let root_sectors = (f.root_entries * 32 + f.bps - 1) / f.bps;
    let first_data = f.reserved + f.fats * f.spf + root_sectors;
    if first_data >= f.total {
        return false;
    }
    let volume = f.total * f.bps;
    volume <= available && volume >= first_data * f.bps
}

fn valid_entry(entry: &[u8]) -> Option<bool> {
    let first = entry[0];
    if first == 0 {
        return None;
    }
    if first == 0xE5 {
        return Some(false);
    }
    let attr = entry[11];
    if attr == 0x0F || attr & 0x08 != 0 {
        return Some(false);
    }
    if first < 0x20 && first != 0x05 {
        return Some(false);
    }
    Some(true)
}

impl HdiFilesystem {
    pub fn open(path: &Path) -> Result<Self> {
        let data = std::fs::read(path)?;
        if data.len() < 0x20 {
            bail!("HDI image is too small");
        }
        let header_size = u32le(&data, 8) as usize;
        let data_size = u32le(&data, 12) as usize;
        let bps = u32le(&data, 16) as usize;
        let spt = u32le(&data, 20) as usize;
        let heads = u32le(&data, 24) as usize;
        let cylinders = u32le(&data, 28) as usize;
        if header_size < 0x20 || header_size > data.len() {
            bail!("Invalid HDI header size");
        }
        if data_size == 0 || header_size + data_size > data.len() {
            bail!("Invalid HDI data size");
        }
        if !PHYS.contains(&bps) {
            bail!("Unsupported HDI physical sector size");
        }
        if !(spt > 0 && spt <= 255 && heads > 0 && heads <= 255 && cylinders > 0 && cylinders <= 0xFFFF) {
            bail!("Invalid HDI geometry");
        }
        let mut fs = HdiFilesystem {
            data,
            header_size,
            data_size,
            physical_bps: bps,
            spt,
            heads,
            volume_bps: 0,
            spc: 0,
            fat_offset: 0,
            root_offset: 0,
            root_sectors: 0,
            data_offset: 0,
            volume_end: 0,
            fat16: false,
            entries: Vec::new(),
        };
        fs.parse_fat()?;
        fs.entries = fs.walk();
        Ok(fs)
    }

    fn disk_end(&self) -> usize {
        self.header_size + self.data_size
    }

    fn partition_offsets(&self) -> Vec<usize> {
        let mut result = Vec::new();
        let bps = self.physical_bps;
        if self.data_size < bps * 2 {
            return result;
        }
        let len = 512.max(bps).min(self.data_size - bps);
        let start = self.header_size + bps;
        let table = &self.data[start..start + len];
        let total_sectors = self.data_size / bps;
        for index in 0..16.min(table.len() / 32) {
            let e = &table[index * 32..index * 32 + 32];
            if e.iter().all(|&b| b == 0) {
                continue;
            }
            let (sh, ss, sc) = (e[8] as usize, e[9] as usize, u16le(e, 10) as usize);
            let (eh, es, ec) = (e[12] as usize, e[13] as usize, u16le(e, 14) as usize);
            if sh >= self.heads || eh >= self.heads || ss >= self.spt || es >= self.spt || ec < sc {
                continue;
            }
            let start_lba = sc * self.heads * self.spt + sh * self.spt + ss;
            let end_lba = ec * self.heads * self.spt + eh * self.spt + es;
            if start_lba >= total_sectors || end_lba < start_lba {
                continue;
            }
            result.push(start_lba * bps);
        }
        result
    }

    fn candidates(&self) -> Vec<usize> {
        let mut out: Vec<usize> = Vec::new();
        let mut add = |offset: usize| {
            let abs = self.header_size + offset;
            if abs < self.disk_end() && !out.contains(&abs) {
                out.push(abs);
            }
        };
        add(0);
        for o in self.partition_offsets() {
            add(o);
        }
        let cyl1 = self.spt * self.heads * self.physical_bps;
        if cyl1 > 0 && cyl1 < self.data_size {
            add(cyl1);
        }
        for marker in [&b"FAT12"[..], &b"FAT16"[..]] {
            let region = &self.data[self.header_size..self.disk_end()];
            let mut from = 0;
            while let Some(pos) = region[from..].windows(5).position(|w| w == marker) {
                let p = from + pos;
                if p >= 0x36 {
                    add(p - 0x36);
                }
                from = p + 1;
            }
        }
        out
    }

    fn parse_fat(&mut self) -> Result<()> {
        type Score = (i64, i64, i64, i64, i64, i64);
        let mut best: Option<(Score, usize, Bpb)> = None;
        for abs in self.candidates() {
            let available = self.disk_end() - abs;
            if available < 512 {
                continue;
            }
            let boot = &self.data[abs..abs + available.min(4096)];
            let Some(f) = parse_bpb(boot) else { continue };
            if !bpb_sane(&f, available) {
                continue;
            }
            let root_sectors = (f.root_entries * 32 + f.bps - 1) / f.bps;
            let fat_offset = abs + f.reserved * f.bps;
            let root_offset = fat_offset + f.fats * f.spf * f.bps;
            let data_offset = root_offset + root_sectors * f.bps;
            let volume_end = abs + f.total * f.bps;
            if !(fat_offset < root_offset && root_offset < data_offset && data_offset <= volume_end && volume_end <= self.disk_end()) {
                continue;
            }
            let media = if FAT_MEDIA.contains(&self.data[fat_offset]) { 2 } else { 0 };
            let root_raw = &self.data[root_offset..root_offset + root_sectors * f.bps];
            let mut root_score = 0;
            for entry in root_raw.chunks_exact(32) {
                match valid_entry(entry) {
                    None => break,
                    Some(false) => continue,
                    Some(true) => {
                        if entry[..8].iter().any(|&b| b != b' ') {
                            root_score += 1;
                        }
                    }
                }
            }
            let marker = if boot.len() >= 0x3B && (&boot[0x36..0x3B] == b"FAT12" || &boot[0x36..0x3B] == b"FAT16") { 3 } else { 0 };
            let sig = if boot.len() >= 512 && boot[0x1FE] == 0x55 && boot[0x1FF] == 0xAA { 1 } else { 0 };
            let score: Score = (0, root_score, media, marker, sig, -(abs as i64));
            if best.as_ref().map_or(true, |b| score > b.0) {
                best = Some((score, abs, f));
            }
        }
        let (_, abs, f) = best.ok_or_else(|| anyhow!("No readable FAT12/FAT16 filesystem found inside the PC-98 HDI image"))?;
        self.volume_bps = f.bps;
        self.spc = f.spc;
        self.fat_offset = abs + f.reserved * f.bps;
        self.root_sectors = (f.root_entries * 32 + f.bps - 1) / f.bps;
        self.root_offset = self.fat_offset + f.fats * f.spf * f.bps;
        self.data_offset = self.root_offset + self.root_sectors * f.bps;
        self.volume_end = abs + f.total * f.bps;
        let clusters = (self.volume_end - self.data_offset) / (self.spc * self.volume_bps);
        if clusters < 4085 {
            self.fat16 = false;
        } else if clusters < 65525 {
            self.fat16 = true;
        } else {
            bail!("PC-98 FAT volume is FAT32-sized; Touhou PC-98 media should be FAT12/FAT16");
        }
        Ok(())
    }

    fn fat_entry(&self, cluster: usize) -> usize {
        if self.fat16 {
            let pos = self.fat_offset + cluster * 2;
            if pos + 2 > self.root_offset {
                return 0xFFFF;
            }
            return u16le(&self.data, pos) as usize;
        }
        let pos = self.fat_offset + cluster * 3 / 2;
        if pos + 2 > self.root_offset {
            return 0xFFF;
        }
        let v = u16le(&self.data, pos) as usize;
        if cluster & 1 == 1 { v >> 4 } else { v & 0x0FFF }
    }

    fn cluster_size(&self) -> usize {
        self.spc * self.volume_bps
    }

    fn chain(&self, first: u16) -> Vec<usize> {
        let mut out = Vec::new();
        if first < 2 {
            return out;
        }
        let max = ((self.volume_end - self.data_offset) / self.cluster_size()).max(1);
        let mut seen = std::collections::HashSet::new();
        let mut cur = first as usize;
        while (2..0xFFF8).contains(&cur) && seen.insert(cur) && out.len() < max {
            out.push(cur);
            let next = self.fat_entry(cur);
            if (!self.fat16 && next >= 0xFF8) || (self.fat16 && next >= 0xFFF8) {
                break;
            }
            if next <= 1 || next == 0xFF7 {
                break;
            }
            cur = next;
        }
        out
    }

    fn cluster_bytes(&self, cluster: usize) -> &[u8] {
        let pos = self.data_offset + (cluster - 2) * self.cluster_size();
        let end = (pos + self.cluster_size()).min(self.data.len());
        if pos >= end {
            &[]
        } else {
            &self.data[pos..end]
        }
    }

    fn dir_entries(raw: &[u8], prefix: &str) -> Vec<HdiEntry> {
        let mut out = Vec::new();
        for entry in raw.chunks_exact(32) {
            match valid_entry(entry) {
                None => break,
                Some(false) => continue,
                Some(true) => {}
            }
            let mut base_raw = entry[..8].to_vec();
            if base_raw[0] == 0x05 {
                base_raw[0] = 0xE5;
            }
            let decode = |b: &[u8]| {
                let end = b.iter().rposition(|&c| c != b' ').map_or(0, |p| p + 1);
                crate::util::decode_cp932(&b[..end])
            };
            let base = decode(&base_raw);
            let ext = decode(&entry[8..11]);
            if base.is_empty() || base == "." || base == ".." {
                continue;
            }
            let name = if ext.is_empty() { base } else { format!("{base}.{ext}") };
            let path = if prefix.is_empty() { name } else { format!("{prefix}/{name}") };
            out.push(HdiEntry { path, is_dir: entry[11] & 0x10 != 0, size: u32le(entry, 28), first_cluster: u16le(entry, 26) });
        }
        out
    }

    fn walk(&self) -> Vec<HdiEntry> {
        let mut result = Vec::new();
        let root = &self.data[self.root_offset..self.root_offset + self.root_sectors * self.volume_bps];
        let mut queue: std::collections::VecDeque<HdiEntry> = Self::dir_entries(root, "").into();
        while let Some(entry) = queue.pop_front() {
            if entry.is_dir && result.len() < 100_000 {
                let raw: Vec<u8> = self.chain(entry.first_cluster).into_iter().flat_map(|c| self.cluster_bytes(c).to_vec()).collect();
                queue.extend(Self::dir_entries(&raw, &entry.path));
            }
            result.push(entry);
        }
        result
    }

    pub fn entries(&self) -> &[HdiEntry] {
        &self.entries
    }

    pub fn read_file(&self, path: &str) -> Result<Vec<u8>> {
        let target = path.replace('\\', "/").trim_start_matches('/').to_lowercase();
        let entry = self
            .entries
            .iter()
            .find(|e| e.path.to_lowercase() == target && !e.is_dir)
            .ok_or_else(|| anyhow!("{path} not found"))?;
        let mut out = Vec::with_capacity(entry.size as usize);
        let mut remaining = entry.size as usize;
        for c in self.chain(entry.first_cluster) {
            let chunk = self.cluster_bytes(c);
            if chunk.is_empty() {
                break;
            }
            let take = remaining.min(chunk.len());
            out.extend_from_slice(&chunk[..take]);
            remaining -= take;
            if remaining == 0 {
                break;
            }
        }
        if remaining > 0 {
            bail!("Unexpected end of file while reading {path}");
        }
        Ok(out)
    }
}
