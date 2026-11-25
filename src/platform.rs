
use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::process::{Child, Command};

pub const EGL_PICK_MARK: &str = "MUKYU_EGL_PICKED";

pub fn host_env() -> HashMap<String, String> {
    let mut env = host_env_unfiltered();
    if let Some(pick) = env.remove(EGL_PICK_MARK) {
        if pick == "mesa-pci" {
            env.remove("DRI_PRIME");
        }
        env.remove("__EGL_VENDOR_LIBRARY_FILENAMES");
    }
    env
}

fn host_env_unfiltered() -> HashMap<String, String> {
    let mut env: HashMap<String, String> = std::env::vars().collect();
    if std::env::var_os("TL_APPIMAGE").is_none() {
        return env;
    }
    let keys: Vec<String> = env.keys().filter(|k| k.starts_with("TL_ORIG_")).cloned().collect();
    for key in keys {
        let name = key["TL_ORIG_".len()..].to_string();
        let value = env.remove(&key).unwrap_or_default();
        if value == "__TL_UNSET__" {
            env.remove(&name);
        } else {
            env.insert(name, value);
        }
    }
    env.remove("TL_APPIMAGE");
    env
}

pub fn host_env_var(name: &str) -> Option<String> {
    if std::env::var_os("TL_APPIMAGE").is_some() {
        if let Ok(orig) = std::env::var(format!("TL_ORIG_{name}")) {
            return if orig == "__TL_UNSET__" { None } else { Some(orig) };
        }
    }
    std::env::var(name).ok()
}

pub fn no_window(cmd: &mut Command) -> &mut Command {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x0800_0000);
    }
    cmd
}

pub fn split_launch_options(text: &str) -> Vec<String> {
    let mut parts = Vec::new();
    let mut current = String::new();
    let mut quote: Option<char> = None;
    let mut has = false;
    for ch in text.chars() {
        match quote {
            Some(q) if ch == q => {
                quote = None;
                current.push(ch);
            }
            Some(_) => current.push(ch),
            None if ch == '"' || ch == '\'' => {
                quote = Some(ch);
                current.push(ch);
                has = true;
            }
            None if ch.is_whitespace() => {
                if has {
                    parts.push(std::mem::take(&mut current));
                    has = false;
                }
            }
            None => {
                current.push(ch);
                has = true;
            }
        }
    }
    if has {
        parts.push(current);
    }
    parts
        .into_iter()
        .map(|p| {
            let b = p.as_bytes();
            if b.len() >= 2 && b[0] == b[b.len() - 1] && (b[0] == b'"' || b[0] == b'\'') {
                p[1..p.len() - 1].to_string()
            } else {
                p
            }
        })
        .collect()
}

pub fn shell_split(text: &str) -> Vec<String> {
    if text.trim().is_empty() {
        return Vec::new();
    }
    shlex::split(text).unwrap_or_else(|| text.split_whitespace().map(String::from).collect())
}

pub fn shell_join(args: &[String]) -> String {
    args.iter()
        .map(|a| shlex::try_quote(a).map(|c| c.into_owned()).unwrap_or_else(|_| a.clone()))
        .collect::<Vec<_>>()
        .join(" ")
}

pub const SESSION_ENV_VAR: &str = "MUKYU_LAUNCHER_SESSION";

#[cfg_attr(not(target_os = "linux"), allow(dead_code))]
const WINE_SYSTEM_EXES: &[&str] = &[
    "services.exe", "winedevice.exe", "plugplay.exe", "svchost.exe", "explorer.exe",
    "rpcss.exe", "conhost.exe", "start.exe", "winemenubuilder.exe", "wineboot.exe",
    "rundll32.exe", "mscorsvw.exe", "tabtip.exe", "steam.exe", "iexplore.exe",
    "winedbg.exe", "cmd.exe",
];

#[cfg(target_os = "linux")]
mod procfs {
    use super::*;

    fn stat_fields(pid: u32) -> Option<Vec<String>> {
        let data = std::fs::read_to_string(format!("/proc/{pid}/stat")).ok()?;
        let closing = data.rfind(')')?;
        Some(data.get(closing + 2..)?.split_whitespace().map(String::from).collect())
    }

    pub fn exists(pid: u32) -> bool {
        match std::fs::read_to_string(format!("/proc/{pid}/stat")) {
            Ok(data) => match data.rfind(')') {
                None => true,
                Some(c) => data.get(c + 2..).and_then(|s| s.split_whitespace().next()).map_or(true, |s| s != "Z"),
            },
            Err(_) => false,
        }
    }

    pub fn children(pid: u32) -> Vec<u32> {
        std::fs::read_to_string(format!("/proc/{pid}/task/{pid}/children"))
            .map(|s| s.split_whitespace().filter_map(|v| v.parse().ok()).collect())
            .unwrap_or_default()
    }

    pub fn tree(root: u32, known: &HashSet<u32>) -> HashSet<u32> {
        let mut pids = known.clone();
        if exists(root) {
            pids.insert(root);
            let mut pending = vec![root];
            let mut seen = HashSet::new();
            while let Some(pid) = pending.pop() {
                if !seen.insert(pid) || !exists(pid) {
                    continue;
                }
                for child in children(pid) {
                    pids.insert(child);
                    if !seen.contains(&child) {
                        pending.push(child);
                    }
                }
            }
        }
        pids
    }

    fn all_pids() -> Vec<u32> {
        std::fs::read_dir("/proc")
            .map(|it| it.flatten().filter_map(|e| e.file_name().to_str()?.parse().ok()).collect())
            .unwrap_or_default()
    }

    pub fn group_alive(pgid: u32) -> bool {
        all_pids().into_iter().any(|pid| {
            stat_fields(pid).map_or(false, |f| f.len() >= 3 && f[0] != "Z" && f[2].parse::<u32>().ok() == Some(pgid))
        })
    }

    pub fn session_pids(token: &str) -> Vec<u32> {
        let marker = format!("{SESSION_ENV_VAR}={token}");
        let own = std::process::id();
        all_pids()
            .into_iter()
            .filter(|&pid| pid != own)
            .filter(|&pid| {
                std::fs::read(format!("/proc/{pid}/environ"))
                    .map(|env| env.split(|&b| b == 0).any(|e| e == marker.as_bytes()))
                    .unwrap_or(false)
                    && exists(pid)
            })
            .collect()
    }

    pub fn windows_exe_name(pid: u32) -> Option<String> {
        let raw = std::fs::read(format!("/proc/{pid}/cmdline")).ok()?;
        for arg in raw.split(|&b| b == 0).take(2) {
            let text = String::from_utf8_lossy(arg);
            let base = text.trim().rsplit(['\\', '/']).next().unwrap_or("").to_lowercase();
            if base.ends_with(".exe") {
                return Some(base);
            }
        }
        None
    }

    pub fn session_game_alive(token: &str) -> bool {
        session_pids(token)
            .into_iter()
            .any(|pid| windows_exe_name(pid).map_or(false, |exe| !WINE_SYSTEM_EXES.contains(&exe.as_str())))
    }
}

#[cfg(windows)]
mod job {
    use std::os::windows::io::AsRawHandle;
    use windows::Win32::Foundation::{CloseHandle, BOOL, HANDLE, HWND, LPARAM, WPARAM};
    use windows::Win32::System::JobObjects::*;
    use windows::Win32::UI::WindowsAndMessaging::{EnumWindows, GetWindowThreadProcessId, PostMessageW, WM_CLOSE};

    pub struct Job(HANDLE);
    unsafe impl Send for Job {}

    #[repr(C)]
    struct PidList {
        assigned: u32,
        in_list: u32,
        ids: [usize; 256],
    }

    impl Job {
        pub fn new(child: &std::process::Child) -> Option<Job> {
            unsafe {
                let handle = CreateJobObjectW(None, None).ok()?;
                let process = HANDLE(child.as_raw_handle() as _);
                if AssignProcessToJobObject(handle, process).is_err() {
                    let _ = CloseHandle(handle);
                    return None;
                }
                Some(Job(handle))
            }
        }

        pub fn active_count(&self) -> Option<u32> {
            unsafe {
                let mut info = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION::default();
                QueryInformationJobObject(
                    self.0,
                    JobObjectBasicAccountingInformation,
                    &mut info as *mut _ as *mut _,
                    std::mem::size_of_val(&info) as u32,
                    None,
                )
                .ok()?;
                Some(info.ActiveProcesses)
            }
        }

        pub fn pids(&self) -> Vec<u32> {
            unsafe {
                let mut list = PidList { assigned: 0, in_list: 0, ids: [0; 256] };
                if QueryInformationJobObject(
                    self.0,
                    JobObjectBasicProcessIdList,
                    &mut list as *mut _ as *mut _,
                    std::mem::size_of::<PidList>() as u32,
                    None,
                )
                .is_err()
                {
                    return Vec::new();
                }
                list.ids[..(list.in_list as usize).min(256)].iter().map(|&p| p as u32).collect()
            }
        }

        pub fn request_close(&self) {
            let pids = self.pids();
            if pids.is_empty() {
                return;
            }
            unsafe extern "system" fn on_window(hwnd: HWND, lparam: LPARAM) -> BOOL {
                let pids = &*(lparam.0 as *const Vec<u32>);
                let mut owner = 0u32;
                GetWindowThreadProcessId(hwnd, Some(&mut owner));
                if pids.contains(&owner) {
                    let _ = PostMessageW(hwnd, WM_CLOSE, WPARAM(0), LPARAM(0));
                }
                BOOL(1)
            }
            unsafe {
                let _ = EnumWindows(Some(on_window), LPARAM(&pids as *const Vec<u32> as isize));
            }
        }

        pub fn terminate(&self) {
            unsafe {
                let _ = TerminateJobObject(self.0, 1);
            }
        }
    }

    impl Drop for Job {
        fn drop(&mut self) {
            unsafe {
                let _ = CloseHandle(self.0);
            }
        }
    }
}

pub struct GameProcess {
    pub child: Child,
    #[cfg_attr(not(target_os = "linux"), allow(dead_code))]
    pub session: String,
    #[allow(dead_code)]
    tree: HashSet<u32>,
    pub stopping: bool,
    pub exit_status: Option<i32>,
    #[cfg(windows)]
    job: Option<job::Job>,
    watch: Option<ExeWatch>,
}

struct ExeWatch {
    dir: PathBuf,
    #[cfg_attr(not(target_os = "linux"), allow(dead_code))]
    app_id: u32,
    started: std::time::Instant,
    seen: bool,
    cancelling: bool,
}

const STEAM_START_GRACE: std::time::Duration = std::time::Duration::from_secs(90);

static STEAM_LAUNCH_GEN: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);

fn end_steam_game(dir: &Path, app_id: u32, force: bool) -> bool {
    #[cfg(target_os = "linux")]
    let launchers = steam_launch_pids(app_id);
    #[cfg(not(target_os = "linux"))]
    let launchers: Vec<u32> = {
        let _ = app_id;
        Vec::new()
    };
    #[cfg(target_os = "linux")]
    for &pid in &launchers {
        unsafe {
            libc::kill(pid as i32, libc::SIGTERM);
        }
    }
    let game = pids_running_from(dir);
    end_pids(&game, force);
    !launchers.is_empty() || !game.is_empty()
}

fn cancel_pending_steam_launch(dir: PathBuf, app_id: u32, deadline: std::time::Instant) {
    let gen = STEAM_LAUNCH_GEN.load(std::sync::atomic::Ordering::Relaxed);
    let _ = std::thread::Builder::new().name("steam-cancel".into()).spawn(move || {
        let mut found_before = false;
        while std::time::Instant::now() < deadline {
            std::thread::sleep(std::time::Duration::from_millis(500));
            if STEAM_LAUNCH_GEN.load(std::sync::atomic::Ordering::Relaxed) != gen {
                return;
            }
            found_before = end_steam_game(&dir, app_id, found_before);
        }
    });
}

#[cfg_attr(not(target_os = "linux"), allow(dead_code))]
fn path_in_dir(candidate: &str, dir: &Path) -> bool {
    let unix = match candidate.as_bytes() {
        [d, b':', b'\\', ..] if d.eq_ignore_ascii_case(&b'z') => candidate[2..].replace('\\', "/"),
        [b'/', ..] => candidate.to_string(),
        _ => return false,
    };
    if !unix.to_ascii_lowercase().ends_with(".exe") {
        return false;
    }
    let path = Path::new(&unix);
    if std::fs::canonicalize(path).is_ok_and(|real| real.starts_with(dir)) {
        return true;
    }
    let prefix = format!("{}/", dir.to_string_lossy().trim_end_matches('/')).to_ascii_lowercase();
    unix.to_ascii_lowercase().starts_with(&prefix)
}

pub fn pids_running_from(dir: &Path) -> Vec<u32> {
    let mut found = Vec::new();
    #[cfg(target_os = "linux")]
    {
        let dir = std::fs::canonicalize(dir).unwrap_or_else(|_| dir.to_path_buf());
        let me = std::process::id();
        if let Ok(entries) = std::fs::read_dir("/proc") {
            for entry in entries.flatten() {
                let Some(pid) = entry.file_name().to_str().and_then(|s| s.parse::<u32>().ok()) else { continue };
                if pid == me || !procfs::exists(pid) {
                    continue;
                }
                let Ok(raw) = std::fs::read(entry.path().join("cmdline")) else { continue };
                if raw.split(|&b| b == 0).any(|arg| path_in_dir(&String::from_utf8_lossy(arg), &dir)) {
                    found.push(pid);
                }
            }
        }
    }
    #[cfg(windows)]
    unsafe {
        use windows::core::PWSTR;
        use windows::Win32::System::Diagnostics::ToolHelp::{CreateToolhelp32Snapshot, Process32FirstW, Process32NextW, PROCESSENTRY32W, TH32CS_SNAPPROCESS};
        use windows::Win32::System::Threading::{OpenProcess, QueryFullProcessImageNameW, PROCESS_NAME_WIN32, PROCESS_QUERY_LIMITED_INFORMATION};
        let prefix = format!("{}\\", dir.to_string_lossy().replace('/', "\\").trim_end_matches('\\')).to_lowercase();
        if let Ok(snap) = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0) {
            let mut entry = PROCESSENTRY32W { dwSize: std::mem::size_of::<PROCESSENTRY32W>() as u32, ..Default::default() };
            let mut ok = Process32FirstW(snap, &mut entry).is_ok();
            while ok {
                let pid = entry.th32ProcessID;
                if let Ok(h) = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid) {
                    let mut buf = [0u16; 1024];
                    let mut len = buf.len() as u32;
                    if QueryFullProcessImageNameW(h, PROCESS_NAME_WIN32, PWSTR(buf.as_mut_ptr()), &mut len).is_ok() {
                        let path = String::from_utf16_lossy(&buf[..len as usize]).to_lowercase();
                        if path.starts_with(&prefix) && path.ends_with(".exe") {
                            found.push(pid);
                        }
                    }
                    let _ = windows::Win32::Foundation::CloseHandle(h);
                }
                ok = Process32NextW(snap, &mut entry).is_ok();
            }
            let _ = windows::Win32::Foundation::CloseHandle(snap);
        }
    }
    #[cfg(not(any(target_os = "linux", windows)))]
    let _ = dir;
    found
}

#[cfg(target_os = "linux")]
fn steam_launch_pids(app_id: u32) -> Vec<u32> {
    let tag = format!("AppId={app_id}");
    let mut found = Vec::new();
    if let Ok(entries) = std::fs::read_dir("/proc") {
        for entry in entries.flatten() {
            let Some(pid) = entry.file_name().to_str().and_then(|s| s.parse::<u32>().ok()) else { continue };
            let Ok(raw) = std::fs::read(entry.path().join("cmdline")) else { continue };
            let text = String::from_utf8_lossy(&raw);
            let tagged = text.match_indices(&tag).any(|(i, m)| !text[i + m.len()..].starts_with(|c: char| c.is_ascii_digit()));
            if tagged {
                found.push(pid);
            }
        }
    }
    found
}

fn end_pids(pids: &[u32], force: bool) {
    #[cfg(unix)]
    {
        let sig = if force { libc::SIGKILL } else { libc::SIGTERM };
        for &pid in pids {
            unsafe {
                libc::kill(pid as i32, sig);
            }
        }
    }
    #[cfg(windows)]
    {
        if !force {
            if pids.is_empty() {
                return;
            }
            let mut cmd = Command::new("taskkill");
            for pid in pids {
                cmd.arg("/PID").arg(pid.to_string());
            }
            no_window(&mut cmd);
            let _ = cmd.status();
            return;
        }
        use windows::Win32::System::Threading::{OpenProcess, TerminateProcess, PROCESS_TERMINATE};
        for &pid in pids {
            unsafe {
                if let Ok(h) = OpenProcess(PROCESS_TERMINATE, false, pid) {
                    let _ = TerminateProcess(h, 1);
                    let _ = windows::Win32::Foundation::CloseHandle(h);
                }
            }
        }
    }
}

impl GameProcess {
    pub fn new(child: Child, session: String) -> Self {
        let pid = child.id();
        #[cfg(windows)]
        let job = job::Job::new(&child);
        GameProcess {
            child,
            session,
            tree: HashSet::from([pid]),
            stopping: false,
            exit_status: None,
            #[cfg(windows)]
            job,
            watch: None,
        }
    }

    pub fn watching(mut self, game_dir: PathBuf, app_id: u32) -> Self {
        STEAM_LAUNCH_GEN.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        self.watch = Some(ExeWatch { dir: game_dir, app_id, started: std::time::Instant::now(), seen: false, cancelling: false });
        self
    }

    fn poll_child(&mut self) -> bool {
        match self.child.try_wait() {
            Ok(None) => true,
            Ok(Some(status)) => {
                if self.exit_status.is_none() {
                    self.exit_status = Some(status.code().unwrap_or(-1));
                }
                false
            }
            Err(_) => false,
        }
    }

    pub fn alive(&mut self) -> bool {
        if let Some(w) = self.watch.as_mut() {
            let _ = self.child.try_wait();
            if !pids_running_from(&w.dir).is_empty() {
                w.seen = true;
                return true;
            }
            return !w.seen && !self.stopping && w.started.elapsed() < STEAM_START_GRACE;
        }
        let child_alive = self.poll_child();
        #[cfg(windows)]
        {
            if let Some(count) = self.job.as_ref().and_then(|j| j.active_count()) {
                return count > 0;
            }
            return child_alive;
        }
        #[cfg(target_os = "linux")]
        {
            if child_alive {
                return true;
            }
            let pid = self.child.id();
            if procfs::group_alive(pid) {
                return true;
            }
            let known: HashSet<u32> = self.tree.iter().copied().filter(|&p| procfs::exists(p)).collect();
            let mut tree = procfs::tree(pid, &known);
            tree.remove(&pid);
            self.tree = tree.clone();
            if tree.iter().any(|&p| procfs::exists(p)) {
                return true;
            }
            return procfs::session_game_alive(&self.session);
        }
        #[allow(unreachable_code)]
        child_alive
    }

    pub fn snapshot_tree(&mut self) {
        if self.watch.is_some() {
            return;
        }
        #[cfg(target_os = "linux")]
        {
            self.tree = procfs::tree(self.child.id(), &self.tree);
        }
    }

    pub fn signal(&mut self, force: bool) {
        self.stopping = true;
        if let Some(w) = self.watch.as_mut() {
            end_steam_game(&w.dir, w.app_id, force);
            if !w.seen && !w.cancelling {
                w.cancelling = true;
                cancel_pending_steam_launch(w.dir.clone(), w.app_id, w.started + STEAM_START_GRACE);
            }
            return;
        }
        #[cfg(windows)]
        {
            if !force {
                match &self.job {
                    Some(job) => job.request_close(),
                    None => {
                        let _ = self.child.kill();
                    }
                }
            } else {
                if let Some(job) = &self.job {
                    job.terminate();
                }
                let _ = self.child.kill();
            }
        }
        #[cfg(unix)]
        {
            let sig = if force { libc::SIGKILL } else { libc::SIGTERM };
            let pid = self.child.id() as i32;
            unsafe {
                if libc::killpg(pid, sig) != 0 && std::io::Error::last_os_error().raw_os_error() == Some(libc::EPERM) {
                    libc::kill(pid, sig);
                }
            }
            #[cfg(target_os = "linux")]
            for p in procfs::session_pids(&self.session) {
                unsafe {
                    libc::kill(p as i32, sig);
                }
            }
            if force {
                for &p in &self.tree {
                    unsafe {
                        libc::kill(p as i32, libc::SIGKILL);
                    }
                }
            }
        }
    }
}

pub fn detach(cmd: &mut Command) -> &mut Command {
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        unsafe {
            cmd.pre_exec(|| {
                libc::setsid();
                Ok(())
            });
        }
    }
    cmd
}

pub fn trim_memory() {
    #[cfg(all(target_os = "linux", target_env = "gnu"))]
    unsafe {
        libc::malloc_trim(0);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[cfg(target_os = "linux")]
    #[test]
    fn only_a_single_active_display_card_can_be_pinned() {
        let drm = std::env::temp_dir().join(format!("mukyu-drm-test-{:016x}", rand::random::<u64>()));
        let set_output = |name: &str, status: &str, enabled: &str| {
            let output = drm.join(name);
            std::fs::create_dir_all(&output).unwrap();
            std::fs::write(output.join("status"), status).unwrap();
            std::fs::write(output.join("enabled"), enabled).unwrap();
        };
        set_output("card0-HDMI-A-1", "connected", "disabled");
        assert_eq!(active_display_device(&drm), None);
        set_output("card1-DP-1", "connected", "enabled");
        set_output("card1-DP-2", "connected", "enabled");
        assert_eq!(active_display_device(&drm), Some(drm.join("card1/device")));
        set_output("card0-HDMI-A-1", "connected", "enabled");
        assert_eq!(active_display_device(&drm), None);
        std::fs::remove_dir_all(drm).unwrap();
    }

    #[test]
    fn windows_split() {
        assert_eq!(split_launch_options(r#"-a "b c" 'd'"#), vec!["-a", "b c", "d"]);
    }

    #[test]
    fn posix_split() {
        assert_eq!(shell_split("mangohud %command% -x"), vec!["mangohud", "%command%", "-x"]);
    }
}

#[cfg(windows)]
pub fn vsync_off_while(window: &slint::Window, condition: fn() -> bool) {
    use windows::core::s;
    use windows::Win32::Graphics::OpenGL::wglGetProcAddress;
    let current = std::cell::Cell::new(1);
    let _ = window.set_rendering_notifier(move |state, _| {
        if !matches!(state, slint::RenderingState::BeforeRendering) {
            return;
        }
        let wanted = if condition() { 0 } else { 1 };
        if wanted == current.get() {
            return;
        }
        unsafe {
            if let Some(proc) = wglGetProcAddress(s!("wglSwapIntervalEXT")) {
                let set_interval: unsafe extern "system" fn(i32) -> i32 = std::mem::transmute(proc);
                if set_interval(wanted) != 0 {
                    current.set(wanted);
                }
            }
        }
    });
}

#[cfg(target_os = "linux")]
fn active_display_device(drm: &Path) -> Option<PathBuf> {
    let mut active_card = None;
    for entry in std::fs::read_dir(drm).ok()? {
        let entry = entry.ok()?;
        let name = entry.file_name();
        let Some((card, _)) = name.to_str()?.split_once('-') else { continue };
        if !card.starts_with("card") {
            continue;
        }
        let status = std::fs::read_to_string(entry.path().join("status")).ok()?;
        if status.trim() != "connected" {
            continue;
        }
        let enabled = std::fs::read_to_string(entry.path().join("enabled")).ok()?;
        if enabled.trim() != "enabled" {
            continue;
        }
        let device = drm.join(card).join("device");
        if active_card.as_ref().is_some_and(|previous| previous != &device) {
            return None;
        }
        active_card = Some(device);
    }
    active_card
}

#[cfg(target_os = "linux")]
fn egl_vendor_files(nvidia: bool) -> Vec<String> {
    let mut dirs = vec![std::path::PathBuf::from("/etc/glvnd/egl_vendor.d")];
    let data_dirs = std::env::var("XDG_DATA_DIRS").unwrap_or_default();
    for d in data_dirs.split(':').filter(|d| !d.is_empty()).chain(["/usr/local/share", "/usr/share"]) {
        dirs.push(std::path::Path::new(d).join("glvnd/egl_vendor.d"));
    }
    let mut seen = std::collections::HashSet::new();
    let mut picked = Vec::new();
    for dir in dirs {
        let Ok(entries) = std::fs::read_dir(&dir) else { continue };
        let mut files: Vec<std::path::PathBuf> = entries.flatten().map(|e| e.path()).filter(|p| p.extension().is_some_and(|e| e == "json")).collect();
        files.sort();
        for file in files {
            let Some(name) = file.file_name().map(|n| n.to_owned()) else { continue };
            if !seen.insert(name) {
                continue;
            }
            let Ok(text) = std::fs::read_to_string(&file) else { continue };
            let Ok(json) = serde_json::from_str::<serde_json::Value>(&text) else { continue };
            let lib = json.pointer("/ICD/library_path").and_then(|v| v.as_str()).unwrap_or("").to_ascii_lowercase();
            let is_nvidia = lib.contains("nvidia");
            let is_mesa = lib.contains("mesa");
            if (nvidia && is_nvidia) || (!nvidia && is_mesa) {
                picked.push(file.display().to_string());
            }
        }
    }
    picked
}

#[cfg(target_os = "linux")]
pub fn pick_egl_vendor() {
    if std::env::var_os("WAYLAND_DISPLAY").is_none() && std::env::var_os("WAYLAND_SOCKET").is_none() {
        let display = std::env::var("DISPLAY").unwrap_or_default();
        if !display.starts_with(':') && !display.starts_with("unix:") {
            return;
        }
    }
    let user_set = [
        "__EGL_VENDOR_LIBRARY_FILENAMES", "__EGL_VENDOR_LIBRARY_DIRS", "MUKYU_GPU_PICK",
        "DRI_PRIME", "__NV_PRIME_RENDER_OFFLOAD", "__NV_PRIME_RENDER_OFFLOAD_PROVIDER",
    ].iter().any(|k| std::env::var_os(k).is_some());
    if user_set {
        return;
    }
    let Some(device) = active_display_device(Path::new("/sys/class/drm")) else { return };
    let Ok(driver) = std::fs::read_link(device.join("driver")) else { return };
    let nvidia = match driver.file_name().and_then(|name| name.to_str()) {
        Some("nvidia") => true,
        Some("amdgpu" | "radeon" | "i915" | "xe" | "nouveau") => false,
        _ => return,
    };
    let files = egl_vendor_files(nvidia);
    if files.is_empty() {
        return;
    }
    let mut mark = "1";
    if !nvidia {
        if let Ok(info) = std::fs::read_to_string(device.join("uevent")) {
            if let Some(slot) = info.lines().find_map(|line| line.strip_prefix("PCI_SLOT_NAME=")) {
                std::env::set_var("DRI_PRIME", format!("pci-{}", slot.replace([':', '.'], "_")));
                mark = "mesa-pci";
            }
        }
    }
    std::env::set_var("__EGL_VENDOR_LIBRARY_FILENAMES", files.join(":"));
    std::env::set_var(EGL_PICK_MARK, mark);
}
