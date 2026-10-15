from mukyu.paths import ROOT_DIR
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mukyu.music.formats.pc98_hdi import HdiFilesystem
from mukyu.platform_compat import IS_WINDOWS, cache_home, exe_name, no_window_kwargs

APP_DIR = ROOT_DIR
BIN_DIR = APP_DIR / "tools" / "pc98" / "bin"
CACHE_DIR = Path(cache_home()) / "mukyulauncher" / "pc98"
CACHE_VERSION = "6"

RENDER_TAIL = 1.5
RHYTHM_NAMES = ("BD", "SD", "TOP", "HH", "TOM", "RIM")


_PF_NONE = 0xF388
_PF_RLE = 0x9595


def _rle_unpack(buf, orgsize):
    out = bytearray()
    prev = -1
    i = 0
    n = len(buf)
    while len(out) < orgsize and i < n:
        b = buf[i]
        i += 1
        if b == prev:
            count = buf[i] if i < n else 0
            i += 1
            out.append(b)
            if count:
                out.extend(bytes([b]) * count)
        else:
            prev = b
            out.append(b)
    return bytes(out[:orgsize])


class _Member:
    __slots__ = ("name", "kind", "aux", "psize", "osize", "offset")

    def __init__(self, name, kind, aux, psize, osize, offset):
        self.name, self.kind, self.aux = name, kind, aux
        self.psize, self.osize, self.offset = psize, osize, offset


def _parse_pf_th02(data):
    members = []
    pos = 0
    while pos + 32 <= len(data):
        kind = struct.unpack_from("<H", data, pos)[0]
        if kind == 0:
            break
        if kind not in (_PF_NONE, _PF_RLE):
            return None
        aux = 0x12
        raw = bytes((~c) & 0xFF for c in data[pos + 3:pos + 16])
        name = raw.split(b"\xff", 1)[0]
        if not name or not all(0x20 <= c < 0x7F for c in name):
            return None
        psize, osize, offset = struct.unpack_from("<III", data, pos + 16)
        if offset + psize > len(data):
            return None
        members.append(_Member(name.decode("ascii").upper(), kind, aux, psize, osize, offset))
        pos += 32
    return members or None


def _parse_pf_th03(data):
    if len(data) < 48:
        return None
    esize, _unk, _count, key = struct.unpack_from("<HHHH", data, 0)
    if esize < 32 or esize % 32 or 16 + esize > len(data):
        return None
    table = bytearray(data[16:16 + esize])
    al = key & 0xFF
    for i, c in enumerate(table):
        plain = c ^ al
        table[i] = plain
        al = (al - plain) & 0xFF
    members = []
    for pos in range(0, esize, 32):
        kind, aux = struct.unpack_from("<HB", table, pos)
        if kind == 0:
            break
        if kind not in (_PF_NONE, _PF_RLE):
            return None
        name = bytes(table[pos + 3:pos + 16]).split(b"\0", 1)[0]
        if not name or not all(0x20 <= c < 0x7F for c in name):
            return None
        psize, osize, offset = struct.unpack_from("<HHI", table, pos + 16)
        if offset + psize > len(data):
            return None
        members.append(_Member(name.decode("ascii").upper(), kind, aux, psize, osize, offset))
    return members or None


class PfArchive:
    def __init__(self, label, data, members):
        self.label = label
        self.data = data
        self.members = {m.name: m for m in members}

    @classmethod
    def open(cls, label, data):
        for parser in (_parse_pf_th03, _parse_pf_th02):
            try:
                members = parser(data)
            except (struct.error, IndexError):
                members = None
            if members:
                return cls(label, data, members)
        return None

    def read(self, name):
        m = self.members[name.upper()]
        raw = self.data[m.offset:m.offset + m.psize]
        if m.aux:
            raw = bytes(b ^ m.aux for b in raw)
        return _rle_unpack(raw, m.osize) if m.kind == _PF_RLE else raw[:m.osize]


_TH01 = [
    ("A Sacred Lot", ["REIMU"]),
    ("Eternal Shrine Maiden (永遠の巫女)", ["ST0", "ST6"]),
    ("The Positive and Negative", ["POSITIVE"]),
    ("Highly Responsive to Prayers", ["ST1"]),
    ("Eastern Tale of Fancy (東方怪奇談)", ["ST2"]),
    ("Angel's Legend (天使伝説)", ["LEGEND"]),
    ("Oriental Magician", ["ST3"]),
    ("Small Evil-Crushing Blade (破邪の小太刀)", ["ST4"]),
    ("Magic Mirror (魔鏡)", ["KAMI", "KAMI2"]),
    ("The Legend of KAGE", ["ST5"]),
    ("Now, Until the Moment You Die (いざ、倒れ逝くその時まで)", ["TENSI"]),
    ("Civilization of Magic", ["SHUGEN", "SYUGEN"]),
    ("Angel of a Distant Star (星幽天使)", ["ALICE"]),
    ("Iris (アイリス)", ["IRIS"]),
    ("Shrine of the Wind", ["ZIPANGU"]),
]

_TH02 = [
    ("東方封魔録 ～ 浄土曼荼羅 (Pure Land Mandala)", ["OP"]),
    ("博麗 ～ Eastern Wind", ["STAGE0"]),
    ("She's in a temper!!", ["BOSS1"]),
    ("End of Daylight", ["STAGE1"]),
    ("やみのちから (Power of Darkness)", ["BOSS4"]),
    ("幻夢界 (Dream World)", ["STAGE2"]),
    ("死を賭して (Staking Your Life)", ["BOSS2"]),
    ("ひもろぎ、むらさきにもえ (Himorogi, Burning Purple)", ["STAGE3"]),
    ("恋色マジック (Love-Colored Magic)", ["BOSS3"]),
    ("東方封魔録 ～ 幽幻乱舞 (Phantom Dance)", ["STAGE4"]),
    ("Complete Darkness", ["MIMA"]),
    ("エキストララブ (Extra Love)", ["STAGE5"]),
    ("戦車むすめのみるゆめ (The Dream a Tank Girl Sees)", ["BOSS5"]),
    ("遠野の森 (Forest of Tōno)", ["END1"]),
    ("昔話わんだーらんど (Folktale Wonderland)", ["ENDING"]),
]

_TH03 = [
    ('A Dream Transcending Spacetime', ["OP"]),
    ('Selection', ["SELECT"]),
    ('Eastern Mystical Tale of Romance', ["00MM"]),
    ('Reincarnation', ["01MM"]),
    ('Dim. Dream', ["02MM"]),
    ('Tabula rasa ~ The Empty Girl', ["03MM"]),
    ('Maniacal Princess', ["04MM"]),
    ('Vanishing Dream ~ Lost Dream', ["05MM"]),
    ('Visionary Game ~ Dream War', ["06MM"]),
    ('Decisive Magic Battle! ~ Fight it out!', ["DEC"]),
    ('Sailor of Time', ["07MM"]),
    ('Strawberry Crisis!!', ["08MM"]),
    ('Disunified Field Theory of Magic', ["DEMO1"]),
    ('Adoration of Magic', ["DEMO2"]),
    ('Dream of Eternity', ["DEMO3"]),
    ('Eastern Blue Sky', ["DEMO4"]),
    ('Eternal Full Moon', ["DEMO5"]),
    ('Maple Dream...', ["ED"]),
    ("Ghostly Person's Holiday", ["SCORE"]),
    ('Victory Demonstration', ["WIN"]),
    ('Game Over', ["OVER"]),
]

_TH04 = [
    ("幻想郷 ～ Lotus Land Story", ["OP"]),
    ("Witching Dream", ["ST00"]),
    ("Selene's light", ["ST10"]),
    ("装飾戦 ～ Decoration Battle", ["ST00B"]),
    ("Break the Sabbath", ["ST01"]),
    ("紅響曲 ～ Scarlet Phoneme", ["ST01B"]),
    ("Bad Apple!!", ["ST02"]),
    ("霊戦 ～ Perdition crisis", ["ST02B"]),
    ("アリスマエステラ (Alice Maestra)", ["ST03"]),
    ("少女綺想曲 ～ Capriccio", ["ST03C"]),
    ("星の器 ～ Casket of Star", ["ST03B"]),
    ("Lotus Love", ["ST04"]),
    ("眠れる恐怖 ～ Sleeping Terror", ["ST04B"]),
    ("Dream Land", ["ST05"]),
    ("幽夢 ～ Inanimate Dream", ["ST05B"]),
    ("禁じざるをえない遊戯 (A Game We Cannot Help Playing)", ["ST06"]),
    ("メイド幻想 ～ Icemilk Magic", ["ST06B"]),
    ("かわいい悪魔 ～ Innocence", ["ST06C"]),
    ("Days", ["END1"]),
    ("Peaceful", ["END2"]),
    ("Arcadian Dream", ["STAFF"]),
    ("幻想の住人 (Residents of Fantasy)", ["NAME"]),
]

_TH05 = [
    ("怪綺談 ～ Mystic Square", ["OP"]),
    ("Dream Express", ["ST00"]),
    ("魔法陣 ～ Magic Square", ["ST00B"]),
    ("夢想時空 (Dream Spacetime)", ["ST01"]),
    ("霊天 ～ Spiritual Heaven", ["ST01B"]),
    ("Romantic Children", ["ST02"]),
    ("プラスチックマインド (Plastic Mind)", ["ST02B"]),
    ("メイプルワイズ (Maple Wise)", ["ST03"]),
    ("禁断の魔法 ～ Forbidden Magic", ["ST03B"]),
    ("真紅の少女 ～ Crimson Dead!!", ["ST03C"]),
    ("裏切りの少女 ～ Judas Kiss", ["ST03D"]),
    ("the Last Judgement", ["ST04"]),
    ("悲しき人形 ～ Doll of Misery", ["ST04B"]),
    ("世界の果て ～ World's End", ["ST05"]),
    ("神話幻想 ～ Infinite Being", ["ST05B"]),
    ("不思議の国のアリス (Alice in Wonderland)", ["ST06"]),
    ("the Grimoire of Alice", ["ST06B"]),
    ("神社 (Shrine)", ["ED00"]),
    ("Endless", ["ED01"]),
    ("久遠の楽園 (Eternal Paradise)", ["ED02"]),
    ("Mystic Dream", ["STAFF"]),
    ("Peaceful Romancer", ["EXED"]),
    ("魂の休らむ所 (Where Souls Rest)", ["NAME"]),
]


_TH02 += [
    ("Hakurei Shrine Grounds (博麗神社境内)", ["H_NG00"]),
    ("Sunfall (陽落ちて)", ["H_NG01"]),
    ("Demon-Sealing Finale (封魔終演)", ["H_NG02"]),
]
_TH03 += [
    ('Winds of Time', ["Y_NG00"]),
    ('Starbow Dream', ["Y_NG01"]),
    ('Phantasmagoria', ["Y_NG02"]),
]
_TH04 += [(title, [f"G_NG{i:02d}"]) for i, title in enumerate([
    "Lotus Road", "Dreamy Pilot", "Incomplete Plot", "Border Land",
    "Magic Shop of Raspberry", "Crescent Dream",
])]


_TH03_MUSIC_ORDER = (
    "OP", "SELECT", "00MM", "01MM", "02MM", "03MM", "04MM", "05MM", "06MM",
    "WIN", "DEC", "DEMO1", "07MM", "DEMO2", "08MM", "DEMO3", "DEMO4", "DEMO5",
    "ED", "OVER", "SCORE", "Y_NG00", "Y_NG01", "Y_NG02",
)

CATALOG = {1: _TH01, 2: _TH02, 3: _TH03, 4: _TH04, 5: _TH05}
EXTENSIONS = {
    1: (".MDT",),
    2: (".M",),
    3: (".M",),
    4: (".M86", ".M26"),
    5: (".M2", ".M"),
}


def _tool(name):
    name = exe_name(name)
    path = BIN_DIR / name
    if path.is_file() and os.access(path, os.X_OK):
        return str(path)
    return shutil.which(name)


def renderer_missing_message(game_number):
    tool = "mdt_render" if game_number == 1 else "pmd_render"
    if IS_WINDOWS:
        return (f"The PC-98 music renderer ({tool}.exe) is not installed. "
                "Build it with packaging/windows (see README.md) and put it in tools/pc98/bin/.")
    return (f"The PC-98 music renderer ({tool}) is not installed or cannot run. "
            "Run scripts/install_pc98_music.sh in the launcher folder.")


def _file_sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _synthesize_rhythm(directory):
    import random
    rate = 48000
    rng = random.Random(98)

    def write(name, samples):
        with wave.open(str(directory / f"2608_{name}.WAV"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(b"".join(struct.pack("<h", max(-32767, min(32767, int(s)))) for s in samples))

    import math
    def sweep(f0, f1, dur, decay, amp):
        n = int(rate * dur)
        phase = 0.0
        out = []
        for i in range(n):
            t = i / n
            phase += 2 * math.pi * (f1 + (f0 - f1) * math.exp(-t * 6)) / rate
            out.append(amp * math.sin(phase) * math.exp(-t * decay))
        return out

    def noise(dur, decay, amp, hp=0.0):
        n = int(rate * dur)
        prev = 0.0
        out = []
        for i in range(n):
            x = rng.uniform(-1, 1)
            y = x - hp * prev
            prev = x
            out.append(amp * y * math.exp(-i / n * decay))
        return out

    write("BD", sweep(160, 45, 0.25, 7, 24000))
    sd_tone = sweep(260, 180, 0.2, 9, 9000)
    sd_noise = noise(0.2, 8, 9000, 0.3)
    write("SD", [a + b for a, b in zip(sd_tone, sd_noise)])
    write("TOP", noise(0.7, 5, 9000, 0.9))
    write("HH", noise(0.08, 9, 8000, 0.95))
    write("TOM", sweep(220, 90, 0.3, 6, 22000))
    write("RIM", sweep(1700, 1500, 0.04, 20, 18000))


def rhythm_dir(image_path):
    candidates = [Path(image_path).resolve().parent, Path(image_path).resolve().parent.parent,
                  APP_DIR / "tools" / "pc98" / "rhythm", CACHE_DIR / "rhythm_user"]
    for d in candidates:
        files = {p.name.upper() for p in d.glob("*")} if d.is_dir() else set()
        if all(f"2608_{n}.WAV" in files for n in RHYTHM_NAMES):
            out = CACHE_DIR / "rhythm_real"
            out.mkdir(parents=True, exist_ok=True)
            for p in d.iterdir():
                if p.name.upper() in {f"2608_{n}.WAV" for n in RHYTHM_NAMES}:
                    target = out / p.name.upper()
                    if not target.exists() or target.stat().st_size != p.stat().st_size:
                        shutil.copyfile(p, target)
            return str(out), True
    out = CACHE_DIR / "rhythm_synth"
    if not all((out / f"2608_{n}.WAV").is_file() for n in RHYTHM_NAMES):
        out.mkdir(parents=True, exist_ok=True)
        _synthesize_rhythm(out)
    return str(out), False


def _decode_text(raw):
    for enc in ("cp932", "utf-8"):
        try:
            return raw.decode(enc).strip()
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1").strip()


def _collect_members(fs, game_number):
    index = {}
    archives = []
    for entry in fs.entries():
        if entry.is_dir or entry.size < 32:
            continue
        base = Path(entry.path).name.upper()
        suffix = Path(base).suffix
        if game_number == 1 and base == "MDRV98.COM":
            index[base] = (None, entry.path)
            continue
        if suffix in (".EXE", ".COM", ".SYS", ".BAT", ".TXT", ".URL", ".PI", ".GRP", ".GRZ", ".GRF"):
            continue
        if suffix in EXTENSIONS[game_number]:
            index.setdefault(base, (None, entry.path))
            continue
        if game_number == 1:
            continue
        if entry.size > 4 * 1024 * 1024:
            continue
        try:
            data = fs.read_file(entry.path)
        except Exception:
            continue
        archive = PfArchive.open(entry.path, data)
        if archive:
            archives.append(archive)
    for archive in archives:
        for name in archive.members:
            index.setdefault(name, (archive, name))
    return index


def _write_member(fs, loader, dest):
    archive, ref = loader
    data = archive.read(ref) if archive else fs.read_file(ref)
    Path(dest).write_bytes(data)


def _parse_kv(stdout):
    values = {}
    for line in stdout.splitlines():
        if b"=" in line:
            k, v = line.split(b"=", 1)
            values[k.decode("ascii", "ignore")] = v
    return values


def _probe(tool, path, rhythm, driver=None):
    if driver:
        cmd = [tool, "--info", str(path), "--driver", str(driver)]
    else:
        cmd = [tool, "--info", str(path), "--rhythm", rhythm]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False, **no_window_kwargs())
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    values = _parse_kv(result.stdout)
    try:
        if driver:
            length = int(values.get("LENGTH_MS", b"0"))
            looped = values.get("LOOPED", b"0") == b"1"
            start = int(values.get("LOOP_START_MS", b"0"))
            return {"length_ms": length, "loop_ms": (length - start) if looped else 0, "title": ""}
        return {
            "length_ms": int(values.get("LENGTH_MS", b"0")),
            "loop_ms": int(values.get("LOOP_MS", b"0")),
            "title": _decode_text(values.get("TITLE", b"")),
        }
    except ValueError:
        return None


def _music_room_source(game, number):
    if number not in (2, 3, 4):
        return None, {}
    image = Path(game['path'])
    candidates = []
    configured = game.get('pc98_music_room')
    if configured:
        candidates.append(Path(configured))

    candidates.extend(sorted(image.parent.glob('th05*.hdi')))
    candidates.extend(sorted(image.parent.glob('TH05*.HDI')))
    for candidate in dict.fromkeys(candidates):
        if candidate.is_file() and candidate.resolve() != image.resolve():
            try:
                fs = HdiFilesystem(candidate)
                index = _collect_members(fs, 5)
                if any(name.startswith(('H_NG', 'Y_NG', 'G_NG')) for name in index):
                    return fs, index
            except (OSError, ValueError):
                continue
    return None, {}


def discover(game, scratch_root, track_cls):
    key = game["key"]
    m = re.fullmatch(r"th(\d+)", key)
    number = int(m.group(1)) if m else 0
    if number not in CATALOG:
        return [], "This game's music format is not recognized."
    try:
        fs = HdiFilesystem(game["path"])
    except Exception as exc:
        return [], f"The PC-98 disk image could not be read: {exc}"

    index = _collect_members(fs, number)
    if not index:
        return [], "No music files were found inside the PC-98 disk image."

    work = Path(scratch_root) / f"pc98-{key}"
    work.mkdir(parents=True, exist_ok=True)
    tool = _tool("mdt_render" if number == 1 else "pmd_render")
    rhythm, _real = rhythm_dir(game["path"])
    image_id = _file_sha1(game["path"])[:16]
    cache_file = CACHE_DIR / f"{key}-{image_id}-v{CACHE_VERSION}.json"
    try:
        cache = json.loads(cache_file.read_text())
    except (OSError, ValueError):
        cache = {}

    driver = None
    if number == 1:
        if "MDRV98.COM" not in index:
            return [], "MDRV98.COM (the TH01 music driver) was not found on the disk image."
        driver = work / "MDRV98.COM"
        try:
            _write_member(fs, index["MDRV98.COM"], driver)
        except Exception as exc:
            return [], f"The TH01 music driver could not be read: {exc}"

    room_fs, room_index = _music_room_source(game, number)
    picks = []
    for position, (title, stems) in enumerate(CATALOG[number], start=1):
        if number == 3 and stems[0] not in _TH03_MUSIC_ORDER:
            continue
        chosen = None
        for stem in stems:
            for ext in EXTENSIONS[number]:
                name = stem + ext
                if name in index:
                    chosen = (name, index[name])
                    break
            if chosen:
                break
        source_fs = fs
        if not chosen:
            for stem in stems:
                if not stem.startswith(('H_NG', 'Y_NG', 'G_NG')):
                    continue
                for ext in ('.M2', '.M'):
                    name = stem + ext
                    if name in room_index:
                        chosen = (name, room_index[name])
                        source_fs = room_fs
                        break
                if chosen:
                    break
        if not chosen:
            continue
        name, loader = chosen
        dest = work / f"{position:02d}_{name}"
        try:
            _write_member(source_fs, loader, dest)
        except Exception:
            continue
        picks.append((position, title, name, dest))

    if not picks:
        return [], "None of this game's music files could be read from the disk image."

    infos = {}
    todo = []
    driver_data = driver.read_bytes() if driver else b""
    for position, title, name, dest in picks:
        ck = hashlib.sha1(dest.read_bytes() + driver_data).hexdigest()
        if ck in cache:
            infos[position] = cache[ck]
        else:
            todo.append((position, ck, dest))
    if todo and tool:
        with ThreadPoolExecutor(max_workers=max(1, min(4, os.cpu_count() or 2))) as pool:
            for (position, ck, dest), info in zip(todo, pool.map(lambda t: _probe(tool, t[2], rhythm, driver), todo)):
                if info:
                    infos[position] = info
                    cache[ck] = info
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(cache))
        except OSError:
            pass

    tracks = []
    for position, title, name, dest in picks:
        info = infos.get(position) or {}
        length = info.get("length_ms", 0) / 1000.0
        loop = info.get("loop_ms", 0) / 1000.0
        track = track_cls(
            id=f"{key}:{position:02d}:{name.lower()}",
            game_key=key, game_title=game["title"],
            filename=name, title=title, artist=game["title"],
            source_kind="pc98_mdt" if number == 1 else "pc98_pmd",
            source_path=str(dest),
            sample_rate=44100, channels=2, bits=16, byte_rate=176400,
            duration=length,
        )
        if loop > 0.5 and length >= loop:
            track.loop_start = max(length - loop, 0.0)
            track.loop_end = length
        elif loop <= 0:
            track.duration = length + RENDER_TAIL
        track.rhythm_dir = rhythm
        tracks.append(track)
    if number == 3:
        order = {stem: i for i, stem in enumerate(_TH03_MUSIC_ORDER)}
        tracks.sort(key=lambda track: order[Path(track.filename).stem.upper()])
    error = "" if tool else renderer_missing_message(number)
    return tracks, error


def render(track, scratch_dir):
    m = re.fullmatch(r"th(\d+)", track.game_key)
    number = int(m.group(1)) if m else 0
    tool = _tool("mdt_render" if number == 1 else "pmd_render")
    if not tool:
        raise FileNotFoundError(renderer_missing_message(number))
    out = Path(scratch_dir) / (re.sub(r"[^A-Za-z0-9._-]+", "_", track.id) + f"-v{CACHE_VERSION}.wav")
    if out.is_file() and out.stat().st_size > 44:
        return str(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rhythm = getattr(track, "rhythm_dir", None) or rhythm_dir(track.source_path)[0]
    tmp = out.with_suffix(".part")
    cmd = [tool, "--render", track.source_path, str(tmp), "--rhythm", rhythm]
    if number == 1:
        driver = Path(track.source_path).with_name("MDRV98.COM")
        if not driver.is_file():
            raise FileNotFoundError("The TH01 music driver (MDRV98.COM) has not been extracted yet.")
        cmd += ["--driver", str(driver)]
    result = subprocess.run(cmd,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            timeout=300, check=False, **no_window_kwargs())
    if result.returncode != 0 or not tmp.is_file() or tmp.stat().st_size <= 44:
        tmp.unlink(missing_ok=True)
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(detail or f"The renderer failed (exit code {result.returncode}).")
    os.replace(tmp, out)
    return str(out)
