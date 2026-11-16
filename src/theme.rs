
use std::path::PathBuf;

use serde::{Deserialize, Serialize};

use crate::paths;

pub type Rgb = [f64; 3];

pub const DEFAULT_ACCENT: &str = "#d96bc8";

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ThemeSettings {
    #[serde(default = "default_mode")]
    pub mode: String,
    #[serde(default = "default_accent")]
    pub accent_color: String,
}

fn default_mode() -> String {
    "dark".into()
}
fn default_accent() -> String {
    DEFAULT_ACCENT.into()
}

impl Default for ThemeSettings {
    fn default() -> Self {
        ThemeSettings { mode: default_mode(), accent_color: default_accent() }
    }
}

fn settings_file() -> PathBuf {
    paths::config_dir().join("ui_settings.json")
}

impl ThemeSettings {
    pub fn load() -> Self {
        let mut s: ThemeSettings = crate::util::read_json(&settings_file()).unwrap_or_default();
        if s.mode != "dark" && s.mode != "light" {
            s.mode = "dark".into();
        }
        s.accent_color = normalize_hex(&s.accent_color).unwrap_or_else(default_accent);
        s
    }

    pub fn save(&self) {
        let _ = crate::util::write_json_atomic(&settings_file(), self);
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Palette {
    pub bg: Rgb,
    pub surface: Rgb,
    pub surface_alt: Rgb,
    pub surface_high: Rgb,
    pub popover: Rgb,
    pub fg: Rgb,
    pub fg_dim: Rgb,
    pub fg_disabled: Rgb,
    pub accent: Rgb,
    pub accent_hover: Rgb,
    pub on_accent: Rgb,
}

impl Palette {
    pub fn is_dark(&self) -> bool {
        luminance(self.bg) < 0.18
    }
}

pub fn normalize_hex(value: &str) -> Option<String> {
    let v = value.trim().trim_start_matches('#');
    let v = if v.len() == 3 { v.chars().flat_map(|c| [c, c]).collect::<String>() } else { v.to_string() };
    if v.len() == 6 && v.chars().all(|c| c.is_ascii_hexdigit()) {
        Some(format!("#{}", v.to_lowercase()))
    } else {
        None
    }
}

pub fn hex_rgb(value: &str) -> Rgb {
    let v = normalize_hex(value).unwrap_or_else(default_accent);
    let p = |i: usize| u8::from_str_radix(&v[1 + i..3 + i], 16).unwrap_or(0) as f64;
    [p(0), p(2), p(4)]
}

pub fn rgb_hex(rgb: Rgb) -> String {
    let c = |v: f64| v.round().clamp(0.0, 255.0) as u8;
    format!("#{:02x}{:02x}{:02x}", c(rgb[0]), c(rgb[1]), c(rgb[2]))
}

pub fn mix(a: Rgb, b: Rgb, amount: f64) -> Rgb {
    [a[0] + (b[0] - a[0]) * amount, a[1] + (b[1] - a[1]) * amount, a[2] + (b[2] - a[2]) * amount]
}

pub fn luminance(rgb: Rgb) -> f64 {
    let lin = |c: f64| {
        let c = c / 255.0;
        if c <= 0.04045 { c / 12.92 } else { ((c + 0.055) / 1.055).powf(2.4) }
    };
    0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2])
}

fn on_accent_for(accent: Rgb) -> Rgb {
    let lum = luminance(accent);
    let dark_text = hex_rgb("#1a1a1a");
    let contrast_dark = (lum + 0.05) / (luminance(dark_text) + 0.05);
    let contrast_white = 1.05 / (lum + 0.05);
    if contrast_dark >= contrast_white { dark_text } else { [255.0; 3] }
}

pub fn manual_palette(mode: &str, accent_hex: &str) -> Palette {
    let accent = hex_rgb(accent_hex);
    let dark = mode != "light";
    let base = |d: &str, l: &str| hex_rgb(if dark { d } else { l });
    let tint = |dt: f64, lt: f64| if dark { dt } else { lt };
    let t = |b: Rgb, amount: f64| mix(b, accent, amount);
    Palette {
        bg: t(base("#0e0e0e", "#f4f4f4"), tint(0.05, 0.05)),
        surface: t(base("#171717", "#fcfcfc"), tint(0.07, 0.07)),
        surface_alt: t(base("#1f1f1f", "#ebebeb"), tint(0.09, 0.09)),
        surface_high: t(base("#292929", "#e0e0e0"), tint(0.12, 0.13)),
        popover: t(base("#2e2e2e", "#fcfcfc"), tint(0.12, 0.07)),
        fg: t(base("#f4f4f4", "#1c1c1c"), tint(0.05, 0.06)),
        fg_dim: t(base("#bdbdbd", "#5c5c5c"), tint(0.06, 0.06)),
        fg_disabled: t(base("#808080", "#9a9a9a"), tint(0.05, 0.05)),
        accent,
        accent_hover: mix(accent, [0.0; 3], if dark { 0.12 } else { 0.18 }),
        on_accent: on_accent_for(accent),
    }
}


pub fn rgb_to_hls(r: f64, g: f64, b: f64) -> (f64, f64, f64) {
    let maxc = r.max(g).max(b);
    let minc = r.min(g).min(b);
    let sumc = maxc + minc;
    let rangec = maxc - minc;
    let l = sumc / 2.0;
    if minc == maxc {
        return (0.0, l, 0.0);
    }
    let s = if l <= 0.5 { rangec / sumc } else { rangec / (2.0 - maxc - minc) };
    let rc = (maxc - r) / rangec;
    let gc = (maxc - g) / rangec;
    let bc = (maxc - b) / rangec;
    let h = if r == maxc {
        bc - gc
    } else if g == maxc {
        2.0 + rc - bc
    } else {
        4.0 + gc - rc
    };
    ((h / 6.0).rem_euclid(1.0), l, s)
}

pub fn hls_to_rgb(h: f64, l: f64, s: f64) -> (f64, f64, f64) {
    if s == 0.0 {
        return (l, l, l);
    }
    let m2 = if l <= 0.5 { l * (1.0 + s) } else { l + s - l * s };
    let m1 = 2.0 * l - m2;
    let v = |hue: f64| {
        let hue = hue.rem_euclid(1.0);
        if hue < 1.0 / 6.0 {
            m1 + (m2 - m1) * hue * 6.0
        } else if hue < 0.5 {
            m2
        } else if hue < 2.0 / 3.0 {
            m1 + (m2 - m1) * (2.0 / 3.0 - hue) * 6.0
        } else {
            m1
        }
    };
    (v(h + 1.0 / 3.0), v(h), v(h - 1.0 / 3.0))
}

fn hls(h: f64, s: f64, l: f64) -> Rgb {
    let (r, g, b) = hls_to_rgb(h.rem_euclid(1.0), l.clamp(0.0, 1.0), s.clamp(0.0, 1.0));
    [(r * 255.0).round(), (g * 255.0).round(), (b * 255.0).round()]
}

fn contrast(a: Rgb, b: Rgb) -> f64 {
    let (la, lb) = (luminance(a), luminance(b));
    let (hi, lo) = if la > lb { (la, lb) } else { (lb, la) };
    (hi + 0.05) / (lo + 0.05)
}

#[derive(Clone, Debug, PartialEq)]
pub struct MusicPalette {
    pub primary: Rgb,
    pub on_primary: Rgb,
    pub primary_container: Rgb,
    pub on_primary_container: Rgb,
    pub secondary_container: Rgb,
    pub surface: Rgb,
    pub surface_container: Rgb,
    pub surface_high: Rgb,
    pub text: Rgb,
    pub text_dim: Rgb,
    pub track: Rgb,
}

pub fn music_palette(rgb: Rgb, dark: bool) -> MusicPalette {
    let (h, _l, s) = rgb_to_hls(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0);
    let a = if s < 0.12 { 0.10 } else { s.clamp(0.38, 0.85) };
    if !dark {
        let on_primary = hls(h, a * 0.3, 0.98);
        let mut lightness: f64 = 0.38;
        while lightness > 0.2 && contrast(on_primary, hls(h, a, lightness)) < 4.5 {
            lightness -= 0.02;
        }
        return MusicPalette {
            primary: hls(h, a, lightness),
            on_primary,
            primary_container: hls(h, a * 0.85, 0.86),
            on_primary_container: hls(h, a, 0.17),
            secondary_container: hls(h, a * 0.60, 0.89),
            surface: hls(h, a * 0.60, 0.955),
            surface_container: hls(h, a * 0.55, 0.925),
            surface_high: hls(h, a * 0.55, 0.895),
            text: hls(h, a * 0.45, 0.11),
            text_dim: hls(h, a * 0.25, 0.36),
            track: hls(h, a * 0.40, 0.77),
        };
    }
    MusicPalette {
        primary: hls(h, a, 0.77),
        on_primary: hls(h, a * 0.7, 0.13),
        primary_container: hls(h, a * 0.55, 0.30),
        on_primary_container: hls(h, a, 0.90),
        secondary_container: hls(h, a * 0.38, 0.27),
        surface: hls(h, a * 0.45, 0.095),
        surface_container: hls(h, a * 0.42, 0.150),
        surface_high: hls(h, a * 0.40, 0.210),
        text: hls(h, a * 0.20, 0.94),
        text_dim: hls(h, a * 0.16, 0.72),
        track: hls(h, a * 0.30, 0.31),
    }
}

pub fn music_palette_from_hue(hue: f64, dark: bool) -> MusicPalette {
    let (r, g, b) = hls_to_rgb(hue.rem_euclid(1.0), 0.55, 0.6);
    music_palette([(r * 255.0).round(), (g * 255.0).round(), (b * 255.0).round()], dark)
}

pub fn dominant_rgb(pixels: &[u8], channels: usize) -> Rgb {
    const BINS: usize = 12;
    let mut weight = [0.0f64; BINS];
    let mut sums = [[0.0f64; 3]; BINS];
    let (mut tr, mut tg, mut tb, mut count) = (0.0, 0.0, 0.0, 0usize);
    for px in pixels.chunks_exact(channels) {
        let (r, g, b) = (px[0] as f64, px[1] as f64, px[2] as f64);
        tr += r;
        tg += g;
        tb += b;
        count += 1;
        let (h, l, s) = rgb_to_hls(r / 255.0, g / 255.0, b / 255.0);
        let w = (s * s + 0.02) * (1.0 - (2.0 * l - 1.0).abs()).max(0.04).powf(1.5);
        let k = ((h * BINS as f64) as usize).min(BINS - 1);
        weight[k] += w;
        sums[k][0] += r * w;
        sums[k][1] += g * w;
        sums[k][2] += b * w;
    }
    if count == 0 {
        return [110.0, 110.0, 140.0];
    }
    let best = (0..BINS).max_by(|&a, &b| weight[a].partial_cmp(&weight[b]).unwrap()).unwrap();
    if weight[best] <= 0.0 {
        return [(tr / count as f64).round(), (tg / count as f64).round(), (tb / count as f64).round()];
    }
    let w = weight[best];
    [(sums[best][0] / w).round(), (sums[best][1] / w).round(), (sums[best][2] / w).round()]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hls_roundtrip() {
        let (h, l, s) = rgb_to_hls(0.2, 0.4, 0.9);
        let (r, g, b) = hls_to_rgb(h, l, s);
        assert!((r - 0.2).abs() < 1e-9 && (g - 0.4).abs() < 1e-9 && (b - 0.9).abs() < 1e-9);
    }

    #[test]
    fn manual_dark_matches_python() {
        let p = manual_palette("dark", "#d96bc8");
        assert_eq!(rgb_hex(p.bg), "#181317");
        assert_eq!(rgb_hex(p.on_accent), "#1a1a1a");
    }
}

#[cfg(test)]
mod parity {
    use super::*;

    fn join(p: &MusicPalette) -> String {
        [p.primary, p.on_primary, p.primary_container, p.on_primary_container, p.secondary_container, p.surface,
         p.surface_container, p.surface_high, p.text, p.text_dim, p.track]
            .iter()
            .map(|c| rgb_hex(*c))
            .collect::<Vec<_>>()
            .join(",")
    }

    #[test]
    fn music_palette_matches_python() {
        assert_eq!(join(&music_palette([200.0, 80.0, 120.0], true)), "#e3a6ba,#2d151d,#623745,#f3d8e1,#533740,#1e1316,#2f1e23,#412a32,#f1eeef,#beb2b6,#5b434b");
        assert_eq!(join(&music_palette([200.0, 80.0, 120.0], false)), "#932e50,#fbf9fa,#ebcbd6,#421524,#ecdae0,#f7f0f2,#f1e6ea,#ecdde2,#23151a,#685058,#d1b8c0");
        assert_eq!(join(&music_palette_from_hue(0.86, true)), "#e8a1dc,#2f132b,#66335e,#f5d6f0,#553550,#1f121d,#301d2d,#42293e,#f2eef1,#beb1bc,#5d4159");
    }
}
