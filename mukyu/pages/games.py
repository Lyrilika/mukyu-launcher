from mukyu.paths import ROOT_DIR, ASSETS_DIR, TOOLS_DIR
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

from mukyu.ui import file_picker
from mukyu.ui.dialogs import ACCENT, NEUTRAL, show_dialog
from mukyu.platform_compat import (
    IS_WINDOWS, GameJob, cache_home, config_home, data_home, host_env, split_launch_options,
)

import gi
gi.require_version("Gsk", "4.0")
gi.require_version("Graphene", "1.0")
from gi.repository import Gtk, Gdk, Gio, GLib, Gsk, Graphene, Pango

try:
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf
except (ImportError, ValueError):
    GdkPixbuf = None

OPEN_SETTINGS_WINDOWS = []
COVER_JOBS = []
SETTINGS_REFRESHERS = {}
SETTINGS_PAGE_ROOT = None
SETTINGS_DISMISS_GESTURE = None
ACTIVE_GAME = None
ACTIVE_GAME_TITLE = None


def _set_main_window_dimmed(dimmed):
    global SETTINGS_DISMISS_GESTURE

    if SETTINGS_PAGE_ROOT is None:
        return
    root = SETTINGS_PAGE_ROOT.get_root()
    if not isinstance(root, Gtk.Window):
        return
    main_child = root.get_child()
    if not isinstance(main_child, Gtk.Overlay):
        return

    child = main_child.get_first_child()
    while child is not None:
        if child.has_css_class("settings-main-dim"):
            if SETTINGS_DISMISS_GESTURE is None:
                SETTINGS_DISMISS_GESTURE = Gtk.GestureClick.new()
                SETTINGS_DISMISS_GESTURE.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

                def dismiss_from_scrim(_gesture, _n_press, _x, _y):
                    if any(
                        popup is not None and popup.is_visible()
                        for _button, popup in OPEN_SETTINGS_WINDOWS
                    ):
                        dismiss_settings_windows()
                        _gesture.set_state(Gtk.EventSequenceState.CLAIMED)

                SETTINGS_DISMISS_GESTURE.connect("pressed", dismiss_from_scrim)
                child.add_controller(SETTINGS_DISMISS_GESTURE)

            child.set_visible(dimmed)
            child.set_can_target(dimmed)
            return
        child = child.get_next_sibling()

BASE_DIR = str(ROOT_DIR)
CONFIG_FILE = os.path.join(
    config_home(),
    "mukyulauncher",
    "games_config.json",
)
PREFIX_ROOT = os.path.join(
    data_home(),
    "mukyulauncher",
    "prefixes",
)
UMU_DATA_ROOT = os.path.join(
    data_home(),
    "umu",
)
UMU_RUNTIME_NAME = "steamrt4"
DOSBOX_ROOT = os.path.join(data_home(), "mukyulauncher", "dosbox-x")
DOSBOX_BINARY = os.path.join(DOSBOX_ROOT, "dosbox-x.exe" if IS_WINDOWS else "dosbox-x")


PLAYTIME_FILE = os.path.join(
    data_home(),
    "mukyulauncher",
    "playtime.json",
)


def load_playtime():
    try:
        with open(PLAYTIME_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_playtime(data):
    os.makedirs(os.path.dirname(PLAYTIME_FILE), exist_ok=True)
    with open(PLAYTIME_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def add_playtime(game_key, seconds):
    if not game_key:
        return
    data = load_playtime()
    entry = data.setdefault(game_key, {"seconds": 0})
    entry["seconds"] += int(seconds)
    save_playtime(data)


def get_playtime_text(game_key):
    seconds = load_playtime().get(game_key, {}).get("seconds", 0)

    if seconds <= 0:
        return ""

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"Playtime: {hours}h {minutes}m {secs}s"
CARD_WIDTH = 210
COVER_ASPECT = 1.012
CARD_PAD = 10
CARD_BORDER = 1
COVER_W = CARD_WIDTH - 2 * CARD_BORDER - 2 * CARD_PAD - 2 * CARD_BORDER
COVER_H = round(COVER_W / COVER_ASPECT)
CARD_IMG_HEIGHT = COVER_H
CARD_SPACING = 16

TYPE_SCALE = {
    "gl-title": 2.2,
    "game-card-title": 1.0,
    "game-card-status": 0.82,
    "gc-badge-text": 0.8,
    "gs-heading": 1.25,
    "rb-caption": 0.75,
    "rb-name": 1.1,
    "rb-time": 0.9,
}

ACTIVE_CARD = None


def get_umu_path():
    bundled = str(TOOLS_DIR / "umu" / "umu-run")
    if os.path.isfile(bundled) and os.access(bundled, os.X_OK):
        return bundled
    return "umu-run"


def get_config_dir():
    path = os.path.dirname(CONFIG_FILE)
    os.makedirs(path, exist_ok=True)
    return path


def load_config():
    get_config_dir()
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            raw = json.loads(content) if content else {}
    else:
        raw = {}

    config = {}
    for game_key, value in raw.items():
        if isinstance(value, str):
            config[game_key] = {
                "exe": value,
                "launch_options": "",
                "runner": "wine",
            }
        else:
            runner = value.get("runner", "wine")
            if runner not in ("wine", "ge-proton", "dosbox-x"):
                runner = "wine"
            config[game_key] = {
                "exe": value.get("exe"),
                "launch_options": value.get("launch_options", ""),
                "runner": runner,
            }
    return config


def save_config(config):
    get_config_dir()
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    os.replace(tmp, CONFIG_FILE)


class GameFlowBox(Gtk.FlowBox):

    def _columns_for(self, content_width):
        return max(1, int((content_width + CARD_SPACING) // (CARD_WIDTH + CARD_SPACING)))

    def do_measure(self, orientation, for_size):
        min_size, nat_size, min_baseline, nat_baseline = Gtk.FlowBox.do_measure(
            self, orientation, for_size
        )
        if orientation == Gtk.Orientation.HORIZONTAL:
            min_size = CARD_WIDTH + self.get_margin_start() + self.get_margin_end()
            return (min_size, max(nat_size, min_size), min_baseline, nat_baseline)

        if for_size > 0:
            columns = self._columns_for(for_size)
            count = 0
            row_height = 0
            child = self.get_first_child()
            while child is not None:
                if child.get_visible():
                    count += 1
                    child_min, child_nat, _mb, _nb = child.measure(
                        Gtk.Orientation.VERTICAL, -1
                    )
                    row_height = max(row_height, child_min, child_nat)
                child = child.get_next_sibling()
            if count:
                rows = -(-count // columns)
                height = rows * row_height + (rows - 1) * self.get_row_spacing()
                return (height, height, -1, -1)
        return (min_size, nat_size, min_baseline, nat_baseline)

    def do_size_allocate(self, width, height, baseline):
        columns = self._columns_for(width)
        if self.get_max_children_per_line() != columns:
            self.set_max_children_per_line(columns)
            self.set_min_children_per_line(columns)
        Gtk.FlowBox.do_size_allocate(self, width, height, baseline)


class AspectCover(Gtk.Widget):

    def __init__(self, width, height):
        super().__init__()
        self._w = width
        self._h = height
        self.set_overflow(Gtk.Overflow.HIDDEN)

    def set_child(self, child):
        old = self.get_first_child()
        if old is not None:
            old.unparent()
        if child is not None:
            child.set_parent(self)

    def do_measure(self, orientation, for_size):
        size = self._w if orientation == Gtk.Orientation.HORIZONTAL else self._h
        return (size, size, -1, -1)

    def do_size_allocate(self, width, height, baseline):
        child = self.get_first_child()
        if child is not None:
            child.allocate(width, height, -1, None)

    def do_dispose(self):
        child = self.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            child.unparent()
            child = next_child
        Gtk.Widget.do_dispose(self)


SquareCover = AspectCover


def _format_session(seconds):
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def _set_running_card(card):
    global ACTIVE_CARD
    previous = ACTIVE_CARD
    if previous is not None and previous is not card:
        previous.remove_css_class("is-running")
        badge = getattr(previous, "running_badge", None)
        if badge is not None:
            badge.set_visible(False)
    ACTIVE_CARD = card
    if card is not None:
        card.add_css_class("is-running")
        badge = getattr(card, "running_badge", None)
        if badge is not None:
            badge.set_visible(True)


def _build_library_header():
    header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    header.add_css_class("gl-header")
    header.set_margin_start(10)
    header.set_margin_end(10)

    title = Gtk.Label(label="Game Library")
    title.add_css_class("gl-title")
    title.set_halign(Gtk.Align.START)
    header.append(title)
    return header


def create_games_page():
    global SETTINGS_PAGE_ROOT

    outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    SETTINGS_PAGE_ROOT = outer_box
    outer_box.add_css_class("gl-page")
    outer_box.set_margin_start(20)
    outer_box.set_margin_end(20)
    outer_box.set_margin_top(12)
    outer_box.set_margin_bottom(20)

    outer_box.append(_build_library_header())

    scroll = Gtk.ScrolledWindow()
    scroll.set_vexpand(True)
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    flow_box = GameFlowBox()
    flow_box.set_hexpand(True)
    flow_box.set_row_spacing(CARD_SPACING)
    flow_box.set_column_spacing(CARD_SPACING)
    flow_box.set_margin_start(10)
    flow_box.set_margin_end(10)
    flow_box.set_margin_top(14)
    flow_box.set_margin_bottom(84)
    flow_box.set_valign(Gtk.Align.START)
    flow_box.set_homogeneous(True)
    flow_box.set_selection_mode(Gtk.SelectionMode.NONE)
    flow_box.add_css_class("game-library")

    config = load_config()
    games = [
        ("Touhou 1: The Highly Responsive to Prayers", "th1", "th1.jpg"),
        ("Touhou 2: Story of Eastern Wonderland", "th2", "th2.jpg"),
        ("Touhou 3: Phantasmagoria of Dim.Dream", "th3", "th3.jpg"),
        ("Touhou 4: Lotus Land Story", "th4", "th4.jpg"),
        ("Touhou 5: Mystic Square", "th5", "th5.jpg"),
        ("Touhou 6: The Embodiment of Scarlet Devil", "th6", "th6.jpg"),
        ("Touhou 7: Perfect Cherry Blossom", "th7", "th7.jpg"),
        ("Touhou 7.5: Immaterial and Missing Power", "th7.5", "th75.jpg"),
        ("Touhou 8: Imperishable Night", "th8", "th8.jpg"),
        ("Touhou 9: Phantasmagoria of Flower View", "th9", "th9.jpg"),
        ("Touhou 9.5: Shoot the Bullet", "th9.5", "th95.jpg"),
        ("Touhou 10: Mountain of Faith", "th10", "th10.jpg"),
        ("Touhou 10.5: Scarlet Weather Rhapsody", "th10.5", "th105.jpg"),
        ("Touhou 11: Subterranean Animism", "th11", "th11.jpg"),
        ("Touhou 12: Undefined Fantastic Object", "th12", "th12.jpg"),
        ("Touhou 12.3: Hisoutensoku", "th12.3", "th123.jpg"),
        ("Touhou 12.5: Double Spoiler", "th12.5", "th125.jpg"),
        ("Touhou 12.8: Great Fairy Wars", "th12.8", "th128.jpg"),
        ("Touhou 13: Ten Desires", "th13", "th13.jpg"),
        ("Touhou 13.5: Hopeless Masquerade", "th13.5", "th135.jpg"),
        ("Touhou 14: Double Dealing Character", "th14", "th14.jpg"),
        ("Touhou 14.3: Impossible Spell Card", "th14.3", "th143.jpg"),
        ("Touhou 14.5: Urban Legend in Limbo", "th14.5", "th145.jpg"),
        ("Touhou 15: Legacy of Lunatic Kingdom", "th15", "th15.jpg"),
        ("Touhou 15.5: Antinomy of Common Flowers", "th15.5", "th155.jpg"),
        ("Touhou 16: Hidden Star in Four Seasons", "th16", "th16.jpg"),
        ("Touhou 16.5: Violet Detector", "th16.5", "th165.jpg"),
        ("Touhou 17: Wily Beast and Weakest Creature", "th17", "th17.jpg"),
        ("Touhou 17.5: Sunken Fossil World", "th17.5", "th175.jpg"),
        ("Touhou 18: Unconnected Marketeers", "th18", "th18.jpg"),
        ("Touhou 18.5: 100th Black Market", "th18.5", "th185.jpg"),
        ("Touhou 19: Unfinished Dream of All Living Ghost", "th19", "th19.jpg"),
        ("Touhou 20: Fossilized Wonders", "th20", "th20.jpg"),
    ]

    running_bar = create_running_bar()
    running_bar.set_visible(False)

    COVER_JOBS.clear()
    for index, (game_title, game_key, image_file) in enumerate(games):
        card = create_game_card(game_title, game_key, image_file, config, running_bar)
        appear = f"appear-{min(index % 8 + index // 8, 10)}"
        card.add_css_class(appear)
        GLib.timeout_add(1500, lambda c=card, a=appear: (c.remove_css_class(a), False)[1])
        flow_box.append(card)
    load_covers_in_background(list(COVER_JOBS))
    COVER_JOBS.clear()

    scroll.set_child(flow_box)
    library_overlay = Gtk.Overlay()
    library_overlay.set_child(scroll)
    library_overlay.set_measure_overlay(running_bar, False)
    library_overlay.add_overlay(running_bar)
    running_bar.set_halign(Gtk.Align.FILL)
    running_bar.set_valign(Gtk.Align.END)
    outer_box.append(library_overlay)

    outside_click = Gtk.GestureClick()
    outside_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

    def on_outside_click(gesture, _n_press, _x, _y):
        visible_windows = [
            window for _button, window in OPEN_SETTINGS_WINDOWS
            if window is not None and window.is_visible()
        ]
        if not visible_windows:
            return

        dismiss_settings_windows()
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    outside_click.connect("pressed", on_outside_click)
    outer_box.add_controller(outside_click)
    return outer_box

def ge_proton_directory():
    return os.path.join(data_home(), "Steam", "compatibilitytools.d")


def ge_proton_installed():
    directory = ge_proton_directory()
    if not os.path.isdir(directory):
        return False
    return any(
        name.startswith("GE-Proton") and os.path.isdir(os.path.join(directory, name))
        for name in os.listdir(directory)
    )


def latest_ge_proton_info():
    api_url = "https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/latest"
    request = urllib.request.Request(
        api_url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Mukyu-Launcher"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        release = json.load(response)

    if os.uname().machine in ("x86_64", "amd64"):
        suffix = "-x86_64.tar.gz"
    elif os.uname().machine in ("aarch64", "arm64"):
        suffix = "-aarch64.tar.gz"
    else:
        raise RuntimeError(f"Unsupported architecture: {os.uname().machine}")

    tarball_url = None
    checksum_url = None
    tarball_name = None

    for asset in release.get("assets", []):
        name = asset.get("name", "")
        url = asset.get("browser_download_url")
        if name.endswith(suffix):
            tarball_name = name
            tarball_url = url

    if not tarball_url or not tarball_name:
        raise RuntimeError("Could not find the latest GE-Proton release for this architecture")

    expected_checksum_name = f"{tarball_name[:-len('.tar.gz')]}.sha512sum"
    for asset in release.get("assets", []):
        if asset.get("name") == expected_checksum_name:
            checksum_url = asset.get("browser_download_url")
            break

    release_name = tarball_name[:-len(".tar.gz")]
    return release_name, tarball_url, checksum_url


def _download_file_with_progress(url, destination, progress_callback):
    request = urllib.request.Request(url, headers={"User-Agent": "Mukyu-Launcher"})
    with urllib.request.urlopen(request, timeout=30) as response, open(destination, "wb") as output:
        total = response.headers.get("Content-Length")
        total = int(total) if total else 0
        downloaded = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            downloaded += len(chunk)
            if total:
                progress_callback(min(100, int(downloaded * 100 / total)))
            else:
                progress_callback(None)


def _read_sha512sum_file(path, tarball_name):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].lstrip("*") == tarball_name:
            return parts[0]
    for line in text.splitlines():
        value = line.strip().split()[0] if line.strip() else ""
        if len(value) == 128 and all(c in "0123456789abcdefABCDEF" for c in value):
            return value
    return None


def _install_latest_ge_proton(progress_callback):
    release_name, tarball_url, checksum_url = latest_ge_proton_info()
    install_dir = ge_proton_directory()
    target_dir = os.path.join(install_dir, release_name)

    if os.path.isdir(target_dir):
        progress_callback(100)
        return True

    os.makedirs(install_dir, exist_ok=True)
    tarball_name = os.path.basename(tarball_url)

    with tempfile.TemporaryDirectory(prefix="mukyu-ge-proton-") as temp_dir:
        tarball_path = os.path.join(temp_dir, tarball_name)
        checksum_path = os.path.join(temp_dir, f"{tarball_name}.sha512sum")

        progress_callback(0)
        _download_file_with_progress(tarball_url, tarball_path, progress_callback)

        if checksum_url:
            _download_file_with_progress(checksum_url, checksum_path, lambda _percent: None)
            expected = _read_sha512sum_file(checksum_path, tarball_name)
            if expected:
                digest = hashlib.sha512()
                with open(tarball_path, "rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                if digest.hexdigest().lower() != expected.lower():
                    raise RuntimeError("GE-Proton checksum verification failed")

        staging_dir = tempfile.mkdtemp(prefix="ge-proton-install-", dir=install_dir)
        try:
            with tarfile.open(tarball_path, "r:gz") as archive:
                root = os.path.realpath(staging_dir)
                for member in archive.getmembers():
                    destination = os.path.realpath(os.path.join(staging_dir, member.name))
                    if not destination.startswith(root + os.sep):
                        raise RuntimeError("Unsafe path found in GE-Proton archive")
                if hasattr(tarfile, 'data_filter'):
                    archive.extractall(staging_dir, filter='data')
                else:
                    archive.extractall(staging_dir)

            extracted = os.path.join(staging_dir, release_name)
            if not os.path.isdir(extracted):
                raise RuntimeError("GE-Proton archive did not contain the expected directory")
            os.replace(extracted, target_dir)
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

    progress_callback(100)
    return True


def update_runner_status(label):
    if ge_proton_installed():
        label.set_text("GE-Proton: installed")
        label.remove_css_class("runner-missing")
        label.add_css_class("runner-installed")
    else:
        label.set_text("GE-Proton: not downloaded")
        label.remove_css_class("runner-installed")
        label.add_css_class("runner-missing")


def on_download_ge_clicked(button, status_label, download_button, progress_bar=None):
    download_button.set_sensitive(False)
    status_label.set_text("GE-Proton: checking for latest release…")
    status_label.remove_css_class("runner-missing")
    status_label.remove_css_class("runner-installed")
    status_label.add_css_class("runner-downloading")
    if progress_bar is not None:
        progress_bar.set_fraction(0)
        progress_bar.set_text("0%")
        progress_bar.set_visible(True)

    def update_progress(percent):
        def update():
            if percent is None:
                status_label.set_text("GE-Proton: downloading…")
                if progress_bar is not None:
                    progress_bar.set_text("Downloading…")
            else:
                status_label.set_text(f"GE-Proton: downloading… {percent}%")
                if progress_bar is not None:
                    progress_bar.set_fraction(percent / 100.0)
                    progress_bar.set_text(f"{percent}%")
            return False
        GLib.idle_add(update)

    def worker():
        try:
            ok = _install_latest_ge_proton(update_progress)
        except Exception as error:
            ok = False
            error_text = str(error)
        else:
            error_text = ""

        def finish():
            download_button.set_sensitive(True)
            status_label.remove_css_class("runner-downloading")
            if progress_bar is not None:
                progress_bar.set_fraction(1.0 if ok else progress_bar.get_fraction())
                progress_bar.set_text("100%" if ok else "Failed")
            update_runner_status(status_label)
            if not ok:
                status_label.set_text(f"GE-Proton: download failed — {error_text}")
                status_label.add_css_class("runner-missing")
            return False

        GLib.idle_add(finish)

    threading.Thread(target=worker, daemon=True).start()


def dismiss_settings_windows(except_window=None):
    for _button, popup in OPEN_SETTINGS_WINDOWS:
        if popup is not except_window and popup.is_visible():
            popup.hide()

COVER_PX = 340


def _prepare_cover(path):
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
    width, height = pixbuf.get_width(), pixbuf.get_height()
    ratio = min(1.0, COVER_PX / min(width, height))
    if ratio < 1.0:
        width, height = max(1, round(width * ratio)), max(1, round(height * ratio))
        pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
    return pixbuf


def load_covers_in_background(jobs):
    if GdkPixbuf is None:
        for picture, path in jobs:
            picture.set_filename(path)
        return

    def apply(picture, pixbuf):
        picture.set_paintable(Gdk.Texture.new_for_pixbuf(pixbuf))
        picture.add_css_class("cover-pop")
        return False

    def work():
        for picture, path in jobs:
            try:
                pixbuf = _prepare_cover(path)
            except Exception:
                GLib.idle_add(lambda p=picture, f=path: (p.set_filename(f), False)[1])
                continue
            GLib.idle_add(apply, picture, pixbuf)

    threading.Thread(target=work, daemon=True, name="cover-loader").start()


def create_game_card(title, game_key, image_file, config, running_bar):
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    card.set_size_request(CARD_WIDTH, -1)
    card.set_halign(Gtk.Align.CENTER)
    card.add_css_class("game-card")
    card.set_overflow(Gtk.Overflow.HIDDEN)

    entry = config.get(game_key, {})
    exe_path = entry.get("exe")
    runner = entry.get("runner", "wine")
    if runner not in ("wine", "ge-proton", "dosbox-x"):
        runner = "wine"

    if exe_path and os.path.exists(exe_path):
        card.add_css_class("enabled-card")
    else:
        card.add_css_class("disabled-card")

    cover_overlay = Gtk.Overlay()
    cover_overlay.set_size_request(COVER_W, COVER_H)

    thumb = Gtk.Picture()
    thumb.add_css_class("game-cover")
    thumb.set_content_fit(Gtk.ContentFit.COVER)
    thumb.set_can_shrink(True)
    COVER_JOBS.append((thumb, str(ASSETS_DIR / "covers" / image_file)))
    cover_frame = AspectCover(COVER_W, COVER_H)
    cover_frame.set_child(thumb)
    cover_overlay.set_child(cover_frame)

    badge = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    badge.add_css_class("gc-badge")
    badge.set_halign(Gtk.Align.START)
    badge.set_valign(Gtk.Align.START)
    badge.set_can_target(False)
    badge_dot = Gtk.Box()
    badge_dot.add_css_class("gc-badge-dot")
    badge_dot.set_valign(Gtk.Align.CENTER)
    badge_text = Gtk.Label(label="Playing")
    badge_text.add_css_class("gc-badge-text")
    badge.append(badge_dot)
    badge.append(badge_text)
    badge.set_visible(False)
    cover_overlay.add_overlay(badge)
    card.running_badge = badge

    settings_icon = Gtk.Image.new_from_gicon(
        Gio.ThemedIcon.new_from_names(["emblem-system-symbolic", "preferences-system-symbolic"])
    )
    settings_icon.set_pixel_size(16)
    settings_button = Gtk.Button()
    settings_button.set_child(settings_icon)
    settings_button.add_css_class("settings-button")
    settings_button.set_has_frame(False)
    settings_button.set_halign(Gtk.Align.END)
    settings_button.set_valign(Gtk.Align.START)
    cover_overlay.add_overlay(settings_button)

    info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    info_box.add_css_class("game-card-info")
    info_box.set_vexpand(True)
    info_box.set_valign(Gtk.Align.CENTER)

    title_label = Gtk.Label()
    title_label.add_css_class("game-card-title")
    title_label.set_halign(Gtk.Align.CENTER)
    title_label.set_justify(Gtk.Justification.CENTER)
    title_label.set_xalign(0.5)
    title_label.set_wrap(True)
    title_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
    title_label.set_lines(2)
    title_label.set_ellipsize(Pango.EllipsizeMode.END)
    title_label.set_max_width_chars(20)

    status_label = Gtk.Label()
    status_label.add_css_class("game-card-status")
    status_label.set_halign(Gtk.Align.CENTER)

    card.title_label = title_label
    card.status_label = status_label

    update_title_label(title_label, title, exe_path, runner, card=card, game_key=game_key)

    info_box.append(title_label)
    info_box.append(status_label)

    cover_outline = Gtk.Box()
    cover_outline.add_css_class("game-cover-frame")
    cover_outline.set_overflow(Gtk.Overflow.HIDDEN)
    cover_outline.set_halign(Gtk.Align.CENTER)
    cover_outline.set_margin_top(CARD_PAD)
    cover_outline.set_margin_start(CARD_PAD)
    cover_outline.set_margin_end(CARD_PAD)
    cover_outline.append(cover_overlay)

    card.append(cover_outline)
    card.append(info_box)

    settings_window = None

    def toggle_settings(_button):
        nonlocal settings_window
        if settings_window is None:
            settings_window = create_settings_window(
                settings_button, title, game_key, config, title_label, card
            )
            OPEN_SETTINGS_WINDOWS.append((settings_button, settings_window))

            def mark_open(_window):
                settings_button.add_css_class("settings-open")
                card.add_css_class("settings-active")
                if SETTINGS_PAGE_ROOT is not None:
                    SETTINGS_PAGE_ROOT.add_css_class("settings-hover-blocked")
                _set_main_window_dimmed(True)

            def mark_closed(_window):
                settings_button.remove_css_class("settings-open")
                card.remove_css_class("settings-active")
                if SETTINGS_PAGE_ROOT is not None and not any(
                    popup is not None and popup.is_visible()
                    for _button, popup in OPEN_SETTINGS_WINDOWS
                ):
                    SETTINGS_PAGE_ROOT.remove_css_class("settings-hover-blocked")
                    _set_main_window_dimmed(False)

            settings_window.connect("show", mark_open)
            settings_window.connect("hide", mark_closed)

        if settings_window.is_visible():
            settings_window.hide()
        else:
            dismiss_settings_windows(settings_window)
            settings_window.present()

    settings_button.connect("clicked", toggle_settings)

    click_controller = Gtk.GestureClick.new()
    click_controller.connect(
        "pressed", on_card_clicked, title, game_key, config, title_label, card, settings_button, running_bar
    )
    card.add_controller(click_controller)

    def on_press_fx(_gesture, _n_press, x, y):
        target = card.pick(x, y, Gtk.PickFlags.DEFAULT)
        if target is not None and _is_descendant(target, settings_button):
            return
        card.set_state_flags(Gtk.StateFlags.ACTIVE, False)
        GLib.timeout_add(450, lambda: (card.unset_state_flags(Gtk.StateFlags.ACTIVE), False)[1])

    press_fx = Gtk.GestureClick.new()
    press_fx.connect("pressed", on_press_fx)
    press_fx.connect("released", lambda *_a: card.unset_state_flags(Gtk.StateFlags.ACTIVE))
    press_fx.connect("stopped", lambda *_a: card.unset_state_flags(Gtk.StateFlags.ACTIVE))
    card.add_controller(press_fx)
    return card


def update_title_label(label, title, exe_path, runner, card=None, game_key=None):
    label.set_text(title)
    if exe_path:
        label.remove_css_class("heading-disabled")
        label.add_css_class("heading-enabled")
    else:
        label.add_css_class("heading-disabled")
        label.remove_css_class("heading-enabled")
    if card is not None and hasattr(card, "status_label"):
        sl = card.status_label
        if not exe_path:
            sl.set_text("Not set")
            sl.add_css_class("game-card-status-unset")
            sl.set_visible(True)
        else:
            sl.set_visible(False)


def _is_descendant(widget, ancestor):
    while widget is not None:
        if widget == ancestor:
            return True
        widget = widget.get_parent()
    return False


def on_card_clicked(controller, n_press, x, y, title, game_key, config, label, card, settings_button, running_bar):
    target = card.pick(x, y, Gtk.PickFlags.DEFAULT)
    if target is not None and _is_descendant(target, settings_button):
        return

    entry = config.get(game_key, {})
    exe_path = entry.get("exe")
    if exe_path and os.path.exists(exe_path):
        launch_game(
            exe_path,
            entry.get("launch_options", ""),
            entry.get("runner", "wine"),
            game_key,
            card,
            title,
            running_bar,
        )
    else:
        prompt_for_exe(title, game_key, config, label, card)


def _find_windows_dosbox():
    best = None
    for folder, dirs, files in os.walk(DOSBOX_ROOT):
        if folder[len(DOSBOX_ROOT):].count(os.sep) > 4:
            dirs[:] = []
            continue
        if "dosbox-x.exe" in (name.lower() for name in files):
            path = os.path.join(folder, "dosbox-x.exe")
            rank = (0 if "sdl2" in path.lower() else 1, len(path))
            if best is None or rank < best[0]:
                best = (rank, path)
    if best:
        return best[1]
    for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), "C:\\"):
        if not root:
            continue
        for sub in ("DOSBox-X", "DOSBox-X-Windows"):
            candidate = os.path.join(root, sub, "dosbox-x.exe")
            if os.path.isfile(candidate):
                return candidate
    return shutil.which("dosbox-x")


def get_dosbox_path():
    if IS_WINDOWS:
        return _find_windows_dosbox()
    candidates = (
        DOSBOX_BINARY,
        os.path.join(DOSBOX_ROOT, "dosbox-x.AppImage"),
        os.path.join(DOSBOX_ROOT, "dosbox-x"),
    )
    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    system = shutil.which("dosbox-x")
    if system:
        return system

    return None


def dosbox_installed():
    return get_dosbox_path() is not None

def _install_dosbox_windows(update_status):
    os.makedirs(DOSBOX_ROOT, exist_ok=True)
    api = "https://api.github.com/repos/joncampbell123/dosbox-x/releases/latest"
    req = urllib.request.Request(api, headers={"User-Agent": "MukyuLauncher"})
    with urllib.request.urlopen(req, timeout=15) as response:
        release = json.loads(response.read().decode("utf-8"))

    assets = [
        a for a in release.get("assets", [])
        if a.get("name", "").lower().endswith(".zip") and "win64" in a.get("name", "").lower()
        and "arm" not in a.get("name", "").lower() and "lowend" not in a.get("name", "").lower()
    ]
    assets.sort(key=lambda a: (0 if "mingw" in a["name"].lower() else 1))
    if not assets:
        raise RuntimeError("No compatible DOSBox-X build found")
    asset = assets[0]

    with tempfile.TemporaryDirectory(prefix="mukyu-dosbox-") as temp_dir:
        archive = os.path.join(temp_dir, "dosbox-x.zip")
        asset_req = urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": "MukyuLauncher"})
        with urllib.request.urlopen(asset_req, timeout=30) as response, open(archive, "wb") as f:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total:
                    update_status(f"Downloading DOSBox-X... {int(done * 100 / total)}%")

        update_status("Unpacking DOSBox-X...")
        staging = tempfile.mkdtemp(prefix="unpack-", dir=DOSBOX_ROOT)
        try:
            with zipfile.ZipFile(archive) as zf:
                root = os.path.realpath(staging)
                for member in zf.namelist():
                    target = os.path.realpath(os.path.join(staging, member))
                    if target != root and not target.startswith(root + os.sep):
                        raise RuntimeError("Unsafe path found in DOSBox-X archive")
                zf.extractall(staging)
            if not any(n.lower() == "dosbox-x.exe" for _d, _s, names in os.walk(staging) for n in names):
                raise RuntimeError("dosbox-x.exe was not found in the download")
            for name in os.listdir(DOSBOX_ROOT):
                old = os.path.join(DOSBOX_ROOT, name)
                if old != staging and os.path.isdir(old) and not os.path.islink(old):
                    shutil.rmtree(old, ignore_errors=True)
            os.replace(staging, os.path.join(DOSBOX_ROOT, "windows-build"))
            staging = None
        finally:
            if staging:
                shutil.rmtree(staging, ignore_errors=True)


def install_dosbox(button, status):
    global DOSBOX_BINARY

    def update_status(text):
        GLib.idle_add(status.set_text, text)

    if IS_WINDOWS:
        def windows_worker():
            try:
                update_status("Downloading DOSBox-X...")
                _install_dosbox_windows(update_status)
                update_status("Installed")
            except Exception as e:
                update_status("Install failed: " + str(e))

        threading.Thread(target=windows_worker, daemon=True).start()
        return

    def worker():
        try:
            update_status("Downloading DOSBox-X...")

            os.makedirs(DOSBOX_ROOT, exist_ok=True)

            api = "https://api.github.com/repos/pkgforge-dev/DOSBox-X-AppImage/releases/latest"
            req = urllib.request.Request(api, headers={"User-Agent": "MukyuLauncher"})
            with urllib.request.urlopen(req, timeout=15) as response:
                release = json.loads(response.read().decode("utf-8"))

            asset_url = None
            for asset in release.get("assets", []):
                name = asset.get("name", "").lower()
                if "appimage" in name and ("x86_64" in name or "amd64" in name):
                    asset_url = asset.get("browser_download_url")
                    break

            if not asset_url:
                raise RuntimeError("No compatible DOSBox-X build found")

            out = os.path.join(DOSBOX_ROOT, "dosbox-x.AppImage")

            asset_req = urllib.request.Request(asset_url, headers={"User-Agent": "MukyuLauncher"})
            with urllib.request.urlopen(asset_req, timeout=30) as response, open(out, "wb") as f:
                total = response.headers.get("Content-Length")
                total = int(total) if total else 0
                done = 0

                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        percent = int(done * 100 / total)
                        update_status(f"Downloading DOSBox-X... {percent}%")

            os.chmod(out, 0o755)

            try:
                if os.path.exists(DOSBOX_BINARY):
                    os.remove(DOSBOX_BINARY)
                os.symlink(out, DOSBOX_BINARY)
            except Exception:
                pass

            update_status("Installed")

        except Exception as e:
            update_status("Install failed: " + str(e))

    threading.Thread(target=worker, daemon=True).start()


def dosbox_config_for_touhou(rom):
    rom = os.path.abspath(rom)
    return [
        "-set", "machine=pc98",
        "-set", "sdl output=opengl",
        "-set", "sdl fullscreen=true",
        "-set", "sdl fullresolution=desktop",
        "-set", "render aspect=true",
        "-set", "render aspect_ratio=4:3",
        "-set", "cpu cycles=max",
        "-c", f'IMGMOUNT C "{rom}"',
        "-c", "C:",
        "-c", "GAME"
    ]

def show_dosbox_missing(parent=None):
    window = None
    if parent is not None:
        try:
            root = parent.get_root()
            if isinstance(root, Gtk.Window):
                window = root
        except Exception:
            pass

    show_dialog(
        window,
        "DOSBox-X",
        "Use the Download DOSBox-X button in the settings, or manually install DOSBox-X and restart the app.",
        [("OK", ACCENT)],
        heading="DOSBox-X is not installed",
        default=0,
        cancel=0,
    )

def build_launch_command(exe_path, launch_options, runner, game_key):
    if runner == "dosbox-x":
        db = get_dosbox_path()
        if not db:
            raise FileNotFoundError("DOSBox-X is not installed")
        return [db] + dosbox_config_for_touhou(exe_path), os.environ.copy()
    options = (launch_options or "").strip()
    if IS_WINDOWS:
        base_command = [exe_path]
        if "%command%" in options:
            before, after = options.split("%command%", 1)
            command = split_launch_options(before) + base_command + split_launch_options(after)
        else:
            command = base_command + (split_launch_options(options) if options else [])
        return command, os.environ.copy()
    option_parts = shlex.split(options) if options else []
    game_dir = os.path.dirname(os.path.abspath(exe_path))

    if runner == "ge-proton":
        prefix = os.path.join(PREFIX_ROOT, game_key)
        os.makedirs(prefix, exist_ok=True)
        env = os.environ.copy()
        env["WINEPREFIX"] = prefix
        env["GAMEID"] = "0"
        env["PROTONPATH"] = "GE-Proton"
        env["STEAM_COMPAT_INSTALL_PATH"] = game_dir
        env["STEAM_COMPAT_LIBRARY_PATHS"] = game_dir
        umu = get_umu_path()
        base_command = [umu, exe_path]
        if "%command%" in options:
            before, after = options.split("%command%", 1)
            before_args = shlex.split(before) if before.strip() else []
            after_args = shlex.split(after) if after.strip() else []
            command = before_args + base_command + after_args
        else:
            command = base_command + option_parts
        return command, env

    env = os.environ.copy()
    base_command = ["wine", exe_path]
    if "%command%" in options:
        before, after = options.split("%command%", 1)
        before_args = shlex.split(before) if before.strip() else []
        after_args = shlex.split(after) if after.strip() else []
        command = before_args + base_command + after_args
    else:
        command = base_command + option_parts
    return command, env


def show_runner_error(card, title):
    root = card.get_root()
    parent = root if isinstance(root, Gtk.Window) else None
    show_dialog(
        parent,
        "GE-Proton",
        f"Download GE-Proton from the settings for {title} before launching this game with GE-Proton.",
        [("OK", ACCENT)],
        heading="GE-Proton is not installed",
        default=0,
        cancel=0,
    )


def show_running_error(card, title, launch_callback):
    root = card.get_root()
    parent = root if isinstance(root, Gtk.Window) else None
    same_game = ACTIVE_GAME_TITLE == title
    if same_game:
        heading = "This game is already running"
        message = f"{title} is already running."
        confirm_label = "Close & Relaunch"
    else:
        current_title = ACTIVE_GAME_TITLE or "the current game"
        heading = "A game is already running"
        message = f"Close {current_title} first and then launch {title}?"
        confirm_label = "Close Current Game"

    def response(selected):
        if selected == 0:
            stop_current_game_and_then(launch_callback)

    show_dialog(
        parent,
        "Game running",
        message,
        [(confirm_label, ACCENT), ("Cancel", NEUTRAL)],
        on_response=response,
        heading=heading,
        default=0,
        cancel=1,
    )


def umu_runtime_installed():
    runtime_dir = os.path.join(UMU_DATA_ROOT, UMU_RUNTIME_NAME)
    if not os.path.isdir(runtime_dir):
        return False
    try:
        with os.scandir(runtime_dir) as entries:
            return next(entries, None) is not None
    except OSError:
        return False


def create_umu_setup_window(card):
    root = card.get_root()
    parent = root if isinstance(root, Gtk.Window) else None

    window = Gtk.Window()
    window.set_title("UMU Setup")
    window.set_modal(True)
    window.set_deletable(False)
    window.set_resizable(False)
    if parent is not None:
        window.set_transient_for(parent)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.set_margin_start(24)
    box.set_margin_end(24)
    box.set_margin_top(20)
    box.set_margin_bottom(20)

    title = Gtk.Label(label="UMU is setting up")
    title.add_css_class("popover-heading")
    title.set_halign(Gtk.Align.START)
    box.append(title)

    runtime = Gtk.Label(label=f"Installing runtime: {UMU_RUNTIME_NAME}")
    runtime.set_halign(Gtk.Align.START)
    box.append(runtime)

    progress = Gtk.ProgressBar()
    progress.set_show_text(True)
    progress.set_fraction(0)
    progress.set_text("0%")
    box.append(progress)

    status = Gtk.Label(label="Preparing…")
    status.set_halign(Gtk.Align.START)
    status.add_css_class("running-status")
    box.append(status)

    window.set_child(box)
    window.present()

    while GLib.MainContext.default().pending():
        GLib.MainContext.default().iteration(False)

    return window, runtime, progress, status


def monitor_umu_setup(process, window, runtime_label, progress_bar, status_label):
    def worker():
        finished = False
        announced = False
        log = _open_launch_log(process.args if isinstance(process.args, list) else [str(process.args)], "ge-proton (first run)", getattr(process, "_mukyu_game_key", "?"))
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                if log is not None:
                    try:
                        log.write(line.encode("utf-8", "replace"))
                    except OSError:
                        pass
                if announced:

                    continue
                line = line.strip()
                runtime_match = re.search(r"runtime ['\"]([^'\"]+)['\"]", line)
                percent_matches = re.findall(r"(?<!\d)(\d{1,3})%", line)
                percent = int(percent_matches[-1]) if percent_matches else None
                runtime_name = runtime_match.group(1) if runtime_match else None
                if "Running '" in line and "using runtime" in line:
                    finished = True

                def update(runtime_name=runtime_name, percent=percent, finished=finished):
                    if runtime_name:
                        runtime_label.set_text(f"Installing runtime: {runtime_name}")
                    if percent is not None:
                        value = min(100, percent)
                        progress_bar.set_fraction(value / 100.0)
                        progress_bar.set_text(f"{value}%")
                    if finished:
                        progress_bar.set_fraction(1.0)
                        progress_bar.set_text("100%")
                        status_label.set_text("Setup complete")
                        window.close()
                    elif percent is not None:
                        status_label.set_text("Downloading…")
                    return False

                GLib.idle_add(update)
                if finished:
                    announced = True
        finally:
            if log is not None:
                log.close()
            def close_if_needed():
                if window.get_visible() and process.poll() is not None:
                    if process.returncode == 0:
                        progress_bar.set_fraction(1.0)
                        progress_bar.set_text("100%")
                        status_label.set_text("Setup complete")
                    else:
                        status_label.set_text("Setup finished with an error")
                    window.close()
                return False
            GLib.idle_add(close_if_needed)

    threading.Thread(target=worker, daemon=True).start()


def prompt_for_exe(title, game_key, config, label, card):
    root = card.get_root()
    parent = root if isinstance(root, Gtk.Window) else None
    pc98 = game_key in ("th1", "th2", "th3", "th4", "th5")
    if pc98:
        patterns = ["*.hdi", "*.nhd", "*.fdi", "*.img", "*.d88"]
        filter_name = "PC-98 ROM images"
    else:
        patterns = ["*.exe"]
        filter_name = "Executable files"

    current = (config.get(game_key) or {}).get("exe")
    start_dir = os.path.dirname(current) if current and os.path.isdir(os.path.dirname(current)) else None

    def on_picked(path):
        if path:
            on_dialog_response(path, title, game_key, config, label, card)

    file_picker.pick_file(
        parent,
        f"Select ROM for {title}" if pc98 else f"Select EXE for {title}",
        patterns,
        filter_name,
        start_dir,
        on_picked,
    )


def on_dialog_response(path, title, game_key, config, label, card):
    entry = config.setdefault(
        game_key, {"exe": None, "launch_options": "", "runner": "wine"}
    )
    entry["exe"] = path
    if game_key in ("th1", "th2", "th3", "th4", "th5"):
        entry["runner"] = "dosbox-x"
    else:
        entry.setdefault("runner", "wine")
    save_config(config)
    update_title_label(label, title, path, entry["runner"], card=card, game_key=game_key)
    if game_key in SETTINGS_REFRESHERS:
        SETTINGS_REFRESHERS[game_key]()
    card.remove_css_class("disabled-card")
    card.add_css_class("enabled-card")


def proc_exists(pid):
    if IS_WINDOWS:
        return False
    status_path = f"/proc/{pid}/stat"
    try:
        data = Path(status_path).read_text(encoding="utf-8", errors="replace")
    except (FileNotFoundError, PermissionError, OSError):
        return False
    closing = data.rfind(")")
    if closing == -1:
        return True
    fields = data[closing + 2:].split()
    return not fields or fields[0] != "Z"


def proc_children(pid):
    path = f"/proc/{pid}/task/{pid}/children"
    try:
        data = Path(path).read_text(encoding="ascii").strip()
    except (FileNotFoundError, PermissionError, OSError):
        return []
    return [int(value) for value in data.split() if value.isdigit()]


def process_tree_snapshot(root_pid, known=None):
    pids = set(known or ())
    if IS_WINDOWS:
        return pids
    if proc_exists(root_pid):
        pids.add(root_pid)
        pending = [root_pid]
        seen = set()
        while pending:
            pid = pending.pop()
            if pid in seen or not proc_exists(pid):
                continue
            seen.add(pid)
            children = proc_children(pid)
            for child in children:
                if child not in pids:
                    pids.add(child)
                if child not in seen:
                    pending.append(child)
    return pids


def process_group_has_live_member(pgid):
    try:
        entries = os.listdir("/proc")
    except OSError:
        return False
    prefix = "/proc/"
    for name in entries:
        if not name.isdigit():
            continue
        path = f"{prefix}{name}/stat"
        try:
            data = Path(path).read_text(encoding="ascii")
        except (FileNotFoundError, PermissionError, OSError):
            continue
        closing = data.rfind(")")
        if closing == -1:
            continue
        fields = data[closing + 2:].split()
        if len(fields) >= 3 and fields[0] != "Z":
            try:
                if int(fields[2]) == pgid:
                    return True
            except ValueError:
                continue
    return False


SESSION_ENV_VAR = "MUKYU_LAUNCHER_SESSION"

WINE_SYSTEM_EXES = {
    "services.exe", "winedevice.exe", "plugplay.exe", "svchost.exe", "explorer.exe",
    "rpcss.exe", "conhost.exe", "start.exe", "winemenubuilder.exe", "wineboot.exe",
    "rundll32.exe", "mscorsvw.exe", "tabtip.exe", "steam.exe", "iexplore.exe",
    "winedbg.exe", "cmd.exe",
}


def _session_marker(token):
    return f"{SESSION_ENV_VAR}={token}".encode()


def session_pids(token):
    if not token:
        return []
    marker = _session_marker(token)
    own_pid = os.getpid()
    found = []
    try:
        entries = os.listdir("/proc")
    except OSError:
        return found
    for name in entries:
        if not name.isdigit() or int(name) == own_pid:
            continue
        try:
            with open(f"/proc/{name}/environ", "rb") as f:
                environ = f.read()
        except OSError:
            continue
        if marker in environ.split(b"\0") and proc_exists(int(name)):
            found.append(int(name))
    return found


def _windows_exe_name(pid):
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            argv = f.read().split(b"\0")
    except OSError:
        return None
    for arg in argv[:2]:
        text = arg.decode("utf-8", "replace").strip()
        base = re.split(r"[\\/]", text)[-1].lower()
        if base.endswith(".exe"):
            return base
    return None


def session_game_alive(token):
    for pid in session_pids(token):
        exe = _windows_exe_name(pid)
        if exe and exe not in WINE_SYSTEM_EXES:
            return True
    return False


def process_tree_exists(process):
    if process is None:
        return False
    if IS_WINDOWS:
        job = getattr(process, "_mukyu_job", None)
        if job is not None and job.ok:
            return job.active_count() > 0
        return process.poll() is None
    process.poll()
    if process.returncode is None:
        return True
    if process_group_has_live_member(process.pid):
        return True
    state = getattr(process, "_mukyu_tree_pids", set())
    state = {pid for pid in state if proc_exists(pid)}
    state.update(process_tree_snapshot(process.pid, state))
    process._mukyu_tree_pids = state
    state.discard(process.pid)
    if any(proc_exists(pid) for pid in state):
        return True
    return session_game_alive(getattr(process, "_mukyu_session", None))


def send_process_group_signal(process, signal):
    if IS_WINDOWS:
        job = getattr(process, "_mukyu_job", None)
        if signal == 15:
            if job is not None and job.ok:
                job.request_close()
            elif process.poll() is None:
                process.terminate()
        elif job is not None:
            job.terminate()
        else:
            process.kill()
        return
    try:
        os.killpg(process.pid, signal)
    except ProcessLookupError:
        pass
    except PermissionError:
        try:
            process.send_signal(signal)
        except ProcessLookupError:
            pass
    for pid in session_pids(getattr(process, "_mukyu_session", None)):
        try:
            os.kill(pid, signal)
        except (ProcessLookupError, PermissionError):
            pass


def stop_current_game_and_then(callback):
    global ACTIVE_GAME
    process = ACTIVE_GAME
    if process is None:
        callback()
        return
    send_process_group_signal(process, 15)
    elapsed = 0

    def finish_stop():
        nonlocal elapsed
        global ACTIVE_GAME
        if not process_tree_exists(process):
            ACTIVE_GAME = None
            _set_running_card(None)
            callback()
            return False
        elapsed += 100
        if elapsed >= 1500:
            send_process_group_signal(process, 9)
            ACTIVE_GAME = None
            _set_running_card(None)
            callback()
            return False
        return True

    GLib.timeout_add(100, finish_stop)


def launch_log_path():
    directory = os.path.join(cache_home(), "mukyulauncher")
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, "launch.log")


def _open_launch_log(command, runner, game_key):

    try:
        path = launch_log_path()
        if os.path.exists(path) and os.path.getsize(path) > 2_000_000:
            os.replace(path, path + ".old")
        handle = open(path, "ab", buffering=0)
        header = f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')}  {game_key}  runner={runner} =====\n$ {shlex.join(command)}\n"
        handle.write(header.encode("utf-8", "replace"))
        return handle
    except OSError:
        return None


def launch_game(exe_path, launch_options, runner, game_key, card, title, running_bar):
    if game_key in ("th1", "th2", "th3", "th4", "th5"):
        runner = "dosbox-x"
    elif IS_WINDOWS:
        runner = "wine"

    if ACTIVE_GAME is not None and process_tree_exists(ACTIVE_GAME):
        show_running_error(
            card,
            title,
            lambda: launch_game(exe_path, launch_options, runner, game_key, card, title, running_bar),
        )
        return
    if runner == "ge-proton" and not ge_proton_installed():
        show_runner_error(card, title)
        return
    game_dir = os.path.dirname(exe_path)
    if runner == "dosbox-x":
        dosbox_path = get_dosbox_path()
        if not dosbox_path:
            show_dosbox_missing(card)
            return

    try:
        command, env = build_launch_command(exe_path, launch_options, runner, game_key)
    except FileNotFoundError:
        if runner == "dosbox-x":
            show_dosbox_missing(card)
            return
        raise
    session_token = os.urandom(8).hex()
    env = host_env(env)
    env[SESSION_ENV_VAR] = session_token
    setup_window = None
    setup_widgets = None
    if runner == "ge-proton" and not umu_runtime_installed():
        setup_window, runtime_label, progress_bar, status_label = create_umu_setup_window(card)
        setup_widgets = (setup_window, runtime_label, progress_bar, status_label)
    start_time = time.time()
    log_handle = None if (IS_WINDOWS or setup_window) else _open_launch_log(command, runner, game_key)
    try:
        process = subprocess.Popen(
            command,
            cwd=game_dir,
            env=env,
            **({} if IS_WINDOWS else {"start_new_session": True}),
            stdout=subprocess.PIPE if setup_window else log_handle,
            stderr=subprocess.STDOUT if setup_window else (log_handle if log_handle else None),
            text=True if setup_window else False,
            bufsize=1 if setup_window else -1,
        )
    except OSError as exc:
        if log_handle is not None:
            try:
                log_handle.write(f"Could not start: {exc}\n".encode())
            except OSError:
                pass
        if not IS_WINDOWS:
            raise
        root = card.get_root()
        detail = str(exc)
        if getattr(exc, "winerror", None) == 740:
            detail = "This game needs administrator rights. Start the launcher as administrator, or turn off \"Run this program as an administrator\" in the game's .exe Properties > Compatibility."
        show_dialog(
            root if isinstance(root, Gtk.Window) else None,
            "Could not start game",
            detail,
            [("OK", ACCENT)],
            heading=f"Could not start {title}",
            default=0,
            cancel=0,
        )
        return
    if log_handle is not None:
        log_handle.close()
    if IS_WINDOWS:
        process._mukyu_job = GameJob(process)
    process._mukyu_tree_pids = {process.pid}
    process._mukyu_session = session_token
    process._mukyu_start_time = start_time
    process._mukyu_game_key = game_key
    if setup_widgets:
        monitor_umu_setup(process, *setup_widgets)
    show_running_game(running_bar, process, title)
    _set_running_card(card)


def hide_running_game(running_bar):
    global ACTIVE_GAME, ACTIVE_GAME_TITLE
    if ACTIVE_GAME is not None:
        start = getattr(ACTIVE_GAME, "_mukyu_start_time", None)
        game_key = getattr(ACTIVE_GAME, "_mukyu_game_key", None)
        if start and game_key:
            add_playtime(game_key, time.time() - start)
        job = getattr(ACTIVE_GAME, "_mukyu_job", None)
        if job is not None:
            job.close()
    ACTIVE_GAME = None
    ACTIVE_GAME_TITLE = None
    _set_running_card(None)
    running_bar.remove_css_class("rb-in")
    def finish_hide():
        if ACTIVE_GAME is None:
            running_bar.set_visible(False)
        return False
    GLib.timeout_add(360, finish_hide)


def show_running_game(running_bar, process, title):
    global ACTIVE_GAME, ACTIVE_GAME_TITLE
    ACTIVE_GAME = process
    ACTIVE_GAME_TITLE = title
    process._mukyu_tree_pids = {process.pid}
    running_bar.name_label.set_text(title)
    running_bar.set_visible(True)
    GLib.timeout_add(40, lambda: (running_bar.add_css_class("rb-in"), False)[1])

    def poll():
        if ACTIVE_GAME is not process:
            return False
        if process_tree_exists(process):
            return True
        hide_running_game(running_bar)
        return False

    running_bar.time_label.set_text("0:00")

    def tick():
        if ACTIVE_GAME is not process:
            return False
        start = getattr(process, "_mukyu_start_time", None)
        if start:
            running_bar.time_label.set_text(_format_session(time.time() - start))
        return True

    GLib.timeout_add(250, poll)
    GLib.timeout_add(1000, tick)


def kill_running_game(running_bar):
    global ACTIVE_GAME
    process = ACTIVE_GAME
    if process is None:
        return

    process._mukyu_tree_pids = process_tree_snapshot(
        process.pid, getattr(process, "_mukyu_tree_pids", set())
    )

    send_process_group_signal(process, 15)
    elapsed = 0

    def wait_then_force_kill():
        nonlocal elapsed
        if ACTIVE_GAME is not process:
            return False

        if not process_tree_exists(process):
            hide_running_game(running_bar)
            return False

        elapsed += 100
        if elapsed >= 1000:
            send_process_group_signal(process, 9)

            for pid in ([] if IS_WINDOWS else list(getattr(process, "_mukyu_tree_pids", set()))):
                try:
                    os.kill(pid, 9)
                except (ProcessLookupError, PermissionError):
                    pass

            hide_running_game(running_bar)
            return False

        return True

    GLib.timeout_add(100, wait_then_force_kill)


def create_running_bar():
    bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    bar.set_margin_start(10)
    bar.set_margin_end(10)
    bar.set_margin_top(4)
    bar.set_margin_bottom(12)
    bar.set_vexpand(False)
    bar.set_hexpand(True)
    bar.add_css_class("running-bar")

    dot = Gtk.Box()
    dot.set_valign(Gtk.Align.CENTER)
    dot.set_margin_start(2)
    dot.add_css_class("running-dot")
    bar.append(dot)

    text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    text.set_valign(Gtk.Align.CENTER)
    text.set_hexpand(True)
    caption = Gtk.Label(label="NOW PLAYING")
    caption.add_css_class("rb-caption")
    caption.set_halign(Gtk.Align.START)
    text.append(caption)
    name = Gtk.Label()
    name.set_halign(Gtk.Align.START)
    name.set_ellipsize(Pango.EllipsizeMode.END)
    name.add_css_class("rb-name")
    text.append(name)
    bar.append(text)
    bar.name_label = name

    time_label = Gtk.Label(label="0:00")
    time_label.set_valign(Gtk.Align.CENTER)
    time_label.add_css_class("rb-time")
    bar.append(time_label)
    bar.time_label = time_label

    stop_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    stop_icon = Gtk.Image.new_from_icon_name("media-playback-stop-symbolic")
    stop_icon.set_pixel_size(14)
    stop_content.append(stop_icon)
    stop_content.append(Gtk.Label(label="Stop"))
    kill_button = Gtk.Button()
    kill_button.set_child(stop_content)
    kill_button.add_css_class("running-stop")
    kill_button.set_valign(Gtk.Align.CENTER)
    kill_button.connect("clicked", lambda _button: kill_running_game(bar))
    bar.append(kill_button)
    return bar


def create_settings_window(button, title, game_key, config, label, card):
    entry = config.get(game_key, {})
    exe_path = entry.get("exe")
    launch_options = entry.get("launch_options", "")
    runner = entry.get("runner", "wine")

    root = card.get_root()
    parent = root if isinstance(root, Gtk.Window) else None

    window = Gtk.Window()
    window.set_title(f"{title} — Settings")
    window.set_default_size(340, -1)
    window.set_resizable(False)
    window.set_decorated(False)
    window.set_hide_on_close(True)
    window.set_modal(False)
    if parent is not None:
        window.set_transient_for(parent)
        window.set_destroy_with_parent(True)
    window.add_css_class("game-settings-window")

    surface = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    surface.add_css_class("game-settings-surface")
    surface.set_size_request(310, -1)
    surface.set_margin_start(4)
    surface.set_margin_end(4)
    surface.set_margin_top(4)
    surface.set_margin_bottom(4)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.set_margin_start(14)
    box.set_margin_end(14)
    box.set_margin_top(14)
    box.set_margin_bottom(14)
    surface.append(box)
    window.set_child(surface)

    heading = Gtk.Label(label=title)
    heading.add_css_class("popover-heading")
    heading.add_css_class("gs-heading")
    heading.set_wrap(True)
    heading.set_halign(Gtk.Align.START)
    box.append(heading)

    playtime_text = get_playtime_text(game_key)
    if playtime_text:
        playtime_label = Gtk.Label(label=playtime_text)
        playtime_label.set_halign(Gtk.Align.START)
        playtime_label.add_css_class("dim-label")
        playtime_label.add_css_class("caption")
        box.append(playtime_label)

    def close_settings():
        if persist_callback[0] is not None:
            persist_callback[0]()
        window.hide()

    persist_callback = [None]

    if entry.get("runner") == "dosbox-x" or game_key in ("th1", "th2", "th3", "th4", "th5"):
        status = Gtk.Label(label="")
        status.set_halign(Gtk.Align.START)
        status.set_text("DOSBox-X installed on system" if dosbox_installed() else "DOSBox-X not installed")
        box.append(status)

        install = Gtk.Button(label="Download DOSBox-X")
        box.append(install)

        change = Gtk.Button()
        box.append(change)

        remove_button = Gtk.Button(label="Remove ROM")
        remove_button.add_css_class("destructive-action")
        remove_button.set_visible(bool(exe_path and Path(exe_path).exists()))
        box.append(remove_button)

        def choose(_button):
            window.hide()
            prompt_for_exe(title, game_key, config, label, card)
            config.setdefault(game_key, {})["runner"] = "dosbox-x"
            save_config(config)

        def remove_rom(_button):
            current = config.setdefault(game_key, {})
            current["exe"] = None
            save_config(config)
            update_title_label(label, title, None, "dosbox-x", card=card, game_key=game_key)
            if game_key in SETTINGS_REFRESHERS:
                SETTINGS_REFRESHERS[game_key]()
            card.remove_css_class("enabled-card")
            card.add_css_class("disabled-card")
            window.hide()

        change.connect("clicked", choose)
        remove_button.connect("clicked", remove_rom)

        def refresh_rom_button():
            current_exe = config.get(game_key, {}).get("exe")
            rom_assigned = bool(current_exe and Path(current_exe).exists())
            change.set_label(
                "Change ROM (.hdi/.nhd/.fdi/.img/.d88)…"
                if rom_assigned
                else "Add ROM (.hdi/.nhd/.fdi/.img/.d88)…"
            )
            remove_button.set_visible(rom_assigned)

        SETTINGS_REFRESHERS[game_key] = refresh_rom_button
        refresh_rom_button()
        install.connect("clicked", lambda *_: install_dosbox(install, status))

        persist_callback[0] = lambda: None

    else:
        runner_label_text = Gtk.Label(label="Runner:")
        runner_label_text.set_halign(Gtk.Align.START)
        runner_label_text.add_css_class("settings-label")
        box.append(runner_label_text)

        runner_dropdown = Gtk.DropDown.new_from_strings(["Wine", "GE-Proton"])
        runner_dropdown.set_selected(1 if runner == "ge-proton" else 0)
        box.append(runner_dropdown)

        ge_status = Gtk.Label()
        ge_status.set_halign(Gtk.Align.START)
        ge_status.add_css_class("runner-status-small")
        update_runner_status(ge_status)
        box.append(ge_status)

        download_button = Gtk.Button(label="Download / update GE-Proton")
        box.append(download_button)

        download_progress = Gtk.ProgressBar()
        download_progress.add_css_class("download-progress")
        download_progress.set_show_text(True)
        download_progress.set_visible(False)
        box.append(download_progress)

        change_button = Gtk.Button(label="Change .exe…" if exe_path else "Set .exe…")
        box.append(change_button)

        remove_button = Gtk.Button(label="Remove .exe")
        remove_button.add_css_class("destructive-action")
        remove_button.set_visible(bool(exe_path and Path(exe_path).exists()))
        box.append(remove_button)

        options_label = Gtk.Label(label="Launch options:")
        options_label.set_halign(Gtk.Align.START)
        options_label.add_css_class("settings-label")
        box.append(options_label)

        options_entry = Gtk.Entry()
        options_entry.set_text(launch_options)
        options_entry.set_placeholder_text("e.g. mangohud %command%")
        box.append(options_entry)

        def persist():
            current = config.setdefault(
                game_key, {"exe": exe_path, "launch_options": "", "runner": "wine"}
            )
            current["launch_options"] = options_entry.get_text()
            current["runner"] = "ge-proton" if runner_dropdown.get_selected() == 1 else "wine"
            save_config(config)
            update_title_label(
                label, title, current.get("exe"), current["runner"], card=card, game_key=game_key
            )

        persist_callback[0] = persist

        def on_runner_changed(_dropdown, _param):
            persist()
            if runner_dropdown.get_selected() == 1 and not ge_proton_installed():
                ge_status.set_text("GE-Proton is not installed yet.")

        def on_change_clicked(_button):
            persist()
            window.hide()
            prompt_for_exe(title, game_key, config, label, card)

        def on_remove_clicked(_button):
            current = config.setdefault(game_key, {})
            current["exe"] = None
            save_config(config)
            update_title_label(
                label, title, None, current.get("runner", "wine"), card=card, game_key=game_key
            )
            if game_key in SETTINGS_REFRESHERS:
                SETTINGS_REFRESHERS[game_key]()
            card.remove_css_class("enabled-card")
            card.add_css_class("disabled-card")
            window.hide()

        if IS_WINDOWS:
            for widget in (runner_label_text, runner_dropdown, ge_status, download_button, download_progress):
                widget.set_visible(False)
            options_entry.set_placeholder_text("e.g. -windowed")

        runner_dropdown.connect("notify::selected", on_runner_changed)
        options_entry.connect("activate", lambda _entry: persist())
        change_button.connect("clicked", on_change_clicked)
        remove_button.connect("clicked", on_remove_clicked)

        def refresh_exe_button():
            current_exe = config.get(game_key, {}).get("exe")
            remove_button.set_visible(bool(current_exe and Path(current_exe).exists()))

        SETTINGS_REFRESHERS[game_key] = refresh_exe_button
        download_button.connect(
            "clicked",
            lambda _button: on_download_ge_clicked(
                download_button, ge_status, download_button, download_progress
            ),
        )

    def on_close_request(_window):
        close_settings()
        return True

    window.connect("close-request", on_close_request)
    return window
