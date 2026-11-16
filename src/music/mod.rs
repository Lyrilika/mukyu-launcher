pub mod bgm;
pub mod engine;
pub mod hdi;
pub mod metadata;
pub mod pc98;
pub mod radio;
pub mod tasofro;
pub mod titles;

use std::path::PathBuf;

#[derive(Clone, Debug)]
pub enum Source {
    Pcm { path: PathBuf, offset: u64, length: u64, channels: u16, bits: u16 },
    File(PathBuf),
    Tasofro(tasofro::Member),
    Pc98 { path: PathBuf, mdt: bool, rhythm: PathBuf },
}

#[derive(Clone, Debug)]
pub struct GameTrack {
    pub id: String,
    pub game_key: String,
    pub game_title: String,
    pub filename: String,
    pub title: String,
    pub title_en: String,
    pub title_ja: String,
    pub source: Source,
    pub sample_rate: u32,
    #[allow(dead_code)]
    pub channels: u16,
    pub duration: f64,
    pub loop_start: f64,
    pub loop_end: f64,
}

impl GameTrack {
    pub fn display_title(&self, language: &str) -> String {
        let t = if language == "ja" { &self.title_ja } else { &self.title_en };
        if t.is_empty() { self.title.clone() } else { t.clone() }
    }

    pub fn loop_region(&self) -> Option<(f64, f64)> {
        if 0.0 <= self.loop_start && self.loop_start < self.loop_end && self.loop_end <= self.duration + 0.05 {
            Some((self.loop_start, self.loop_end.min(self.duration)))
        } else {
            None
        }
    }
}
