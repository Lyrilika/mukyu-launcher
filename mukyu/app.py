from mukyu.paths import ASSETS_DIR, ICON_PATH
import os
import platform
import sys


os.environ.setdefault("MALLOC_ARENA_MAX", "2")
os.environ.setdefault("MALLOC_TRIM_THRESHOLD_", "131072")

PROCESS_NAME = "mukyulauncher"


def _set_process_name(name=PROCESS_NAME):

    if not sys.platform.startswith("linux"):
        return
    try:
        import ctypes
        libc = ctypes.CDLL(None, use_errno=True)
        libc.prctl(15, name.encode(), 0, 0, 0)
    except Exception:
        pass


_set_process_name()


def _trim_memory():
    try:
        import gc
        gc.collect()
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass
    return True


import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib, GObject

from mukyu.ui.theme import ThemeManager
from mukyu.ui.color_picker import ColorPicker
from mukyu.platform_compat import IS_WINDOWS


BASE_DIR = str(ASSETS_DIR)

if IS_WINDOWS:
    _exe_dir = os.path.dirname(sys.executable)
    if _exe_dir and _exe_dir not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = _exe_dir + os.pathsep + os.environ.get("PATH", "")


class LauncherApp(Gtk.Application):
    def __init__(self):
        GLib.set_prgname(PROCESS_NAME)
        GLib.set_application_name("Mukyu Launcher")
        super().__init__(application_id="mukyulauncher")
        self.theme_manager = None
        self.main_window = None
        self.settings_window = None
        self.settings_dim = None
        self.theme_dark_button = None
        self.theme_light_button = None
        self.theme_system_button = None
        self.accent_button = None
        self.accent_swatches = []
        self._updating_theme_controls = False
        self._tooltip_hook = 0

    def _install_tooltip_policy(self):
        if self._tooltip_hook:
            return

        def disable(widget, _property=None):
            if widget.get_has_tooltip():
                widget.set_has_tooltip(False)

        def mapped(_hint, _count, values, _data):
            widget = values[0]


            if not getattr(widget, "_mukyu_no_tooltips", False):
                widget._mukyu_no_tooltips = True
                widget.connect("notify::has-tooltip", disable)
            disable(widget)
            return True

        self._tooltip_hook = GObject.signal_add_emission_hook(
            GObject.signal_lookup("map", Gtk.Widget), 0, mapped, None)

    def _make_icon(self, name, size=18):
        image = Gtk.Image.new_from_icon_name(name)
        image.set_pixel_size(size)
        return image

    def _make_gear(self, size=21):
        gear = Gtk.Label(label="⚙")
        gear.add_css_class("launcher-settings-glyph")
        gear.set_size_request(size, size)
        gear.set_halign(Gtk.Align.CENTER)
        gear.set_valign(Gtk.Align.CENTER)
        return gear

    def _make_nav_button(self, icon_name, label, active=False, glyph=None):
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        content.set_halign(Gtk.Align.FILL)
        if glyph is not None:
            icon = Gtk.Label(label=glyph)
            icon.add_css_class("settings-nav-glyph")
            icon.set_size_request(16, 16)
        else:
            icon = self._make_icon(icon_name, 16)
        text = Gtk.Label(label=label, xalign=0)
        text.set_hexpand(True)
        content.append(icon)
        content.append(text)

        button = Gtk.Button()
        button.set_child(content)
        button.add_css_class("settings-nav-button")
        if active:
            button.add_css_class("settings-nav-active")
        return button

    def _make_row(self, title, description=None, control=None):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add_css_class("settings-row")

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        text.set_hexpand(True)
        text.set_valign(Gtk.Align.CENTER)
        title_label = Gtk.Label(label=title, xalign=0)
        title_label.add_css_class("settings-row-title")
        text.append(title_label)
        if description:
            desc_label = Gtk.Label(label=description, xalign=0)
            desc_label.add_css_class("settings-row-desc")
            desc_label.set_wrap(True)
            text.append(desc_label)
        row.append(text)

        if control is not None:
            control.set_valign(Gtk.Align.CENTER)
            row.append(control)
        return row

    def _make_section(self, title, rows, note=None):
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        section.add_css_class("settings-section")

        heading = Gtk.Label(label=title, xalign=0)
        heading.add_css_class("settings-section-title")
        section.append(heading)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.add_css_class("settings-card")
        for index, row in enumerate(rows):
            if index:
                separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                separator.add_css_class("settings-row-sep")
                card.append(separator)
            card.append(row)
        section.append(card)

        if note:
            note_label = Gtk.Label(label=note, xalign=0)
            note_label.add_css_class("settings-note")
            note_label.set_wrap(True)
            section.append(note_label)
        return section

    def _make_page(self, title):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.add_css_class("settings-page")
        page.set_margin_start(22)
        page.set_margin_end(22)
        page.set_margin_top(16)
        page.set_margin_bottom(22)
        heading = Gtk.Label(label=title, xalign=0)
        heading.add_css_class("settings-page-title")
        page.append(heading)
        return page

    def _make_about_page(self):
        page = self._make_page("About")
        identity = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        identity.set_halign(Gtk.Align.CENTER)
        identity.set_margin_top(8)
        identity.set_margin_bottom(8)
        icon = Gtk.Image.new_from_file(str(ICON_PATH))
        icon.set_pixel_size(112)
        identity.append(icon)
        name = Gtk.Label(label="Mukyu Launcher")
        name.add_css_class("settings-page-title")
        identity.append(name)
        github = Gtk.LinkButton.new_with_label("https://github.com/Lyrilika/mukyu-launcher", "GitHub")
        github.set_halign(Gtk.Align.CENTER)
        github.add_css_class("settings-github-button")
        content = Gtk.Box(spacing=10)
        content.set_halign(Gtk.Align.CENTER)
        logo = Gtk.Image.new_from_icon_name("github-symbolic")
        logo.set_pixel_size(22)
        content.append(logo)
        content.append(Gtk.Label(label="GitHub"))
        github.set_child(content)
        github.update_property([Gtk.AccessibleProperty.LABEL], ["GitHub repository"])
        identity.append(github)
        page.append(identity)
        system = "Windows" if IS_WINDOWS else platform.system()
        page.append(self._make_section("Build", [
            self._make_row(f"{system} build", platform.machine()),
        ]))
        return page

    def _build_settings_window(self):
        window = Gtk.Window()
        window.set_title("Settings")
        window.set_default_size(700, 470)
        window.set_resizable(True)
        window.set_hide_on_close(True)
        window.set_modal(False)
        window.set_destroy_with_parent(True)
        window.add_css_class("launcher-settings-window")
        if self.main_window is not None:
            window.set_transient_for(self.main_window)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        sidebar.add_css_class("settings-sidebar")
        sidebar.set_vexpand(True)

        sidebar_title = Gtk.Label(label="Settings", xalign=0)
        sidebar_title.add_css_class("settings-sidebar-title")
        sidebar.append(sidebar_title)

        nav_theme = self._make_nav_button(None, "Theme", active=True, glyph="◐")
        nav_about = self._make_nav_button("help-about-symbolic", "About")
        sidebar.append(nav_theme)
        sidebar.append(nav_about)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)
        scroller.add_css_class("settings-content")

        pages = Gtk.Stack()
        pages.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        pages.set_transition_duration(160)
        pages.set_hexpand(True)
        pages.set_vexpand(True)

        theme_page = self._make_page("Theme")

        SEG_W, SEG_H = 72, 28
        dark_button = Gtk.ToggleButton(label="Dark")
        light_button = Gtk.ToggleButton(label="Light")
        for button in (dark_button, light_button):
            button.add_css_class("theme-mode-button")
            button.set_size_request(SEG_W, SEG_H)
        dark_button.set_group(light_button)

        def mirror_active_class(button, css_class):
            def sync(*_):
                if button.get_active():
                    button.add_css_class(css_class)
                else:
                    button.remove_css_class(css_class)
            button.connect("notify::active", sync)
            sync()

        for button in (dark_button, light_button):
            mirror_active_class(button, "theme-mode-active")

        pill = Gtk.Box()
        pill.add_css_class("theme-mode-pill")
        pill.set_size_request(SEG_W, SEG_H)
        pill.set_halign(Gtk.Align.START)
        pill.set_valign(Gtk.Align.CENTER)
        track = Gtk.Box()
        track.set_size_request(SEG_W * 2, SEG_H)
        track.append(pill)

        segment_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        segment_buttons.append(dark_button)
        segment_buttons.append(light_button)

        segment_overlay = Gtk.Overlay()
        segment_overlay.set_child(track)
        segment_overlay.add_overlay(segment_buttons)

        mode_selector = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        mode_selector.add_css_class("theme-mode-selector")
        mode_selector.append(segment_overlay)

        pill_anim = {"pos": 0.0, "tick": None}

        def move_pill(index, animate):
            target = float(index * SEG_W)
            if pill_anim["tick"] is not None:
                pill.remove_tick_callback(pill_anim["tick"])
                pill_anim["tick"] = None
            if not animate or not pill.get_mapped():
                pill_anim["pos"] = target
                pill.set_margin_start(int(target))
                return
            start = pill_anim["pos"]
            if start == target:
                return
            began = [None]

            def tick(_widget, clock):
                now = clock.get_frame_time()
                if began[0] is None:
                    began[0] = now
                t = min(1.0, (now - began[0]) / 200000.0)
                eased = 1.0 - (1.0 - t) ** 3
                pill_anim["pos"] = start + (target - start) * eased
                pill.set_margin_start(int(round(pill_anim["pos"])))
                if t >= 1.0:
                    pill_anim["tick"] = None
                    return GLib.SOURCE_REMOVE
                return GLib.SOURCE_CONTINUE

            pill_anim["tick"] = pill.add_tick_callback(tick)

        gtk_check = Gtk.Switch()
        gtk_check.add_css_class("theme-system-switch")
        gtk_check.set_active(self.theme_manager.use_gtk_theme)

        mode_row = self._make_row("Mode", "Dark or light launcher palette", mode_selector)
        appearance_section = self._make_section(
            "Appearance",
            [
                mode_row,
                self._make_row(
                    "Use Windows theme" if IS_WINDOWS else "Use GTK theme",
                    "Follow your Windows dark/light mode and accent color instead of the manual colors"
                    if IS_WINDOWS
                    else "Follow your desktop theme and accent instead of the manual colors",
                    gtk_check,
                ),
            ],
        )
        theme_page.append(appearance_section)

        presets = [
            ("Pink", "#d96bc8"),
            ("Rose", "#e97fae"),
            ("Purple", "#9b87f5"),
            ("Blue", "#62a0ea"),
            ("Cyan", "#5cc8c8"),
            ("Green", "#78c98a"),
            ("Orange", "#e99a5a"),
            ("Yellow", "#d9bc66"),
        ]
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        preset_box.add_css_class("accent-preset-box")
        preset_buttons = []
        for name, color in presets:
            button = Gtk.ToggleButton()
            button.set_size_request(30, 30)
            button.update_property([Gtk.AccessibleProperty.LABEL], [name])
            button.add_css_class("accent-swatch")
            dot = Gtk.Box()
            dot.add_css_class("accent-dot")
            dot.add_css_class(f"accent-dot-{name.lower()}")
            dot.set_size_request(20, 20)
            dot.set_halign(Gtk.Align.CENTER)
            dot.set_valign(Gtk.Align.CENTER)
            button.set_child(dot)
            button.set_active(self.theme_manager.accent_color.lower() == color)
            preset_box.append(button)
            preset_buttons.append((button, color))
        self.accent_swatches = preset_buttons
        for button, _ in preset_buttons[1:]:
            button.set_group(preset_buttons[0][0])

        self.accent_picker = ColorPicker(self.theme_manager.accent_color, lambda c, final: on_picker_changed(c, final))
        self.accent_picker.set_margin_top(12)
        self.accent_picker.set_margin_bottom(12)
        self.accent_picker.set_margin_start(12)
        self.accent_picker.set_margin_end(12)
        picker_popover = Gtk.Popover()
        picker_popover.set_child(self.accent_picker)

        accent_swatch = Gtk.DrawingArea()
        accent_swatch.set_content_width(30)
        accent_swatch.set_content_height(16)

        def draw_accent_swatch(_area, cr, width, height):
            r, g, b = ThemeManager._hex_rgb(self.theme_manager.accent_color)
            cr.new_sub_path()
            radius = 5
            import math
            cr.arc(width - radius, radius, radius, -math.pi / 2, 0)
            cr.arc(width - radius, height - radius, radius, 0, math.pi / 2)
            cr.arc(radius, height - radius, radius, math.pi / 2, math.pi)
            cr.arc(radius, radius, radius, math.pi, 3 * math.pi / 2)
            cr.close_path()
            cr.set_source_rgb(r / 255.0, g / 255.0, b / 255.0)
            cr.fill()

        accent_swatch.set_draw_func(draw_accent_swatch)
        self.accent_swatch = accent_swatch
        self.accent_button = Gtk.MenuButton()
        self.accent_button.set_child(accent_swatch)
        self.accent_button.set_popover(picker_popover)
        self.accent_button.add_css_class("theme-accent-picker")

        accent_section = self._make_section(
            "Accent color",
            [
                self._make_row("Presets", None, preset_box),
                self._make_row("Custom color", "Pick any color with the picker", self.accent_button),
            ],
            note="The Music tab keeps its own album-art palette.",
        )
        theme_page.append(accent_section)
        pages.add_titled(theme_page, "theme", "Theme")

        about_page = self._make_about_page()
        pages.add_titled(about_page, "about", "About")

        pages.set_visible_child_name("theme")
        scroller.set_child(pages)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        body.add_css_class("settings-shell")
        body.append(sidebar)
        body.append(scroller)
        window.set_child(body)

        def show_page(name, selected_button):
            pages.set_visible_child_name(name)
            for button in (nav_theme, nav_about):
                button.remove_css_class("settings-nav-active")
            selected_button.add_css_class("settings-nav-active")

        nav_theme.connect("clicked", lambda *_: show_page("theme", nav_theme))
        nav_about.connect("clicked", lambda *_: show_page("about", nav_about))

        def on_key_pressed(_controller, keyval, _keycode, _state):
            if keyval == Gdk.KEY_Escape:
                window.close()
                return True
            return False

        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", on_key_pressed)
        window.add_controller(key_controller)

        self.theme_dark_button = dark_button
        self.theme_light_button = light_button
        self.theme_system_button = gtk_check

        def sync_mode_controls(animate):
            mode = self.theme_manager.effective_mode()
            self._updating_theme_controls = True
            dark_button.set_active(mode == "dark")
            light_button.set_active(mode == "light")
            self._updating_theme_controls = False
            move_pill(0 if mode == "dark" else 1, animate)

        def refresh_controls(animate=True):
            using_gtk = gtk_check.get_active()
            mode_row.set_sensitive(not using_gtk)
            mode_row.set_opacity(0.45 if using_gtk else 1.0)
            accent_section.set_sensitive(not using_gtk)
            accent_section.set_opacity(0.45 if using_gtk else 1.0)
            sync_mode_controls(animate)

        def on_mode_toggled(button, mode):
            if self._updating_theme_controls or not button.get_active():
                return
            self.theme_manager.set_mode(mode)
            move_pill(0 if mode == "dark" else 1, True)

        def on_gtk_toggled(button, _param=None):
            if self._updating_theme_controls:
                return
            self.theme_manager.set_use_gtk_theme(button.get_active())
            refresh_controls(True)

        pending_accent = {"color": None, "timer": 0}

        def flush_accent():
            pending_accent["timer"] = 0
            color = pending_accent["color"]
            if color:
                self.theme_manager.set_accent_color(color, save=False)
                self.accent_swatch.queue_draw()
            return False

        def on_picker_changed(color, final):
            if self._updating_theme_controls:
                return
            self._updating_theme_controls = True
            for swatch, preset_color in preset_buttons:
                swatch.set_active(preset_color.lower() == color.lower())
            self._updating_theme_controls = False
            if final:
                if pending_accent["timer"]:
                    GLib.source_remove(pending_accent["timer"])
                    pending_accent["timer"] = 0
                pending_accent["color"] = None
                self.theme_manager.set_accent_color(color)
                self.accent_swatch.queue_draw()
            else:
                pending_accent["color"] = color
                if not pending_accent["timer"]:
                    pending_accent["timer"] = GLib.timeout_add(40, flush_accent)

        def on_swatch_toggled(button, color):
            if not button.get_active() or self._updating_theme_controls:
                return
            self._updating_theme_controls = True
            self.theme_manager.set_accent_color(color)
            self.accent_picker.set_hex(color)
            self.accent_swatch.queue_draw()
            self._updating_theme_controls = False

        dark_button.connect("toggled", lambda b: on_mode_toggled(b, "dark"))
        light_button.connect("toggled", lambda b: on_mode_toggled(b, "light"))
        gtk_check.connect("notify::active", on_gtk_toggled)
        for swatch, color in preset_buttons:
            swatch.connect("toggled", lambda button, color=color: on_swatch_toggled(button, color))

        self.theme_manager.connect_change(lambda: refresh_controls(True))
        refresh_controls(False)

        def on_close_request(_window):
            if self.settings_dim is not None:
                self.settings_dim.set_visible(False)
                self.settings_dim.set_can_target(False)
            return False

        window.connect("close-request", on_close_request)
        return window

    def close_settings(self):
        if self.settings_window is not None:
            self.settings_window.close()

    def open_settings(self):
        if self.settings_window is None:
            self.settings_window = self._build_settings_window()

        if self.settings_dim is not None:
            self.settings_dim.set_visible(True)
            self.settings_dim.set_can_target(True)
        self.settings_window.present()

    def _warm_pages(self, window, stack, music, printworks):
        original_transition = stack.get_transition_type()
        original_child = stack.get_visible_child_name() or "games"
        state = {"done": False}
        steps = ("printworks", "music")
        music.mukyu_warm = True
        stack.set_transition_type(Gtk.StackTransitionType.NONE)

        def finish():
            if state["done"]:
                return False
            state["done"] = True
            try:
                stack.set_visible_child_name(original_child)
                stack.set_transition_type(original_transition)
            finally:
                music.mukyu_warm = False
                window.set_opacity(1.0)
            try:
                import gc
                gc.collect()
                gc.freeze()
            except Exception:
                pass
            return False

        def step(index):
            if state["done"]:
                return False
            if index < len(steps):
                try:
                    stack.set_visible_child_name(steps[index])
                except Exception:
                    pass
                GLib.timeout_add(180, step, index + 1)
            else:
                GLib.timeout_add(60, finish)
            return False

        GLib.timeout_add(200, step, 0)
        GLib.timeout_add(4000, finish)

    def do_activate(self):
        _icons = os.path.join(BASE_DIR, "icons")
        if os.path.isdir(_icons):
            _display = Gdk.Display.get_default()
            if _display is not None:
                Gtk.IconTheme.get_for_display(_display).add_search_path(_icons)
                Gtk.Window.set_default_icon_name("mukyulauncher")
        from mukyu.pages.games import create_games_page, TYPE_SCALE
        from mukyu.pages.printworks import create_printworks_page
        try:
            from mukyu.pages.music import create_music_page
        except (ImportError, ValueError) as exc:
            missing_reason = str(exc)

            def create_music_page(_theme_manager=None):
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
                box.set_valign(Gtk.Align.CENTER)
                box.set_halign(Gtk.Align.CENTER)
                title = Gtk.Label(label="Music is unavailable")
                title.add_css_class("gs-heading")
                detail = Gtk.Label(
                    label="The music player needs GStreamer (with its base/good/libav plugins).\n"
                          "Install it and restart the launcher.\n\n" + missing_reason
                )
                detail.set_justify(Gtk.Justification.CENTER)
                detail.set_wrap(True)
                box.append(title)
                box.append(detail)
                return box

        window = Gtk.ApplicationWindow(application=self)
        self.main_window = window
        self._install_tooltip_policy()
        window.set_title("Mukyu Launcher")
        window.set_default_size(1280, 720)
        window.add_css_class("launcher-window")

        display = Gdk.Display.get_default()
        css_path = os.path.join(BASE_DIR, "styles", "style.css")
        self.theme_manager = ThemeManager(display, css_path)
        self.theme_manager.apply(save=False)
        self.theme_manager.install_system_followup()

        window.connect(
            "notify::is-active",
            lambda w, _p: w.is_active() and self.theme_manager.refresh_from_system("window focus"),
        )

        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        stack.set_transition_duration(280)
        stack.set_vexpand(True)
        stack.add_css_class("launcher-bg")
        stack.connect(
            "notify::transition-running",
            lambda s, _p: s.set_can_target(not s.get_transition_running()),
        )
        stack_switcher = Gtk.StackSwitcher(stack=stack)
        stack_switcher.remove_css_class("linked")
        stack_switcher.add_css_class("tab-switcher")
        stack_switcher.set_margin_top(10)
        page_games = create_games_page()
        page_music = create_music_page(self.theme_manager)
        page_printworks = create_printworks_page()

        stack.add_titled(page_games, "games", "Games")
        stack.add_titled(page_music, "music", "Music")
        stack.add_titled(page_printworks, "printworks", "Print Works")
        stack_switcher.set_halign(Gtk.Align.CENTER)
        stack_switcher.set_margin_bottom(10)

        def mirror_tab_state():
            tab = stack_switcher.get_first_child()
            while tab is not None:
                if isinstance(tab, Gtk.ToggleButton) and not getattr(tab, "_tab_mirrored", False):
                    tab._tab_mirrored = True

                    def sync(button, *_):
                        if button.get_active():
                            button.add_css_class("tab-active")
                        else:
                            button.remove_css_class("tab-active")

                    tab.connect("notify::active", sync)
                    sync(tab)
                tab = tab.get_next_sibling()

        mirror_tab_state()
        stack.connect("notify::visible-child", lambda *_: mirror_tab_state())

        header_overlay = Gtk.CenterBox()
        header_overlay.add_css_class("launcher-header")
        header_overlay.set_center_widget(stack_switcher)

        settings_button = Gtk.Button()
        settings_button.set_child(self._make_gear())
        settings_button.add_css_class("launcher-settings-button")
        settings_button.update_property([Gtk.AccessibleProperty.LABEL], ["Settings"])
        settings_button.set_halign(Gtk.Align.END)
        settings_button.set_valign(Gtk.Align.CENTER)
        settings_button.set_margin_end(12)
        settings_button.set_margin_top(8)
        settings_button.set_margin_bottom(8)
        settings_button.connect("clicked", lambda *_: self.open_settings())
        header_overlay.set_end_widget(settings_button)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        container.add_css_class("launcher-bg")
        container.append(header_overlay)
        container.append(stack)

        content_overlay = Gtk.Overlay()
        content_overlay.add_css_class("launcher-bg")
        content_overlay.set_child(container)

        settings_dim = Gtk.Box()
        settings_dim.add_css_class("settings-main-dim")
        settings_dim.set_hexpand(True)
        settings_dim.set_vexpand(True)
        settings_dim.set_can_target(False)
        settings_dim.set_visible(False)
        dim_click = Gtk.GestureClick()
        dim_click.connect("pressed", lambda *_: self.close_settings())
        settings_dim.add_controller(dim_click)
        content_overlay.add_overlay(settings_dim)
        self.settings_dim = settings_dim
        window.set_child(content_overlay)

        self.theme_manager.apply(save=False)

        scale_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            display, scale_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 3
        )
        applied_font_size = [None]
        pending_resize = {"timer": 0}

        def apply_scale(width, height):
            scale = max(0.65, min(1.0, min(width / 1280, height / 720)))
            font_size = int(12 * scale)
            if font_size == applied_font_size[0]:
                return
            applied_font_size[0] = font_size
            rules = [f"* {{ font-size: {font_size}px; }}"]
            rules += [
                f".{name} {{ font-size: {max(1, round(font_size * factor))}px; }}"
                for name, factor in TYPE_SCALE.items()
            ]
            scale_provider.load_from_data("\n".join(rules).encode())

        def resize_scale(widget, width, height):


            if applied_font_size[0] is None:
                apply_scale(width, height)
                return
            if pending_resize["timer"]:
                GLib.source_remove(pending_resize["timer"])

            def settle():
                pending_resize["timer"] = 0
                apply_scale(window.get_width(), window.get_height())
                return False

            pending_resize["timer"] = GLib.timeout_add(90, settle)

        window.connect("notify::width", lambda w, p: resize_scale(w, w.get_width(), w.get_height()))
        window.connect("notify::height", lambda w, p: resize_scale(w, w.get_width(), w.get_height()))


        window.set_opacity(0.0)
        window.present()
        self._warm_pages(window, stack, page_music, page_printworks)
        if sys.platform.startswith("linux"):
            GLib.timeout_add_seconds(6, lambda: (_trim_memory(), False)[1])
            GLib.timeout_add_seconds(45, _trim_memory)


def main():
    app = LauncherApp()
    return app.run(None)
