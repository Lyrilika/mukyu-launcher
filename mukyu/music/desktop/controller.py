from mukyu.paths import ASSETS_DIR, ICON_PATH
import hashlib
import logging
import math
import sys
from pathlib import Path

from gi.repository import GLib, Gst

LOG = logging.getLogger(__name__)
TRACK_PREFIX = '/com/github/Lyrilika/MukyuLauncher/track/'


class DesktopMedia:
    def __init__(self, page, backend_factory=None):
        self.page = page
        self.closed = False
        self._idle = 0
        self._engine_play_pending = False
        self.backend = None
        try:
            if backend_factory is None:
                if sys.platform == 'win32':
                    from mukyu.music.desktop.windows import WindowsMedia
                    backend_factory = WindowsMedia
                elif sys.platform.startswith('linux'):
                    from mukyu.music.desktop.mpris import MprisMedia
                    backend_factory = MprisMedia
            if backend_factory is not None:
                self.backend = backend_factory(self)
        except Exception:
            LOG.exception('Desktop media integration could not start')
        self.changed()

    def position(self):
        p = self.page
        if p.mode != 'game' or p.player is None or p._preparing_track_id is not None:
            return 0
        ok, value = p.player.query_position(Gst.Format.TIME)
        return max(0, value // 1000) if ok else 0

    def snapshot(self):
        p = self.page
        track = p._selected_track if p.mode == 'game' else None
        radio = p.mode == 'radio'
        available = radio or track is not None
        title = p.current['title'] if radio else p._track_title(track) if track else ''
        artist = p.current['artist'] if radio else track.artist if track else ''
        album = p.current['album'] if radio else track.game_title if track else ''
        identity = ('radio:' + '\0'.join((title, artist, album))) if radio else track.id if track else ''
        art = p._last_art_url or '' if radio else ''
        if track:
            cover = ASSETS_DIR / 'covers' / (track.game_key.replace('.', '') + '.jpg')
            if cover.is_file():
                art = cover.resolve().as_uri()
        if available and not art:
            icon = ICON_PATH
            if icon.is_file():
                art = icon.resolve().as_uri()
        duration = max(0, round(track.duration * 1_000_000)) if track else 0
        ready = track is not None and p.player is not None and p._preparing_track_id is None
        state = p.player.get_state(0)[1] if ready else Gst.State.NULL
        seekable = ready and state in (Gst.State.PAUSED, Gst.State.PLAYING) and duration > 0
        tracks = p._playback_track_list() if track else []
        index = tracks.index(track) if track in tracks else -1
        return {
            'track_id': TRACK_PREFIX + hashlib.sha256(identity.encode()).hexdigest() if identity else '',
            'title': title, 'artist': artist, 'album': album, 'art': art,
            'duration': duration, 'status': p._media_status if available else 'Stopped',
            'can_play': available, 'can_pause': available, 'can_seek': bool(seekable),
            'can_next': bool(tracks and (p._shuffle and len(tracks) > 1 or p._repeat_mode == 1 or index + 1 < len(tracks))),
            'can_previous': bool(tracks),
            'loop': ('None', 'Playlist', 'Track')[p._repeat_mode] if not radio else 'None',
            'shuffle': bool(p._shuffle and not radio), 'volume': 0.0 if p.muted else p.volume,
        }

    def changed(self):
        if not self.closed and self.backend is not None and not self._idle:
            self._idle = GLib.idle_add(self._publish)

    def _publish(self):
        self._idle = 0
        if not self.closed and self.backend is not None:
            try:
                self.backend.update(self.snapshot())
            except Exception:
                LOG.exception('Desktop media update failed')
        return False

    def seeked(self, position):
        if not self.closed and self.backend is not None:
            try:
                self.backend.seeked(max(0, int(position)))
            except Exception:
                LOG.exception('Desktop media seek notification failed')
        self.changed()

    def command(self, name, value=None):
        if self.closed:
            return
        p = self.page
        state = self.snapshot()
        if name == 'Raise':
            window = p.root.get_root()
            if window is not None:
                window.present()
        elif name == 'Quit':
            window = p.root.get_root()
            app = window.get_application() if window is not None else None
            if app is not None:
                app.quit()
        elif name in ('Play', 'Pause', 'PlayPause', 'Stop'):
            if name == 'PlayPause':
                name = 'Pause' if p.playing or p._preparing_track_id or self._engine_play_pending else 'Play'
            if name == 'Play' and state['can_play'] and not p.playing and p._preparing_track_id is None:
                if p.player is None and not p._engine_ready_flag:
                    if not self._engine_play_pending:
                        self._engine_play_pending = True
                        def ready():
                            self._engine_play_pending = False
                            self.command('Play')
                        p._after_engine.append(ready)
                        p._ensure_engine()
                else:
                    p._on_play_pause(None)
            elif name == 'Pause' and state['can_pause']:
                self._engine_play_pending = False
                if p._preparing_track_id is not None or p.player is None:
                    p._mode_change_generation += 1
                    p._after_engine.clear()
                    p._stop_current_playback()
                    p._media_status = 'Paused'
                elif p.playing:
                    p._on_play_pause(None)
            elif name == 'Stop':
                self._engine_play_pending = False
                p._mode_change_generation += 1
                p._after_engine.clear()
                p._stop_current_playback()
                p._media_status = 'Stopped'
        elif name == 'Next' and state['can_next']:
            p._on_next(None)
        elif name == 'Previous' and state['can_previous']:
            p._on_previous(None)
        elif name == 'Seek' and state['can_seek']:
            position = self.position() + int(value)
            if position > state['duration']:
                p._on_next(None)
            else:
                p._seek_to(max(0, position) / 1_000_000)
        elif name == 'SetPosition' and state['can_seek']:
            track_id, position = value
            if track_id == state['track_id'] and 0 <= position <= state['duration']:
                p._seek_to(position / 1_000_000)
        elif name == 'LoopStatus' and p.mode == 'game':
            wanted = {'None': 0, 'Playlist': 1, 'Track': 2}[value]
            p._set_repeat_mode(wanted)
        elif name == 'Shuffle' and p.mode == 'game':
            if p._shuffle != bool(value):
                p._on_shuffle(p.shuffle_btn)
        elif name == 'Volume':
            if not math.isfinite(value):
                raise ValueError('Volume must be finite')
            p.volume = min(1.0, max(0.0, value))
            p.muted = False
            if p.player is not None:
                p.player.set_property('volume', p.volume)
        self.changed()

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self._idle:
            GLib.source_remove(self._idle)
            self._idle = 0
        if self.backend is not None:
            self.backend.close()
