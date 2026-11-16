
use std::collections::VecDeque;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Condvar, Mutex};

use pdfium_render::prelude::*;

const MAX_BOX_W: u32 = 3840;
const MAX_BOX_H: u32 = 2400;

pub struct RenderedPage {
    pub width: u32,
    pub height: u32,
    pub rgb: Vec<u8>,
}

pub enum PdfEvent {
    Opened(usize),
    Rendered { index: usize, bbox: (u32, u32), page: Option<RenderedPage> },
    Error(String),
}

#[derive(Default)]
struct WorkerState {
    wanted: VecDeque<usize>,
    bbox: (u32, u32),
    stop: bool,
}

pub struct PdfWorker {
    state: Arc<(Mutex<WorkerState>, Condvar)>,
}

fn library_candidates() -> Vec<PathBuf> {
    let mut dirs: Vec<PathBuf> = Vec::new();
    if let Ok(p) = std::env::var("MUKYU_PDFIUM") {
        let p = PathBuf::from(p);
        dirs.push(if p.is_file() { p.parent().map(Path::to_path_buf).unwrap_or_default() } else { p });
    }
    if let Some(exe_dir) = std::env::current_exe().ok().and_then(|e| e.parent().map(Path::to_path_buf)) {
        dirs.push(exe_dir.join("lib"));
        dirs.push(exe_dir.clone());
        dirs.push(exe_dir.join("../lib"));
    }
    let root = crate::paths::root_dir();
    dirs.push(root.join("lib"));
    dirs.push(root.join("tools").join("pdfium"));
    dirs
}

pub fn bind() -> Result<Pdfium, String> {
    for dir in library_candidates() {
        let lib = Pdfium::pdfium_platform_library_name_at_path(&dir);
        if lib.is_file() {
            if let Ok(b) = Pdfium::bind_to_library(&lib) {
                return Ok(Pdfium::new(b));
            }
        }
    }
    Pdfium::bind_to_system_library().map(Pdfium::new).map_err(|_| {
        "The built-in reader needs the PDFium library (libpdfium), which could not be found. Reinstall Mukyu Launcher, or install PDFium on your system.".to_string()
    })
}

fn describe_open_error(e: &PdfiumError) -> String {
    let text = format!("{e:?}").to_lowercase();
    if text.contains("password") {
        "This PDF is password protected.".into()
    } else if text.contains("format") || text.contains("file") || text.contains("data") {
        "The file is damaged or is not a valid PDF. Try deleting it and downloading it again.".into()
    } else {
        format!("The PDF could not be opened ({e:?}).")
    }
}

impl PdfWorker {
    pub fn spawn(path: PathBuf, on_event: impl Fn(PdfEvent) + Send + 'static) -> PdfWorker {
        let state: Arc<(Mutex<WorkerState>, Condvar)> = Arc::default();
        let shared = state.clone();
        std::thread::Builder::new()
            .name("pdf-worker".into())
            .spawn(move || {
                if !path.is_file() {
                    return on_event(PdfEvent::Error("The file could not be found. It may have been deleted.".into()));
                }
                let pdfium = match bind() {
                    Ok(p) => p,
                    Err(e) => return on_event(PdfEvent::Error(e)),
                };
                let doc = match pdfium.load_pdf_from_file(&path, None) {
                    Ok(d) => d,
                    Err(e) => return on_event(PdfEvent::Error(describe_open_error(&e))),
                };
                let count = doc.pages().len() as usize;
                if count < 1 {
                    return on_event(PdfEvent::Error("This PDF has no pages.".into()));
                }
                on_event(PdfEvent::Opened(count));
                loop {
                    let (index, bbox) = {
                        let (lock, cv) = &*shared;
                        let mut s = lock.lock().unwrap();
                        while !s.stop && s.wanted.is_empty() {
                            s = cv.wait(s).unwrap();
                        }
                        if s.stop {
                            break;
                        }
                        (s.wanted.pop_front().unwrap(), s.bbox)
                    };
                    let page = render(&doc, index, bbox);
                    if shared.0.lock().unwrap().stop {
                        break;
                    }
                    on_event(PdfEvent::Rendered { index, bbox, page });
                }
            })
            .expect("spawn pdf worker");
        PdfWorker { state }
    }

    pub fn request(&self, indices: Vec<usize>, bbox: (u32, u32)) {
        let (lock, cv) = &*self.state;
        let mut s = lock.lock().unwrap();
        s.wanted = indices.into();
        s.bbox = bbox;
        cv.notify_all();
    }

    pub fn stop(&self) {
        let (lock, cv) = &*self.state;
        let mut s = lock.lock().unwrap();
        s.stop = true;
        s.wanted.clear();
        cv.notify_all();
    }
}

fn render(doc: &PdfDocument, index: usize, bbox: (u32, u32)) -> Option<RenderedPage> {
    let bw = bbox.0.clamp(1, MAX_BOX_W) as f32;
    let bh = bbox.1.clamp(1, MAX_BOX_H) as f32;
    let page = doc.pages().get(index as PdfPageIndex).ok()?;
    let (w, h) = (page.width().value, page.height().value);
    if w <= 0.0 || h <= 0.0 {
        return None;
    }
    let scale = (bw / w).min(bh / h).clamp(0.05, 10.0);
    let config = PdfRenderConfig::new().scale_page_by_factor(scale);
    let bitmap = page.render_with_config(&config).ok()?;
    let image = bitmap.as_image().to_rgb8();
    Some(RenderedPage { width: image.width(), height: image.height(), rgb: image.into_raw() })
}
