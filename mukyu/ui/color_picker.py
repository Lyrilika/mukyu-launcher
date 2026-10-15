import colorsys
import math
import re

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

try:
    import cairo
except ImportError:
    cairo = None


SV_W, SV_H = 236, 160
HUE_H = 16
HANDLE_R = 8

_HEX_RE = re.compile(r"#?([0-9a-fA-F]{6})")


def hex_to_hsv(value):
    match = _HEX_RE.fullmatch(value.strip())
    if not match:
        return None
    digits = match.group(1)
    r, g, b = (int(digits[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return colorsys.rgb_to_hsv(r, g, b)


def hsv_to_hex(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def _rounded_rect(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def _handle(cr, x, y, fill_rgb):
    cr.arc(x, y, HANDLE_R, 0, 2 * math.pi)
    cr.set_source_rgb(*fill_rgb)
    cr.fill_preserve()
    cr.set_line_width(3)
    cr.set_source_rgb(1, 1, 1)
    cr.stroke_preserve()
    cr.set_line_width(1)
    cr.set_source_rgba(0, 0, 0, 0.35)
    cr.arc(x, y, HANDLE_R + 1.5, 0, 2 * math.pi)
    cr.stroke()


def draw_sv(cr, width, height, h, s, v):
    _rounded_rect(cr, 0, 0, width, height, 10)
    cr.save()
    cr.clip()
    hue_rgb = colorsys.hsv_to_rgb(h, 1.0, 1.0)
    cr.set_source_rgb(*hue_rgb)
    cr.paint()
    white = cairo.LinearGradient(0, 0, width, 0)
    white.add_color_stop_rgba(0, 1, 1, 1, 1)
    white.add_color_stop_rgba(1, 1, 1, 1, 0)
    cr.set_source(white)
    cr.paint()
    black = cairo.LinearGradient(0, 0, 0, height)
    black.add_color_stop_rgba(0, 0, 0, 0, 0)
    black.add_color_stop_rgba(1, 0, 0, 0, 1)
    cr.set_source(black)
    cr.paint()
    cr.restore()
    x = s * width
    y = (1.0 - v) * height
    x = max(HANDLE_R, min(width - HANDLE_R, x))
    y = max(HANDLE_R, min(height - HANDLE_R, y))
    _handle(cr, x, y, colorsys.hsv_to_rgb(h, s, v))


def draw_hue(cr, width, height, h):
    _rounded_rect(cr, 0, 0, width, height, height / 2)
    cr.save()
    cr.clip()
    rainbow = cairo.LinearGradient(0, 0, width, 0)
    for i in range(7):
        r, g, b = colorsys.hsv_to_rgb(i / 6.0, 1.0, 1.0)
        rainbow.add_color_stop_rgb(i / 6.0, r, g, b)
    cr.set_source(rainbow)
    cr.paint()
    cr.restore()
    radius = height / 2 + 2
    x = max(radius, min(width - radius, h * width))
    cr.arc(x, height / 2, radius, 0, 2 * math.pi)
    cr.set_source_rgb(*colorsys.hsv_to_rgb(h, 1.0, 1.0))
    cr.fill_preserve()
    cr.set_line_width(3)
    cr.set_source_rgb(1, 1, 1)
    cr.stroke_preserve()
    cr.set_line_width(1)
    cr.set_source_rgba(0, 0, 0, 0.35)
    cr.arc(x, height / 2, radius + 1.5, 0, 2 * math.pi)
    cr.stroke()


class ColorPicker(Gtk.Box):
    def __init__(self, hex_color, on_change):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add_css_class("theme-color-picker")
        self._on_change = on_change
        self._updating = False
        hsv = hex_to_hsv(hex_color) or (0.85, 0.5, 0.85)
        self.h, self.s, self.v = hsv

        self.sv_area = Gtk.DrawingArea()
        self.sv_area.set_content_width(SV_W)
        self.sv_area.set_content_height(SV_H)
        self.sv_area.set_draw_func(lambda _a, cr, w, h: draw_sv(cr, w, h, self.h, self.s, self.v))
        self._attach_drag(self.sv_area, self._sv_pointer)
        self.append(self.sv_area)

        self.hue_area = Gtk.DrawingArea()
        self.hue_area.set_content_width(SV_W)
        self.hue_area.set_content_height(HUE_H + 6)
        self.hue_area.set_draw_func(self._draw_hue_padded)
        self._attach_drag(self.hue_area, self._hue_pointer)
        self.append(self.hue_area)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.preview = Gtk.DrawingArea()
        self.preview.set_content_width(34)
        self.preview.set_content_height(30)
        self.preview.set_valign(Gtk.Align.CENTER)
        self.preview.set_draw_func(self._draw_preview)
        row.append(self.preview)

        self.entry = Gtk.Entry()
        self.entry.set_max_length(7)
        self.entry.set_width_chars(9)
        self.entry.set_hexpand(True)
        self.entry.set_placeholder_text("#rrggbb")
        self.entry.add_css_class("theme-color-hex")
        self.entry.connect("changed", self._on_entry_changed)
        self.entry.connect("activate", lambda *_: self._emit(True))
        row.append(self.entry)
        self.append(row)
        self._sync_entry()

    def hex(self):
        return hsv_to_hex(self.h, self.s, self.v)

    def set_hex(self, value, emit=False):
        hsv = hex_to_hsv(value)
        if hsv is None:
            return
        h, s, v = hsv
        self.h = h if s > 0.02 and v > 0.02 else self.h
        self.s, self.v = s, v
        self._refresh()
        if emit:
            self._emit(True)

    def _draw_hue_padded(self, _area, cr, width, height):
        cr.translate(0, (height - HUE_H) / 2)
        draw_hue(cr, width, HUE_H, self.h)

    def _draw_preview(self, _area, cr, width, height):
        _rounded_rect(cr, 0, 0, width, height, 8)
        r, g, b = colorsys.hsv_to_rgb(self.h, self.s, self.v)
        cr.set_source_rgb(r, g, b)
        cr.fill_preserve()
        cr.set_line_width(1)
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.45)
        cr.stroke()

    def _refresh(self):
        self.sv_area.queue_draw()
        self.hue_area.queue_draw()
        self.preview.queue_draw()
        self._sync_entry()

    def _sync_entry(self):
        self._updating = True
        self.entry.set_text(self.hex())
        self._updating = False

    def _attach_drag(self, widget, handler):
        drag = Gtk.GestureDrag()
        start = {"x": 0.0, "y": 0.0}

        def begin(_g, x, y):
            start["x"], start["y"] = x, y
            handler(x, y, widget)
            self._emit(False)

        def update(_g, dx, dy):
            handler(start["x"] + dx, start["y"] + dy, widget)
            self._emit(False)

        def end(_g, _dx, _dy):
            self._emit(True)

        drag.connect("drag-begin", begin)
        drag.connect("drag-update", update)
        drag.connect("drag-end", end)
        widget.add_controller(drag)

    def _sv_pointer(self, x, y, widget):
        w, h = max(1, widget.get_width()), max(1, widget.get_height())
        self.s = max(0.0, min(1.0, x / w))
        self.v = max(0.0, min(1.0, 1.0 - y / h))
        self._refresh()

    def _hue_pointer(self, x, _y, widget):
        w = max(1, widget.get_width())
        self.h = max(0.0, min(1.0, x / w))
        self._refresh()

    def _on_entry_changed(self, entry):
        if self._updating:
            return
        hsv = hex_to_hsv(entry.get_text())
        if hsv is None:
            return
        h, s, v = hsv
        self.h = h if s > 0.02 and v > 0.02 else self.h
        self.s, self.v = s, v
        self.sv_area.queue_draw()
        self.hue_area.queue_draw()
        self.preview.queue_draw()
        self._emit(True)

    def _emit(self, final):
        if not self._updating:
            self._on_change(self.hex(), final)
