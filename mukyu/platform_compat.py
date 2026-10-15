import os
import subprocess
import sys

IS_WINDOWS = sys.platform.startswith("win")


def config_home():
    if IS_WINDOWS:
        return os.environ.get("APPDATA") or os.path.expanduser(r"~\AppData\Roaming")
    return os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))


def data_home():
    if IS_WINDOWS:
        return os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
    return os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))


def cache_home():
    if IS_WINDOWS:
        return os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
    return os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))


def trim_memory():

    if not sys.platform.startswith("linux"):
        return
    try:
        import gc
        gc.collect()
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass


def exe_name(name):
    if IS_WINDOWS and not name.lower().endswith(".exe"):
        return name + ".exe"
    return name


def no_window_kwargs():
    if IS_WINDOWS:
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}
    return {}


def split_launch_options(text):
    import shlex

    parts = shlex.split(text, posix=False)
    return [p[1:-1] if len(p) >= 2 and p[0] == p[-1] and p[0] in "\"'" else p for p in parts]


def host_env(env=None):
    env = dict(os.environ if env is None else env)
    if not os.environ.get("TL_APPIMAGE"):
        return env
    for key in list(env):
        if key.startswith("TL_ORIG_"):
            name = key[len("TL_ORIG_"):]
            value = env.pop(key)
            if value in ("__TL_UNSET__", "\x00unset"):
                env.pop(name, None)
            else:
                env[name] = value
    env.pop("TL_APPIMAGE", None)
    return env


if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _u32 = ctypes.WinDLL("user32", use_last_error=True)

    _JobObjectBasicAccountingInformation = 1
    _JobObjectBasicProcessIdList = 3
    _WM_CLOSE = 0x0010
    _MAX_PIDS = 256

    class _BASIC_ACCOUNTING(ctypes.Structure):
        _fields_ = [
            ("TotalUserTime", ctypes.c_int64),
            ("TotalKernelTime", ctypes.c_int64),
            ("ThisPeriodTotalUserTime", ctypes.c_int64),
            ("ThisPeriodTotalKernelTime", ctypes.c_int64),
            ("TotalPageFaultCount", wintypes.DWORD),
            ("TotalProcesses", wintypes.DWORD),
            ("ActiveProcesses", wintypes.DWORD),
            ("TotalTerminatedProcesses", wintypes.DWORD),
        ]

    class _PID_LIST(ctypes.Structure):
        _fields_ = [
            ("NumberOfAssignedProcesses", wintypes.DWORD),
            ("NumberOfProcessIdsInList", wintypes.DWORD),
            ("ProcessIdList", ctypes.c_size_t * _MAX_PIDS),
        ]

    _k32.CreateJobObjectW.restype = wintypes.HANDLE
    _k32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    _k32.AssignProcessToJobObject.restype = wintypes.BOOL
    _k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _k32.QueryInformationJobObject.restype = wintypes.BOOL
    _k32.QueryInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD, wintypes.LPVOID,
    ]
    _k32.TerminateJobObject.restype = wintypes.BOOL
    _k32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.CloseHandle.restype = wintypes.BOOL
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]

    _WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    _u32.EnumWindows.argtypes = [_WNDENUMPROC, wintypes.LPARAM]
    _u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    _u32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]


class GameJob:

    def __init__(self, popen):
        self.handle = None
        self.ok = False
        self._popen = popen
        if not IS_WINDOWS:
            return
        try:
            handle = _k32.CreateJobObjectW(None, None)
            if not handle:
                return
            if not _k32.AssignProcessToJobObject(handle, int(popen._handle)):
                _k32.CloseHandle(handle)
                return
            self.handle = handle
            self.ok = True
        except Exception:
            self.handle = None
            self.ok = False

    def active_count(self):
        if not self.ok:
            return 1 if self._popen.poll() is None else 0
        info = _BASIC_ACCOUNTING()
        if not _k32.QueryInformationJobObject(
            self.handle, _JobObjectBasicAccountingInformation,
            ctypes.byref(info), ctypes.sizeof(info), None,
        ):
            return 1 if self._popen.poll() is None else 0
        return int(info.ActiveProcesses)

    def pids(self):
        if not self.ok:
            return [self._popen.pid] if self._popen.poll() is None else []
        data = _PID_LIST()
        if not _k32.QueryInformationJobObject(
            self.handle, _JobObjectBasicProcessIdList,
            ctypes.byref(data), ctypes.sizeof(data), None,
        ):
            return []
        return [int(data.ProcessIdList[i]) for i in range(min(data.NumberOfProcessIdsInList, _MAX_PIDS))]

    def request_close(self):
        pids = set(self.pids())
        if not pids:
            return

        def on_window(hwnd, _lparam):
            owner = wintypes.DWORD(0)
            _u32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value in pids:
                _u32.PostMessageW(hwnd, _WM_CLOSE, 0, 0)
            return True

        callback = _WNDENUMPROC(on_window)
        _u32.EnumWindows(callback, 0)

    def terminate(self):
        if self.ok:
            _k32.TerminateJobObject(self.handle, 1)
        try:
            self._popen.kill()
        except Exception:
            pass

    def close(self):
        if self.ok and self.handle:
            _k32.CloseHandle(self.handle)
        self.ok = False
        self.handle = None
