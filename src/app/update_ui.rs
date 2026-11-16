use std::cell::RefCell;
use std::path::PathBuf;
use std::rc::Rc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use slint::ComponentHandle;

use super::{after, ctx, post, Ctx};
use crate::update::{self, Applied, Method, Release};
use crate::util::fmt_size;
use crate::{ChangelogApi, UpdateApi};

#[derive(Default)]
struct UpdateState {
    release: Option<Release>,
    method: Option<Method>,
    cancel: Option<Arc<AtomicBool>>,
    installed: Option<PathBuf>,
    saved: Option<(PathBuf, String)>,
    waiting: Option<Release>,
    notes_page: Option<String>,
}

thread_local! {
    static STATE: RefCell<UpdateState> = RefCell::new(UpdateState::default());
}

const STATE_AVAILABLE: i32 = 0;
const STATE_DOWNLOADING: i32 = 1;
const STATE_READY: i32 = 2;
const STATE_FAILED: i32 = 3;
const STATE_SAVED: i32 = 4;

fn method_code(m: Method) -> i32 {
    match m {
        Method::ReplaceAppImage => 0,
        Method::WindowsInstaller => 1,
        Method::SaveInstaller => 2,
        Method::OpenPage => 3,
    }
}

pub fn setup(c: &Rc<Ctx>) {
    let api = c.app.global::<UpdateApi>();
    api.set_current(update::current_version().into());
    api.on_update(|| start(&ctx()));
    api.on_ignore(|| {
        let c = ctx();
        if let Some(r) = STATE.with(|s| s.borrow().release.clone()) {
            update::ignore_version(&r.version);
        }
        c.app.global::<UpdateApi>().set_open(false);
    });
    api.on_close(|| close(&ctx()));
    api.on_cancel(|| {
        let c = ctx();
        cancel_download();
        c.app.global::<UpdateApi>().set_state(STATE_AVAILABLE);
    });
    api.on_restart(|| restart(&ctx()));
    api.on_open_installer(|| {
        if let Some((path, sha256)) = STATE.with(|s| s.borrow().saved.clone()) {
            if let Err(e) = update::open_installer(&path, &sha256) {
                let c = ctx();
                let api = c.app.global::<UpdateApi>();
                api.set_message(format!("{e:#}").into());
                api.set_state(STATE_FAILED);
            }
        }
    });
    api.on_set_auto(|on| set_auto_update(&ctx(), on));
    api.on_view_changelog(|| {
        if let Some(r) = STATE.with(|s| s.borrow().release.clone()) {
            let _ = open::that_detached(&r.page_url);
        }
    });

    let prefs = update::prefs();
    let settings = c.app.global::<crate::SettingsApi>();
    settings.set_auto_update(prefs.auto_check);
    api.set_auto_check(prefs.auto_check);
    settings.on_set_auto_update(|on| set_auto_update(&ctx(), on));
    settings.set_show_changelog(prefs.show_changelog);
    settings.on_set_show_changelog(|on| set_show_changelog(&ctx(), on));
    settings.on_check_updates(|| check_manually(&ctx()));

    let changelog = c.app.global::<ChangelogApi>();
    changelog.set_show_again(prefs.show_changelog);
    changelog.on_set_show(|on| set_show_changelog(&ctx(), on));
    changelog.on_close(|| close_changelog(&ctx()));
    changelog.on_open_page(|| {
        let url = STATE.with(|s| s.borrow().notes_page.clone())
            .unwrap_or_else(|| format!("https://github.com/{}/releases/tag/v{}", update::REPO, update::current_version()));
        let _ = open::that_detached(url);
    });

    if let Some(previous) = update::take_update_record() {
        if prefs.show_changelog {
            show_changelog(c, previous);
        }
    }

    if std::env::var_os("MUKYU_NO_UPDATE_CHECK").is_some() {
        return;
    }
    after(2500, || {
        std::thread::Builder::new()
            .name("update-check".into())
            .spawn(|| {
                if let Ok(Some(release)) = update::check() {
                    post(move |c| offer(c, release));
                }
            })
            .ok();
    });
}

const CHECK_IDLE: i32 = 0;
const CHECK_BUSY: i32 = 1;
const CHECK_CURRENT: i32 = 2;
const CHECK_ERROR: i32 = 3;
const CHECK_FOUND: i32 = 4;

fn check_manually(c: &Rc<Ctx>) {
    let settings = c.app.global::<crate::SettingsApi>();
    if settings.get_update_check() == CHECK_BUSY {
        return;
    }
    settings.set_update_check(CHECK_BUSY);
    let started = std::time::Instant::now();
    std::thread::Builder::new()
        .name("update-check-manual".into())
        .spawn(move || {
            let result = update::check_now();
            let wait = 700u64.saturating_sub(started.elapsed().as_millis() as u64);
            post(move |_| after(wait, move || manual_result(&ctx(), result)));
        })
        .ok();
}

fn manual_result(c: &Rc<Ctx>, result: anyhow::Result<Option<Release>>) {
    let settings = c.app.global::<crate::SettingsApi>();
    match result {
        Ok(Some(release)) => {
            settings.set_update_check_text(format!("Mukyu Launcher {} is available", release.version).into());
            settings.set_update_check(CHECK_FOUND);
            let api = c.app.global::<UpdateApi>();
            let same = STATE.with(|s| s.borrow().release.as_ref().is_some_and(|r| r.version == release.version));
            if same && api.get_state() != STATE_AVAILABLE && api.get_state() != STATE_FAILED {
                api.set_open(true);
            } else {
                offer(c, release);
            }
        }
        Ok(None) => {
            settings.set_update_check_text("You're up to date".into());
            settings.set_update_check(CHECK_CURRENT);
        }
        Err(_) => {
            settings.set_update_check_text("Couldn't check for updates. Check your connection and try again.".into());
            settings.set_update_check(CHECK_ERROR);
        }
    }
}

pub fn reset_manual_check(c: &Ctx) {
    let settings = c.app.global::<crate::SettingsApi>();
    if settings.get_update_check() != CHECK_BUSY {
        settings.set_update_check(CHECK_IDLE);
    }
}

fn set_auto_update(c: &Rc<Ctx>, on: bool) {
    update::set_auto_check(on);
    c.app.global::<crate::SettingsApi>().set_auto_update(on);
    c.app.global::<UpdateApi>().set_auto_check(on);
}

fn set_show_changelog(c: &Rc<Ctx>, on: bool) {
    update::set_show_changelog(on);
    c.app.global::<crate::SettingsApi>().set_show_changelog(on);
    c.app.global::<ChangelogApi>().set_show_again(on);
}

fn show_changelog(c: &Rc<Ctx>, previous: String) {
    let version = update::current_version().to_string();
    let api = c.app.global::<ChangelogApi>();
    api.set_version(version.clone().into());
    api.set_previous(previous.into());
    api.set_notes("".into());
    api.set_loading(true);
    api.set_open(true);
    std::thread::Builder::new()
        .name("release-notes".into())
        .spawn(move || {
            let notes = update::release_notes(&version);
            post(move |c| {
                let api = c.app.global::<ChangelogApi>();
                api.set_loading(false);
                match notes {
                    Ok(n) => {
                        api.set_notes(n.text.into());
                        STATE.with(|s| s.borrow_mut().notes_page = Some(n.page_url));
                    }
                    Err(_) => api.set_notes("The release notes could not be loaded. Use View on GitHub to read them.".into()),
                }
            });
        })
        .ok();
}

fn close_changelog(c: &Rc<Ctx>) {
    c.app.global::<ChangelogApi>().set_open(false);
    if let Some(release) = STATE.with(|s| s.borrow_mut().waiting.take()) {
        after(250, move || show(&ctx(), release));
    }
}

fn offer(c: &Rc<Ctx>, release: Release) {
    if c.app.global::<ChangelogApi>().get_open() {
        STATE.with(|s| s.borrow_mut().waiting = Some(release));
    } else {
        show(c, release);
    }
}

pub fn is_open(c: &Ctx) -> bool {
    c.app.global::<UpdateApi>().get_open() || c.app.global::<ChangelogApi>().get_open()
}

fn show(c: &Rc<Ctx>, release: Release) {
    let method = update::method(&release);
    let api = c.app.global::<UpdateApi>();
    api.set_latest(release.version.clone().into());
    api.set_method(method_code(method));
    api.set_state(STATE_AVAILABLE);
    api.set_fraction(0.0);
    api.set_message("".into());
    STATE.with(|s| {
        let mut s = s.borrow_mut();
        s.release = Some(release);
        s.method = Some(method);
    });
    api.set_open(true);
}

fn cancel_download() {
    if let Some(flag) = STATE.with(|s| s.borrow_mut().cancel.take()) {
        flag.store(true, Ordering::Relaxed);
    }
}

pub fn close(c: &Rc<Ctx>) {
    if c.app.global::<ChangelogApi>().get_open() && !c.app.global::<UpdateApi>().get_open() {
        close_changelog(c);
        return;
    }
    cancel_download();
    let api = c.app.global::<UpdateApi>();
    if api.get_state() == STATE_DOWNLOADING {
        api.set_state(STATE_AVAILABLE);
    }
    api.set_open(false);
}

fn start(c: &Rc<Ctx>) {
    let (release, method) = STATE.with(|s| {
        let s = s.borrow();
        (s.release.clone(), s.method)
    });
    let (Some(release), Some(method)) = (release, method) else { return };
    match method {
        Method::OpenPage => {
            let _ = open::that_detached(&release.page_url);
            c.app.global::<UpdateApi>().set_open(false);
        }
        Method::SaveInstaller => pick_folder_then_download(release),
        _ => begin_download(c, release, method, None),
    }
}

#[cfg(windows)]
fn pick_folder_then_download(release: Release) {
    std::thread::spawn(move || {
        let folder = rfd::FileDialog::new().set_title("Choose where to save the Mukyu Launcher installer").pick_folder();
        post(move |c| {
            if let Some(folder) = folder {
                begin_download(c, release, Method::SaveInstaller, Some(folder));
            }
        });
    });
}

#[cfg(not(windows))]
fn pick_folder_then_download(release: Release) {
    let _ = open::that_detached(&release.page_url);
}

fn begin_download(c: &Rc<Ctx>, release: Release, method: Method, folder: Option<PathBuf>) {
    cancel_download();
    let cancel = Arc::new(AtomicBool::new(false));
    STATE.with(|s| s.borrow_mut().cancel = Some(cancel.clone()));
    let api = c.app.global::<UpdateApi>();
    api.set_state(STATE_DOWNLOADING);
    api.set_fraction(0.0);
    api.set_progress_text("Starting download…".into());
    std::thread::Builder::new()
        .name("update-download".into())
        .spawn(move || {
            let progress_cancel = cancel.clone();
            let result = update::apply(&release, method, folder.as_deref(), &cancel, &move |p| {
                if progress_cancel.load(Ordering::Relaxed) {
                    return;
                }
                post(move |c| {
                    let api = c.app.global::<UpdateApi>();
                    if api.get_state() != STATE_DOWNLOADING {
                        return;
                    }
                    if p.total > 0 {
                        api.set_fraction((p.done as f64 / p.total as f64).min(1.0) as f32);
                        api.set_progress_text(
                            format!("{} of {}  ({}%)", fmt_size(Some(p.done)), fmt_size(Some(p.total)), p.done * 100 / p.total).into(),
                        );
                    } else {
                        api.set_progress_text(format!("{} downloaded", fmt_size(Some(p.done))).into());
                    }
                });
            });
            let cancelled = cancel.load(Ordering::Relaxed);
            post(move |c| finished(c, &release, result, cancelled));
        })
        .ok();
}

fn finished(c: &Rc<Ctx>, release: &Release, result: anyhow::Result<Applied>, cancelled: bool) {
    STATE.with(|s| s.borrow_mut().cancel = None);
    let api = c.app.global::<UpdateApi>();
    if cancelled {
        return;
    }
    if result.is_ok() {
        update::mark_updated(&release.version);
    }
    match result {
        Ok(Applied::Replaced(path)) => {
            STATE.with(|s| s.borrow_mut().installed = Some(path));
            api.set_message(
                format!("Mukyu Launcher {} is installed. It will be used the next time you open the launcher.", release.version).into(),
            );
            api.set_state(STATE_READY);
        }
        Ok(Applied::InstallerStaged(path)) => {
            update::set_pending_installer(path, release.asset_sha256.clone().unwrap_or_default());
            api.set_message(
                format!("Mukyu Launcher {} is downloaded. It will be installed when you close the launcher.", release.version).into(),
            );
            api.set_state(STATE_READY);
        }
        Ok(Applied::InstallerSaved(path)) => {
            api.set_message(
                format!(
                    "The installer was saved to {}. Run it to update; it installs over your current version.",
                    update::short_path(&path)
                )
                .into(),
            );
            STATE.with(|s| s.borrow_mut().saved = Some((path, release.asset_sha256.clone().unwrap_or_default())));
            api.set_state(STATE_SAVED);
        }
        Err(e) => {
            api.set_message(format!("{e:#}").into());
            api.set_state(STATE_FAILED);
        }
    }
    api.set_open(true);
}

fn restart(c: &Rc<Ctx>) {
    let installed = STATE.with(|s| s.borrow().installed.clone());
    if let Some(path) = installed {
        if let Err(e) = update::relaunch_appimage(&path) {
            let api = c.app.global::<UpdateApi>();
            api.set_message(format!("{e:#}").into());
            api.set_state(STATE_FAILED);
            return;
        }
        super::quit(c);
        return;
    }
    if update::has_pending_installer() {
        update::run_pending_installer(true);
        super::quit(c);
    }
}
