from mukyu.paths import ASSETS_DIR
import collections
from gi.repository import Gtk, Gdk, Gio, GObject, Pango, GLib
try:
    from gi.repository import GdkPixbuf
except ImportError:
    GdkPixbuf = None
import os
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from mukyu.platform_compat import data_home
from mukyu.ui.dialogs import ACCENT, DANGER, NEUTRAL, show_dialog, style_button

PRINTWORKS = [
    ('Print Works', [
        ('Touhou Bunka Chou ~ Bohemian Archive in Japanese Red', 'bohemian_archive_in_japanese_red.jpg', '2005', 'ZUN', 'Genji Asai, alphes, Chiha Ayami, Masato Takashina, Tateha, Touya, TOBI, Yuki Usagi, Tomoe Rokuwata'),
        ('The Grimoire of Marisa', 'grimoire_of_marisa.jpg', '2009', 'ZUN', 'Moriki Takeshi, Genji Asai'),
        ('Alternative Facts in Eastern Utopia', 'alternative_facts_in_eastern_utopia.jpg', '2017', 'ZUN', 'Aoi Kujira, Genji Asai, Aya Azuma, Toshira Arata, ALISON, Amamiya Tokuhisa, Suichuu Hanabi, TOKIAME, nyanya, Haniwa, Akio Hiiragi, Hitori, Masakichi, Mizutaki'),
        ('The Grimoire of Usami', 'grimoire_of_usami.jpg', '2019', 'ZUN', 'Aya Azuma, Genji Asai, Benishake(poprication)'),
        ('Touhou Sangetsusei ~ Eastern and Little Nature Deity', 'eastern_little_nature_deity.jpg', '2005', 'ZUN', 'Nemu Matsukura'),
        ('Touhou Sangetsusei ~ Strange and Bright Nature Deity', 'strange_bright_nature_deity.jpg', '2006', 'ZUN', 'Makoto Hirasaka'),
        ('Touhou Sangetsusei ~ Oriental Sacred Place', 'oriental_sacred_place.jpg', '2009', 'ZUN', 'Makoto Hirasaka'),
        ('Touhou Sangetsusei ~ Visionary Fairies in Shrine', 'visionary_fairies_in_shrine.jpg', '2016', 'ZUN', 'Makoto Hirasaka'),
        ('Touhou Bougetsushou ~ Silent Sinner in Blue', 'silent_sinner_in_blue.jpg', '2007', 'ZUN', 'Aki★Eda'),
        ('Touhou Bougetsushou ~ Inaba of the Moon and Inaba of the Earth', 'inaba_moon_inaba_earth.jpg', '2007', 'Toshihira Arata', 'Toshihira Arata'),
        ('Touhou Ibarakasen ~ Wild and Horned Hermit', 'wild_horned_hermit.jpg', '2010', 'ZUN', 'Aya Azuma'),
        ('Touhou Suzunaan ~ Forbidden Scrollery', 'forbidden_scrollery.jpg', '2012', 'ZUN', 'Moe Harukawa'),
        ('Touhou Suichouka ~ Lotus Eaters (Ongoing)', 'lotuseaters.jpg', '2019', 'ZUN', 'Mizutaki'),
        ('Touhou Chireikiden ~ Foul Detective Satori (Ongoing)', 'foul_detective_satori.jpg', '2019', 'ZUN', 'Ginmokusei, Akimaki Yuu'),
    ]),
]

DESCRIPTIONS = {'Touhou Sangetsusei ~ Eastern and Little Nature Deity': 'The story focuses on the daily lives of the Three Fairies of Light : Sunny Milk, Luna Child and Star Sapphire, said to be typical residents of Gensokyo.',
'Touhou Sangetsusei ~ Strange and Bright Nature Deity': 'The story continues where Eastern and Little Nature Deity left off, it focuses on the daily lives of the Three Fairies of Light : Sunny Milk, Luna Child and Star Sapphire, said to be typical residents of Gensokyo.',
'Touhou Bougetsushou ~ Silent Sinner in Blue': 'Silent Sinner in Blue follows the efforts of Reimu Hakurei, Marisa Kirisame, and the residents of the Scarlet Devil Mansion as they attempt to send a rocket to the moon, purportedly in order to invade the Lunar Capital. ',
'Touhou Bougetsushou ~ Inaba of the Moon and Inaba of the Earth': 'A lighthearted spin-off following Reisen, Tewi, and the residents of Eientei. (not canonical to the Touhou Project)',
'Touhou Sangetsusei ~ Oriental Sacred Place': 'The story continues where Strange and Bright Nature Deity left off, it focuses on the daily lives of the Three Fairies of Light : Sunny Milk, Luna Child and Star Sapphire, said to be typical residents of Gensokyo. ',
'Touhou Ibarakasen ~ Wild and Horned Hermit': "Kasen Ibaraki appears at the Hakurei Shrine one day, and immediately takes a liking to Reimu Hakurei and Marisa Kirisame, agreeing to help out around the shrine. Over the manga's nearly ten-year run, Kasen's inner thoughts around the direction and purpose of Gensokyo are expounded upon, as well as her own internal debates as to whether or not events from her own past should remain in the past, or be dealt with once and for all, as she joins Reimu and Marisa in their social gatherings and small adventures. ",
'Touhou Suzunaan ~ Forbidden Scrollery': 'The plot follows Kosuzu Motoori, a cheerful and naive librarian, as the protagonist, as she goes about her daily life as the proprietor of her bookstore, Suzunaan. Throughout the story, she comes into contact with various demon books and otherwise old tomes from varying and unknown sources, leading to the slow reintroduction of traditional-style youkai into Gensokyo, juxtaposed with the relatively modern-minded and agreeable youkai typically seen in modern-day Gensokyo. Due to the various issues this causes, she attracts the attention of various incident solvers such as Reimu Hakurei, Marisa Kirisame, and Mamizou Futatsuiwa, as they attempt to investigate and sometimes contain the various youkai found in her mysterious demon books.',
'Touhou Sangetsusei ~ Visionary Fairies in Shrine': 'The story takes place some times after Oriental Sacred Place, it focuses on the daily lives of the Three Fairies of Light : Sunny Milk, Luna Child and Star Sapphire, as well as their newfound fairy friend Clownpiece. ',
'Touhou Suichouka ~ Lotus Eaters (Ongoing)': 'In the Human Village lies the bar Geidontei, where the zashiki-warashi Miyoi Okunoda works as a poster girl and waitress. The series revolves around her and the various mysteries and incidents surrounding her. After hours there is a small youkai-only get-together called the Sanshoku Geidontei (蚕喰鯢呑亭) with Suika Ibuki, Aya Shameimaru and Mamizou Futatsuiwa. ',
'Touhou Chireikiden ~ Foul Detective Satori (Ongoing)': "A most difficult case suddenly appears in Gensokyo. The usual incident resolvers are perplexed, so it's the job of the mind-reading youkai Satori to resolve this case!",
'Touhou Kourindou ~ Curiosities of Lotus Asia': 'Stories centered around Kourindou, the antique shop between the human and youkai worlds.',
'Touhou Bunka Chou ~ Bohemian Archive in Japanese Red': 'a collection of newspaper articles written by Aya Shameimaru.',
'Touhou Gumonshiki ~ Perfect Memento in Strict Sense': "An encyclopedia written by Hieda no Akyuu documenting Gensokyo's people, youkai, and history.",
'The Grimoire of Marisa': 'spell card album of many characters with screen shots of that spell card from the games and comments written in the perspective of Marisa Kirisame.',
'Touhou Gumonkuju ~ Symposium of Post-mysticism': 'A collection of discussions covering incidents, history, and supernatural topics.',
'Alternative Facts in Eastern Utopia': "Aya Shameimaru's attempt to create a tabloid magazine in the style of those from the Outside World, which she eventually cancelled and left unpublished.[2] The book features in-universe articles, interviews and advertisements similar to the earlier Bohemian Archive in Japanese Red, but in a significantly more chaotic and haphazard format.",
'The Grimoire of Usami': 'features a large selection of Spell Cards which are commented and judged by various characters during a firework festival.',
'Strange Creators of Outer World': 'An official Touhou magazine supervised by ZUN featuring interviews, creator spotlights, comics, and information about Touhou works.',
'Strange Articles of the Outer World': 'An official online magazine covering Touhou news, interviews, reviews, and related articles.',
'Touhou Bougetsushou ~ Cage in Lunatic Runagate': 'The stand-alone stories in Cage in Lunatic Runagate offer detailed background information to the events in Silent Sinner in Blue, offering the insights and perspectives of various major and minor characters, and of those who didn\'t appear at all. ',
'Whispered Oracle of Hakurei Shrine': 'Following the events of Unfinished Dream of All Living Ghost, Zanmu Nippaku approaches Reimu Hakurei to warn her that the youkai of Gensokyo would soon disappear. This was due to Chimata Tenkyuu releasing ownership of all land in Gensokyo, whose ownership was foundational to the existence of certain youkai. To help solidify their existence, Reimu, as well as some of the other humans in Gensokyo, created and sold omikuji slips based on the youkai they’d met.'}

class PWItem(GObject.Object):
    def __init__(self, name, cover=None, year=None, author=None, artist=None, description="placeholder description", category=False):
        super().__init__()
        self.name = name
        self.cover = cover
        self.year = year
        self.author = author
        self.artist = artist
        self.description = description
        self.category = category

ONGOING_SUFFIX = ' (Ongoing)'

CHAPTERS = {
    'Touhou Sangetsusei ~ Eastern and Little Nature Deity': 7,
    'Touhou Sangetsusei ~ Strange and Bright Nature Deity': 25,
    'Touhou Sangetsusei ~ Oriental Sacred Place': 18,
    'Touhou Sangetsusei ~ Visionary Fairies in Shrine': 15,
    'Touhou Bougetsushou ~ Silent Sinner in Blue': 21,
    'Touhou Bougetsushou ~ Inaba of the Moon and Inaba of the Earth': 30,
    'Touhou Ibarakasen ~ Wild and Horned Hermit': 51,
    'Touhou Suzunaan ~ Forbidden Scrollery': 54,
    'Touhou Suichouka ~ Lotus Eaters (Ongoing)': 81,
    'Touhou Chireikiden ~ Foul Detective Satori (Ongoing)': 54,
}


DOWNLOAD_ROOT = os.path.join(
    data_home(),
    "mukyulauncher",
    "PrintWorks",
)

ARCHIVE_BASE = 'https://archive.org/download/touhouprintworks/'

ARCHIVE_FILES = {
    'Touhou Sangetsusei ~ Eastern and Little Nature Deity': 'Eastern and Little Nature Deity.pdf',
    'Touhou Sangetsusei ~ Strange and Bright Nature Deity': 'Strange and Bright Nature Deity.pdf',
    'Touhou Sangetsusei ~ Oriental Sacred Place': 'Oriental Sacred Place.pdf',
    'Touhou Sangetsusei ~ Visionary Fairies in Shrine': 'Visionary Fairies in Shrine.pdf',
    'Touhou Bougetsushou ~ Silent Sinner in Blue': 'Silent Sinner in Blue.pdf',
    'Touhou Bougetsushou ~ Inaba of the Moon and Inaba of the Earth': 'Inaba of the moon Inaba of the earth.pdf',
    'Touhou Suzunaan ~ Forbidden Scrollery': 'Forbidden Scrollery.pdf',
    'Touhou Suichouka ~ Lotus Eaters (Ongoing)': 'Lotus Eaters.pdf',
    'Touhou Chireikiden ~ Foul Detective Satori (Ongoing)': 'Foul Detective Satori.pdf',
    'Touhou Bunka Chou ~ Bohemian Archive in Japanese Red': 'Bohemian Archive in Japanese Red.pdf',
    'The Grimoire of Marisa': 'The Grimoire of Marisa.pdf',
    'The Grimoire of Usami': 'The Grimoire of Usami.pdf',
    'Alternative Facts in Eastern Utopia': 'Alternative Facts in Eastern Utopia.pdf',
    'Touhou Ibarakasen ~ Wild and Horned Hermit': 'Wild and Horned Hermit.pdf',
}

PDF_URLS = {name: ARCHIVE_BASE + urllib.parse.quote(filename) for name, filename in ARCHIVE_FILES.items()}

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0'
CHUNK_SIZE = 64 * 1024
NET_TIMEOUT = 30

ACTIVE_NAMES = set()
SIZE_CACHE = {}


class DownloadError(Exception):
    pass


class DownloadCancelled(Exception):
    pass


def _folder_name(name):
    if name.endswith(ONGOING_SUFFIX):
        name = name[:-len(ONGOING_SUFFIX)]
    return name.replace('/', '-').replace('\0', '').strip()

def pdf_dir(name):
    return os.path.join(DOWNLOAD_ROOT, _folder_name(name))

def pdf_path(name):
    return os.path.join(pdf_dir(name), _folder_name(name) + '.pdf')

def is_downloaded(name):
    return os.path.isfile(pdf_path(name))

def fmt_size(n):
    if n is None or n < 0:
        return 'Unknown'
    value = float(n)
    for unit in ('B', 'KB', 'MB', 'GB'):
        if value < 1024 or unit == 'GB':
            return f'{int(value)} B' if unit == 'B' else f'{value:.1f} {unit}'
        value /= 1024

def _open_url(url, method='GET'):
    req = urllib.request.Request(url, method=method, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/pdf,*/*',
        'Accept-Encoding': 'identity',
    })
    return urllib.request.urlopen(req, timeout=NET_TIMEOUT)

def _is_web_page(response):
    return response.headers.get_content_type() in ('text/html', 'application/xhtml+xml')

def _host(response):
    return urllib.parse.urlparse(response.geturl()).netloc or 'the server'

def fetch_size(url):
    for method in ('HEAD', 'GET'):
        try:
            with _open_url(url, method) as response:
                if _is_web_page(response):
                    return None
                length = (response.headers.get('Content-Length') or '').strip()
                if length.isdigit() and int(length) > 0:
                    return int(length)
        except Exception:
            continue
    return None

def _remove_quietly(path):
    try:
        os.remove(path)
    except OSError:
        pass

def _rmdir_if_empty(path):
    try:
        os.rmdir(path)
    except OSError:
        pass

def download_pdf(name, url, cancel_event, on_progress):
    directory = pdf_dir(name)
    final = pdf_path(name)
    part = final + '.part'
    try:
        os.makedirs(directory, exist_ok=True)
        _remove_quietly(part)
        with _open_url(url) as response:
            if _is_web_page(response):
                raise DownloadError(
                    f'This link opens a web page ({_host(response)}), not the PDF itself. '
                    'It needs to be a direct download URL.')
            length = (response.headers.get('Content-Length') or '').strip()
            total = int(length) if length.isdigit() and int(length) > 0 else -1
            if total > 0 and shutil.disk_usage(directory).free < total + (1 << 20):
                raise DownloadError('Not enough free disk space for this download.')
            done = 0
            first = True
            with open(part, 'wb') as out:
                while True:
                    if cancel_event.is_set():
                        raise DownloadCancelled()
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    if first:
                        if not chunk.startswith(b'%PDF'):
                            raise DownloadError(
                                f'The server did not send a PDF file '
                                f'(got {response.headers.get_content_type()} from {_host(response)}).')
                        first = False
                    out.write(chunk)
                    done += len(chunk)
                    on_progress(done, total)
                out.flush()
                os.fsync(out.fileno())
        if first:
            raise DownloadError('The downloaded file was empty.')
        if total > 0 and done != total:
            raise DownloadError('The download ended early. Please try again.')
        if cancel_event.is_set():
            raise DownloadCancelled()
        os.replace(part, final)
    except BaseException:
        _remove_quietly(part)
        if not os.path.isfile(final):
            _rmdir_if_empty(directory)
        raise

def describe_error(exc):
    if isinstance(exc, DownloadError):
        return str(exc)
    if isinstance(exc, urllib.error.HTTPError):
        return f'The server answered with an error (HTTP {exc.code}).'
    if isinstance(exc, urllib.error.URLError):
        return 'Could not reach the download server. Check your internet connection.'
    if isinstance(exc, TimeoutError):
        return 'The connection timed out. Please try again.'
    if isinstance(exc, OSError) and getattr(exc, 'errno', None) == 28:
        return 'Not enough free disk space for this download.'
    return f'Download failed: {exc}'

def open_reader(parent, name):
    try:
        from mukyu.reader.pdf_reader import PdfReader
    except ImportError as exc:
        show_message(parent, 'Reader unavailable',
                     "The built-in reader needs the 'pypdfium2' package.\n\n"
                     "Install it with:\n    pip install pypdfium2\n\n"
                     f"({exc})")
        return
    PdfReader(parent, _folder_name(name), pdf_path(name), _folder_name(name)).present()

def delete_download(name):
    _remove_quietly(pdf_path(name))
    if name not in ACTIVE_NAMES:
        _remove_quietly(pdf_path(name) + '.part')
        _rmdir_if_empty(pdf_dir(name))

def show_message(parent, title, text):
    show_dialog(parent, title, text, [('OK', ACCENT)], default=0, cancel=0)


class DownloadDialog(Gtk.Window):

    def __init__(self, parent, name, url, on_change):
        super().__init__(title='Download', modal=True, resizable=False)
        self.add_css_class('pw-dialog')
        if parent is not None:
            self.set_transient_for(parent)
        self.set_default_size(440, -1)
        self.pw_name = name
        self.pw_url = url
        self.pw_on_change = on_change
        self.pw_state = 'prompt'
        self.pw_closed = False
        self.pw_cancel = threading.Event()
        self._reset_stats()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for side in ('start', 'end', 'top', 'bottom'):
            getattr(box, f'set_margin_{side}')(24)

        self.heading = Gtk.Label(xalign=0)
        self.heading.add_css_class('popover-heading')
        self.body = Gtk.Label(xalign=0)
        self.body.set_wrap(True)
        self.body.set_max_width_chars(46)
        self.size_label = Gtk.Label(xalign=0)
        self.size_label.add_css_class('running-status')
        self.progress = Gtk.ProgressBar()
        self.progress.set_visible(False)
        self.progress_label = Gtk.Label(xalign=0)
        self.progress_label.add_css_class('running-status')
        self.progress_label.set_visible(False)
        self.error_label = Gtk.Label(xalign=0)
        self.error_label.set_wrap(True)
        self.error_label.set_max_width_chars(46)
        self.error_label.set_visible(False)

        buttons = Gtk.Box(spacing=8)
        buttons.set_halign(Gtk.Align.END)
        buttons.set_margin_top(6)
        self.cancel_btn = Gtk.Button(label='Cancel')
        style_button(self.cancel_btn, NEUTRAL)
        self.action_btn = Gtk.Button(label='Download')
        style_button(self.action_btn, ACCENT)
        self.cancel_btn.connect('clicked', self._on_cancel_clicked)
        self.action_btn.connect('clicked', self._on_action_clicked)
        buttons.append(self.cancel_btn)
        buttons.append(self.action_btn)

        for w in (self.heading, self.body, self.size_label, self.progress,
                  self.progress_label, self.error_label, buttons):
            box.append(w)
        self.set_child(box)
        self.connect('close-request', self._on_close_request)

        self._set_state('prompt')
        self._load_size()

    def _reset_stats(self):
        self._speed = None
        self._win_t = None
        self._win_b = 0
        self._last_ui = 0.0

    def _set_state(self, state, error=None):
        self.pw_state = state
        base = _folder_name(self.pw_name)
        show_progress = state == 'downloading'
        self.progress.set_visible(show_progress)
        self.progress_label.set_visible(show_progress)
        self.error_label.set_visible(state == 'error')
        self.size_label.set_visible(state in ('prompt', 'error'))
        self.body.set_visible(state != 'downloading')
        if state in ('prompt', 'error'):
            self.heading.set_text('Download required' if state == 'prompt' else 'Download failed')
            self.body.set_text(f'You\'ll need to download "{base}" before you can read it.'
                               if state == 'prompt' else f'"{base}" could not be downloaded.')
            self.cancel_btn.set_label('Cancel')
            self.action_btn.set_label('Download' if state == 'prompt' else 'Retry')
            self.action_btn.set_sensitive(True)
            if state == 'error':
                self.error_label.set_markup(
                    f'<span foreground="#ff5555">{GLib.markup_escape_text(error or "")}</span>')
        elif state == 'downloading':
            self.heading.set_text(f'Downloading {base}')
            self.progress.set_fraction(0.0)
            self.progress_label.set_text('Starting…')
            self.cancel_btn.set_label('Cancel')
            self.action_btn.set_visible(False)
            return
        elif state == 'done':
            self.heading.set_text('Download complete')
            self.body.set_text(f'"{base}" is ready to read.')
            self.cancel_btn.set_label('Close')
            self.action_btn.set_label('Read now')
            self.action_btn.set_sensitive(True)
        self.action_btn.set_visible(True)

    def _load_size(self):
        if self.pw_name in SIZE_CACHE:
            self.size_label.set_text(f'File size: {fmt_size(SIZE_CACHE[self.pw_name])}')
            return
        self.size_label.set_text('File size: checking…')
        def work():
            size = fetch_size(self.pw_url)
            SIZE_CACHE[self.pw_name] = size
            if not self.pw_closed:
                GLib.idle_add(lambda: self.size_label.set_text(f'File size: {fmt_size(size)}') or False)
        threading.Thread(target=work, daemon=True).start()

    def _on_cancel_clicked(self, _btn):
        self.close()

    def _on_close_request(self, _win):
        self.pw_closed = True
        if self.pw_state == 'downloading':
            self.pw_cancel.set()
        return False

    def _on_action_clicked(self, _btn):
        if self.pw_state in ('prompt', 'error'):
            self._start_download()
        elif self.pw_state == 'done':
            parent, name = self.get_transient_for(), self.pw_name
            self.close()
            GLib.idle_add(lambda: (open_reader(parent, name), False)[1])

    def _start_download(self):
        if self.pw_name in ACTIVE_NAMES:
            self._set_state('error', 'The previous attempt is still stopping. Please try again in a moment.')
            return
        ACTIVE_NAMES.add(self.pw_name)
        self.pw_cancel = threading.Event()
        self._reset_stats()
        self._set_state('downloading')
        threading.Thread(target=self._worker, args=(self.pw_cancel,), daemon=True).start()

    def _worker(self, cancel_event):
        outcome, message = 'ok', None
        try:
            download_pdf(self.pw_name, self.pw_url, cancel_event, self._on_progress)
        except DownloadCancelled:
            outcome = 'cancelled'
        except BaseException as exc:
            outcome, message = 'error', describe_error(exc)
        finally:
            ACTIVE_NAMES.discard(self.pw_name)
        if outcome == 'ok':
            GLib.idle_add(self._finish_ok)
        elif outcome == 'error' and not self.pw_closed:
            GLib.idle_add(self._finish_error, message)

    def _on_progress(self, done, total):
        now = time.monotonic()
        if self._win_t is None:
            self._win_t, self._win_b = now, 0
        elapsed = now - self._win_t
        if elapsed >= 0.5:
            current = (done - self._win_b) / elapsed
            self._speed = current if self._speed is None else 0.6 * self._speed + 0.4 * current
            self._win_t, self._win_b = now, done
        if now - self._last_ui >= 0.1 or (total > 0 and done >= total):
            self._last_ui = now
            GLib.idle_add(self._update_ui, done, total, self._speed)

    def _update_ui(self, done, total, speed):
        if self.pw_closed or self.pw_state != 'downloading':
            return False
        speed_text = f'{fmt_size(speed)}/s' if speed is not None else 'calculating speed…'
        if total > 0:
            self.progress.set_fraction(min(1.0, done / total))
            self.progress_label.set_text(
                f'{fmt_size(done)} of {fmt_size(total)}  ({int(done * 100 / total)}%)  ·  {speed_text}')
        else:
            self.progress.pulse()
            self.progress_label.set_text(f'{fmt_size(done)}  ·  {speed_text}')
        return False

    def _finish_ok(self):
        self.pw_on_change()
        if not self.pw_closed:
            self._set_state('done')
        return False

    def _finish_error(self, message):
        if not self.pw_closed:
            self._set_state('error', message)
        return False


THUMB_MAX_W, THUMB_MAX_H = 360, 500
THUMB_CACHE_SIZE = 6
_THUMB_CACHE = collections.OrderedDict()
_THUMB_WAITING = {}


def _decode_thumb(path):
    info = GdkPixbuf.Pixbuf.get_file_info(path)
    width, height = (info[1], info[2]) if info and info[0] is not None else (0, 0)
    if width > THUMB_MAX_W or height > THUMB_MAX_H or not width:
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, THUMB_MAX_W, THUMB_MAX_H, True)
    return GdkPixbuf.Pixbuf.new_from_file(path)


def _thumb_ready(path, pixbuf):
    pictures = _THUMB_WAITING.pop(path, [])
    if pixbuf is None:
        return False
    texture = Gdk.Texture.new_for_pixbuf(pixbuf)
    _THUMB_CACHE[path] = texture
    while len(_THUMB_CACHE) > THUMB_CACHE_SIZE:
        _THUMB_CACHE.popitem(last=False)
    for picture in pictures:
        if getattr(picture, 'pw_thumb_path', None) == path:
            picture.set_paintable(texture)
    return False


def request_thumb(path, picture=None):
    if picture is not None:
        picture.pw_thumb_path = path
    texture = _THUMB_CACHE.get(path)
    if texture is not None:
        _THUMB_CACHE.move_to_end(path)
        if picture is not None:
            picture.set_paintable(texture)
        return
    if picture is not None:
        picture.set_paintable(None)
    if GdkPixbuf is None:
        if picture is not None:
            picture.set_filename(path)
        return
    if path in _THUMB_WAITING:
        if picture is not None:
            _THUMB_WAITING[path].append(picture)
        return
    _THUMB_WAITING[path] = [picture] if picture is not None else []

    def work():
        try:
            pixbuf = _decode_thumb(path)
        except Exception:
            pixbuf = None
        GLib.idle_add(_thumb_ready, path, pixbuf)

    threading.Thread(target=work, daemon=True, name='pw-thumb').start()


def _thumb_path(cover):
    return str(ASSETS_DIR / 'print_thumbnails' / cover)


def _label(css_class=None, lines=False):
    lbl = Gtk.Label(xalign=0)
    lbl.set_wrap(True)
    lbl.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
    lbl.set_hexpand(True)
    lbl.set_halign(Gtk.Align.FILL)
    if css_class:
        lbl.add_css_class(css_class)
    return lbl

def _chip(text):
    c = Gtk.Label()
    c.set_use_markup(True)
    c.add_css_class('pw-chip')
    c.set_halign(Gtk.Align.START)
    return c

def create_printworks_page():
    store = Gio.ListStore.new(PWItem)
    for category, items in PRINTWORKS:
        for item in items:
            store.append(
                PWItem(
                    *item,
                    description=DESCRIPTIONS.get(
                        item[0], "No description available."
                    ),
                )
            )

    refs = {}

    def refresh_rows():
        for it, widgets in refs.items():
            r = it.get_item()
            if r is not None:
                widgets['trash'].set_visible(is_downloaded(r.name))

    def on_read(button, item):
        r = item.get_item()
        if r is None:
            return
        root = button.get_root()
        parent = root if isinstance(root, Gtk.Window) else None
        if is_downloaded(r.name):
            open_reader(parent, r.name)
            return
        url = PDF_URLS.get(r.name)
        if not url:
            show_message(parent, 'Not available', 'This print work is not available to download yet.')
            return
        DownloadDialog(parent, r.name, url, refresh_rows).present()

    def on_delete(button, item):
        r = item.get_item()
        if r is None:
            return
        name = r.name
        root = button.get_root()
        parent = root if isinstance(root, Gtk.Window) else None

        def confirmed(choice):
            if choice == 1:
                delete_download(name)
                refresh_rows()


        show_dialog(parent, 'Delete PDF',
                    f'"{_folder_name(name)}" will be removed from this computer. '
                    'You can download it again later.',
                    [('Cancel', NEUTRAL), ('Delete', DANGER)], on_response=confirmed,
                    heading='Are you sure you want to delete this?', default=0, cancel=0)
    factory = Gtk.SignalListItemFactory()

    def setup(_, item):
        card = Gtk.Box(spacing=18)
        card.add_css_class('pw-card')
        img = Gtk.Picture()
        img.set_size_request(220, 300)
        img.set_can_shrink(True)
        img.set_content_fit(Gtk.ContentFit.COVER)
        img.add_css_class('printwork-cover')
        img.set_valign(Gtk.Align.START)
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info.set_hexpand(True)
        head = Gtk.Box(spacing=10)
        title = _label('printwork-title')
        badge = Gtk.Label()
        badge.set_markup('<span size="small" weight="bold">Ongoing</span>')
        badge.add_css_class('pw-badge')
        badge.set_valign(Gtk.Align.START)
        head.append(title)
        head.append(badge)
        chips = Gtk.Box(spacing=6)
        year = _chip('')
        author = _chip('')
        chapters = _chip('')
        chips.append(year)
        chips.append(author)
        chips.append(chapters)
        desc = _label('pw-desc')
        desc.set_max_width_chars(60)
        artist = _label('pw-artist')
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        button = Gtk.Button(label='Read')
        button.add_css_class('pw-read')
        trash_icon = Gtk.Image.new_from_icon_name('user-trash-symbolic')
        trash_icon.set_pixel_size(14)
        trash = Gtk.Button()
        trash.set_child(trash_icon)
        trash.add_css_class('pw-delete')
        trash.set_valign(Gtk.Align.CENTER)
        trash.set_visible(False)
        actions = Gtk.Box(spacing=8)
        actions.set_halign(Gtk.Align.START)
        actions.append(button)
        actions.append(trash)
        button.connect('clicked', on_read, item)
        trash.connect('clicked', on_delete, item)
        for widget in (head, chips, desc, artist, spacer, actions):
            info.append(widget)
        card.append(img)
        card.append(info)
        wrap = Gtk.Box()
        wrap.add_css_class('pw-wrap')
        wrap.append(card)
        card.set_hexpand(True)
        item.set_child(wrap)
        refs[item] = {
            'card': card,
            'img': img,
            'title': title,
            'badge': badge,
            'year': year,
            'author': author,
            'chapters': chapters,
            'desc': desc,
            'artist': artist,
            'trash': trash,
        }

    def bind(_, item):
        r = item.get_item()
        w = refs[item]
        card = w['card']
        name = r.name
        ongoing = name.endswith(ONGOING_SUFFIX)
        if ongoing:
            name = name[:-len(ONGOING_SUFFIX)]
        w['title'].set_markup(f'<span weight="bold" size="large">{GLib.markup_escape_text(name)}</span>')
        w['badge'].set_visible(ongoing)
        w['year'].set_markup(f'<span size="small">{GLib.markup_escape_text(str(r.year))}</span>')
        w['author'].set_markup(f'<span size="small">by {GLib.markup_escape_text(str(r.author))}</span>')
        count = CHAPTERS.get(r.name)
        w['chapters'].set_visible(count is not None)
        if count is not None:
            text = f'{count}-ongoing' if ongoing else str(count)
            w['chapters'].set_markup(f'<span size="small">Chapters: {text}</span>')
        w['artist'].set_markup(f'<span alpha="65%">Art  ·  {GLib.markup_escape_text(str(r.artist))}</span>')
        w['desc'].set_text(r.description)
        path = _thumb_path(r.cover)
        if os.path.exists(path):
            request_thumb(path, w['img'])
        w['trash'].set_visible(is_downloaded(r.name))
        card.remove_css_class('pw-in')
        delay = 60 + min(item.get_position(), 6) * 70
        def reveal():
            card.add_css_class('pw-in')
            return False
        GLib.timeout_add(delay, reveal)

    factory.connect('setup', setup)
    factory.connect('bind', bind)
    view = Gtk.ListView(model=Gtk.NoSelection(model=store), factory=factory)
    view.set_vexpand(True)
    view.set_hexpand(True)
    view.add_css_class('pw-list')
    scroll = Gtk.ScrolledWindow()
    scroll.set_child(view)
    scroll.set_vexpand(True)
    scroll.set_hexpand(True)
    scroll.add_css_class('pw-scroll')

    header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    header.add_css_class('pw-header')
    title = Gtk.Label()
    title.set_markup('<span weight="bold" size="x-large">Print Works</span>')
    title.add_css_class('pw-page-title')
    header.append(title)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.add_css_class('pw-page')
    box.append(header)
    box.append(scroll)

    def prewarm():
        for _category, items in PRINTWORKS[:1]:
            for item in items[:3]:
                path=_thumb_path(item[1])
                if os.path.exists(path):
                    request_thumb(path)
        return False
    GLib.timeout_add(2500, prewarm)
    return box
