import ctypes
from pathlib import Path


def main():
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.CreateWindowExW.argtypes = [ctypes.c_uint32, ctypes.c_wchar_p, ctypes.c_wchar_p,
        ctypes.c_uint32, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    user.CreateWindowExW.restype = ctypes.c_void_p
    user.DestroyWindow.argtypes = [ctypes.c_void_p]
    window = user.CreateWindowExW(0, 'STATIC', 'Mukyu SMTC verification', 0x00cf0000,
        0, 0, 300, 200, None, None, None, None)
    if not window:
        raise ctypes.WinError(ctypes.get_last_error())
    dll = ctypes.CDLL(str(Path(__file__).resolve().parents[2] / 'tools' / 'windows' / 'mukyu_smtc.dll'))
    dll.smtc_create.argtypes = [ctypes.c_void_p]
    dll.smtc_create.restype = ctypes.c_int32
    dll.smtc_update.argtypes = [ctypes.c_wchar_p] * 4 + [ctypes.c_int32] * 4
    dll.smtc_update.restype = ctypes.c_int32
    dll.smtc_timeline.argtypes = [ctypes.c_int64, ctypes.c_int64]
    dll.smtc_timeline.restype = ctypes.c_int32
    dll.smtc_close.argtypes = []
    dll.smtc_close.restype = None
    def check(hr):
        if hr < 0:
            raise RuntimeError(f'SMTC failure 0x{hr & 0xffffffff:08x}')
    try:
        check(dll.smtc_create(window))
        for state in (0, 2, 1, 0):
            check(dll.smtc_update('永遠の巫女', 'ZUN', 'Touhou 1', '', state, 31, 1, 0))
            check(dll.smtc_timeline(60_000_000, 20_000_000))
        print('SMTC initialization, Unicode metadata, playback states and timeline passed')
    finally:
        dll.smtc_close()
        dll.smtc_close()
        user.DestroyWindow(window)


if __name__ == '__main__':
    main()
