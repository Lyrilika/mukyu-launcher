from mukyu.paths import TOOLS_DIR
import ctypes
import logging
from pathlib import Path

import gi
from gi.repository import Gio, GLib


class WindowsMedia:
    def __init__(self, controller):
        gi.require_version('GdkWin32', '4.0')
        from gi.repository import GdkWin32
        self.controller = controller
        self.closed = False
        self.last = None
        self._ticks = 0
        self._timer = 0
        self.dll = ctypes.CDLL(str(TOOLS_DIR / 'windows' / 'mukyu_smtc.dll'))
        self.dll.smtc_create.argtypes = [ctypes.c_void_p]
        self.dll.smtc_create.restype = ctypes.c_int32
        self.dll.smtc_update.argtypes = [ctypes.c_wchar_p] * 4 + [ctypes.c_int32] * 4
        self.dll.smtc_update.restype = ctypes.c_int32
        self.dll.smtc_timeline.argtypes = [ctypes.c_int64, ctypes.c_int64]
        self.dll.smtc_timeline.restype = ctypes.c_int32
        self.dll.smtc_poll.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int64)]
        self.dll.smtc_poll.restype = ctypes.c_int32
        self.dll.smtc_close.argtypes = []
        self.dll.smtc_close.restype = None
        window = controller.page.root.get_root()
        surface = window.get_surface()
        handle = GdkWin32.Win32Surface.get_handle(surface)
        result = self.dll.smtc_create(handle)
        if result < 0:
            self.dll.smtc_close()
            raise OSError(f'Windows media controls initialization failed (0x{result & 0xffffffff:08x})')
        self._timer = GLib.timeout_add(100, self._poll)

    def update(self, state):
        if self.closed:
            return
        flags = sum(1 << index for index, name in enumerate(
            ('can_play', 'can_pause', 'can_next', 'can_previous', 'can_seek')) if state[name])
        art = state['art']
        if art.startswith('file:'):
            art = Gio.File.new_for_uri(art).get_path() or ''
        values = (state['title'], state['artist'], state['album'], art,
            {'Stopped': 0, 'Paused': 1, 'Playing': 2}[state['status']], flags,
            {'None': 0, 'Track': 1, 'Playlist': 2}[state['loop']], int(state['shuffle']))
        if values != self.last:
            self._check(self.dll.smtc_update(*values))
            self.last = values
        self._check(self.dll.smtc_timeline(state['duration'] if state['can_seek'] else 0,
            self.controller.position() if state['can_seek'] else 0))

    @staticmethod
    def _check(result):
        if result < 0:
            raise OSError(f'Windows media controls update failed (0x{result & 0xffffffff:08x})')

    def _poll(self):
        if self.closed:
            return False
        try:
            command, value = ctypes.c_int32(), ctypes.c_int64()
            for _ in range(32):
                if not self.dll.smtc_poll(ctypes.byref(command), ctypes.byref(value)):
                    break
                if command.value in (1, 2, 3, 4, 5):
                    self.controller.command({1: 'Play', 2: 'Pause', 3: 'Stop', 4: 'Next', 5: 'Previous'}[command.value])
                elif command.value == 6:
                    self.controller.command('SetPosition', (self.controller.snapshot()['track_id'], value.value))
                elif command.value == 7:
                    self.controller.command('Shuffle', bool(value.value))
                elif command.value == 8 and value.value in (0, 1, 2):
                    self.controller.command('LoopStatus', ('None', 'Track', 'Playlist')[value.value])
            self._ticks = (self._ticks + 1) % 10
            if self._ticks == 0 and self.controller.page.playing:
                self.update(self.controller.snapshot())
        except Exception:
            logging.getLogger(__name__).exception('Windows media controls failed')
            self.close()
            return False
        return True

    def seeked(self, _position):
        self.update(self.controller.snapshot())

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = 0
        self.dll.smtc_close()
