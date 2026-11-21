
use std::collections::HashMap;
use std::sync::OnceLock;

use serde::Deserialize;

use super::GameTrack;

#[derive(Deserialize)]
struct Names {
    en: String,
    ja: String,
    #[serde(default)]
    suffix_en: String,
    #[serde(default)]
    suffix_ja: String,
}

fn titles() -> &'static HashMap<String, HashMap<String, Names>> {
    static T: OnceLock<HashMap<String, HashMap<String, Names>>> = OnceLock::new();
    T.get_or_init(|| {
        let path = crate::paths::assets_dir().join("catalogs/bgm_titles.json");
        std::fs::read_to_string(path).ok().and_then(|t| serde_json::from_str(&t).ok()).unwrap_or_default()
    })
}

pub fn apply_titles(track: &mut GameTrack) {
    let filename = track.filename.replace('\\', "/").to_lowercase();
    let base = filename.rsplit('/').next().unwrap_or(&filename).to_string();
    let game = titles().get(&track.game_key);
    let names = game.and_then(|g| g.get(&filename).or_else(|| g.get(&base)));
    if let Some(n) = names {
        track.title_en = format!("{}{}", n.en, n.suffix_en);
        track.title_ja = format!("{}{}", n.ja, n.suffix_ja);
    } else {
        let stem = std::path::Path::new(&filename).file_stem().map(|s| s.to_string_lossy().to_string()).unwrap_or_default();
        track.title_en = format!("Track {stem}");
        track.title_ja = if track.title.is_empty() { format!("トラック {stem}") } else { track.title.clone() };
    }
    track.title = track.title_en.clone();
}

fn prefs_file() -> std::path::PathBuf {
    crate::paths::config_dir().join("music_prefs.json")
}

pub fn load_title_language() -> String {
    let prefs: serde_json::Map<String, serde_json::Value> = crate::util::read_json(&prefs_file()).unwrap_or_default();
    match prefs.get("title_language").and_then(|v| v.as_str()) {
        Some("ja") => "ja".into(),
        _ => "en".into(),
    }
}

pub fn load_volume() -> f64 {
    let prefs: serde_json::Map<String, serde_json::Value> = crate::util::read_json(&prefs_file()).unwrap_or_default();
    prefs.get("volume").and_then(|v| v.as_f64()).filter(|v| v.is_finite()).map_or(0.8, |v| v.clamp(0.0, 1.0))
}

pub fn save_volume(volume: f64) -> std::io::Result<()> {
    let mut prefs: serde_json::Map<String, serde_json::Value> = crate::util::read_json(&prefs_file()).unwrap_or_default();
    prefs.insert("volume".into(), volume.into());
    crate::util::write_json_atomic(&prefs_file(), &prefs)
}

pub fn save_title_language(language: &str) -> std::io::Result<()> {
    let mut prefs: serde_json::Map<String, serde_json::Value> = crate::util::read_json(&prefs_file()).unwrap_or_default();
    prefs.insert("title_language".into(), language.into());
    crate::util::write_json_atomic(&prefs_file(), &prefs)
}
