import json
import os
import re
from urllib.parse import unquote

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, Gio, GLib

from mukyu.platform_compat import IS_WINDOWS, config_home


CONFIG_DIR = os.path.join(
    config_home(),
    "mukyulauncher",
)


def windows_appearance():
    dark = True
    accent = "#0078d4"
    if not IS_WINDOWS:
        return dark, accent
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            dark = int(winreg.QueryValueEx(key, "AppsUseLightTheme")[0]) == 0
    except (OSError, ImportError, ValueError):
        pass
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM") as key:
            try:
                value = int(winreg.QueryValueEx(key, "AccentColor")[0]) & 0xFFFFFFFF
                red, green, blue = value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF
            except OSError:
                value = int(winreg.QueryValueEx(key, "ColorizationColor")[0]) & 0xFFFFFFFF
                red, green, blue = (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF
        accent = "#%02x%02x%02x" % (red, green, blue)
    except (OSError, ImportError, ValueError):
        pass
    return dark, accent
THEME_SETTINGS_FILE = os.path.join(CONFIG_DIR, "ui_settings.json")

DEFAULT_SETTINGS = {
    "mode": "dark",
    "use_gtk_theme": False,
    "accent_color": "#d96bc8",
}


MANUAL_BASES = {
    "dark": {
        "app_bg": "#0e0e0e",
        "app_surface": "#171717",
        "app_surface_alt": "#1f1f1f",
        "app_surface_high": "#292929",
        "app_popover": "#2e2e2e",
        "app_fg": "#f4f4f4",
        "app_fg_dim": "#bdbdbd",
        "app_fg_disabled": "#808080",
    },
    "light": {
        "app_bg": "#f4f4f4",
        "app_surface": "#fcfcfc",
        "app_surface_alt": "#ebebeb",
        "app_surface_high": "#e0e0e0",
        "app_popover": "#fcfcfc",
        "app_fg": "#1c1c1c",
        "app_fg_dim": "#5c5c5c",
        "app_fg_disabled": "#9a9a9a",
    },
}

TINT = {
    "dark": {
        "app_bg": 0.05, "app_surface": 0.07, "app_surface_alt": 0.09,
        "app_surface_high": 0.12, "app_popover": 0.12, "app_fg": 0.05, "app_fg_dim": 0.06,
        "app_fg_disabled": 0.05,
    },
    "light": {
        "app_bg": 0.05, "app_surface": 0.07, "app_surface_alt": 0.09,
        "app_surface_high": 0.13, "app_popover": 0.07, "app_fg": 0.06, "app_fg_dim": 0.06,
        "app_fg_disabled": 0.05,
    },
}


GTK_NAMED_COLORS = {
    "window_bg_color": "app_bg",
    "dialog_bg_color": "app_bg",
    "headerbar_bg_color": "app_bg",
    "headerbar_backdrop_color": "app_bg",
    "theme_bg_color": "app_bg",
    "theme_unfocused_bg_color": "app_bg",
    "view_bg_color": "app_surface",
    "card_bg_color": "app_surface",
    "sidebar_bg_color": "app_surface",
    "sidebar_backdrop_color": "app_surface",
    "theme_base_color": "app_surface",
    "theme_unfocused_base_color": "app_surface",
    "popover_bg_color": "app_popover",
    "window_fg_color": "app_fg",
    "dialog_fg_color": "app_fg",
    "headerbar_fg_color": "app_fg",
    "view_fg_color": "app_fg",
    "card_fg_color": "app_fg",
    "sidebar_fg_color": "app_fg",
    "popover_fg_color": "app_fg",
    "theme_fg_color": "app_fg",
    "theme_text_color": "app_fg",
    "theme_unfocused_fg_color": "app_fg_dim",
    "theme_unfocused_text_color": "app_fg_dim",
}


class ThemeManager:

    _PALETTE_NAMES = (
        "app_bg",
        "app_surface",
        "app_surface_alt",
        "app_surface_high",
        "app_fg",
        "app_fg_dim",
        "app_fg_disabled",
        "app_popover",
        "app_accent",
        "app_accent_hover",
        "app_on_accent",
    )

    def __init__(self, display=None, css_path=None):
        self.display = display
        self.settings = (
            Gtk.Settings.get_for_display(display)
            if display is not None
            else Gtk.Settings.get_default()
        )
        self.provider = Gtk.CssProvider()
        self.css_path = css_path
        self._base_css = ""
        self.mode = "dark"
        self.use_gtk_theme = False
        self.accent_color = DEFAULT_SETTINGS["accent_color"]
        self._system_signal_ids = []
        self._change_callbacks = []
        self._appearance_callbacks = []
        self._syncing_pref = False
        self._refresh_source = 0
        self._last_system_palette = None
        self._config_monitor = None
        self._config_dirty = False
        self._followup_installed = False
        self._user_css_providers = []
        self._user_colors = {}
        self._use_user_colors = True
        self._palette_source = ""
        self._user_css_signature = None
        self._user_css_monitors = []
        self._pinned_settings = set()
        self._debug = bool(os.environ.get("MUKYU_THEME_DEBUG"))
        self._orig_prefer_dark = None
        self._orig_color_scheme = None
        self._portal_dark = self._read_portal_scheme()
        self._portal_sub = 0
        self._remember_system_preferences()
        self._provider_installed = False
        self._load_preferences()
        self._load_base_css()

    def _load_preferences(self):
        try:
            with open(THEME_SETTINGS_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError, TypeError):
            data = {}

        if not isinstance(data, dict):
            return

        mode = data.get("mode")
        if mode in MANUAL_BASES:
            self.mode = mode

        self.use_gtk_theme = bool(data.get("use_gtk_theme", False))

        accent = data.get("accent_color")
        if isinstance(accent, str) and self._is_hex_color(accent):
            self.accent_color = self._normalize_hex(accent)

    def save_preferences(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        temporary = THEME_SETTINGS_FILE + ".tmp"
        payload = {
            "mode": self.mode,
            "use_gtk_theme": self.use_gtk_theme,
            "accent_color": self.accent_color,
        }
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        os.replace(temporary, THEME_SETTINGS_FILE)

    def _load_base_css(self):
        if not self.css_path:
            self._base_css = ""
            return
        try:
            with open(self.css_path, "r", encoding="utf-8") as handle:
                self._base_css = handle.read()
        except OSError:
            self._base_css = ""

    @staticmethod
    def _normalize_hex(value):
        value = value.strip()
        if not value.startswith("#"):
            value = "#" + value
        if len(value) == 4:
            value = "#" + "".join(char * 2 for char in value[1:])
        return value.lower()

    @staticmethod
    def _is_hex_color(value):
        return bool(re.fullmatch(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})", value.strip()))

    @staticmethod
    def _hex_rgb(value):
        value = ThemeManager._normalize_hex(value).lstrip("#")
        if len(value) != 6:
            value = "d96bc8"
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def _rgb_hex(rgb):
        return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in rgb)

    @staticmethod
    def _mix(a, b, amount):
        ar, ag, ab = ThemeManager._hex_rgb(a)
        br, bg, bb = ThemeManager._hex_rgb(b)
        return ThemeManager._rgb_hex(
            (
                ar + (br - ar) * amount,
                ag + (bg - ag) * amount,
                ab + (bb - ab) * amount,
            )
        )

    @staticmethod
    def _relative_luminance(value):
        rgb = [channel / 255.0 for channel in ThemeManager._hex_rgb(value)]
        linear = []
        for channel in rgb:
            linear.append(
                channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
            )
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    def _on_accent_for(self, accent):
        lum = self._relative_luminance(accent)
        dark_text = "#1a1a1a"
        contrast_dark = (lum + 0.05) / (self._relative_luminance(dark_text) + 0.05)
        contrast_white = 1.05 / (lum + 0.05)
        return dark_text if contrast_dark >= contrast_white else "#ffffff"

    def _manual_palette(self):
        return self._manual_palette_for(self.mode, self.accent_color)

    def _manual_palette_for(self, mode, accent):
        palette = {
            name: self._mix(base, accent, TINT[mode][name])
            for name, base in MANUAL_BASES[mode].items()
        }
        palette.update(
            {
                "app_accent": accent,
                "app_accent_hover": self._mix(accent, "#000000", 0.12 if mode == "dark" else 0.18),
                "app_on_accent": self._on_accent_for(accent),
            }
        )
        return palette

    def _windows_palette(self):
        dark, accent = windows_appearance()
        return self._manual_palette_for("dark" if dark else "light", accent)

    def _lookup_system_color(self, *names):
        for name in names:
            value = self._resolve_user_color(name)
            if value:
                return value
        try:
            probe = Gtk.Label()
            context = probe.get_style_context()
            for name in names:
                found, rgba = context.lookup_color(name)
                if found and isinstance(rgba, Gdk.RGBA) and rgba.alpha > 0:
                    return self._rgb_hex(
                        (rgba.red * 255.0, rgba.green * 255.0, rgba.blue * 255.0)
                    )
        except (AttributeError, TypeError, ValueError):
            pass
        return None

    def _system_accent(self):
        for name in ("accent_bg_color", "accent_color"):
            value = self._resolve_user_color(name)
            if value:
                return value
        if self.settings is not None:
            try:
                rgba = self.settings.get_property("gtk-accent-color")
                if isinstance(rgba, Gdk.RGBA) and rgba.alpha > 0:
                    return self._rgb_hex(
                        (rgba.red * 255.0, rgba.green * 255.0, rgba.blue * 255.0)
                    )
            except (AttributeError, TypeError, ValueError):
                pass
        theme_accent = self._lookup_system_color("accent_bg_color", "accent_color")
        if theme_accent:
            return theme_accent
        return "#3584e4"

    def _system_palette(self):
        if IS_WINDOWS:
            return self._windows_palette()
        self._user_colors = self._parse_user_css_colors()
        expected_dark = self._scheme_is_dark()
        self._use_user_colors = True
        palette = self._system_palette_from_sources()
        self._palette_source = "user-css" if self._user_colors else "gtk-lookup"
        if self._user_colors and expected_dark is not None:
            if self._palette_is_dark(palette) != expected_dark:
                self._use_user_colors = False
                alternative = self._system_palette_from_sources()
                if self._palette_is_dark(alternative) == expected_dark:
                    palette = alternative
                    self._palette_source = "gtk-lookup (user-css disagreed with scheme)"
                else:
                    self._use_user_colors = True
                    self._palette_source = "user-css (neither source matched scheme)"
        self._use_user_colors = True
        if (
            self._portal_dark is not None
            and "window_bg_color" not in self._user_colors
            and self._palette_is_dark(palette) != self._portal_dark
        ):

            palette = self._manual_palette_for(
                "dark" if self._portal_dark else "light", palette["app_accent"]
            )
            self._palette_source += " (forced to desktop scheme)"
        return palette

    def _palette_is_dark(self, palette):
        return self._relative_luminance(palette["app_bg"]) < 0.18

    def _system_palette_from_sources(self):
        interface_dark = False
        if self.settings is not None:
            try:
                scheme = self.settings.get_property("gtk-interface-color-scheme")
                interface_dark = self._is_dark_value(scheme)
            except (AttributeError, TypeError, ValueError):
                pass
        if self._portal_dark is not None:
            interface_dark = self._portal_dark

        fallback_bg = "#1e1e1e" if interface_dark else "#f8f8f8"
        fallback_fg = "#f2f2f2" if interface_dark else "#242424"
        app_bg = self._lookup_system_color("window_bg_color", "dialog_bg_color") or fallback_bg
        app_fg = self._lookup_system_color("window_fg_color", "dialog_fg_color") or fallback_fg
        app_surface = self._lookup_system_color("card_bg_color", "view_bg_color") or self._mix(app_bg, app_fg, 0.06)
        app_surface_alt = self._lookup_system_color("view_bg_color", "card_bg_color") or self._mix(app_bg, app_fg, 0.10)
        app_surface_high = self._lookup_system_color("headerbar_bg_color", "sidebar_bg_color", "card_bg_color") or self._mix(app_bg, app_fg, 0.14)
        app_fg_dim = self._mix(app_fg, app_bg, 0.28)
        app_fg_disabled = self._mix(app_fg, app_bg, 0.55)
        app_popover = self._lookup_system_color("popover_bg_color") or app_surface_high
        accent = self._system_accent()
        return {
            "app_bg": app_bg,
            "app_surface": app_surface,
            "app_surface_alt": app_surface_alt,
            "app_surface_high": app_surface_high,
            "app_fg": app_fg,
            "app_fg_dim": app_fg_dim,
            "app_fg_disabled": app_fg_disabled,
            "app_popover": app_popover,
            "app_accent": accent,
            "app_accent_hover": self._mix(accent, "#000000", 0.10),
            "app_on_accent": self._on_accent_for(accent),
        }

    def _palette_block(self):
        palette = self._system_palette() if self.use_gtk_theme else self._manual_palette()
        self._last_system_palette = dict(palette) if self.use_gtk_theme else None
        lines = [
            f"@define-color {name} {palette[name]};"
            for name in self._PALETTE_NAMES
        ]
        if not self.use_gtk_theme or IS_WINDOWS:
            accent = palette["app_accent"]
            on_accent = palette["app_on_accent"]
            lines += [
                f"@define-color accent_color {accent};",
                f"@define-color accent_bg_color {accent};",
                f"@define-color accent_fg_color {on_accent};",
                f"@define-color theme_selected_bg_color {accent};",
                f"@define-color theme_selected_fg_color {on_accent};",
            ]
            lines += [
                f"@define-color {gtk_name} {palette[ours]};"
                for gtk_name, ours in GTK_NAMED_COLORS.items()
            ]
        return "\n".join(lines) + "\n\n"

    def _render_css(self):
        if not self._base_css:
            return ""
        return re.sub(
            r"(?:@define-color app_[^;]+;\s*){11}",
            self._palette_block(),
            self._base_css,
            count=1,
        )

    def _install_provider(self):
        if self.display is None or not self._base_css:
            return
        if self._provider_installed:
            Gtk.StyleContext.remove_provider_for_display(self.display, self.provider)
            self._provider_installed = False
        self.provider.load_from_data(self._render_css().encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            self.display,
            self.provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER + 1,
        )
        self._provider_installed = True

    def _read_setting(self, name):
        if self.settings is None:
            return None
        try:
            return self.settings.get_property(name)
        except (AttributeError, TypeError, ValueError):
            return None


    @staticmethod
    def _scheme_from_portal(value):
        if value == 1:
            return True
        if value == 2:
            return False
        return None

    def _read_portal_scheme(self):
        if IS_WINDOWS:
            return None
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            reply = bus.call_sync(
                "org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop",
                "org.freedesktop.portal.Settings",
                "Read",
                GLib.Variant("(ss)", ("org.freedesktop.appearance", "color-scheme")),
                GLib.VariantType("(v)"),
                Gio.DBusCallFlags.NONE,
                800,
                None,
            )
            value = reply.get_child_value(0)
            while value.get_type_string() == "v":
                value = value.get_variant()
            return self._scheme_from_portal(value.get_uint32())
        except Exception:
            return None

    def _watch_portal_scheme(self):
        if IS_WINDOWS or self._portal_sub:
            return
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self._portal_sub = bus.signal_subscribe(
                "org.freedesktop.portal.Desktop",
                "org.freedesktop.portal.Settings",
                "SettingChanged",
                "/org/freedesktop/portal/desktop",
                None,
                Gio.DBusSignalFlags.NONE,
                self._on_portal_setting,
            )
        except Exception:
            self._portal_sub = 0

    def _on_portal_setting(self, _conn, _sender, _path, _iface, _signal, params, *_rest):
        try:
            namespace, key, value = params.unpack()
        except Exception:
            return
        if namespace != "org.freedesktop.appearance" or key != "color-scheme":
            return
        self._portal_dark = self._scheme_from_portal(value)
        self._log(f"portal color-scheme changed: dark={self._portal_dark}")
        self._schedule_system_refresh("portal color-scheme")

    def _remember_system_preferences(self):
        self._orig_prefer_dark = self._read_setting("gtk-application-prefer-dark-theme")
        self._orig_color_scheme = self._read_setting("gtk-interface-color-scheme")

    def _set_setting_if_changed(self, name, value):
        if self.settings is None or value is None:
            return
        try:
            if self.settings.get_property(name) == value:
                return
            self.settings.set_property(name, value)
            self._pinned_settings.add(name)
        except (AttributeError, TypeError, ValueError):
            pass

    def _release_setting(self, name):
        if self.settings is None:
            return False
        try:
            self.settings.reset_property(name)
        except (AttributeError, TypeError, ValueError):
            return False
        self._pinned_settings.discard(name)
        return True

    def _scheme_for(self, dark):
        enum = getattr(Gtk, "InterfaceColorScheme", None)
        if enum is None:
            return None
        return enum.DARK if dark else enum.LIGHT

    def _sync_system_preferences(self):
        if self.settings is None:
            return
        self._syncing_pref = True
        try:
            if self.use_gtk_theme and IS_WINDOWS:
                dark = windows_appearance()[0]
                self._set_setting_if_changed("gtk-application-prefer-dark-theme", dark)
                self._set_setting_if_changed(
                    "gtk-interface-color-scheme", self._scheme_for(dark)
                )
            elif self.use_gtk_theme and self._portal_dark is not None:

                self._set_setting_if_changed("gtk-application-prefer-dark-theme", self._portal_dark)
                self._set_setting_if_changed(
                    "gtk-interface-color-scheme", self._scheme_for(self._portal_dark)
                )
            elif self.use_gtk_theme:
                originals = {
                    "gtk-application-prefer-dark-theme": self._orig_prefer_dark,
                    "gtk-interface-color-scheme": self._orig_color_scheme,
                }
                for name in list(self._pinned_settings):
                    if not self._release_setting(name):
                        self._set_setting_if_changed(name, originals.get(name))
            else:
                dark = self.mode == "dark"
                self._set_setting_if_changed("gtk-application-prefer-dark-theme", dark)
                self._set_setting_if_changed(
                    "gtk-interface-color-scheme", self._scheme_for(dark)
                )
        finally:
            self._syncing_pref = False

    def apply(self, *, save=True):
        self._sync_system_preferences()
        self._install_provider()
        if save:
            self.save_preferences()
        for callback in list(self._appearance_callbacks):
            try:
                callback()
            except Exception:
                pass

    def connect_appearance(self, callback):
        self._appearance_callbacks.append(callback)

    def effective_mode(self):
        if not self.use_gtk_theme:
            return self.mode
        background = self._system_palette()["app_bg"]
        return "dark" if self._relative_luminance(background) < 0.18 else "light"

    def connect_change(self, callback):
        self._change_callbacks.append(callback)

    def set_mode(self, mode):
        if mode not in MANUAL_BASES:
            return
        self.mode = mode
        self.use_gtk_theme = False
        self.apply()

    def set_accent_color(self, accent, save=True):
        accent = self._normalize_hex(accent)
        if not self._is_hex_color(accent):
            return
        self.accent_color = accent
        self.apply(save=save)

    def set_use_gtk_theme(self, enabled):
        self.use_gtk_theme = bool(enabled)
        self.apply()

    def _log(self, message):
        if self._debug:
            print(f"[theme] {message}", flush=True)

    def install_system_followup(self):
        if self._followup_installed:
            return
        self._followup_installed = True
        if IS_WINDOWS:
            self._windows_state = windows_appearance()
            GLib.timeout_add_seconds(2, self._poll_windows_appearance)
            return
        if self.settings is not None:
            for prop in (
                "gtk-theme-name",
                "gtk-application-prefer-dark-theme",
                "gtk-interface-color-scheme",
                "gtk-accent-color",
            ):
                try:
                    signal_id = self.settings.connect(
                        f"notify::{prop}", self._on_system_theme_change
                    )
                except (TypeError, ValueError):
                    continue
                self._system_signal_ids.append(signal_id)
        self._watch_portal_scheme()
        self._user_css_signature = self._compute_user_css_signature()
        self._install_config_monitor()
        self._watch_user_css_files()

    def _poll_windows_appearance(self):
        state = windows_appearance()
        if state != getattr(self, "_windows_state", None):
            self._windows_state = state
            if self.use_gtk_theme:
                self._schedule_system_refresh("windows appearance")
        return GLib.SOURCE_CONTINUE

    def refresh_from_system(self, reason="request"):

        now = GLib.get_monotonic_time()
        if now - getattr(self, "_last_focus_refresh", 0) < 1_500_000:
            return
        self._last_focus_refresh = now
        self._schedule_system_refresh(reason)

    def _user_css_paths(self):
        config = os.path.join(GLib.get_user_config_dir(), "gtk-4.0")
        return [os.path.join(config, "gtk.css"), os.path.join(config, "gtk-dark.css")]

    def _user_css_files(self):
        found = []
        for path in self._user_css_paths():
            if not os.path.exists(path):
                continue
            found.append(path)
            real = os.path.realpath(path)
            if real != path:
                found.append(real)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
            except OSError:
                continue
            for match in re.finditer(
                r"@import\s+(?:url\(\s*)?[\"']?([^\"')\s;]+)", text
            ):
                target = match.group(1)
                if target.startswith("file://"):
                    target = target[7:]
                elif "://" in target:
                    continue
                elif not os.path.isabs(target):
                    target = os.path.join(os.path.dirname(real), target)
                found.append(target)
                found.append(os.path.realpath(target))
        unique = []
        for item in found:
            if item not in unique:
                unique.append(item)
        return unique

    def _compute_user_css_signature(self):
        parts = []
        for path in self._user_css_files():
            try:
                info = os.stat(path)
                parts.append((path, info.st_mtime_ns, info.st_size))
            except OSError:
                parts.append((path, None, None))
        parts.append(tuple(os.path.exists(p) for p in self._user_css_paths()))
        parts.append(self._desktop_prefers_dark())
        return tuple(parts)

    def _watch_user_css_files(self):
        for monitor in self._user_css_monitors:
            try:
                monitor.cancel()
            except Exception:
                pass
        self._user_css_monitors = []
        for path in self._user_css_files():
            try:
                monitor = Gio.File.new_for_path(path).monitor_file(
                    Gio.FileMonitorFlags.WATCH_MOVES, None
                )
            except GLib.Error:
                continue
            monitor.connect("changed", self._on_user_css_file_changed)
            self._user_css_monitors.append(monitor)

    def _on_user_css_file_changed(self, _monitor, _file, _other, event):
        if event == Gio.FileMonitorEvent.CHANGES_DONE_HINT or event in (
            Gio.FileMonitorEvent.CHANGED,
            Gio.FileMonitorEvent.CREATED,
            Gio.FileMonitorEvent.DELETED,
            Gio.FileMonitorEvent.RENAMED,
            Gio.FileMonitorEvent.MOVED_IN,
            Gio.FileMonitorEvent.MOVED_OUT,
        ):
            self._schedule_system_refresh("user gtk.css")

    def _collect_define_colors(self, path, colors, seen, dark, depth=0):
        real = os.path.realpath(path)
        if depth > 6 or real in seen or not os.path.isfile(real):
            return
        seen.add(real)
        try:
            with open(real, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            return
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        token = re.compile(
            r"(@media\s*\(\s*prefers-color-scheme\s*:\s*(dark|light)\s*\)\s*\{)"
            r"|(\{)|(\})"
            r"|@import\s+(?:url\(\s*)?[\"']?([^\"')\s;]+)[\"']?\s*\)?\s*;"
            r"|@define-color\s+([\w-]+)\s+([^;]+);"
        )
        stack = []
        for match in token.finditer(text):
            if match.group(1):
                stack.append(match.group(2) == "dark")
            elif match.group(3):
                stack.append(None)
            elif match.group(4):
                if stack:
                    stack.pop()
            elif match.group(5):
                if any(c is not None and c != dark for c in stack):
                    continue
                target = match.group(5)
                if target.startswith("file://"):
                    target = unquote(target[7:])
                elif "://" in target:
                    continue
                elif not os.path.isabs(target):
                    target = os.path.join(os.path.dirname(real), target)
                self._collect_define_colors(target, colors, seen, dark, depth + 1)
            else:
                if any(c is not None and c != dark for c in stack):
                    continue
                colors[match.group(6)] = match.group(7).strip()

    def _parse_user_css_colors(self):
        colors = {}
        gtk_css, dark_css = self._user_css_paths()
        paths = [gtk_css]
        if self._desktop_prefers_dark():
            paths.append(dark_css)
        seen = set()
        dark = self._desktop_prefers_dark()
        for path in paths:
            self._collect_define_colors(path, colors, seen, dark)
        return colors

    def _resolve_user_color(self, name, depth=0):
        raw = self._user_colors.get(name) if (self._user_colors and self._use_user_colors) else None
        if raw is None or depth > 8:
            return None
        raw = raw.strip()
        if raw.startswith("@"):
            return self._resolve_user_color(raw[1:].strip(), depth + 1)
        match = re.fullmatch(r"#([0-9a-fA-F]+)", raw)
        if match:
            digits = match.group(1)
            if len(digits) in (3, 4):
                return "#" + "".join(c * 2 for c in digits[:3]).lower()
            if len(digits) in (6, 8):
                return "#" + digits[:6].lower()
            return None
        match = re.fullmatch(r"rgba?\(\s*([^)]*)\)", raw)
        if match:
            parts = [p for p in re.split(r"[,\s/]+", match.group(1).strip()) if p]
            if len(parts) >= 3:
                try:
                    rgb = []
                    for part in parts[:3]:
                        if part.endswith("%"):
                            rgb.append(float(part[:-1]) * 2.55)
                        else:
                            rgb.append(float(part))
                    return self._rgb_hex(rgb)
                except ValueError:
                    return None
        return None

    def _explain_palette(self):
        if not self._debug:
            return
        names = (
            "window_bg_color", "window_fg_color", "card_bg_color", "view_bg_color",
            "headerbar_bg_color", "popover_bg_color", "accent_bg_color",
        )
        saved = self._user_colors
        self._user_colors = self._parse_user_css_colors()
        parsed = {n: self._resolve_user_color(n) for n in names}
        self._user_colors = {}
        probed = {n: self._lookup_system_color(n) for n in names}
        self._user_colors = saved
        self._log(f"user gtk.css defines {len(self._user_colors)} colours")
        for n in names:
            self._log(f"  {n}: user-css={parsed[n]}  gtk-lookup={probed[n]}")
        self._log(f"  scheme dark={self._scheme_is_dark()}  palette source: {self._palette_source}")
        if self._last_system_palette:
            self._log(f"  app palette: {self._last_system_palette}")

    @staticmethod
    def _is_dark_value(value):
        if value is None:
            return False
        nick = getattr(value, "value_nick", None) or str(value)
        return "dark" in str(nick).lower()

    def _scheme_is_dark(self):
        if self._portal_dark is not None:
            return self._portal_dark
        scheme = self._read_setting("gtk-interface-color-scheme")
        if scheme is not None:
            nick = str(getattr(scheme, "value_nick", None) or scheme).lower()
            if "dark" in nick:
                return True
            if "light" in nick:
                return False
        prefer = self._read_setting("gtk-application-prefer-dark-theme")
        return None if prefer is None else bool(prefer)

    def _desktop_prefers_dark(self):
        return bool(self._scheme_is_dark())

    def _reload_user_css(self):
        if self.display is None:
            return
        for provider in self._user_css_providers:
            Gtk.StyleContext.remove_provider_for_display(self.display, provider)
        self._user_css_providers = []
        gtk_css, dark_css = self._user_css_paths()
        wanted = [gtk_css]
        if self._desktop_prefers_dark():
            wanted.append(dark_css)
        loaded = []
        for path in wanted:
            if not os.path.exists(path):
                continue
            provider = Gtk.CssProvider()
            try:
                provider.load_from_path(os.path.realpath(path))
            except GLib.Error:
                continue
            Gtk.StyleContext.add_provider_for_display(
                self.display, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
            )
            self._user_css_providers.append(provider)
            loaded.append(os.path.basename(path))
        self._watch_user_css_files()
        self._log(f"reloaded user css: {loaded or 'none'}")

    def _schedule_system_refresh(self, reason=""):
        self._log(f"change signalled: {reason}")
        if self._refresh_source:
            GLib.source_remove(self._refresh_source)
        self._refresh_source = GLib.timeout_add(150, self._run_system_refresh)

    def _install_config_monitor(self):
        directory = Gio.File.new_for_path(
            os.path.join(GLib.get_user_config_dir(), "gtk-4.0")
        )
        try:
            self._config_monitor = directory.monitor_directory(
                Gio.FileMonitorFlags.NONE, None
            )
        except GLib.Error:
            return
        self._config_monitor.connect("changed", self._on_config_changed)

    def _on_config_changed(self, _monitor, file, other_file, event):
        wanted = (
            Gio.FileMonitorEvent.CHANGED,
            Gio.FileMonitorEvent.CHANGES_DONE_HINT,
            Gio.FileMonitorEvent.CREATED,
            Gio.FileMonitorEvent.RENAMED,
            Gio.FileMonitorEvent.MOVED_IN,
        )
        if event not in wanted:
            return
        names = {f.get_basename() for f in (file, other_file) if f is not None}
        if "settings.ini" not in names:
            return
        self._config_dirty = True
        self._schedule_system_refresh("settings.ini")

    def _run_system_refresh(self):
        self._refresh_source = 0
        self._config_dirty = False
        self._log(
            "state: theme=%r prefer_dark=%r scheme=%r"
            % (
                self._read_setting("gtk-theme-name"),
                self._read_setting("gtk-application-prefer-dark-theme"),
                self._read_setting("gtk-interface-color-scheme"),
            )
        )
        css_reloaded = False
        signature = self._compute_user_css_signature()
        if signature != self._user_css_signature:
            self._user_css_signature = signature
            self._reload_user_css()
            css_reloaded = True
        if not self.use_gtk_theme:
            return GLib.SOURCE_REMOVE
        try:
            current = self._system_palette()
        except Exception:
            current = None
        if not css_reloaded and current is not None and current == self._last_system_palette:
            self._log("desktop palette unchanged; nothing to do")
            return GLib.SOURCE_REMOVE
        self._log("desktop palette changed; re-rendering")
        self.apply(save=False)
        self._explain_palette()
        for callback in list(self._change_callbacks):
            try:
                callback()
            except Exception:
                pass
        return GLib.SOURCE_REMOVE

    def _on_system_theme_change(self, *args):
        if self._syncing_pref:
            return
        prop = getattr(args[1], "name", "") if len(args) > 1 else ""
        if not self.use_gtk_theme:
            if prop == "gtk-interface-color-scheme":
                self._orig_color_scheme = self._read_setting(prop)
                self._sync_system_preferences()
            elif prop == "gtk-application-prefer-dark-theme":
                self._orig_prefer_dark = self._read_setting(prop)
                self._sync_system_preferences()
            return
        self._schedule_system_refresh(f"notify::{prop}")
