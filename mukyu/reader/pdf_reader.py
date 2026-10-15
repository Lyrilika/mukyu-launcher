import json
import os
import time

from gi.repository import Gtk, Gdk, GLib, Pango

from mukyu.platform_compat import data_home, trim_memory
from mukyu.reader.pdf_backend import PdfWorker

PROGRESS_FILE = os.path.join(
    data_home(),
    'mukyulauncher',
    'reading_progress.json',
)

UI_HIDE_MS = 2600
TICK_MS = 120
CACHE_RADIUS = 3
CACHE_BUDGET = 128 * 1024 * 1024
SCROLL_COOLDOWN = 0.16
EDGE_ZONE = 0.25

KEYS_NEXT = {Gdk.KEY_Right, Gdk.KEY_Down, Gdk.KEY_Page_Down, Gdk.KEY_KP_Right, Gdk.KEY_KP_Down,
             Gdk.KEY_KP_Page_Down, Gdk.KEY_space, Gdk.KEY_Return, Gdk.KEY_KP_Enter}
KEYS_PREV = {Gdk.KEY_Left, Gdk.KEY_Up, Gdk.KEY_Page_Up, Gdk.KEY_KP_Left, Gdk.KEY_KP_Up,
             Gdk.KEY_KP_Page_Up, Gdk.KEY_BackSpace}


def _load_progress():
    try:
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_progress(key, page_number):
    try:
        data = _load_progress()
        data[key] = int(page_number)
        os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
        tmp = PROGRESS_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, PROGRESS_FILE)
    except OSError:
        pass


def _icon_button(icon_name, css_class, accessible_name, pixel_size=22):
    image = Gtk.Image.new_from_icon_name(icon_name)
    image.set_pixel_size(pixel_size)
    button = Gtk.Button()
    button.set_child(image)
    button.add_css_class(css_class)
    button.update_property([Gtk.AccessibleProperty.LABEL], [accessible_name])
    button.set_focusable(False)
    return button


class PdfReader(Gtk.Window):
    def __init__(self, parent, title, path, progress_key):
        super().__init__(title=title)
        if parent is not None:
            self.set_transient_for(parent)
        self.set_default_size(1280, 720)
        self.add_css_class('pv-window')

        self.pw_progress_key = progress_key
        self.pw_count = 0
        self.pw_cur = 0
        self.pw_cache = {}
        self.pw_box = (0, 0)
        self.pw_seen_box = (0, 0)
        self.pw_closed = False
        self.pw_syncing = False
        self.pw_ui_visible = True
        self.pw_last_pointer = None
        self.pw_scroll_acc = 0.0
        self.pw_scroll_time = 0.0
        self.pw_hide_id = 0
        self.pw_toast_id = 0
        self.pw_spinner_id = 0
        self.pw_tick_id = 0

        self._build()

        self.pw_worker = PdfWorker(path, self._worker_opened, self._worker_rendered, self._worker_error)
        self.pw_worker.start()
        self.pw_tick_id = GLib.timeout_add(TICK_MS, self._tick)

        self.connect('close-request', self._on_close_request)
        self.fullscreen()
        self._poke_ui()

    def _build(self):
        overlay = Gtk.Overlay()
        overlay.add_css_class('pv-root')

        self.pw_picture = Gtk.Picture()
        self.pw_picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.pw_picture.set_can_shrink(True)
        self.pw_picture.set_hexpand(True)
        self.pw_picture.set_vexpand(True)
        overlay.set_child(self.pw_picture)

        click = Gtk.GestureClick.new()
        click.set_button(1)
        click.connect('pressed', self._on_picture_pressed)
        self.pw_picture.add_controller(click)

        self.pw_spinner = Gtk.Spinner()
        self.pw_spinner.set_size_request(48, 48)
        self.pw_spinner.set_halign(Gtk.Align.CENTER)
        self.pw_spinner.set_valign(Gtk.Align.CENTER)
        self.pw_spinner.set_can_target(False)
        self.pw_spinner.set_visible(True)
        self.pw_spinner.start()
        overlay.add_overlay(self.pw_spinner)

        self.pw_error = Gtk.Label()
        self.pw_error.add_css_class('pv-error')
        self.pw_error.set_wrap(True)
        self.pw_error.set_max_width_chars(48)
        self.pw_error.set_justify(Gtk.Justification.CENTER)
        self.pw_error.set_halign(Gtk.Align.CENTER)
        self.pw_error.set_valign(Gtk.Align.CENTER)
        self.pw_error.set_can_target(False)
        self.pw_error.set_visible(False)
        overlay.add_overlay(self.pw_error)

        self.pw_prev_btn = _icon_button('go-previous-symbolic', 'pv-nav', 'Previous page (←)', 28)
        self.pw_prev_btn.set_halign(Gtk.Align.START)
        self.pw_prev_btn.set_valign(Gtk.Align.CENTER)
        self.pw_prev_btn.connect('clicked', lambda _b: self.prev_page())
        overlay.add_overlay(self.pw_prev_btn)

        self.pw_next_btn = _icon_button('go-next-symbolic', 'pv-nav', 'Next page (→)', 28)
        self.pw_next_btn.set_halign(Gtk.Align.END)
        self.pw_next_btn.set_valign(Gtk.Align.CENTER)
        self.pw_next_btn.connect('clicked', lambda _b: self.next_page())
        overlay.add_overlay(self.pw_next_btn)

        top = Gtk.Box(spacing=12)
        top.add_css_class('pv-bar')
        top.add_css_class('pv-top')
        top.set_halign(Gtk.Align.FILL)
        top.set_valign(Gtk.Align.START)
        title = Gtk.Label(label=self.get_title() or '')
        title.add_css_class('pv-title')
        title.set_xalign(0)
        title.set_hexpand(True)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        close_btn = _icon_button('window-close-symbolic', 'pv-nav-small', 'Close (Esc)', 18)
        close_btn.connect('clicked', lambda _b: self.close())
        top.append(title)
        top.append(close_btn)
        overlay.add_overlay(top)
        self.pw_top = top

        bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        bottom.add_css_class('pv-bar')
        bottom.add_css_class('pv-bottom')
        bottom.set_halign(Gtk.Align.FILL)
        bottom.set_valign(Gtk.Align.END)
        row = Gtk.Box(spacing=16)
        self.pw_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 2, 1)
        self.pw_slider.add_css_class('pv-scale')
        self.pw_slider.set_draw_value(False)
        self.pw_slider.set_hexpand(True)
        self.pw_slider.set_focusable(False)
        self.pw_slider.set_sensitive(False)
        self.pw_slider.connect('value-changed', self._on_slider_changed)
        self.pw_pages_label = Gtk.Label(label='')
        self.pw_pages_label.add_css_class('pv-pages')
        self.pw_pages_label.set_width_chars(10)
        self.pw_pages_label.set_xalign(1)
        row.append(self.pw_slider)
        row.append(self.pw_pages_label)
        hint = Gtk.Label(label='←  →  turn page      Home / End  first / last      F  windowed      Esc  close')
        hint.add_css_class('pv-hint')
        bottom.append(row)
        bottom.append(hint)
        overlay.add_overlay(bottom)
        self.pw_bottom = bottom

        self.pw_counter = Gtk.Label(label='')
        self.pw_counter.add_css_class('pv-counter')
        self.pw_counter.set_halign(Gtk.Align.END)
        self.pw_counter.set_valign(Gtk.Align.END)
        self.pw_counter.set_can_target(False)
        overlay.add_overlay(self.pw_counter)

        self.pw_toast = Gtk.Label(label='')
        self.pw_toast.add_css_class('pv-toast')
        self.pw_toast.set_halign(Gtk.Align.CENTER)
        self.pw_toast.set_valign(Gtk.Align.END)
        self.pw_toast.set_margin_bottom(130)
        self.pw_toast.set_can_target(False)
        overlay.add_overlay(self.pw_toast)

        self.set_child(overlay)
        self.pw_overlay = overlay

        keys = Gtk.EventControllerKey.new()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect('key-pressed', self._on_key)
        self.add_controller(keys)

        scroll = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.VERTICAL)
        scroll.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        scroll.connect('scroll', self._on_scroll)
        self.add_controller(scroll)

        motion = Gtk.EventControllerMotion.new()
        motion.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        motion.connect('motion', self._on_motion)
        self.add_controller(motion)

    def _worker_opened(self, count):
        GLib.idle_add(self._on_opened, count)

    def _worker_rendered(self, index, box, result):
        GLib.idle_add(self._on_rendered, index, box, result)

    def _worker_error(self, message):
        GLib.idle_add(self._on_error, message)

    def _on_opened(self, count):
        if self.pw_closed:
            return False
        self.pw_count = count
        self.pw_slider.set_range(1, max(2, count))
        self.pw_slider.set_sensitive(count > 1)

        saved = _load_progress().get(self.pw_progress_key)
        start = 0
        if isinstance(saved, int) and 1 < saved < count:
            start = saved - 1
            self._toast(f'Continuing from page {saved}   ·   Home for the start')
        self.pw_cur = start
        self._update_ui()
        self._schedule()
        self._start_spinner_timer()
        return False

    def _on_rendered(self, index, box, result):
        if self.pw_closed:
            return False
        if result is None:
            if index == self.pw_cur:
                self._stop_spinner()
                self._toast('This page could not be displayed')
            return False
        if abs(index - self.pw_cur) > self._cache_radius():
            return False
        existing = self.pw_cache.get(index)
        if existing and existing[1] == self.pw_box and box != self.pw_box:
            return False
        width, height, stride, data = result
        texture = Gdk.MemoryTexture.new(width, height, Gdk.MemoryFormat.R8G8B8,
                                        GLib.Bytes.new(data), stride)
        self.pw_cache[index] = (texture, box)
        if index == self.pw_cur:
            self._show_current()
        return False

    def _on_error(self, message):
        if self.pw_closed:
            return False
        self._stop_spinner()
        self.pw_error.set_text(message + '\n\nPress Esc to go back.')
        self.pw_error.set_visible(True)
        self._set_ui(True)
        return False

    def go_to(self, index):
        if self.pw_count < 1:
            return
        index = max(0, min(self.pw_count - 1, index))
        if index == self.pw_cur:
            return
        self.pw_cur = index
        self._update_ui()
        self._show_current()
        self._schedule()

    def next_page(self):
        if self.pw_count < 1:
            return
        if self.pw_cur >= self.pw_count - 1:
            self._toast('Last page')
        else:
            self.go_to(self.pw_cur + 1)

    def prev_page(self):
        if self.pw_count < 1:
            return
        if self.pw_cur <= 0:
            self._toast('First page')
        else:
            self.go_to(self.pw_cur - 1)

    def _cache_radius(self):


        per_page = max(1, self.pw_box[0] * self.pw_box[1] * 3)
        pages = max(3, CACHE_BUDGET // per_page)
        return max(1, min(CACHE_RADIUS, (pages - 1) // 2))

    def _schedule(self):
        if self.pw_count < 1 or self.pw_box[0] < 1 or self.pw_box[1] < 1:
            return
        cur = self.pw_cur
        radius = self._cache_radius()
        order = [cur, cur + 1, cur - 1, cur + 2, cur - 2, cur + 3]
        wanted = []
        for index in order:
            if abs(index - cur) <= radius and 0 <= index < self.pw_count and index not in wanted:
                entry = self.pw_cache.get(index)
                if entry is None or entry[1] != self.pw_box:
                    wanted.append(index)
        for index in [k for k in self.pw_cache if abs(k - cur) > radius]:
            del self.pw_cache[index]
        self.pw_worker.request(wanted, self.pw_box)

    def _show_current(self):
        entry = self.pw_cache.get(self.pw_cur)
        if entry is not None:
            self.pw_picture.set_paintable(entry[0])
            self._stop_spinner()
        else:
            self._start_spinner_timer()

    def _start_spinner_timer(self):
        if self.pw_spinner_id or self.pw_error.get_visible():
            return
        def show():
            self.pw_spinner_id = 0
            if not self.pw_closed and self.pw_cur not in self.pw_cache:
                self.pw_spinner.set_visible(True)
                self.pw_spinner.start()
            return False
        self.pw_spinner_id = GLib.timeout_add(220, show)

    def _stop_spinner(self):
        if self.pw_spinner_id:
            GLib.source_remove(self.pw_spinner_id)
            self.pw_spinner_id = 0
        self.pw_spinner.stop()
        self.pw_spinner.set_visible(False)

    def _tick(self):
        if self.pw_closed:
            self.pw_tick_id = 0
            return False
        factor = max(1, self.get_scale_factor())
        box = (self.pw_picture.get_width() * factor, self.pw_picture.get_height() * factor)
        if box[0] > 0 and box[1] > 0 and box != self.pw_box:
            if self.pw_box == (0, 0) or box == self.pw_seen_box:
                self.pw_box = box
                self._schedule()
        self.pw_seen_box = box
        return True

    def _update_ui(self):
        total = self.pw_count
        self.pw_syncing = True
        self.pw_slider.set_value(self.pw_cur + 1)
        self.pw_syncing = False
        text = f'{self.pw_cur + 1} / {total}' if total else ''
        self.pw_pages_label.set_text(text)
        self.pw_counter.set_text(text)
        self.pw_prev_btn.set_sensitive(total > 1 and self.pw_cur > 0)
        self.pw_next_btn.set_sensitive(total > 1 and self.pw_cur < total - 1)

    def _set_ui(self, visible):
        self.pw_ui_visible = visible
        for widget in (self.pw_top, self.pw_bottom, self.pw_prev_btn, self.pw_next_btn):
            if visible:
                widget.remove_css_class('pv-hidden')
            else:
                widget.add_css_class('pv-hidden')
            widget.set_can_target(visible)
        if visible:
            self.pw_counter.remove_css_class('pv-counter-on')
            self.set_cursor(None)
        else:
            self.pw_counter.add_css_class('pv-counter-on')
            self.set_cursor_from_name('none')

    def _poke_ui(self):
        self._set_ui(True)
        if self.pw_hide_id:
            GLib.source_remove(self.pw_hide_id)
        self.pw_hide_id = GLib.timeout_add(UI_HIDE_MS, self._auto_hide)

    def _auto_hide(self):
        self.pw_hide_id = 0
        if not self.pw_closed and not self.pw_error.get_visible():
            self._set_ui(False)
        return False

    def _toast(self, text):
        self.pw_toast.set_text(text)
        self.pw_toast.add_css_class('pv-toast-on')
        if self.pw_toast_id:
            GLib.source_remove(self.pw_toast_id)
        def hide():
            self.pw_toast_id = 0
            self.pw_toast.remove_css_class('pv-toast-on')
            return False
        self.pw_toast_id = GLib.timeout_add(2200, hide)

    def _on_key(self, _controller, keyval, _keycode, state):
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        if keyval == Gdk.KEY_Escape or keyval in (Gdk.KEY_q, Gdk.KEY_Q):
            self.close()
        elif keyval == Gdk.KEY_space and shift:
            self.prev_page()
        elif keyval in KEYS_NEXT:
            self.next_page()
        elif keyval in KEYS_PREV:
            self.prev_page()
        elif keyval in (Gdk.KEY_Home, Gdk.KEY_KP_Home):
            self.go_to(0)
        elif keyval in (Gdk.KEY_End, Gdk.KEY_KP_End):
            self.go_to(self.pw_count - 1)
        elif keyval in (Gdk.KEY_f, Gdk.KEY_F, Gdk.KEY_F11):
            if self.is_fullscreen():
                self.unfullscreen()
            else:
                self.fullscreen()
        else:
            return False
        return True

    def _on_scroll(self, _controller, _dx, dy):
        now = time.monotonic()
        if now - self.pw_scroll_time < SCROLL_COOLDOWN:
            self.pw_scroll_acc = 0.0
            return True
        self.pw_scroll_acc += dy
        if self.pw_scroll_acc >= 1.0:
            self.pw_scroll_acc = 0.0
            self.pw_scroll_time = now
            self.next_page()
        elif self.pw_scroll_acc <= -1.0:
            self.pw_scroll_acc = 0.0
            self.pw_scroll_time = now
            self.prev_page()
        return True

    def _on_motion(self, _controller, x, y):
        last = self.pw_last_pointer
        self.pw_last_pointer = (x, y)
        if last is not None and abs(x - last[0]) < 3 and abs(y - last[1]) < 3:
            return
        self._poke_ui()

    def _on_picture_pressed(self, _gesture, _n_press, x, _y):
        width = self.pw_picture.get_width()
        if width <= 0 or self.pw_count < 1:
            return
        if x < width * EDGE_ZONE:
            self.prev_page()
        elif x > width * (1 - EDGE_ZONE):
            self.next_page()
        elif self.pw_ui_visible:
            self._set_ui(False)
        else:
            self._poke_ui()

    def _on_slider_changed(self, slider):
        if self.pw_syncing or self.pw_count < 1:
            return
        self.go_to(int(round(slider.get_value())) - 1)

    def _on_close_request(self, _window):
        if self.pw_closed:
            return False
        self.pw_closed = True
        if self.pw_count > 0:
            _save_progress(self.pw_progress_key, self.pw_cur + 1)
        for attr in ('pw_hide_id', 'pw_toast_id', 'pw_spinner_id', 'pw_tick_id'):
            source = getattr(self, attr)
            if source:
                GLib.source_remove(source)
                setattr(self, attr, 0)
        self.pw_worker.stop()
        self.pw_cache.clear()
        self.pw_picture.set_paintable(None)


        GLib.timeout_add(1500, lambda: (trim_memory(), False)[1])
        return False
