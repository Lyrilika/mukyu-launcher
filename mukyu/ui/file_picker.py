
import fnmatch
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GLib, GObject, Gtk, Pango

from mukyu.platform_compat import IS_WINDOWS, host_env


_KDE_HINTS = ("dolphin", "konqueror", "krusader", "kde", "plasma")


def _default_file_manager():

    try:
        out = subprocess.run(
            ["xdg-mime", "query", "default", "inode/directory"],
            capture_output=True, text=True, timeout=3, env=host_env(),
        ).stdout.strip()
        if out:
            return out.lower()
    except Exception:
        pass
    try:
        info = Gio.AppInfo.get_default_for_type("inode/directory", False)
        if info is not None:
            return (info.get_id() or "").lower()
    except Exception:
        pass
    return ""


def _backend_order():
    fm = _default_file_manager()
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    kde = any(hint in fm for hint in _KDE_HINTS) or "kde" in desktop
    if kde:
        order = ["kdialog", "portal", "zenity", "qarma", "yad"]
    else:
        order = ["portal", "zenity", "qarma", "yad", "kdialog"]
    return order


def _host_which(name):
    return shutil.which(name, path=host_env().get("PATH"))


def _portal_pick(title, patterns, filter_name, start_dir, done):

    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        unique = bus.get_unique_name()
        if not unique:
            raise RuntimeError("no session bus")
    except Exception:
        done("fail", None)
        return

    sender = unique.lstrip(":").replace(".", "_")
    token = f"mukyu{os.getpid()}x{int(time.time() * 1000)}"
    handle = f"/org/freedesktop/portal/desktop/request/{sender}/{token}"
    state = {"sub": 0, "finished": False}

    def finish(status, path=None):
        if state["finished"]:
            return
        state["finished"] = True
        if state["sub"]:
            try:
                bus.signal_unsubscribe(state["sub"])
            except Exception:
                pass
            state["sub"] = 0
        done(status, path)

    def on_response(_conn, _sender, _path, _iface, _signal, params, *_rest):
        try:
            code, results = params.unpack()
        except Exception:
            finish("fail")
            return
        if code == 0:
            uris = results.get("uris") or []
            if uris:
                path = Gio.File.new_for_uri(uris[0]).get_path()
                if path:
                    finish("ok", path)
                    return
            finish("fail")
        elif code == 1:
            finish("cancel")
        else:
            finish("fail")

    state["sub"] = bus.signal_subscribe(
        "org.freedesktop.portal.Desktop",
        "org.freedesktop.portal.Request",
        "Response",
        handle,
        None,
        Gio.DBusSignalFlags.NONE,
        on_response,
    )

    options = {
        "handle_token": GLib.Variant("s", token),
        "modal": GLib.Variant("b", True),
    }
    if patterns:
        globs = []
        for pattern in patterns:
            globs.append((0, pattern))

            if pattern.startswith("*."):
                ext = pattern[2:]
                globs.append((0, "*." + "".join(f"[{c.lower()}{c.upper()}]" if c.isalpha() else c for c in ext)))
        options["filters"] = GLib.Variant("a(sa(us))", [(filter_name, globs)])
    if start_dir and os.path.isdir(start_dir):
        options["current_folder"] = GLib.Variant("ay", os.fsencode(start_dir) + b"\x00")

    def on_call_done(source, result):
        try:
            source.call_finish(result)
        except Exception:
            finish("fail")

    try:
        bus.call(
            "org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.FileChooser",
            "OpenFile",
            GLib.Variant("(ssa{sv})", ("", title, options)),
            GLib.VariantType("(o)"),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            on_call_done,
        )
    except Exception:
        finish("fail")


def _command_for(tool, title, patterns, filter_name, start_dir):
    exe = _host_which(tool)
    if not exe:
        return None
    start = (start_dir.rstrip("/") + "/") if start_dir and os.path.isdir(start_dir) else os.path.expanduser("~/")
    globs = []
    for pattern in patterns or []:
        globs.append(pattern)
        if pattern.startswith("*."):
            globs.append(pattern.upper())
    if tool == "kdialog":
        cmd = [exe, "--title", title, "--getopenfilename", start]
        if globs:
            cmd.append(" ".join(globs) + "|" + filter_name)
        return cmd
    cmd = [exe]
    if tool == "yad":
        cmd += ["--file"]
    else:
        cmd += ["--file-selection"]
    cmd += ["--title", title, "--filename", start]
    if globs:
        cmd += ["--file-filter", f"{filter_name} | " + " ".join(globs)]
    return cmd


def _external_pick(tool, title, patterns, filter_name, start_dir, done):
    cmd = _command_for(tool, title, patterns, filter_name, start_dir)
    if cmd is None:
        done("fail", None)
        return

    def work():
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, env=host_env())
        except Exception:
            GLib.idle_add(lambda: (done("fail", None), False)[1])
            return
        out = proc.stdout.strip().splitlines()
        path = out[0].strip() if out else ""
        if proc.returncode == 0 and path and os.path.isfile(path):
            result = ("ok", path)
        elif proc.returncode == 1 and not path:
            result = ("cancel", None)
        else:
            result = ("fail", None)
        GLib.idle_add(lambda: (done(*result), False)[1])

    threading.Thread(target=work, daemon=True, name="file-picker").start()


_KEEP_ALIVE = set()


def pick_file(parent, title, patterns, filter_name, start_dir, callback):

    if IS_WINDOWS:
        _pick_native_gtk(parent, title, patterns, filter_name, start_dir, callback)
        return

    def run_builtin():
        dialog = BuiltinFileDialog(parent, title, patterns, filter_name, start_dir, callback)
        dialog.present()

    def run_chain(order):
        if not order:
            run_builtin()
            return
        backend, rest = order[0], order[1:]

        def done(status, path):
            if status == "ok":
                callback(path)
            elif status == "cancel":
                callback(None)
            else:
                run_chain(rest)

        if backend == "portal":
            _portal_pick(title, patterns, filter_name, start_dir, done)
        else:
            _external_pick(backend, title, patterns, filter_name, start_dir, done)

    def start():
        order = _backend_order()


        order = [b for b in order if b == "portal" or _host_which(b)]
        run_chain(order)
        return False

    GLib.idle_add(start)


def _pick_native_gtk(parent, title, patterns, filter_name, start_dir, callback):
    dialog = Gtk.FileChooserNative.new(
        title=title, parent=parent, action=Gtk.FileChooserAction.OPEN,
        accept_label="Select", cancel_label="Cancel",
    )
    flt = Gtk.FileFilter()
    flt.set_name(filter_name)
    for pattern in patterns or []:
        flt.add_pattern(pattern)
    dialog.add_filter(flt)
    if start_dir and os.path.isdir(start_dir):
        try:
            dialog.set_current_folder(Gio.File.new_for_path(start_dir))
        except Exception:
            pass

    def on_response(dlg, response):
        path = None
        if response == Gtk.ResponseType.ACCEPT:
            file = dlg.get_file()
            path = file.get_path() if file is not None else None
        dlg.destroy()
        _KEEP_ALIVE.discard(dlg)
        callback(path)

    dialog.connect("response", on_response)
    _KEEP_ALIVE.add(dialog)
    dialog.show()


class _Entry(GObject.Object):
    def __init__(self, name, path, is_dir, size, mtime):
        super().__init__()
        self.name = name
        self.path = path
        self.is_dir = is_dir
        self.size = size
        self.mtime = mtime


def _human_size(size):
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{int(value)} B" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return ""


def _human_time(ts):
    try:
        moment = datetime.fromtimestamp(ts)
    except (OverflowError, OSError, ValueError):
        return ""
    if moment.year == datetime.now().year:
        return moment.strftime("%d %b  %H:%M")
    return moment.strftime("%d %b %Y")


def _places():
    places = [("Home", os.path.expanduser("~"), "user-home-symbolic")]
    specials = (
        (GLib.UserDirectory.DIRECTORY_DESKTOP, "Desktop", "user-desktop-symbolic"),
        (GLib.UserDirectory.DIRECTORY_DOCUMENTS, "Documents", "folder-documents-symbolic"),
        (GLib.UserDirectory.DIRECTORY_DOWNLOAD, "Downloads", "folder-download-symbolic"),
        (GLib.UserDirectory.DIRECTORY_MUSIC, "Music", "folder-music-symbolic"),
    )
    seen = {places[0][1]}
    for directory, label, icon in specials:
        path = GLib.get_user_special_dir(directory)
        if path and os.path.isdir(path) and path not in seen:
            seen.add(path)
            places.append((label, path, icon))
    return places


def _drives():
    drives = [("Computer", "/", "drive-harddisk-symbolic")]
    try:
        for mount in Gio.VolumeMonitor.get().get_mounts():
            root = mount.get_root()
            path = root.get_path() if root is not None else None
            if path and path != "/" and os.path.isdir(path):
                drives.append((mount.get_name() or os.path.basename(path), path, "drive-removable-media-symbolic"))
    except Exception:
        pass
    return drives


class BuiltinFileDialog(Gtk.Window):


    def __init__(self, parent, title, patterns, filter_name, start_dir, callback):
        super().__init__(title=title)
        self.add_css_class("fp-window")
        self.set_default_size(780, 520)
        self.set_modal(True)
        if isinstance(parent, Gtk.Window):
            self.set_transient_for(parent)
        self._callback = callback
        self._called = False
        self._patterns = [p.lower() for p in (patterns or [])]
        self._filter_name = filter_name
        self._show_all = not self._patterns
        self._show_hidden = False
        self._search = ""
        self._history = []
        self._hist_index = -1
        self._cwd = None
        self._load_token = 0

        self._store = Gio.ListStore.new(_Entry)
        self._filter = Gtk.CustomFilter.new(self._match)
        self._filtered = Gtk.FilterListModel(model=self._store, filter=self._filter)
        self._selection = Gtk.SingleSelection(model=self._filtered)
        self._selection.set_autoselect(False)
        self._selection.set_can_unselect(True)
        self._selection.connect("notify::selected", self._on_selection_changed)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.add_css_class("fp-root")
        root.append(self._build_toolbar())

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        body.set_vexpand(True)
        body.append(self._build_sidebar())
        body.append(self._build_list())
        root.append(body)
        root.append(self._build_footer())
        self.set_child(root)

        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)
        self.connect("close-request", self._on_close_request)

        start = start_dir if start_dir and os.path.isdir(start_dir) else os.path.expanduser("~")
        self.navigate(start)


    def _icon_button(self, icon, accessible_name, handler, toggle=False):
        button = Gtk.ToggleButton() if toggle else Gtk.Button()
        button.set_child(Gtk.Image.new_from_icon_name(icon))
        button.update_property([Gtk.AccessibleProperty.LABEL], [accessible_name])
        button.add_css_class("fp-icon-btn")
        button.set_has_frame(False)
        button.connect("toggled" if toggle else "clicked", handler)
        return button

    def _build_toolbar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        bar.add_css_class("fp-toolbar")
        self._back_btn = self._icon_button("go-previous-symbolic", "Back  (Alt+Left)", lambda *_: self._go_history(-1))
        self._fwd_btn = self._icon_button("go-next-symbolic", "Forward  (Alt+Right)", lambda *_: self._go_history(1))
        self._up_btn = self._icon_button("go-up-symbolic", "Parent folder  (Alt+Up)", lambda *_: self._go_up())
        for button in (self._back_btn, self._fwd_btn, self._up_btn):
            bar.append(button)

        self._path_entry = Gtk.Entry()
        self._path_entry.add_css_class("fp-path")
        self._path_entry.set_hexpand(True)
        self._path_entry.set_placeholder_text("Type a path and press Enter")
        self._path_entry.connect("activate", self._on_path_activate)
        bar.append(self._path_entry)

        self._search_entry = Gtk.SearchEntry()
        self._search_entry.add_css_class("fp-search")
        self._search_entry.set_placeholder_text("Filter")
        self._search_entry.set_size_request(160, -1)
        self._search_entry.connect("search-changed", self._on_search_changed)
        self._search_entry.connect("stop-search", lambda *_: self._list_view.grab_focus())
        bar.append(self._search_entry)

        self._hidden_btn = self._icon_button("view-reveal-symbolic", "Show hidden files  (Ctrl+H)", self._on_hidden_toggled, toggle=True)
        bar.append(self._hidden_btn)
        return bar

    def _build_sidebar(self):
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        side.add_css_class("fp-sidebar")
        side.set_size_request(168, -1)
        self._side_list = Gtk.ListBox()
        self._side_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._side_list.add_css_class("fp-side-list")
        self._side_paths = {}

        def add_row(label, path, icon):
            row = Gtk.ListBoxRow()
            row.add_css_class("fp-side-row")
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            image = Gtk.Image.new_from_icon_name(icon)
            image.set_pixel_size(16)
            text = Gtk.Label(label=label, xalign=0)
            text.set_ellipsize(Pango.EllipsizeMode.END)
            box.append(image)
            box.append(text)
            row.set_child(box)
            self._side_paths[row] = path
            self._side_list.append(row)

        for label, path, icon in _places():
            add_row(label, path, icon)
        for label, path, icon in _drives():
            add_row(label, path, icon)
        self._side_list.connect("row-activated", lambda _l, row: self.navigate(self._side_paths[row]))
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(self._side_list)
        scroll.set_vexpand(True)
        side.append(scroll)
        return side

    def _build_list(self):
        factory = Gtk.SignalListItemFactory()

        def setup(_f, item):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.add_css_class("fp-row")
            icon = Gtk.Image()
            icon.set_pixel_size(18)
            name = Gtk.Label(xalign=0)
            name.set_hexpand(True)
            name.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            name.add_css_class("fp-name")
            size = Gtk.Label(xalign=1)
            size.set_size_request(76, -1)
            size.add_css_class("fp-meta")
            when = Gtk.Label(xalign=1)
            when.set_size_request(116, -1)
            when.add_css_class("fp-meta")
            for widget in (icon, name, size, when):
                row.append(widget)
            row.fp = (icon, name, size, when)
            item.set_child(row)

        def bind(_f, item):
            entry = item.get_item()
            icon, name, size, when = item.get_child().fp
            if entry.is_dir:
                icon.set_from_icon_name("folder-symbolic")
                icon.add_css_class("fp-folder-icon")
                size.set_text("")
            else:
                icon.set_from_icon_name("application-x-executable-symbolic" if entry.name.lower().endswith(".exe") else "text-x-generic-symbolic")
                icon.remove_css_class("fp-folder-icon")
                size.set_text(_human_size(entry.size))
            name.set_text(entry.name)
            when.set_text(_human_time(entry.mtime))

        factory.connect("setup", setup)
        factory.connect("bind", bind)

        self._list_view = Gtk.ListView(model=self._selection, factory=factory)
        self._list_view.add_css_class("fp-list")
        self._list_view.set_single_click_activate(False)
        self._list_view.connect("activate", self._on_activate)

        self._empty = Gtk.Label(label="This folder is empty")
        self._empty.add_css_class("fp-empty")
        self._empty.set_valign(Gtk.Align.CENTER)
        self._empty.set_halign(Gtk.Align.CENTER)
        self._empty.set_visible(False)

        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.set_child(self._list_view)
        overlay = Gtk.Overlay()
        overlay.set_child(scroll)
        overlay.add_overlay(self._empty)
        self._empty.set_can_target(False)
        return overlay

    def _build_footer(self):
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        footer.add_css_class("fp-footer")

        self._type_model = Gtk.StringList.new([self._filter_name, "All files"] if self._patterns else ["All files"])
        self._type_drop = Gtk.DropDown(model=self._type_model)
        self._type_drop.add_css_class("fp-type")
        self._type_drop.connect("notify::selected", self._on_type_changed)
        footer.append(self._type_drop)

        self._status = Gtk.Label(xalign=0)
        self._status.add_css_class("fp-status")
        self._status.set_hexpand(True)
        self._status.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        footer.append(self._status)

        cancel = Gtk.Button(label="Cancel")
        cancel.add_css_class("fp-cancel")
        cancel.connect("clicked", lambda *_: self.close())
        self._accept_btn = Gtk.Button(label="Select")
        self._accept_btn.add_css_class("fp-accept")
        self._accept_btn.set_sensitive(False)
        self._accept_btn.connect("clicked", lambda *_: self._accept_selected())
        footer.append(cancel)
        footer.append(self._accept_btn)
        return footer


    def _name_matches(self, name):
        if self._show_all or not self._patterns:
            return True
        lowered = name.lower()
        return any(fnmatch.fnmatchcase(lowered, pattern) for pattern in self._patterns)

    def _match(self, entry):
        if not self._show_hidden and entry.name.startswith("."):
            return False
        if self._search and self._search not in entry.name.lower():
            return False
        return entry.is_dir or self._name_matches(entry.name)

    def _refilter(self):
        self._filter.changed(Gtk.FilterChange.DIFFERENT)
        self._empty.set_visible(self._filtered.get_n_items() == 0)
        self._update_status()

    def _on_search_changed(self, entry):
        self._search = entry.get_text().strip().lower()
        self._refilter()

    def _on_hidden_toggled(self, button):
        self._show_hidden = button.get_active()
        self._refilter()

    def _on_type_changed(self, dropdown, _param):
        self._show_all = (not self._patterns) or dropdown.get_selected() == 1
        self._refilter()


    def navigate(self, path, record=True):
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(path):
            self._flash_error("Not a folder")
            return
        if not os.access(path, os.R_OK | os.X_OK):
            self._flash_error("Permission denied")
            return
        if record:
            del self._history[self._hist_index + 1:]
            if not self._history or self._history[-1] != path:
                self._history.append(path)
            self._hist_index = len(self._history) - 1
        self._cwd = path
        self._path_entry.set_text(path)
        self._path_entry.remove_css_class("fp-error")
        self._search_entry.set_text("")
        self._search = ""
        self._update_nav_buttons()
        self._load(path)

    def _go_history(self, step):
        index = self._hist_index + step
        if 0 <= index < len(self._history):
            self._hist_index = index
            self.navigate(self._history[index], record=False)

    def _go_up(self):
        if self._cwd and self._cwd != "/":
            self.navigate(os.path.dirname(self._cwd))

    def _update_nav_buttons(self):
        self._back_btn.set_sensitive(self._hist_index > 0)
        self._fwd_btn.set_sensitive(self._hist_index < len(self._history) - 1)
        self._up_btn.set_sensitive(bool(self._cwd) and self._cwd != "/")

    def _flash_error(self, message):
        self._path_entry.add_css_class("fp-error")
        self._status.set_text(message)

    def _load(self, path):
        self._load_token += 1
        token = self._load_token
        self._status.set_text("Loading…")

        def work():
            entries = []
            try:
                with os.scandir(path) as it:
                    for de in it:
                        try:
                            is_dir = de.is_dir()
                            st = de.stat()
                            entries.append((de.name, de.path, is_dir, 0 if is_dir else st.st_size, st.st_mtime))
                        except OSError:
                            continue
            except OSError:
                pass
            entries.sort(key=lambda e: (not e[2], e[0].casefold()))
            GLib.idle_add(self._loaded, token, entries)

        threading.Thread(target=work, daemon=True, name="fp-scan").start()

    def _loaded(self, token, entries):
        if token != self._load_token:
            return False
        self._store.splice(0, self._store.get_n_items(), [_Entry(*e) for e in entries])
        self._selection.set_selected(Gtk.INVALID_LIST_POSITION)
        self._refilter()
        if self._filtered.get_n_items() and hasattr(self._list_view, "scroll_to"):
            self._list_view.scroll_to(0, Gtk.ListScrollFlags.NONE, None)
        return False


    def _selected_entry(self):
        position = self._selection.get_selected()
        if position == Gtk.INVALID_LIST_POSITION:
            return None
        return self._filtered.get_item(position)

    def _on_selection_changed(self, *_):
        entry = self._selected_entry()
        self._accept_btn.set_sensitive(entry is not None and not entry.is_dir)
        self._update_status()

    def _update_status(self):
        entry = self._selected_entry()
        if entry is not None:
            self._status.set_text(entry.path)
        else:
            count = self._filtered.get_n_items()
            self._status.set_text(f"{count} item{'s' if count != 1 else ''}")

    def _on_activate(self, _view, position):
        entry = self._filtered.get_item(position)
        if entry is None:
            return
        if entry.is_dir:
            self.navigate(entry.path)
        else:
            self._finish(entry.path)

    def _accept_selected(self):
        entry = self._selected_entry()
        if entry is not None and not entry.is_dir:
            self._finish(entry.path)

    def _on_path_activate(self, entry):
        text = entry.get_text().strip()
        if not text:
            return
        path = os.path.abspath(os.path.expanduser(text if os.path.isabs(os.path.expanduser(text)) else os.path.join(self._cwd or "/", text)))
        if os.path.isdir(path):
            self.navigate(path)
        elif os.path.isfile(path):
            self._finish(path)
        else:
            self._flash_error("No such file or folder")


    def _on_key(self, _controller, keyval, _keycode, state):
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        alt = bool(state & Gdk.ModifierType.ALT_MASK)
        if keyval == Gdk.KEY_Escape:
            if self._search_entry.get_text():
                self._search_entry.set_text("")
            else:
                self.close()
            return True
        if alt and keyval == Gdk.KEY_Left:
            self._go_history(-1)
            return True
        if alt and keyval == Gdk.KEY_Right:
            self._go_history(1)
            return True
        if alt and keyval == Gdk.KEY_Up:
            self._go_up()
            return True
        if ctrl and keyval in (Gdk.KEY_l, Gdk.KEY_L):
            self._path_entry.grab_focus()
            return True
        if ctrl and keyval in (Gdk.KEY_f, Gdk.KEY_F):
            self._search_entry.grab_focus()
            return True
        if ctrl and keyval in (Gdk.KEY_h, Gdk.KEY_H):
            self._hidden_btn.set_active(not self._hidden_btn.get_active())
            return True
        if keyval == Gdk.KEY_BackSpace:
            focus = self.get_focus()
            if focus is not None and (focus is self._list_view or focus.is_ancestor(self._list_view)):
                self._go_up()
                return True
        return False

    def _finish(self, path):
        if self._called:
            return
        self._called = True
        callback = self._callback
        self.close()
        callback(path)

    def _on_close_request(self, _window):
        if not self._called:
            self._called = True
            GLib.idle_add(lambda: (self._callback(None), False)[1])
        return False
