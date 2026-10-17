from mukyu.paths import ASSETS_DIR
import atexit
import collections
import json
import math
import os
import random
import re
import shutil
import tempfile
import threading
import time
import urllib.parse
import urllib.request

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gst", "1.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio, Gst, Pango

from mukyu.platform_compat import config_home

from mukyu.music.game_bgm import GAME_INFO, GameTrack, assigned_games, discover_tracks, materialize_track
from mukyu.music.titles import display_title, load_title_language, save_title_language
from mukyu.music.theme import dominant_rgb, make_palette, palette_css, palette_from_hue

COVER_PX = 800

RADIO_URL = "https://stream.gensokyoradio.net/1"
NOW_PLAYING_URL = "https://gensokyoradio.net/api/station/playing/"
GR_LOGO_URL = "https://gensokyoradio.net/images/assets/gr-logo-placeholder.png"
USER_AGENT = "MukyuLauncher/1.0 (Gensokyo Radio integration)"

METADATA_INTERVAL_MS = 10_000
RECONNECT_DELAY_MS = 2_500
POSITION_INTERVAL_MS = 180
PREPARED_CACHE_BYTES = 256 * 1024 * 1024
PALETTE_PRIORITY = Gtk.STYLE_PROVIDER_PRIORITY_USER + 2

CONFIG_FILE = os.path.join(
    config_home(),
    "mukyulauncher",
    "games_config.json",
)
FAVORITES_FILE = os.path.join(
    config_home(),
    "mukyulauncher",
    "music_favorites.json",
)
MUSIC_PREFS_FILE = os.path.join(config_home(), "mukyulauncher", "music_prefs.json")
COVER_DIR = str(ASSETS_DIR / "covers")


def _label(css_class=None, xalign=0.0, ellipsize=True):
    label = Gtk.Label(xalign=xalign)
    if ellipsize:
        label.set_ellipsize(Pango.EllipsizeMode.END)
    if css_class:
        label.add_css_class(css_class)
    return label


class MarqueeLabel(Gtk.Stack):


    SPEED = 30.0
    START_DELAY = 0.9
    GAP = "      \u00b7      "

    def __init__(self, css_class=None, xalign=0.0, always=False):
        super().__init__()
        self.set_hexpand(True)

        self.set_hhomogeneous(True)
        self.set_vhomogeneous(True)
        self.set_transition_type(Gtk.StackTransitionType.NONE)
        self._always = always
        self._hover = False
        self._playing = False
        self._text = ""
        self._tick = 0
        self._phase = None
        self._began = 0.0
        self._period = 0.0
        self._allocated_width = 0

        self._idle = Gtk.Label(xalign=xalign)
        self._idle.set_ellipsize(Pango.EllipsizeMode.END)
        self._moving = Gtk.Label(xalign=0.0)
        self._moving.set_wrap(False)
        if css_class:
            self._idle.add_css_class(css_class)
            self._moving.add_css_class(css_class)

        self._scroller = Gtk.ScrolledWindow()
        self._scroller.set_policy(Gtk.PolicyType.EXTERNAL, Gtk.PolicyType.NEVER)
        self._scroller.set_propagate_natural_height(True)
        self._scroller.set_hexpand(True)
        self._scroller.set_can_target(False)
        self._scroller.set_kinetic_scrolling(False)
        self._scroller.set_child(self._moving)

        self.add_named(self._idle, "idle")
        self.add_named(self._scroller, "moving")
        self.set_visible_child_name("idle")
        self.connect("unmap", lambda *_: self._stop())
        self.connect("map", lambda *_: self._refresh())


    def do_size_allocate(self, width, height, baseline):
        Gtk.Stack.do_size_allocate(self, width, height, baseline)
        if width != self._allocated_width:
            self._allocated_width = width
            self._stop()
            self._refresh()

    def set_text(self, text):
        text = text or ""
        if text == self._text:
            return
        self._text = text
        self._idle.set_text(text)
        self._stop()
        self._refresh()

    def get_text(self):
        return self._text

    def set_justify(self, justification):
        self._idle.set_justify(justification)


    def set_hover(self, on):
        if on != self._hover:
            self._hover = on
            self._refresh()

    def set_playing(self, on):
        if on != self._playing:
            self._playing = on
            self._refresh()

    def _active(self):
        return self._always or self._hover or self._playing

    def _refresh(self):
        if self._active() and self.get_mapped():
            if not self._tick and self._phase != "fits":
                self._phase = "check"
                self._tick = self.add_tick_callback(self._on_tick)
        else:
            self._stop()

    def _stop(self):
        if self._tick:
            self.remove_tick_callback(self._tick)
            self._tick = 0
        self._phase = None
        self.set_visible_child_name("idle")
        self._scroller.get_hadjustment().set_value(0)

    def _on_tick(self, _widget, clock):
        now = clock.get_frame_time() / 1_000_000.0
        if not self._active():
            self._tick = 0
            self._stop()
            return GLib.SOURCE_REMOVE
        if self._phase == "check":
            width = self.get_width()
            if width <= 0:
                return GLib.SOURCE_CONTINUE
            text_width = self._idle.create_pango_layout(self._text).get_pixel_size()[0]
            if text_width <= width:
                self._tick = 0
                self._phase = "fits"
                return GLib.SOURCE_REMOVE
            self._moving.set_text(self._text + self.GAP + self._text)
            self._period = float(self._idle.create_pango_layout(self._text + self.GAP).get_pixel_size()[0])
            self._scroller.get_hadjustment().set_value(0)
            self.set_visible_child_name("moving")
            self._began = now
            self._phase = "wait"
        elif self._phase == "wait":
            if now - self._began >= self.START_DELAY:
                self._began = now
                self._phase = "slide"
        elif self._phase == "slide":
            offset = ((now - self._began) * self.SPEED) % max(self._period, 1.0)
            self._scroller.get_hadjustment().set_value(offset)
        return GLib.SOURCE_CONTINUE


def _widget_color(widget):
    try:
        return widget.get_color()
    except AttributeError:
        return widget.get_style_context().get_color()


class EqBars(Gtk.DrawingArea):

    SPEEDS = (7.3, 5.6, 8.4, 6.2)
    PHASES = (0.0, 1.9, 3.4, 5.1)
    IDLE = (0.40, 0.70, 0.52, 0.30)

    def __init__(self, width=20, height=16):
        super().__init__()
        self.set_content_width(width)
        self.set_content_height(height)
        self.set_valign(Gtk.Align.CENTER)
        self.set_can_target(False)
        self._level = 0.0
        self._target = 0.0
        self._tick = 0
        self._last = None
        self._t = 0.0
        self.set_draw_func(self._draw)
        self.connect("map", lambda *_a: self._ensure_tick())
        self.connect("unmap", self._on_unmap)

    def set_active(self, on):
        self._target = 1.0 if on else 0.0
        self._ensure_tick()

    def _ensure_tick(self):
        if not self._tick and self.get_mapped() and (self._target > 0.0 or self._level > 0.0):
            self._last = None
            self._tick = self.add_tick_callback(self._on_tick)

    def _on_unmap(self, *_a):
        if self._tick:
            self.remove_tick_callback(self._tick)
            self._tick = 0

    def _on_tick(self, _widget, clock):
        now = clock.get_frame_time() / 1_000_000.0
        dt = 0.016 if self._last is None else min(0.1, max(0.0, now - self._last))
        self._last = now
        self._t = now
        self._level += (self._target - self._level) * min(1.0, dt * 9.0)
        self.queue_draw()
        if self._target == 0.0 and self._level < 0.02:
            self._level = 0.0
            self._tick = 0
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def _draw(self, _area, cr, width, height):
        color = _widget_color(self)
        cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        count = len(self.SPEEDS)
        gap = 3.0
        bar_w = (width - gap * (count - 1)) / count
        radius = bar_w / 2.0
        for i in range(count):
            dynamic = 0.28 + 0.72 * (0.5 + 0.5 * math.sin(self._t * self.SPEEDS[i] + self.PHASES[i]))
            frac = self.IDLE[i] * (1.0 - self._level) + dynamic * self._level
            bar_h = max(bar_w, frac * height)
            x = i * (bar_w + gap)
            y = (height - bar_h) / 2.0
            cr.new_sub_path()
            cr.arc(x + radius, y + radius, radius, math.pi, 2 * math.pi)
            cr.arc(x + radius, y + bar_h - radius, radius, 0, math.pi)
            cr.close_path()
            cr.fill()


class LoadingIndicator(Gtk.DrawingArea):

    LOBES = (5, 8, 3, 6, 4, 7)
    MORPH_SECONDS = 0.8

    def __init__(self, size=64):
        super().__init__()
        self.add_css_class("mu-loader")
        self.set_content_width(size)
        self.set_content_height(size)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self._tick = 0
        self._t0 = None
        self._t = 0.0
        self.set_draw_func(self._draw)
        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)

    def _on_map(self, *_a):
        if not self._tick:
            self._t0 = None
            self._tick = self.add_tick_callback(self._on_tick)

    def _on_unmap(self, *_a):
        if self._tick:
            self.remove_tick_callback(self._tick)
            self._tick = 0

    def _on_tick(self, _widget, clock):
        now = clock.get_frame_time() / 1_000_000.0
        if self._t0 is None:
            self._t0 = now
        self._t = now - self._t0
        self.queue_draw()
        return GLib.SOURCE_CONTINUE

    @staticmethod
    def _amp(lobes):
        return min(0.2, 0.55 / lobes)

    def _draw(self, _area, cr, width, height):
        color = _widget_color(self)
        phase = self._t / self.MORPH_SECONDS
        index = int(phase) % len(self.LOBES)
        f = phase - int(phase)
        ease = f * f * (3.0 - 2.0 * f)
        a = self.LOBES[index]
        b = self.LOBES[(index + 1) % len(self.LOBES)]
        amp_a = self._amp(a) * (1.0 - ease)
        amp_b = self._amp(b) * ease
        rotation = self._t * 2.0 + 0.5 * math.sin(self._t * 1.3)
        base = min(width, height) * 0.29
        cx, cy = width / 2.0, height / 2.0
        steps = 120
        cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        for k in range(steps + 1):
            theta = 2.0 * math.pi * k / steps
            radius = base * (1.0 + amp_a * math.cos(a * theta) + amp_b * math.cos(b * theta))
            x = cx + radius * math.cos(theta + rotation)
            y = cy + radius * math.sin(theta + rotation)
            if k == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.close_path()
        cr.fill()


def _image(icon_name, size):
    image = Gtk.Image.new_from_icon_name(icon_name)
    image.set_pixel_size(size)
    return image


def _glyph(icon_name, fallback_text, size):
    display = Gdk.Display.get_default()
    theme = Gtk.IconTheme.get_for_display(display) if display is not None else None
    if theme is not None and theme.has_icon(icon_name):
        return _image(icon_name, size)
    label = Gtk.Label()
    label.set_markup(f'<span size="{int(size * 0.62 * 1024)}">{fallback_text}</span>')
    label.set_size_request(size, size)
    return label


def _button(child, *css):
    button = Gtk.Button()
    button.set_child(child)
    button.set_focus_on_click(False)
    for name in css:
        button.add_css_class(name)
    return button


def _fmt(seconds):
    seconds = int(max(0, seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_bytes(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=12) as response:
        return response.read()


def _get_nested(mapping, *keys, default=None):
    value = mapping
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return default if value is None else value


def _first_value(mapping, *paths):
    for path in paths:
        value = _get_nested(mapping, *path, default=None)
        if value not in (None, ""):
            return value
    return None


def _prepare_cover_bytes(data):
    loader = GdkPixbuf.PixbufLoader()

    def on_size(_loader, width, height):


        ratio = min(1.0, COVER_PX / max(1, min(width, height)))
        if ratio < 1.0:
            _loader.set_size(max(1, round(width * ratio)), max(1, round(height * ratio)))

    loader.connect("size-prepared", on_size)
    loader.write(data)
    loader.close()
    pixbuf = loader.get_pixbuf()
    if pixbuf is None:
        raise ValueError("Album art could not be decoded")
    width, height = pixbuf.get_width(), pixbuf.get_height()
    side = min(width, height)
    square = pixbuf.new_subpixbuf((width - side) // 2, (height - side) // 2, side, side).copy()
    tiny = square.scale_simple(32, 32, GdkPixbuf.InterpType.BILINEAR)
    rgb = dominant_rgb(tiny.get_pixels(), 32, 32, tiny.get_n_channels(), tiny.get_rowstride())
    return square, rgb


def _load_favorite_data():
    try:
        with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return {str(item) for item in data}
        if isinstance(data, dict):
            return {str(key) for key, value in data.items() if value}
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return set()


def _save_favorite_data(favorites):
    os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
    temporary = FAVORITES_FILE + ".tmp"
    with open(temporary, "w", encoding="utf-8") as f:
        json.dump(sorted(favorites), f, indent=2)
    os.replace(temporary, FAVORITES_FILE)


class MusicPage:
    def __init__(self, theme_manager=None):
        self._engine_started = False
        self._engine_ready_flag = False
        self._after_engine = []
        self.mode = "game"
        self.playing = False
        self.volume = 1.0
        self.muted = False
        self.current = {
            "title": "Gensokyo Radio",
            "artist": "Live radio",
            "album": "Gensokyo Radio",
            "circle": "",
            "year": "",
            "album_art": "",
        }
        self._palette_provider = Gtk.CssProvider()
        self._last_rgb = None
        self._theme_manager = theme_manager
        self.player = None
        self._metadata_generation = 0
        self._metadata_timer = 0
        self._metadata_request_in_flight = False
        self._metadata_failures = 0
        self._last_metadata_at = 0.0
        self._poll_skip = 0
        self._song_end_timer = 0
        self._reconnect_timer = 0
        self._position_timer = 0
        self._last_error = ""
        self._last_art_url = None
        self._art_generation = 0
        self._enter_widgets = []
        self._flips = {}
        self._connecting = False
        self._ring_off_timer = 0
        self._progress_tick = 0
        self._progress_updating = False
        self._seek_timer = 0
        self._pending_seek = 0.0
        self._seek_pending = False
        self._seek_hold_until = 0.0
        self._progress_dragging = False
        self._game_tracks = {}
        self._assigned = []
        self._selected_game = None
        self._selected_track = None
        self._game_index = -1
        self._title_language = load_title_language(MUSIC_PREFS_FILE)
        self._favorites = _load_favorite_data()
        self._favorites_view = False
        self._shuffle = False
        self._repeat_mode = 0
        self._loop_seqnum = None
        self._loop_pending = False
        self._loop_attempted = False
        self._last_loop_position = None
        self._desktop_media = None
        self._media_closed = False
        self._media_status = "Stopped"
        self._shuffle_rng = random.SystemRandom()
        self._scratch_dir = tempfile.mkdtemp(prefix="mukyulauncher-bgm-")
        self._prepared_tracks = {}
        self._rendered_tracks = ()
        self._local_art_identity = None
        self._preparing_track_id = None
        self._mode_change_generation = 0
        self._intro_played = False
        self._assigned_signature = None
        self._game_paths = {}
        self._scan_queue = collections.deque()
        self._scan_lock = threading.Lock()
        self._scan_running = False
        self._scanning = set()
        self._prefetch_timer = 0

        self._build()
        self.root.connect("map", self._on_root_map)
        self.root.connect("unmap", self._on_root_unmap)
        self._install_palette_provider()
        if self._theme_manager is not None:
            self._theme_manager.connect_appearance(self._on_launcher_appearance_changed)
        self._set_game_defaults()
        self._apply_palette()
        atexit.register(self._shutdown_player)


    def _ensure_desktop_media(self):
        if self._desktop_media is None and not self._media_closed:
            from mukyu.music.desktop.controller import DesktopMedia
            self._desktop_media = DesktopMedia(self)
            window = self.root.get_root()
            app = window.get_application() if window is not None else None
            if app is not None:
                app.connect("shutdown", lambda *_: self._shutdown_player())

    def _media_changed(self):
        if self._desktop_media is not None:
            self._desktop_media.changed()

    def _ensure_engine(self):


        if self._engine_started:
            return
        self._engine_started = True

        def work():
            try:
                Gst.init(None)
                player = Gst.ElementFactory.make("playbin", "mukyu-music-player")
            except Exception:
                player = None
            GLib.idle_add(self._engine_ready, player)

        threading.Thread(target=work, daemon=True, name="gst-init").start()
        self._refresh_assigned_games()

    def _engine_ready(self, player):
        self._engine_ready_flag = True
        self._attach_player(player)
        callbacks, self._after_engine = self._after_engine, []
        if self.player is not None:
            for callback in callbacks:
                callback()
        return False

    def _build(self):
        root = Gtk.Overlay()
        root.add_css_class("mu-root")
        self.root = root

        glow = Gtk.Box()
        glow.add_css_class("mu-page")
        glow.set_hexpand(True)
        glow.set_vexpand(True)
        root.set_child(glow)

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        center.add_css_class("mu-player-page")
        center.add_css_class("mu-full-player")
        center.set_margin_start(24)
        center.set_margin_end(24)
        center.set_margin_top(16)
        center.set_margin_bottom(24)
        center.set_halign(Gtk.Align.CENTER)
        center.set_hexpand(True)
        center.set_vexpand(True)
        root.add_overlay(center)
        self.center = center

        mode_shell = Gtk.Overlay()
        mode_shell.set_halign(Gtk.Align.CENTER)
        mode_shell.add_css_class("mu-mode-shell")
        self.mode_dropdown = Gtk.DropDown.new_from_strings(["Game BGM", "Gensokyo Radio"])
        self.mode_dropdown.add_css_class("mu-mode-dropdown")
        self.mode_dropdown.add_css_class("mu-dd")
        self.mode_dropdown.set_factory(self._make_centered_factory(balance_arrow=True))
        self.mode_dropdown.set_list_factory(self._make_centered_factory(balance_arrow=False))
        self.mode_dropdown.set_selected(0)
        self.mode_dropdown.connect("notify::selected", self._on_mode_changed)
        mode_shell.set_child(self.mode_dropdown)
        self._style_dropdown_popover(self.mode_dropdown)
        center.append(mode_shell)
        self._enter(mode_shell)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        body.set_halign(Gtk.Align.CENTER)
        body.set_hexpand(True)
        body.set_vexpand(True)
        center.append(body)
        self.body = body

        player_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        player_column.add_css_class("mu-player-column")
        player_column.set_halign(Gtk.Align.CENTER)
        player_column.set_vexpand(True)
        body.append(player_column)
        self.player_column = player_column

        self._build_player(player_column)
        self._build_game_track_panel(body)
        self._apply_mode_visibility()

    def _build_player(self, column):
        header = Gtk.Box()
        header.set_halign(Gtk.Align.CENTER)
        chip = Gtk.Box(spacing=10)
        chip.add_css_class("mu-chip")
        self.album_label = _label("mu-chip-text", ellipsize=False)
        self.album_label.set_text("Gensokyo Radio  ·  LIVE")
        chip.append(self.album_label)
        header.append(chip)
        self.header_box = header

        frame = Gtk.AspectFrame()
        frame.set_ratio(1.0)
        frame.set_obey_child(False)
        frame.set_xalign(0.5)
        frame.set_yalign(0.5)
        frame.set_size_request(220, 220)
        frame.set_hexpand(True)
        frame.set_vexpand(True)

        art_wrap = Gtk.Overlay()
        art_wrap.add_css_class("mu-art-wrap")
        self.art_wrap = art_wrap

        self.art_picture = Gtk.Picture()
        self.art_picture.set_can_shrink(True)
        self.art_picture.set_content_fit(Gtk.ContentFit.COVER)
        self.art_picture.add_css_class("mu-art")
        art_wrap.set_child(self.art_picture)

        self.art_placeholder = Gtk.Box()
        self.art_placeholder.add_css_class("mu-art-placeholder")
        self.art_placeholder.set_hexpand(True)
        self.art_placeholder.set_vexpand(True)
        icon = _image("audio-x-generic-symbolic", 96)
        icon.set_opacity(0.65)
        icon.set_halign(Gtk.Align.CENTER)
        icon.set_valign(Gtk.Align.CENTER)
        self.art_placeholder.append(icon)
        art_wrap.add_overlay(self.art_placeholder)

        frame.set_child(art_wrap)
        column.append(frame)
        self.art_frame = frame
        self._enter(frame)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_halign(Gtk.Align.FILL)
        info.set_hexpand(True)
        self.title_label = MarqueeLabel("mu-title", xalign=0.5, always=True)
        self.title_label.set_justify(Gtk.Justification.CENTER)
        self.artist_label = _label("mu-artist", xalign=0.5)
        self.artist_label.set_justify(Gtk.Justification.CENTER)
        self.album_detail = _label("mu-album", xalign=0.5)
        self.album_detail.set_justify(Gtk.Justification.CENTER)
        info.append(self.title_label)
        info.append(self.artist_label)
        info.append(self.album_detail)
        column.append(info)
        self.info_box = info
        self._enter(info)

        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        progress_box.set_size_request(560, -1)
        progress_box.set_hexpand(True)
        self.progress = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.01)
        self.progress.set_draw_value(False)
        self.progress.set_hexpand(True)
        self.progress.add_css_class("mu-progress")
        self.progress.set_sensitive(False)
        self.progress.connect("change-value", self._on_progress_change_value)
        press = Gtk.EventControllerLegacy()
        press.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        press.connect("event", self._on_progress_press)
        self.progress.add_controller(press)
        self.time_now = _label("mu-time")
        self.time_total = _label("mu-time", xalign=1.0)
        self.time_total.set_hexpand(True)
        times = Gtk.Box()
        self.time_now.set_text("LIVE")
        self.time_total.set_text("LIVE")
        times.append(self.time_now)
        times.append(self.time_total)
        progress_box.append(self.progress)
        progress_box.append(times)
        column.append(progress_box)
        self._enter(progress_box)

        controls = Gtk.Box(spacing=14)
        controls.set_halign(Gtk.Align.CENTER)
        self.shuffle_btn = _button(_image("media-playlist-shuffle-symbolic", 22), "mu-toggle", "mu-shuffle")
        self.shuffle_btn.connect("clicked", self._on_shuffle)
        self.prev_btn = _button(_image("media-skip-backward-symbolic", 28), "mu-toggle", "mu-previous")
        self.prev_btn.connect("clicked", self._on_previous)

        self.play_icons = Gtk.Overlay()
        self.play_icons.add_css_class("mu-play-icons")
        self.play_glyph = _glyph("media-playback-start-symbolic", "▶", 38)
        self.pause_glyph = _glyph("media-playback-pause-symbolic", "❚❚", 38)
        for glyph, name in ((self.play_glyph, "mu-ico-play"), (self.pause_glyph, "mu-ico-pause")):
            glyph.add_css_class("mu-ico")
            glyph.add_css_class(name)
            glyph.set_halign(Gtk.Align.CENTER)
            glyph.set_valign(Gtk.Align.CENTER)
        self.play_icons.set_child(self.play_glyph)
        self.play_icons.add_overlay(self.pause_glyph)
        self.play_btn = _button(self.play_icons, "mu-play")
        self.play_btn.set_size_request(76, 76)
        try:
            self.play_btn.set_overflow(Gtk.Overflow.HIDDEN)
        except AttributeError:
            pass
        self.play_btn.connect("clicked", self._on_play_pause)

        play_motion = Gtk.EventControllerMotion()
        play_motion.connect("enter", lambda *_args: self.play_holder_hover(True))
        play_motion.connect("leave", lambda *_args: self.play_holder_hover(False))
        self.play_btn.add_controller(play_motion)

        self.play_ripple = Gtk.Box()
        self.play_ripple.add_css_class("mu-ripple-ring")
        self.play_ring = Gtk.Box()
        self.play_ring.add_css_class("mu-ring")
        for overlay_widget in (self.play_ripple, self.play_ring):
            overlay_widget.set_can_target(False)
            overlay_widget.set_can_focus(False)
        for margin in ("start", "end", "top", "bottom"):
            getattr(self.play_ring, f"set_margin_{margin}")(7)
        play_holder = Gtk.Overlay()
        play_holder.add_css_class("mu-play-holder")
        self.play_holder = play_holder

        self.play_glow = Gtk.Box()
        self.play_glow.add_css_class("mu-play-glow")
        self.play_glow.set_can_target(False)
        self.play_glow.set_can_focus(False)
        play_holder.set_child(self.play_glow)
        play_holder.add_overlay(self.play_btn)
        play_holder.add_overlay(self.play_ripple)
        play_holder.add_overlay(self.play_ring)

        self.next_btn = _button(_image("media-skip-forward-symbolic", 28), "mu-toggle", "mu-next")
        self.next_btn.connect("clicked", self._on_next)
        self.repeat_btn = _button(_image("media-playlist-repeat-symbolic", 22), "mu-toggle", "mu-repeat")
        self.repeat_btn.connect("clicked", self._on_repeat)
        for button in (self.shuffle_btn, self.prev_btn, self.next_btn, self.repeat_btn):
            button.connect("clicked", self._on_control_clicked)
        for widget in (self.shuffle_btn, self.prev_btn, play_holder, self.next_btn, self.repeat_btn):
            widget.set_valign(Gtk.Align.CENTER)
            controls.append(widget)
        column.append(controls)
        self.controls_box = controls
        self._enter(controls)

        source = _label("mu-source", xalign=0.5, ellipsize=False)
        source.set_text("Audio from Gensokyo Radio  ·  128 kbps MP3")
        source.set_halign(Gtk.Align.CENTER)
        column.append(source)
        self._enter(source)
        self.source_label = source

    def _build_game_track_panel(self, parent):
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        panel.add_css_class("mu-track-panel")
        panel.set_size_request(390, -1)
        panel.set_hexpand(False)
        panel.set_vexpand(True)
        panel.set_margin_start(30)
        revealer = Gtk.Revealer()
        revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_LEFT)
        revealer.set_transition_duration(420)
        revealer.set_vexpand(True)
        revealer.add_css_class("mu-fade-target")
        revealer.set_child(panel)
        parent.append(revealer)
        self.track_panel = panel
        self.track_revealer = revealer


        self.game_dropdown = Gtk.DropDown()
        self.game_dropdown.add_css_class("mu-game-dropdown")
        self.game_dropdown.add_css_class("mu-dd")
        self._game_dd_handler = self.game_dropdown.connect("notify::selected", self._on_game_dropdown_changed)
        self.game_dropdown.set_hexpand(True)
        panel.append(self.game_dropdown)

        language_row = Gtk.Box(spacing=10)
        language_row.set_halign(Gtk.Align.END)
        language_buttons = Gtk.Box()
        language_buttons.add_css_class("linked")
        language_buttons.add_css_class("mu-title-language")
        self.title_language_buttons = {}
        for language, label, accessible_name in (
            ("en", "EN", "English song titles"),
            ("ja", "JP", "Japanese song titles"),
        ):
            button = Gtk.ToggleButton(label=label)
            button.update_property([Gtk.AccessibleProperty.LABEL], [accessible_name])
            if self.title_language_buttons:
                button.set_group(self.title_language_buttons["en"])
            button.set_active(language == self._title_language)
            language_buttons.append(button)
            self.title_language_buttons[language] = button

        for language, button in self.title_language_buttons.items():
            button.connect("toggled", self._on_title_language_toggled, language)
        language_row.append(language_buttons)
        panel.append(language_row)

        favorites_nav = Gtk.Button()
        favorites_nav.add_css_class("mu-favorites-nav")
        favorites_content = Gtk.Box(spacing=10)
        favorites_content.append(_image("starred-symbolic", 18))
        favorites_label = _label("mu-favorites-nav-label", ellipsize=False)
        favorites_label.set_text("Favorites")
        favorites_content.append(favorites_label)
        favorites_nav.set_child(favorites_content)
        favorites_nav.connect("clicked", self._on_favorites_nav)
        favorites_revealer = Gtk.Revealer()
        favorites_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        favorites_revealer.set_transition_duration(380)
        favorites_revealer.set_reveal_child(False)
        favorites_revealer.set_visible(False)
        favorites_revealer.connect(
            "notify::child-revealed",
            lambda r, _p: r.set_visible(r.get_child_revealed() or r.get_reveal_child()),
        )
        favorites_revealer.set_child(favorites_nav)
        panel.append(favorites_revealer)
        self.favorites_nav = favorites_nav
        self.favorites_revealer = favorites_revealer

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.add_css_class("mu-track-separator")
        panel.append(separator)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.add_css_class("mu-track-scroll")
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.set_activate_on_single_click(True)
        listbox.connect("row-activated", self._on_track_row_activated)
        listbox.add_css_class("mu-track-list")
        scroll.set_child(listbox)
        panel.append(scroll)
        self.track_list = listbox

        empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        empty.set_halign(Gtk.Align.CENTER)
        empty.set_valign(Gtk.Align.CENTER)
        empty.set_margin_top(40)
        empty.set_margin_bottom(40)
        empty_icon = _image("audio-x-generic-symbolic", 34)
        empty_icon.set_opacity(0.5)
        empty.append(empty_icon)
        empty_label = _label("mu-track-empty", xalign=0.5, ellipsize=False)
        empty_label.set_text("Select a game to view its music")
        empty_label.set_wrap(True)
        empty_label.set_max_width_chars(32)
        empty.append(empty_label)
        listbox.append(empty)
        self.track_empty = empty

        self._track_dropdown_factory = Gtk.SignalListItemFactory()
        self._track_dropdown_factory.connect("setup", self._setup_game_dropdown_item)
        self._track_dropdown_factory.connect("bind", self._bind_game_dropdown_item)
        self.game_dropdown.set_factory(self._track_dropdown_factory)
        self.game_dropdown.set_list_factory(self._track_dropdown_factory)
        self._style_dropdown_popover(self.game_dropdown)

    def _make_centered_factory(self, balance_arrow=False):
        factory = Gtk.SignalListItemFactory()

        def setup(_factory, item):
            label = Gtk.Label(xalign=0.5)
            label.set_halign(Gtk.Align.CENTER)
            label.set_hexpand(True)
            if balance_arrow:
                label.set_margin_start(24)
            label.add_css_class("mu-dd-label")
            item.set_child(label)

        def bind(_factory, item):
            obj = item.get_item()
            item.get_child().set_text(obj.get_string() if hasattr(obj, "get_string") else str(obj))

        factory.connect("setup", setup)
        factory.connect("bind", bind)
        return factory

    def _style_dropdown_popover(self, dropdown):
        child = dropdown.get_first_child()
        while child is not None:
            if isinstance(child, Gtk.Popover):
                child.add_css_class("mu-dd-popover")
                child.set_has_arrow(False)
                child.connect("show", lambda pop, dd=dropdown: pop.set_size_request(max(200, dd.get_width()), -1))
                return
            child = child.get_next_sibling()

    def _setup_game_dropdown_item(self, _factory, item):
        label = _label(ellipsize=True)
        label.set_margin_start(6)
        label.set_margin_end(6)
        label.set_margin_top(2)
        label.set_margin_bottom(2)
        item.set_child(label)

    def _bind_game_dropdown_item(self, _factory, item):
        obj = item.get_item()
        label = item.get_child()
        text = obj.get_string() if hasattr(obj, "get_string") else str(obj)
        label.set_text(text)
        note = text.startswith("Only music of provided games")
        item.set_selectable(not note)
        item.set_activatable(not note)
        label.set_sensitive(not note)
        if note:
            label.add_css_class("mu-dropdown-note")
        else:
            label.remove_css_class("mu-dropdown-note")

    def _enter(self, widget):
        widget.add_css_class("mu-enter")
        self._enter_widgets.append(widget)

    def _on_root_map(self, _widget):
        self._ensure_desktop_media()
        if getattr(self.root, "mukyu_warm", False):
            return
        self._ensure_engine()
        self._refresh_assigned_games()
        self._refresh_metadata_if_stale()
        if not self._intro_played:
            self._intro_played = True
            for index, widget in enumerate(self._enter_widgets):
                GLib.timeout_add(60 + index * 65, self._reveal, widget)
        self._update_game_position_timer()

    def _on_root_unmap(self, _widget):
        self._update_game_position_timer()

    def _reveal(self, widget):
        if self.root.get_mapped():
            widget.add_css_class("mu-in")
        return False

    def _retrigger(self, widget, base):
        flip = self._flips[(id(widget), base)] = not self._flips.get((id(widget), base), False)
        widget.remove_css_class(f"{base}-{'b' if flip else 'a'}")
        widget.add_css_class(f"{base}-{'a' if flip else 'b'}")

    def _animate_progress(self, target, ms=650):


        adjustment = self.progress.get_adjustment()
        if adjustment.get_upper() != 1.0 or adjustment.get_lower() != 0.0:
            self._progress_updating = True
            self.progress.set_range(0, 1)
            self._progress_updating = False
        if self._progress_tick:
            self.progress.remove_tick_callback(self._progress_tick)
            self._progress_tick = 0
        start = self.progress.get_value()
        if abs(target - start) < 0.005 or not self.progress.get_mapped():
            self.progress.set_value(target)
            return
        began = [None]

        def tick(widget, clock):
            now = clock.get_frame_time()
            if began[0] is None:
                began[0] = now
            t = min(1.0, (now - began[0]) / (ms * 1000.0))
            self._progress_updating = True
            widget.set_value(start + (target - start) * (1 - (1 - t) ** 3))
            self._progress_updating = False
            if t >= 1.0:
                self._progress_tick = 0
                return GLib.SOURCE_REMOVE
            return GLib.SOURCE_CONTINUE

        self._progress_tick = self.progress.add_tick_callback(tick)

    def play_holder_hover(self, on):
        if not hasattr(self, "play_holder"):
            return
        if on:
            self.play_holder.add_css_class("mu-play-hover")
        else:
            self.play_holder.remove_css_class("mu-play-hover")

    def _set_connecting(self, on):
        if on == self._connecting:
            return
        self._connecting = on
        if self._ring_off_timer:
            GLib.source_remove(self._ring_off_timer)
            self._ring_off_timer = 0
        if on:
            self.play_ring.add_css_class("mu-ring-spin")
            self.play_ring.add_css_class("mu-ring-on")
        else:
            self.play_ring.remove_css_class("mu-ring-on")
            self._ring_off_timer = GLib.timeout_add(300, self._stop_ring_spin)

    def _stop_ring_spin(self):
        self._ring_off_timer = 0
        self.play_ring.remove_css_class("mu-ring-spin")
        return False

    def _set_playing_ui(self, on):
        self._media_status = "Playing" if on else "Paused"
        self._media_changed()
        for widget in (self.play_btn, self.art_wrap):
            if on:
                widget.add_css_class("mu-playing")
            else:
                widget.remove_css_class("mu-playing")
        if hasattr(self, "play_holder"):
            if on:
                self.play_holder.add_css_class("mu-play-playing")
            else:
                self.play_holder.remove_css_class("mu-play-playing")
        if self.mode == "radio":
            self._animate_progress(1.0 if on else 0.0)
        else:
            self._update_game_position_timer()

    def _install_palette_provider(self):
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(display, self._palette_provider, PALETTE_PRIORITY)

    def _palette_mode(self):
        if self._theme_manager is not None:
            try:
                return self._theme_manager.effective_mode()
            except Exception:
                pass
        return "dark"

    def _apply_palette(self, rgb=None):
        self._last_rgb = rgb
        mode = self._palette_mode()
        palette = make_palette(*rgb, mode=mode) if rgb else palette_from_hue(0.86, mode)
        css = palette_css(palette).encode()
        if css != getattr(self, "_palette_css", None):
            self._palette_provider.load_from_data(css)
            self._palette_css = css

    def _on_launcher_appearance_changed(self):
        self._apply_palette(self._last_rgb)

    def _set_station_defaults(self):
        self.title_label.set_text("Gensokyo Radio")
        self.artist_label.set_text("Live radio")
        self.album_detail.set_text("Connecting to the station…")
        self.album_label.set_text("Gensokyo Radio  ·  LIVE")
        self.time_now.set_text("LIVE")
        self.time_total.set_text("LIVE")
        self._apply_palette()

    def _attach_player(self, player):
        self.player = player
        if self.player is None:
            self._set_error("GStreamer playbin is unavailable. Install GStreamer 1.0 plugins.")
            self.play_btn.set_sensitive(False)
            return
        self.player.set_property("uri", RADIO_URL)
        self.player.set_property("volume", 0.0 if self.muted else self.volume)
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_gst_message)
        self.player.connect("notify::volume", lambda *_: self._media_changed())
        self._media_changed()

    def _on_play_pause(self, button):
        if self.player is None:
            if not self._engine_ready_flag:

                self._after_engine.append(lambda: self._on_play_pause(button))
                self._ensure_engine()
            return
        self._retrigger(self.play_ripple, "mu-rip")
        if self.mode == "radio":
            if self.playing:
                self._pause_radio()
            else:
                self._start_radio()
            return
        if self._selected_track is None:
            return
        state = self.player.get_state(0)[1] if self.player is not None else Gst.State.NULL
        if self.playing and state == Gst.State.PLAYING:
            self.playing = False
            self.player.set_state(Gst.State.PAUSED)
            self._set_connecting(False)
            self._set_playing_ui(False)
        elif state == Gst.State.PAUSED:
            self.playing = True
            self.player.set_state(Gst.State.PLAYING)
            self._set_connecting(False)
            self._set_playing_ui(True)
        else:
            self._start_selected_game_track(resume=False)

    def _start_radio(self):
        self._cancel_reconnect()
        self._last_error = ""
        self.playing = True
        self._set_connecting(True)
        self._set_playing_ui(True)
        self._set_error("")
        GLib.timeout_add(60, self._begin_radio_playback)

    def _begin_radio_playback(self):
        if self.player is None or self.mode != "radio" or not self.playing:
            return False
        self.player.set_state(Gst.State.NULL)
        self.player.set_property("uri", RADIO_URL)
        self.player.set_property("volume", 0.0 if self.muted else self.volume)
        self.player.set_state(Gst.State.PLAYING)
        return False

    def _pause_radio(self):
        if self.player is None:
            return
        self._cancel_reconnect()
        self.playing = False
        self._set_connecting(False)
        self._set_playing_ui(False)
        GLib.timeout_add(80, self._end_player)

    def _end_player(self):
        if self.player is not None and not self.playing:
            self.player.set_state(Gst.State.NULL)
        return False

    def _cancel_reconnect(self):
        if self._reconnect_timer:
            GLib.source_remove(self._reconnect_timer)
            self._reconnect_timer = 0

    def _restart_stream_later(self):
        self._cancel_reconnect()
        self._set_connecting(True)
        self._reconnect_timer = GLib.timeout_add(RECONNECT_DELAY_MS, self._reconnect_stream)

    def _reconnect_stream(self):
        self._reconnect_timer = 0
        if self.player is None or self.mode != "radio" or not self.playing:
            return False
        self.player.set_state(Gst.State.NULL)
        self.player.set_property("uri", RADIO_URL)
        self.player.set_property("volume", 0.0 if self.muted else self.volume)
        self.player.set_state(Gst.State.PLAYING)
        return False

    def _stop_position_timer(self):
        if self._position_timer:
            GLib.source_remove(self._position_timer)
            self._position_timer = 0

    def _update_game_position_timer(self):
        should_run = self.mode == "game" and self.playing and self._selected_track is not None and (self.root.get_mapped() or self._repeat_mode == 2)
        if should_run and not self._position_timer:
            self._position_timer = GLib.timeout_add(POSITION_INTERVAL_MS, self._poll_game_position)
        elif not should_run:
            self._stop_position_timer()

    def _poll_game_position(self):
        self._position_timer = self._position_timer or 1
        if self.mode != "game" or not self.playing or self.player is None or self._selected_track is None:
            self._position_timer = 0
            return GLib.SOURCE_REMOVE
        ok, position = self.player.query_position(Gst.Format.TIME)
        if not ok:
            return GLib.SOURCE_CONTINUE
        seconds = max(0.0, position / Gst.SECOND)
        if self._repeat_mode == 2:
            if self._last_loop_position is not None and seconds + 0.1 < self._last_loop_position:
                if self._desktop_media is not None:
                    self._desktop_media.seeked(round(seconds * 1_000_000))
            self._last_loop_position = seconds
        track = self._selected_track


        if self._progress_dragging or time.monotonic() < self._seek_hold_until:
            return GLib.SOURCE_CONTINUE
        self._progress_updating = True
        self.progress.set_value(min(max(seconds, 0.0), max(track.duration, 0.01)))
        self._progress_updating = False
        self.time_now.set_text(_fmt(seconds))
        self.time_total.set_text(_fmt(track.duration))
        return GLib.SOURCE_CONTINUE

    def _on_progress_change_value(self, scale, _scroll, value):

        if self.mode != "game" or self._selected_track is None or self.player is None:
            return True
        if self.player.get_state(0)[1] not in (Gst.State.PAUSED, Gst.State.PLAYING):
            return True
        duration = max(self._selected_track.duration, 0.01)
        value = min(max(value, 0.0), duration)
        self._pending_seek = value
        self._seek_pending = True
        self.progress.set_value(value)
        self.time_now.set_text(_fmt(value))
        if not self._progress_dragging:

            if self._seek_timer:
                GLib.source_remove(self._seek_timer)
            self._seek_timer = GLib.timeout_add(60, self._perform_seek)
        return True

    def _on_progress_press(self, _controller, event):
        if self.progress.get_sensitive() and self.mode == "game":
            etype = event.get_event_type()
            if etype in (Gdk.EventType.BUTTON_PRESS, Gdk.EventType.TOUCH_BEGIN):
                self._progress_dragging = True
            elif etype == Gdk.EventType.BUTTON_RELEASE and self._progress_dragging:
                self._progress_dragging = False
                if self._seek_pending:
                    if self._seek_timer:
                        GLib.source_remove(self._seek_timer)
                    self._perform_seek()
            elif etype == Gdk.EventType.TOUCH_END or etype == Gdk.EventType.GRAB_BROKEN:
                if self._progress_dragging:
                    self._progress_dragging = False
                    if self._seek_pending:
                        self._perform_seek()
        return False

    def _loop_bounds(self):
        track = self._selected_track
        if self.mode != "game" or track is None or self._repeat_mode != 2:
            return None
        if 0 <= track.loop_start < track.loop_end <= track.duration + 0.05:
            return track.loop_start, min(track.loop_end, track.duration)
        if track.duration > 0:
            return 0.0, track.duration
        return None

    def _reset_loop(self):
        self._loop_seqnum = None
        self._loop_pending = False
        self._loop_attempted = False
        self._last_loop_position = None

    def _seek_to(self, seconds, flush=True, notify=True):
        if self.player is None or self.mode != "game" or self._selected_track is None:
            return False
        track = self._selected_track
        target = min(max(0.0, seconds), max(0.0, track.duration - 1 / track.sample_rate))
        bounds = self._loop_bounds()
        flags = Gst.SeekFlags.ACCURATE
        if flush:
            flags |= Gst.SeekFlags.FLUSH
        if bounds:
            start, end = bounds
            if target >= end:
                target = start
            flags |= Gst.SeekFlags.SEGMENT
            event = Gst.Event.new_seek(1.0, Gst.Format.TIME, flags,
                Gst.SeekType.SET, round(target * Gst.SECOND),
                Gst.SeekType.SET, round(end * Gst.SECOND))
        else:
            event = Gst.Event.new_seek(1.0, Gst.Format.TIME, flags,
                Gst.SeekType.SET, round(target * Gst.SECOND), Gst.SeekType.SET, -1)
        seqnum = event.get_seqnum()
        if not self.player.send_event(event):
            return False
        self._loop_seqnum = seqnum if bounds else None
        self._loop_pending = False
        if flush:
            self._last_loop_position = target
            self._seek_hold_until = time.monotonic() + 0.45
            self._progress_updating = True
            self.progress.set_value(target)
            self._progress_updating = False
            self.time_now.set_text(_fmt(target))
            if notify and self._desktop_media is not None:
                self._desktop_media.seeked(round(target * 1_000_000))
        return True

    def _configure_loop(self):
        if self.player is None or self.mode != "game" or self._selected_track is None:
            return
        state = self.player.get_state(0)[1]
        if state not in (Gst.State.PAUSED, Gst.State.PLAYING):
            return
        if self._loop_bounds() and not self._loop_attempted:
            self._loop_attempted = True
            ok, position = self.player.query_position(Gst.Format.TIME)
            self._seek_to(position / Gst.SECOND if ok else 0.0, notify=False)

    def _continue_loop(self):
        bounds = self._loop_bounds()
        if bounds and self.playing:
            if self.player.get_state(0)[1] != Gst.State.PLAYING:
                self._loop_pending = True
                return
            if not self._seek_to(bounds[0], flush=False, notify=False):
                if not self._seek_to(bounds[0]):
                    self._loop_seqnum = None
                    self._select_and_play_track(self._selected_track)

    def _perform_seek(self):
        self._seek_timer = 0
        if self._seek_pending:
            self._seek_pending = False
            self._seek_to(self._pending_seek)
        return False

    def _prepare_game_track_async(self, track):
        self._reset_loop()
        self._preparing_track_id = track.id
        self._media_changed()
        self._set_connecting(True)
        self.source_label.set_text("Preparing selected track…")
        generation = self._mode_change_generation

        def worker():
            try:
                cached = self._prepared_tracks.get(track.id)
                if cached and os.path.exists(cached):
                    path = cached
                else:
                    track_scratch = os.path.join(self._scratch_dir, re.sub(r"[^A-Za-z0-9._-]+", "_", track.id))
                    os.makedirs(track_scratch, exist_ok=True)
                    path, temporary = materialize_track(track, track_scratch)
                    if temporary:
                        self._prepared_tracks[track.id] = path
                GLib.idle_add(self._on_game_track_ready, track, path, generation)
            except Exception as exc:
                GLib.idle_add(self._on_game_track_prepare_failed, track, str(exc), generation)

        threading.Thread(target=worker, daemon=True, name="game-bgm-prepare").start()

    def _start_selected_game_track(self, resume=False):
        track = self._selected_track
        if track is None:
            return
        if self.player is None:
            if not self._engine_ready_flag:
                self._after_engine.append(lambda: self._start_selected_game_track(resume))
                self._ensure_engine()
            return
        cached = self._prepared_tracks.get(track.id)
        if not resume and cached and os.path.exists(cached):
            self._on_game_track_ready(track, cached, self._mode_change_generation)
            return
        if not resume and track.source_kind == "file":
            self._on_game_track_ready(track, track.source_path, self._mode_change_generation)
            return
        self._prepare_game_track_async(track)

    def _on_game_track_ready(self, track, path, generation):
        if generation != self._mode_change_generation or self.mode != "game" or self._selected_track is not track:
            return False
        self._preparing_track_id = None
        self._reset_loop()
        self._set_connecting(False)
        self.playing = True
        self._set_playing_ui(True)
        self._set_error("")
        self.player.set_state(Gst.State.NULL)
        self.player.set_property("uri", Gio.File.new_for_path(path).get_uri())
        self.player.set_property("volume", 0.0 if self.muted else self.volume)
        self.player.set_state(Gst.State.PAUSED if self._loop_bounds() else Gst.State.PLAYING)
        self._update_game_position_timer()
        self._evict_prepared_tracks(track.id)
        return False

    def _evict_prepared_tracks(self, current_id):


        cache = self._prepared_tracks
        if current_id in cache:
            cache[current_id] = cache.pop(current_id)
        sizes = {}
        total = 0
        for track_id, cached_path in list(cache.items()):
            try:
                size = os.path.getsize(cached_path)
            except OSError:
                cache.pop(track_id, None)
                continue
            sizes[track_id] = size
            total += size
        for track_id in list(cache):
            if total <= PREPARED_CACHE_BYTES or track_id == current_id:
                break
            cached_path = cache.pop(track_id, None)
            total -= sizes.get(track_id, 0)
            if cached_path:
                try:
                    os.remove(cached_path)
                except OSError:
                    pass

    def _on_game_track_prepare_failed(self, track, message, generation):
        if generation != self._mode_change_generation or self.mode != "game" or self._selected_track is not track:
            return False
        self._preparing_track_id = None
        self.playing = False
        self._set_connecting(False)
        self._set_playing_ui(False)
        self._set_error(f"Could not prepare {self._track_title(track)}: {message}")
        self._media_status = "Stopped"
        self._media_changed()
        return False

    def _on_stream_live(self):
        if self.mode == "radio" and self.playing:
            self._set_connecting(False)
            self._set_error("")
        elif self.mode == "game" and self.playing:
            self._set_connecting(False)
            self._set_error("")
        return False

    def _on_gst_message(self, _bus, message):
        mtype = message.type
        if mtype in (Gst.MessageType.STATE_CHANGED, Gst.MessageType.ASYNC_DONE, Gst.MessageType.EOS, Gst.MessageType.ERROR):
            self._media_changed()
        if mtype == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            if self.mode == "radio":
                self._set_error(f"Gensokyo Radio may be temporarily down. Radio playback error: {error.message}")
                self._last_error = debug or error.message
                if self.playing:
                    self._restart_stream_later()
            else:
                title = self._track_title(self._selected_track) if self._selected_track else "the selected track"
                self.playing = False
                self._set_connecting(False)
                self._set_playing_ui(False)
                self._set_error(f"Could not play {title}: {error.message}")
                self._media_status = "Stopped"
        elif mtype == Gst.MessageType.ASYNC_DONE:
            self._configure_loop()
            if self.playing and self.mode == "game" and self.player.get_state(0)[1] == Gst.State.PAUSED:
                self.player.set_state(Gst.State.PLAYING)
        elif mtype == Gst.MessageType.SEGMENT_DONE:
            if self._loop_seqnum is not None and self._loop_bounds():
                if self.playing:
                    self._continue_loop()
                else:
                    self._loop_pending = True
        elif mtype == Gst.MessageType.EOS:
            if self.mode == "radio":
                if self.playing:
                    self._restart_stream_later()
            elif self.playing and self._selected_track is not None:
                self._advance_track(auto=True)
        elif mtype == Gst.MessageType.STATE_CHANGED:
            if message.src == self.player:
                _old, new, _pending = message.parse_state_changed()
                if new == Gst.State.PLAYING:
                    if self._loop_pending:
                        self._continue_loop()
                    self._configure_loop()
                    GLib.idle_add(self._on_stream_live)
        elif mtype == Gst.MessageType.TAG and self.mode == "radio":
            taglist = message.parse_tag()
            title = taglist.get_string("title")
            if title:
                GLib.idle_add(lambda t=title: (self._apply_stream_title(t) or False))

    def _apply_stream_title(self, title):
        if self.mode == "radio" and self.current["title"] in ("Gensokyo Radio", "Connecting…"):
            self.title_label.set_text(title)
            self.current["title"] = title
            self._media_changed()
        return False

    def _shutdown_player(self):
        if self._media_closed:
            return
        self._media_closed = True
        self._mode_change_generation += 1
        self._stop_position_timer()
        if self._desktop_media is not None:
            self._desktop_media.close()
        try:
            player = getattr(self, "player", None)
            if player is not None:
                bus = player.get_bus()
                if bus is not None:
                    bus.remove_signal_watch()
                player.set_state(Gst.State.NULL)
        except Exception:
            pass
        try:
            shutil.rmtree(self._scratch_dir, ignore_errors=True)
        except Exception:
            pass

    def _start_metadata_polling(self):
        if self._metadata_timer:
            return
        self._metadata_timer = GLib.timeout_add(METADATA_INTERVAL_MS, self._poll_now_playing)
        self._poll_now_playing()

    def _refresh_metadata_if_stale(self):


        if self.mode != "radio":
            return
        if time.monotonic() - self._last_metadata_at < METADATA_INTERVAL_MS / 1000.0:
            return
        self._poll_skip = 0
        self._poll_now_playing()

    def _poll_now_playing(self):
        if self.mode != "radio" or self._metadata_request_in_flight:
            return True
        if self._metadata_generation > 0 and not self.playing and not self.root.get_mapped():
            return True
        if self._poll_skip > 0:
            self._poll_skip -= 1
            return True
        self._metadata_request_in_flight = True
        generation = self._metadata_generation = self._metadata_generation + 1

        def worker():
            try:
                payload = _fetch_json(NOW_PLAYING_URL)
                GLib.idle_add(self._apply_now_playing, payload, generation)
            except Exception as exc:
                GLib.idle_add(self._metadata_failed, str(exc), generation)

        threading.Thread(target=worker, daemon=True, name="gensokyo-now-playing").start()
        return True

    def _apply_now_playing(self, payload, generation):
        self._metadata_request_in_flight = False
        if generation != self._metadata_generation or self.mode != "radio":
            return False
        songinfo = payload.get("SONGINFO") if isinstance(payload, dict) else None
        misc = payload.get("MISC") if isinstance(payload, dict) else None
        if not isinstance(songinfo, dict):
            songinfo = {}
        if not isinstance(misc, dict):
            misc = {}
        title = _first_value(songinfo, ("TITLE",), ("title",)) or "Gensokyo Radio"
        artist = _first_value(songinfo, ("ARTIST",), ("artist",)) or "Live radio"
        album = _first_value(songinfo, ("ALBUM",), ("album",)) or "Gensokyo Radio"
        circle = _first_value(songinfo, ("CIRCLE",), ("circle",)) or ""
        year = _first_value(songinfo, ("YEAR",), ("year",)) or ""
        art = _first_value(misc, ("ALBUMART",), ("album_art",), ("albumart",)) or ""
        track_changed = (str(title), str(artist)) != (self.current["title"], self.current["artist"])
        self.current.update({
            "title": str(title),
            "artist": str(artist),
            "album": str(album),
            "circle": str(circle),
            "year": str(year),
            "album_art": str(art),
        })
        self._media_changed()
        self.title_label.set_text(self.current["title"])
        self.artist_label.set_text(self.current["artist"])
        detail = self.current["album"]
        if circle:
            detail += f"  ·  {circle}"
        if year:
            detail += f"  ·  {year}"
        self.album_detail.set_text(detail)
        self.album_label.set_text("Gensokyo Radio  ·  LIVE")
        self.time_now.set_text("LIVE")
        self.time_total.set_text("LIVE")
        self._set_error("")
        self._metadata_failures = 0
        self._last_metadata_at = time.monotonic()
        self._poll_skip = 0
        if track_changed:
            self._retrigger(self.info_box, "mu-swap")
        self._load_album_art(art)
        self._schedule_song_end_poll(payload)
        return False

    def _schedule_song_end_poll(self, payload):
        if self._song_end_timer:
            GLib.source_remove(self._song_end_timer)
            self._song_end_timer = 0
        try:
            times = payload.get("SONGTIMES") if isinstance(payload, dict) else None
            remaining = float(_first_value(times, ("REMAINING",), ("remaining",))) if isinstance(times, dict) else 0.0
        except (TypeError, ValueError):
            return
        if remaining < 4 or remaining > 900:
            return
        delay_ms = int((remaining + 1.5) * 1000)

        def fire():
            self._song_end_timer = 0
            if self.mode == "radio":
                self._poll_skip = 0
                self._poll_now_playing()
            return False

        self._song_end_timer = GLib.timeout_add(delay_ms, fire)

    def _metadata_failed(self, message, generation):
        self._metadata_request_in_flight = False
        if generation != self._metadata_generation or self.mode != "radio":
            return False
        self._metadata_failures += 1
        self._poll_skip = min(6, self._metadata_failures * 2)
        if self._metadata_failures >= 4 and not self.playing:
            self.album_detail.set_text("Unable to read live song information")
            self._set_error("Gensokyo Radio may be temporarily down or busy. Retrying…")
        return False

    def _album_art_urls(self, album_art):

        if not album_art:
            return [GR_LOGO_URL]
        if album_art.startswith("http://") or album_art.startswith("https://"):
            return [album_art]
        name = urllib.parse.quote(album_art.lstrip("/"))
        base = "https://gensokyoradio.net/images/albums/"
        return [base + "original/" + name, base + "500/" + name]

    def _album_art_url(self, album_art):
        return self._album_art_urls(album_art)[0]

    def _load_album_art(self, album_art):
        self._local_art_identity = None
        url = self._album_art_url(album_art)
        if url == self._last_art_url:
            return
        self._last_art_url = url
        self._media_changed()
        self._art_generation += 1
        generation = self._art_generation

        candidates = self._album_art_urls(album_art)

        def worker():
            for candidate in candidates + [GR_LOGO_URL]:
                try:
                    data = _fetch_bytes(candidate)
                    pixbuf, rgb = _prepare_cover_bytes(data)
                except Exception:
                    continue
                GLib.idle_add(self._apply_art, pixbuf, rgb, generation)
                return

        threading.Thread(target=worker, daemon=True, name="gensokyo-album-art").start()

    def _load_local_art(self, game_key):
        normalized = game_key.replace(".", "")
        path = os.path.join(COVER_DIR, normalized + ".jpg")
        self._last_art_url = None
        self._art_generation += 1
        generation = self._art_generation
        try:
            stat = os.stat(path)
            identity = (path, stat.st_size, stat.st_mtime_ns)
        except OSError:
            self._set_placeholder_art(generation)
            return
        if identity == self._local_art_identity and self.art_picture.get_paintable() is not None:
            self._retrigger(self.art_frame, "mu-artswap")
            return
        def worker():
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)

                w, h = pixbuf.get_width(), pixbuf.get_height()
                side = min(w, h)
                pixbuf = pixbuf.new_subpixbuf((w - side) // 2, (h - side) // 2, side, side)
                if side > COVER_PX:
                    pixbuf = pixbuf.scale_simple(COVER_PX, COVER_PX, GdkPixbuf.InterpType.BILINEAR)
                else:
                    pixbuf = pixbuf.copy()
                tiny = pixbuf.scale_simple(32, 32, GdkPixbuf.InterpType.BILINEAR)
                rgb = dominant_rgb(tiny.get_pixels(), 32, 32, tiny.get_n_channels(), tiny.get_rowstride())
                GLib.idle_add(self._apply_art, pixbuf, rgb, generation, identity)
            except Exception:
                GLib.idle_add(self._set_placeholder_art, generation)
        threading.Thread(target=worker, daemon=True, name="game-bgm-art").start()

    def _set_placeholder_art(self, generation=None):
        if generation is not None and generation != self._art_generation:
            return False
        self._local_art_identity = None
        self.art_picture.set_paintable(None)
        self.art_placeholder.set_visible(True)
        self._apply_palette()
        return False

    def _load_station_art(self):
        self._load_album_art("")

    def _apply_art(self, pixbuf, rgb, generation=None, local_identity=None):
        if generation is not None and generation != self._art_generation:
            return False
        try:
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            self.art_picture.set_paintable(texture)
            self._local_art_identity = local_identity
            self.art_placeholder.set_visible(False)
            self._apply_palette(rgb)
            self._retrigger(self.art_frame, "mu-artswap")
        except Exception:
            pass
        return False

    def _set_error(self, message):
        if message:
            self.source_label.set_text(message)
            self.source_label.add_css_class("mu-error")
        elif self.mode == "radio":
            self.source_label.set_text("Audio from Gensokyo Radio  ·  128 kbps MP3")
            self.source_label.remove_css_class("mu-error")
        else:
            self.source_label.set_text("Audio from your provided game files  ·  local playback")
            self.source_label.remove_css_class("mu-error")

    def _on_mode_changed(self, dropdown, _param):
        selected = dropdown.get_selected()
        new_mode = "game" if selected == 0 else "radio"
        if new_mode == self.mode:
            return
        self._mode_change_generation += 1
        self.mode = new_mode
        self._media_status = "Stopped"
        self._media_changed()
        self._favorites_view = False
        self._apply_mode_visibility()
        self._retrigger(self.info_box, "mu-swap")
        self._retrigger(self.art_frame, "mu-artswap")
        GLib.timeout_add(40, self._finish_mode_change, self._mode_change_generation)

    def _finish_mode_change(self, generation):
        if generation != self._mode_change_generation:
            return False
        self._stop_current_playback()
        if self.mode == "radio":
            self._set_station_defaults()
            self._last_art_url = None
            self.current.update({"title": "", "artist": "", "album": "", "circle": "", "year": "", "album_art": ""})
            self._load_station_art()
            self._set_game_controls_enabled(False)
            self._selected_track = None
            self._progress_updating = True
            self.progress.set_range(0, 1)
            self.progress.set_value(0)
            self._progress_updating = False
            if self._metadata_timer:
                self._poll_now_playing()
            else:
                self._start_metadata_polling()
        else:
            self._set_game_defaults()
            self._refresh_assigned_games(render=True)
        return False

    def _set_game_defaults(self):
        self._set_error("")
        self._selected_track = None
        self.title_label.set_text("Game BGM")
        self.artist_label.set_text("Choose a game and track")
        self.album_detail.set_text("Your assigned game files stay on your device")
        self.album_label.set_text("Game BGM")
        self.time_now.set_text("0:00")
        self.time_total.set_text("0:00")
        self.progress.set_range(0, 1)
        self.progress.set_value(0)
        self.progress.set_sensitive(False)
        self._set_game_controls_enabled(False)

    def _apply_mode_visibility(self):
        game = self.mode == "game"
        self.track_revealer.set_reveal_child(game)
        if game:
            self.track_revealer.add_css_class("mu-shown")
        else:
            self.track_revealer.remove_css_class("mu-shown")
        if game:
            self.player_column.add_css_class("mu-player-column-game")
        else:
            self.player_column.remove_css_class("mu-player-column-game")
        self.player_column.set_halign(Gtk.Align.CENTER)
        self.body.set_spacing(0)
        if self.player is not None:
            self.player.set_property("volume", 0.0 if self.muted else self.volume)

    def _stop_current_playback(self):
        self._reset_loop()
        self._preparing_track_id = None
        self.playing = False
        self._cancel_reconnect()
        self._stop_position_timer()
        self._set_connecting(False)
        self._set_playing_ui(False)
        if self.player is not None:
            self.player.set_state(Gst.State.NULL)
        if self._seek_timer:
            GLib.source_remove(self._seek_timer)
            self._seek_timer = 0
        self._seek_pending = False
        self._progress_dragging = False

    def _refresh_assigned_games(self, render=False):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
            else:
                raw = {}
        except (OSError, json.JSONDecodeError):
            raw = {}
        config = {}
        for key, value in raw.items():
            if isinstance(value, str):
                config[key] = {"exe": value}
            elif isinstance(value, dict):
                config[key] = value
        assigned = assigned_games(config)
        signature = tuple((g["key"], g["path"], g.get("pc98_music_room")) for g in assigned)
        changed = signature != self._assigned_signature
        self._assigned = assigned
        if changed:
            self._assigned_signature = signature
            wanted = {g["key"]: (g["path"], g.get("pc98_music_room")) for g in assigned}
            for key in list(self._game_tracks):
                if self._game_paths.get(key) != wanted.get(key):
                    self._game_tracks.pop(key, None)
            self._game_paths = wanted
            self._rebuild_game_dropdown()
            if self._selected_game is not None and self._selected_game["key"] not in wanted:
                self._selected_game = None
                if self.mode == "game":
                    self._stop_current_playback()
                    self._selected_track = None
            render = True
            self._schedule_prefetch()
        self._update_favorites_nav()
        if render and self.mode == "game":
            if self._assigned:
                self._on_game_dropdown_changed(self.game_dropdown, None)
            else:
                self._render_tracks([], message="Only music of provided games will be available")

    def _rebuild_game_dropdown(self):
        store = Gio.ListStore.new(Gtk.StringObject)
        if not self._assigned:
            store.append(Gtk.StringObject.new("Only music of provided games will be available"))
        for game in self._assigned:
            store.append(Gtk.StringObject.new(game["title"]))
        index = 0
        if self._selected_game is not None:
            for i, game in enumerate(self._assigned):
                if game["key"] == self._selected_game["key"]:
                    index = i
                    break
        self.game_dropdown.handler_block(self._game_dd_handler)
        try:
            self.game_dropdown.set_model(store)
            self.game_dropdown.set_selected(index)
        finally:
            self.game_dropdown.handler_unblock(self._game_dd_handler)

    def _on_game_dropdown_changed(self, dropdown, _param):
        if self.mode != "game" or not self._assigned:
            return
        index = dropdown.get_selected()
        if index < 0 or index >= len(self._assigned):
            return
        game = self._assigned[index]
        self._favorites_view = False
        self._selected_game = game
        self.album_label.set_text("Game BGM")
        self._render_game_tracks(game)

    def _schedule_prefetch(self):
        if self._prefetch_timer:
            GLib.source_remove(self._prefetch_timer)
        self._prefetch_timer = GLib.timeout_add(1200, self._prefetch_games)

    def _prefetch_games(self):
        self._prefetch_timer = 0
        for game in self._assigned:
            self._request_scan(game)
        return False

    def _request_scan(self, game, urgent=False):
        key = game["key"]
        if key in self._game_tracks:
            return
        start_thread = False
        with self._scan_lock:
            if key in self._scanning:
                if urgent:
                    for queued in list(self._scan_queue):
                        if queued["key"] == key:
                            self._scan_queue.remove(queued)
                            self._scan_queue.appendleft(queued)
                            break
                return
            self._scanning.add(key)
            if urgent:
                self._scan_queue.appendleft(game)
            else:
                self._scan_queue.append(game)
            if not self._scan_running:
                self._scan_running = True
                start_thread = True
        if start_thread:
            threading.Thread(target=self._scan_worker, daemon=True, name="game-bgm-scan").start()

    def _scan_worker(self):
        while True:
            with self._scan_lock:
                if not self._scan_queue:
                    self._scan_running = False
                    return
                game = self._scan_queue.popleft()
            try:
                tracks, error = discover_tracks(game, self._scratch_dir)
            except Exception as exc:
                tracks, error = [], str(exc)
            GLib.idle_add(self._on_tracks_discovered, game, tracks, error)

    def _render_game_tracks(self, game):
        key = game["key"]
        if key in self._game_tracks:
            self._show_game_track_selection(game, self._game_tracks[key])
            return
        if self._selected_track is None:
            self.title_label.set_text("Game BGM")
            self.artist_label.set_text(game["title"])
            self.album_detail.set_text("Reading game music…")
            self._set_game_controls_enabled(False)
            self._load_local_art(key)
        self._render_tracks([], loading=True)
        self._retrigger(self.track_list, "mu-swap")
        self._request_scan(game, urgent=True)

    def _on_tracks_discovered(self, game, tracks, error):
        self._media_changed()
        key = game["key"]
        with self._scan_lock:
            self._scanning.discard(key)
        if self._game_paths.get(key) != (game["path"], game.get("pc98_music_room")):

            current = next((g for g in self._assigned if g["key"] == key), None)
            if current:
                self._request_scan(current, urgent=True)
            return False
        if tracks:
            self._game_tracks[key] = tracks
        if self.mode == "game" and self._selected_game and self._selected_game["key"] == key and not self._favorites_view:
            self._show_game_track_selection(game, tracks, error)
            self._retrigger(self.track_list, "mu-swap")
        self._update_favorites_nav()
        return False

    def _show_game_track_selection(self, game, tracks, error=""):
        if error and not tracks:
            self._render_tracks([], message=error)
            if self._selected_track is None:
                self.title_label.set_text("Game BGM")
                self.artist_label.set_text(game["title"])
                self.album_detail.set_text(error)
                self._set_game_controls_enabled(False)
                self._load_local_art(game["key"])
            return
        self._render_tracks(tracks)
        if self._selected_track is None:
            self.title_label.set_text("Game BGM")
            self.artist_label.set_text(game["title"])
            self.album_detail.set_text(f"{len(tracks)} track{'s' if len(tracks) != 1 else ''} available")
            self._load_local_art(game["key"])
            self._set_game_controls_enabled(False)

    def _clear_track_list(self):
        self._rendered_tracks = ()
        child = self.track_list.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.track_list.remove(child)
            child = next_child

    def _refresh_track_selection(self):
        selected_id = self._selected_track.id if self._selected_track is not None else None
        row = self.track_list.get_first_child()
        while row is not None:
            if hasattr(row, "track"):
                active = row.track.id == selected_id
                if active:
                    row.add_css_class("mu-track-row-active")
                else:
                    row.remove_css_class("mu-track-row-active")
                row.title_label.set_playing(active)
            row = row.get_next_sibling()

    def _render_tracks(self, tracks, loading=False, message=""):
        if tracks and not loading and len(tracks) == len(self._rendered_tracks) and all(
            old is new for old, new in zip(self._rendered_tracks, tracks)
        ):
            self._refresh_track_selection()
            return
        self._clear_track_list()
        if loading:
            row = Gtk.ListBoxRow()
            row.set_selectable(False)
            row.set_activatable(False)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
            box.set_halign(Gtk.Align.CENTER)
            box.set_valign(Gtk.Align.CENTER)
            box.set_margin_top(48)
            box.set_margin_bottom(48)
            box.append(LoadingIndicator(64))
            label = _label("mu-track-empty", xalign=0.5, ellipsize=False)
            label.set_text("Loading songs…")
            box.append(label)
            row.set_child(box)
            self.track_list.append(row)
            return
        if not tracks:
            self.track_empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            self.track_empty.set_halign(Gtk.Align.CENTER)
            self.track_empty.set_valign(Gtk.Align.CENTER)
            self.track_empty.set_margin_top(40)
            self.track_empty.set_margin_bottom(40)
            icon = _image("audio-x-generic-symbolic", 34)
            icon.set_opacity(0.5)
            self.track_empty.append(icon)
            label = _label("mu-track-empty", xalign=0.5, ellipsize=False)
            label.set_text(message or "No game music is available")
            label.set_wrap(True)
            label.set_max_width_chars(34)
            self.track_empty.append(label)
            self.track_list.append(self.track_empty)
            return
        for index, track in enumerate(tracks):
            self.track_list.append(self._make_track_row(track, index + 1))
        self._rendered_tracks = tuple(tracks)
        self.track_empty = None

    def _track_title(self, track):
        return display_title(track, self._title_language)

    def _on_title_language_toggled(self, button, language):
        if not button.get_active() or language == self._title_language:
            return
        self._title_language = language


        row = self.track_list.get_first_child()
        while row is not None:
            if hasattr(row, "track") and hasattr(row, "title_label"):
                row.title_label.set_text(self._track_title(row.track))
            row = row.get_next_sibling()
        if self.mode == "game" and self._selected_track is not None:
            self.title_label.set_text(self._track_title(self._selected_track))
        self._media_changed()
        try:
            save_title_language(MUSIC_PREFS_FILE, language)
        except OSError:
            self._set_error("Could not save the song title language preference.")

    def _make_track_row(self, track, number):
        row = Gtk.ListBoxRow()
        row.add_css_class("mu-track-row")
        row.set_activatable(True)
        row.set_selectable(False)
        row.track = track
        content = Gtk.Box(spacing=12)
        content.set_margin_start(10)
        content.set_margin_end(8)
        content.set_margin_top(8)
        content.set_margin_bottom(8)
        number_label = _label("mu-track-number", xalign=1.0, ellipsize=False)
        number_label.set_text(str(number))
        number_label.set_size_request(28, -1)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        title_box.set_hexpand(True)
        title = MarqueeLabel("mu-track-title")
        title.set_text(self._track_title(track))
        row.title_label = title
        subtitle = _label("mu-track-subtitle")
        subtitle.set_text(_fmt(track.duration))
        title_box.append(title)
        title_box.append(subtitle)
        favorite = Gtk.ToggleButton()
        favorite.set_focus_on_click(False)
        favorite.add_css_class("mu-track-favorite")
        favorite.set_child(_image("starred-symbolic" if track.id in self._favorites else "non-starred-symbolic", 18))
        favorite.set_active(track.id in self._favorites)
        favorite.connect("toggled", self._on_favorite_toggled, track)
        content.append(number_label)
        content.append(title_box)
        content.append(favorite)
        row.set_child(content)
        selected_id = self._selected_track.id if self._selected_track is not None else None
        if selected_id is not None and track.id == selected_id:
            row.add_css_class("mu-track-row-active")
            title.set_playing(True)
        hover = Gtk.EventControllerMotion()
        hover.connect("enter", lambda *_: title.set_hover(True))
        hover.connect("leave", lambda *_: title.set_hover(False))
        row.add_controller(hover)
        return row

    def _on_track_row_activated(self, _listbox, row):
        track = getattr(row, "track", None)
        if track is None:
            return
        self._selected_track = track
        self._game_index = self._current_track_list().index(track) if track in self._current_track_list() else -1
        self._update_game_track_ui()
        self._load_local_art(track.game_key)
        self._start_selected_game_track(resume=False)
        self._render_tracks(self._current_track_list())

    def _current_track_list(self):
        if self._favorites_view:
            return self._favorite_tracks()
        return self._game_tracks.get(self._selected_game["key"], []) if self._selected_game else []

    def _playback_track_list(self):
        if self._favorites_view:
            return self._favorite_tracks()
        if self._selected_track is not None:
            return self._game_tracks.get(self._selected_track.game_key, [])
        return self._current_track_list()

    def _update_game_track_ui(self):
        self._media_changed()
        track = self._selected_track
        if track is None:
            self._set_game_controls_enabled(False)
            return
        self.title_label.set_text(self._track_title(track))
        self.artist_label.set_text(track.game_title)
        self.album_detail.set_text(track.filename)
        self._seek_hold_until = 0.0
        self._seek_pending = False
        self._progress_dragging = False
        self.progress.set_range(0, max(track.duration, 0.01))
        self.progress.set_sensitive(True)
        self._progress_updating = True
        self.progress.set_value(0)
        self._progress_updating = False
        self.time_now.set_text("0:00")
        self.time_total.set_text(_fmt(track.duration))
        self.album_label.set_text("Game BGM")
        self._set_error("")
        self._set_game_controls_enabled(True)
        self._retrigger(self.info_box, "mu-swap")

    def _favorite_tracks(self):
        result = []
        for game in self._assigned:
            tracks = self._game_tracks.get(game["key"], [])
            for track in tracks:
                if track.id in self._favorites:
                    result.append(track)
        return result

    def _update_favorites_nav(self):
        show = bool(self._favorite_tracks())
        if show:
            self.favorites_revealer.set_visible(True)
        self.favorites_revealer.set_reveal_child(show)
        if show:
            self.favorites_nav.add_css_class("mu-fav-in")
        else:
            self.favorites_nav.remove_css_class("mu-fav-in")

    def _on_favorite_toggled(self, button, track):
        self._media_changed()
        active = button.get_active()
        if active:
            self._favorites.add(track.id)
        else:
            self._favorites.discard(track.id)
        child = button.get_child()
        if isinstance(child, Gtk.Image):
            child.set_from_icon_name("starred-symbolic" if active else "non-starred-symbolic")
            if active:
                self._retrigger(child, "mu-star")
        try:
            _save_favorite_data(self._favorites)
        except OSError:
            pass
        self._update_favorites_nav()
        if self._favorites_view:
            self._render_tracks(self._favorite_tracks())

    def _on_favorites_nav(self, _button):
        self._media_changed()
        tracks = self._favorite_tracks()
        if self._favorites_view:
            self._favorites_view = False
            if self._selected_game:
                self._render_tracks(self._game_tracks.get(self._selected_game["key"], []))
        else:
            self._favorites_view = True
            self._render_tracks(tracks, message="Favorite songs from your assigned games")
        self._update_favorites_nav()

    def _set_game_controls_enabled(self, enabled):
        has_track = bool(enabled and self.mode == "game" and self._selected_track is not None)
        for widget in (self.shuffle_btn, self.prev_btn, self.next_btn, self.repeat_btn):
            widget.set_sensitive(has_track)
        self.play_btn.set_sensitive(has_track or self.mode == "radio")
        self.progress.set_sensitive(has_track)
        self._update_favorites_nav()
        if self.mode == "radio":
            for widget in (self.shuffle_btn, self.prev_btn, self.next_btn, self.repeat_btn):
                widget.set_sensitive(False)
            self.progress.set_sensitive(False)

    def _on_control_clicked(self, button):
        self._retrigger(button, "mu-control-pulse")

    def _on_shuffle(self, button):
        if self.mode != "game":
            return
        self._shuffle = not self._shuffle
        if self._shuffle:
            button.add_css_class("mu-active")
        else:
            button.remove_css_class("mu-active")
        self._media_changed()

    def _on_repeat(self, button):
        if self.mode != "game":
            return
        self._set_repeat_mode(0 if self._repeat_mode else 2)

    def _set_repeat_mode(self, mode):
        if self.mode != "game" or mode == self._repeat_mode:
            return
        self._repeat_mode = mode
        button = self.repeat_btn
        button.remove_css_class("mu-active")
        button.remove_css_class("mu-repeat-one")
        if self._repeat_mode == 1:
            button.add_css_class("mu-active")
        elif self._repeat_mode == 2:
            button.add_css_class("mu-active")
            button.add_css_class("mu-repeat-one")
        had_segment = self._loop_seqnum is not None
        self._reset_loop()
        if self._repeat_mode == 2:
            self._configure_loop()
        elif had_segment and self.player is not None:
            ok, position = self.player.query_position(Gst.Format.TIME)
            if ok:
                self._seek_to(position / Gst.SECOND, notify=False)
        self._update_game_position_timer()
        self._media_changed()

    def _on_previous(self, _button):
        if self.mode != "game" or self._selected_track is None:
            return
        ok, position = self.player.query_position(Gst.Format.TIME) if self.player else (False, 0)
        if ok and position / Gst.SECOND > 3:
            self._seek_to(0.0)
            return
        tracks = self._playback_track_list()
        if not tracks:
            return
        index = tracks.index(self._selected_track) if self._selected_track in tracks else 0
        next_index = (index - 1) % len(tracks)
        self._select_and_play_track(tracks[next_index])

    def _on_next(self, _button):
        if self.mode == "game":
            self._advance_track(auto=False)

    def _advance_track(self, auto=False):
        if self.mode != "game":
            return
        tracks = self._playback_track_list()
        if not tracks:
            self._stop_current_playback()
            return
        if auto and self._repeat_mode == 2:
            bounds = self._loop_bounds()
            if not bounds or not self._seek_to(bounds[0]):
                self._select_and_play_track(self._selected_track)
            return
        if self._shuffle and len(tracks) > 1:
            choices = [track for track in tracks if track is not self._selected_track]
            track = self._shuffle_rng.choice(choices)
        else:
            index = tracks.index(self._selected_track) if self._selected_track in tracks else -1
            next_index = index + 1
            if next_index >= len(tracks):
                if self._repeat_mode == 1:
                    next_index = 0
                else:
                    self._stop_current_playback()
                    return
            track = tracks[next_index]
        self._select_and_play_track(track)

    def _select_and_play_track(self, track):
        self._selected_track = track
        tracks = self._playback_track_list()
        self._game_index = tracks.index(track) if track in tracks else -1
        self._update_game_track_ui()
        self._load_local_art(track.game_key)
        if not self._favorites_view and self._selected_game and self._selected_game["key"] == track.game_key:
            self._render_tracks(self._current_track_list())
        elif self._favorites_view and track in self._favorite_tracks():
            self._render_tracks(self._favorite_tracks())
        self._start_selected_game_track(resume=False)


def create_music_page(theme_manager=None):
    return MusicPage(theme_manager).root
