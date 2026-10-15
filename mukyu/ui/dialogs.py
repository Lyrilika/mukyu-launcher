

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Gtk

ACCENT = "accent"
DANGER = "danger"
NEUTRAL = "neutral"

_ROLE_CLASS = {ACCENT: "dlg-accent", DANGER: "dlg-danger", NEUTRAL: "dlg-neutral"}


def style_button(button, role):

    for name in _ROLE_CLASS.values():
        button.remove_css_class(name)
    button.add_css_class(_ROLE_CLASS.get(role, _ROLE_CLASS[NEUTRAL]))


def _deliver(callback, index):
    callback(index)
    return False


def show_dialog(parent, title, message, buttons, on_response=None, heading=None,
                default=0, cancel=-1):

    window = Gtk.Window(title=title, modal=True, resizable=False)
    window.add_css_class("pw-dialog")
    if isinstance(parent, Gtk.Window):
        window.set_transient_for(parent)
        window.set_destroy_with_parent(True)
    window.set_default_size(380, -1)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    for side in ("start", "end", "top", "bottom"):
        getattr(box, f"set_margin_{side}")(24)

    if heading:
        head = Gtk.Label(label=heading, xalign=0)
        head.add_css_class("popover-heading")
        head.set_wrap(True)
        head.set_max_width_chars(46)
        box.append(head)
    if message:
        body = Gtk.Label(label=message, xalign=0)
        body.set_wrap(True)
        body.set_max_width_chars(46)
        box.append(body)

    row = Gtk.Box(spacing=8)
    row.set_halign(Gtk.Align.END)
    row.set_margin_top(8)

    state = {"done": False}

    def resolve(index):
        if state["done"]:
            return
        state["done"] = True
        if on_response is not None:

            GLib.idle_add(_deliver, on_response, index)

    def make_handler(index):
        def clicked(_button):
            resolve(index)
            window.close()
        return clicked

    widgets = []
    for index, (label, role) in enumerate(buttons):
        button = Gtk.Button(label=label)
        style_button(button, role)
        button.connect("clicked", make_handler(index))
        row.append(button)
        widgets.append(button)

    box.append(row)
    window.set_child(box)

    def on_key(_controller, keyval, _keycode, _state):
        if keyval == Gdk.KEY_Escape:
            resolve(cancel)
            window.close()
            return True
        return False

    keys = Gtk.EventControllerKey()
    keys.connect("key-pressed", on_key)
    window.add_controller(keys)
    window.connect("close-request", lambda _window: (resolve(cancel), False)[1])

    if 0 <= default < len(widgets):
        window.set_default_widget(widgets[default])
        window.set_focus(widgets[default])

    window.present()
    return window
