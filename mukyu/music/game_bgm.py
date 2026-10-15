from mukyu.paths import ROOT_DIR
import os
import hashlib
import re
import shutil
import struct
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

from mukyu.music.formats import pc98_bgm
from mukyu.music.formats import tasofro_bgm
from mukyu.music.titles import apply_titles
from mukyu.music.metadata import ogg_file_info, file_loop
from mukyu.platform_compat import IS_WINDOWS, exe_name, no_window_kwargs


GAME_INFO = [
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

TH06_TITLES = {
    "th06_01.wav": "A Dream More Scarlet than Red",
    "th06_02.wav": "A Soul as Scarlet as a Ground Cherry",
    "th06_03.wav": "Apparitions Stalk the Night",
    "th06_04.wav": "Lunate Elf",
    "th06_05.wav": "Tomboyish Girl in Love",
    "th06_06.wav": "Shanghai Teahouse ~ Chinese Tea",
    "th06_07.wav": "Shanghai Alice of Meiji 17",
    "th06_08.wav": "Voile, the Magic Library",
    "th06_09.wav": "Locked Girl ~ The Girl's Sealed Room",
    "th06_10.wav": "The Maid and the Pocket Watch of Blood",
    "th06_11.wav": "Lunar Clock ~ Luna Dial",
    "th06_12.wav": "The Young Descendant of Tepes",
    "th06_13.wav": "Septette for a Dead Princess",
    "th06_14.wav": "The Centennial Festival for Magical Girls",
    "th06_15.wav": "U.N. Owen Was Her?",
    "th06_16.wav": "An Eternity More Transient than Scarlet",
    "th06_17.wav": "Scarlet Chamber ~ Eastern Dream...",
}


@dataclass
class GameTrack:
    id: str
    game_key: str
    game_title: str
    filename: str
    title: str
    artist: str
    source_kind: str
    source_path: str
    offset: int = 0
    length: int = 0
    sample_rate: int = 44100
    channels: int = 2
    bits: int = 16
    byte_rate: int = 176400
    loop_start: float = 0.0
    loop_end: float = 0.0
    duration: float = 0.0
    archive_version: int = -1
    archive_key: bytes = b""
    title_en: str = ""
    title_ja: str = ""


def game_info_map():
    return {key: (title, cover) for title, key, cover in GAME_INFO}


def assigned_games(config):
    result = []
    info = game_info_map()
    for title, key, cover in GAME_INFO:
        entry = config.get(key, {})
        path = entry.get("exe") if isinstance(entry, dict) else entry
        if path and os.path.exists(path):
            result.append({"key": key, "title": title, "cover": cover, "path": os.path.abspath(path)})
    room_entry = config.get('th5', {})
    room_path = room_entry.get('exe') if isinstance(room_entry, dict) else room_entry
    if room_path and os.path.isfile(room_path):
        for game in result:
            if game['key'] in ('th2', 'th3', 'th4'):
                game['pc98_music_room'] = os.path.abspath(room_path)
    return result


def _game_number(game_key):
    match = re.fullmatch(r"th(\d+)(?:\.(\d+))?", game_key)
    if not match:
        return None
    whole, decimal = match.groups()
    return int(whole), decimal or ""


def _game_dir(assigned):
    return str(Path(assigned["path"]).resolve().parent)


def _candidate_dat_files(game_dir, game_key):
    number = _game_number(game_key)
    if not number:
        return []
    whole, decimal = number

    stems = []
    variants = [f"{whole}{decimal}", f"{whole:02d}{decimal}"]
    for variant in variants:
        if variant not in stems:
            stems.append(variant)
    if not decimal:
        padded = f"{whole:02d}"
        if padded not in stems:
            stems.insert(0, padded)

    candidates = []
    suffixes = (".dat", "_tr.dat", "tr.dat", "b.dat", "a.dat", "bgm.dat")
    for stem in stems:
        for suffix in suffixes:
            path = Path(game_dir) / f"th{stem}{suffix}"
            if path.is_file():
                candidates.append(path)
        for path in sorted(Path(game_dir).glob(f"th{stem}*.dat")):
            candidates.append(path)

    seen = set()
    result = []
    for path in candidates:
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def _find_existing_fmt(game_dir):
    candidates = [
        Path(game_dir) / "thbgm.fmt",
        Path(game_dir) / "thbgm_tr.fmt",
    ]
    return next((p for p in candidates if p.is_file()), None)


def _tool_path(name):
    name = exe_name(name)
    app_dir = ROOT_DIR
    bundled = app_dir / "tools" / "thtk" / "bin" / name
    if bundled.is_file():
        return bundled
    bundled_flat = app_dir / "tools" / "thtk" / name
    if bundled_flat.is_file():
        return bundled_flat
    return shutil.which(name)


def _tool_env(tool):
    env = os.environ.copy()
    tool_path = Path(tool).resolve()
    lib_dir = tool_path.parent.parent / "lib64"
    if lib_dir.is_dir():
        current = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = str(lib_dir) + ((os.pathsep + current) if current else "")
    return env


def _thtk_game_id(game_key):
    number = _game_number(game_key)
    if not number:
        return None
    whole, decimal = number
    return f"{whole}{decimal}"


def _run_thdat(args, output_dir, timeout, game_key=None):
    thdat = _tool_path("thdat")
    if not thdat:
        return False
    commands = []
    game_id = _thtk_game_id(game_key) if game_key else None
    if game_id and len(args) >= 2 and args[0] in ("-x", "-l") and args[1] == "d":
        commands.append([str(thdat), args[0], game_id, *args[2:]])
    commands.append([str(thdat), *args])
    if args[:2] == ["-x", "d"]:
        commands.append([str(thdat), "-xd", *args[2:]])
    elif args[:2] == ["-l", "d"]:
        commands.append([str(thdat), "-ld", *args[2:]])
    seen = set()
    for command in commands:
        key = tuple(command)
        if key in seen:
            continue
        seen.add(key)
        try:
            result = subprocess.run(
                command,
                cwd=output_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=_tool_env(thdat),
                timeout=timeout,
                check=False,
                **no_window_kwargs(),
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            return True
    return False


def _list_thdat_members(archive, game_key):
    thdat = _tool_path("thdat")
    if not thdat:
        return []
    game_id = _thtk_game_id(game_key)
    commands = []
    if game_id:
        commands.append([str(thdat), "-l", game_id, str(archive)])
    commands.append([str(thdat), "-l", "d", str(archive)])
    commands.append([str(thdat), "-ld", str(archive)])
    for command in commands:
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=_tool_env(thdat),
                timeout=20,
                check=False,
                **no_window_kwargs(),
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return []


def _extract_archive(archive, output_dir, game_key=None):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    _run_thdat(["-x", "d", str(archive)], output_dir, 90, game_key)
    files = [p for p in Path(output_dir).rglob("*") if p.is_file()]
    return files


def _extract_members(archive, output_dir, game_key=None):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    wanted = ("thbgm.fmt", "thbgm_tr.fmt", "musiccmt.txt", "musiccmt_tr.txt")
    members = _list_thdat_members(archive, game_key)
    candidates = []
    for wanted_name in wanted:
        direct = next((m for m in members if m.replace("\\", "/").strip("/").lower() == wanted_name.lower()), None)
        if direct:
            candidates.append(direct)
            continue
        basename = next((m for m in members if Path(m.replace("\\", "/")).name.lower() == wanted_name.lower()), None)
        if basename:
            candidates.append(basename)
        else:
            candidates.append(wanted_name)
    for member in candidates:
        _run_thdat(["-x", "d", str(archive), member], output_dir, 20, game_key)
    for name in ("thbgm.fmt", "thbgm_tr.fmt"):
        path = next(Path(output_dir).rglob(name), None)
        if path and path.is_file():
            return path
    return None


def _find_or_extract_fmt(game_dir, game_key, scratch_root):
    existing = _find_existing_fmt(game_dir)
    if existing:
        return existing
    for archive in _candidate_dat_files(game_dir, game_key):
        extract_dir = Path(scratch_root) / archive.stem
        extract_dir.mkdir(parents=True, exist_ok=True)
        fmt = _extract_members(archive, str(extract_dir), game_key)
        if fmt:
            return fmt
    return None


def _find_musiccmt(game_dir, scratch_root=None):
    direct = [Path(game_dir) / "musiccmt.txt", Path(game_dir) / "musiccmt_tr.txt"]
    for path in direct:
        if path.is_file():
            return path
    root = Path(scratch_root) if scratch_root else None
    if root and root.is_dir():
        for name in ("musiccmt.txt", "musiccmt_tr.txt"):
            found = next(root.rglob(name), None)
            if found:
                return found
    return None


def _parse_musiccmt(path):
    if not path or not path.is_file():
        return {}
    raw = path.read_bytes()
    decoded = None
    for encoding in ("shift_jis", "cp932", "utf-8"):
        try:
            decoded = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if decoded is None:
        return {}

    lines = [line.strip() for line in decoded.splitlines()]
    result = {}
    for i, line in enumerate(lines):
        if not line.lower().startswith("@bgm/"):
            continue
        filename = line.split("/", 1)[1].strip()
        title = ""
        for candidate in lines[i + 1:i + 8]:
            if not candidate or candidate.startswith("#") or candidate.startswith("@"):
                continue
            cleaned = re.sub(r"^No\.\s*\d+\s*", "", candidate).strip()
            if cleaned and not cleaned.startswith("♪"):
                title = cleaned
                break
        if title:
            key = filename.lower()
            result[key] = title
            result[Path(filename).stem.lower()] = title
    return result


def _title_from_filename(filename, game_key, titles):
    key = filename.lower()
    fallback_titles = TH06_TITLES if game_key == "th6" else {}
    if key in fallback_titles:
        return fallback_titles[key]
    if key in titles:
        return titles[key]
    stem = Path(filename).stem.lower()
    for known, title in titles.items():
        if Path(known).stem.lower() == stem:
            return title
    return Path(filename).stem


def _parse_fmt(fmt_path, game_key, game_title, game_dir):
    data = Path(fmt_path).read_bytes()
    tracks = []
    musiccmt = Path(fmt_path).with_name("musiccmt.txt")
    if not musiccmt.exists():
        musiccmt = Path(fmt_path).with_name("musiccmt_tr.txt")
    titles = _parse_musiccmt(musiccmt)
    source_name = "thbgm.dat"
    sibling_dat = Path(game_dir) / source_name
    if not sibling_dat.is_file():
        translated_dat = Path(game_dir) / "thbgm_tr.dat"
        if translated_dat.is_file():
            source_name = translated_dat.name
    for offset in range(0, len(data) - 51, 52):
        block = data[offset:offset + 52]
        filename = block[:16].split(b"\0", 1)[0].decode("ascii", errors="ignore").strip()
        if not filename:
            continue
        start_offset, _preload_length, intro_length, total_length = struct.unpack_from("<IIii", block, 16)
        format_tag, channels, sample_rate, byte_rate, block_align, bits = struct.unpack_from("<HHIIHH", block, 32)
        if format_tag != 1 or channels < 1 or sample_rate <= 0 or bits <= 0 or byte_rate <= 0:
            continue
        if total_length <= 0:
            continue
        loop_start = max(0, intro_length) / byte_rate
        loop_end = total_length / byte_rate if 0 <= intro_length < total_length else 0.0
        duration = total_length / byte_rate
        track = GameTrack(
            id=f"{game_key}:{filename.lower()}",
            game_key=game_key,
            game_title=game_title,
            filename=filename,
            title=_title_from_filename(filename, game_key, titles),
            artist=game_title,
            source_kind="thbgm",
            source_path=str(Path(game_dir) / source_name),
            offset=start_offset,
            length=total_length,
            sample_rate=sample_rate,
            channels=channels,
            bits=bits,
            byte_rate=byte_rate,
            loop_start=loop_start,
            loop_end=loop_end,
            duration=duration,
        )
        tracks.append(track)
    return tracks


def _wav_info(path, game_key, game_title, index):
    try:
        with wave.open(str(path), "rb") as wav:
            channels = wav.getnchannels()
            sample_rate = wav.getframerate()
            bits = wav.getsampwidth() * 8
            frames = wav.getnframes()
            byte_rate = max(1, wav.getnchannels() * wav.getsampwidth() * wav.getframerate())
            duration = frames / sample_rate if sample_rate else 0.0
    except (OSError, wave.Error):
        return None
    loop_start = 0.0
    loop_end = 0.0
    for pos in Path(path).parent.parent.glob("*"):
        if pos.is_dir() and pos.name.lower().endswith("md.dat"):
            candidate = pos / f"{Path(path).stem}.pos"
            if candidate.is_file():
                try:
                    start_sample, end_sample = struct.unpack("<II", candidate.read_bytes()[:8])
                    loop_start = start_sample / sample_rate
                    loop_end = end_sample / sample_rate
                except (OSError, struct.error):
                    pass
                break
    title = _title_from_filename(Path(path).name, game_key, {})
    return GameTrack(
        id=f"{game_key}:{Path(path).name.lower()}",
        game_key=game_key,
        game_title=game_title,
        filename=Path(path).name,
        title=title,
        artist=game_title,
        source_kind="file",
        source_path=str(path),
        sample_rate=sample_rate,
        channels=channels,
        bits=bits,
        byte_rate=byte_rate,
        loop_start=loop_start,
        loop_end=loop_end,
        duration=duration,
    )


def _probe_duration(path):
    try:
        return ogg_file_info(path)[0]
    except (OSError, ValueError, struct.error):
        pass
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 0.0
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=6, check=False,
            **no_window_kwargs(),
        )
        return max(0.0, float(result.stdout.strip())) if result.stdout.strip() else 0.0
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0.0


def _find_or_extract_musiccmt(game_dir, game_key, scratch_root):
    direct = _find_musiccmt(game_dir)
    if direct:
        return direct
    for archive in _candidate_dat_files(game_dir, game_key):
        extract_dir = Path(scratch_root) / f"{archive.stem}-metadata"
        extract_dir.mkdir(parents=True, exist_ok=True)
        for member in ("musiccmt.txt", "musiccmt_tr.txt"):
            _run_thdat(["-x", "d", str(archive), member], str(extract_dir), 20, game_key)
        found = next((extract_dir / name for name in ("musiccmt.txt", "musiccmt_tr.txt") if (extract_dir / name).is_file()), None)
        if found:
            return found
    return None


def _archive_audio_tracks(archive, game_key, game_title, scratch_root, game_dir):


    stat = archive.stat()
    stamp = hashlib.sha256(f"{archive.resolve()}:{stat.st_size}:{stat.st_mtime_ns}".encode()).hexdigest()[:16]
    extract_dir = Path(scratch_root) / f"{archive.stem}-{stamp}"
    rows = tasofro_bgm.CATALOG[game_key]
    wanted = {row['file'] for row in rows}
    wanted.update(str(Path(name).with_suffix('.sfl')) for name in tuple(wanted) if name.endswith('.ogg'))
    extract_dir.mkdir(parents=True, exist_ok=True)
    if not (extract_dir / '.complete').exists():


        _run_thdat(['-x', 'd', str(archive), *sorted(wanted)], str(extract_dir), 90, game_key)
        if all((extract_dir / row['file']).is_file() for row in rows):
            (extract_dir / '.complete').touch()
    tracks = []
    for row in rows:
        path = extract_dir / row['file']
        if not path.is_file():
            continue
        if path.suffix == '.wav':
            track = _wav_info(path, game_key, game_title, len(tracks))
        else:
            try:
                duration, rate, channels = ogg_file_info(path)
            except (OSError, ValueError, struct.error):
                continue
            track = GameTrack(
                id=f"{game_key}:{row['file'].lower()}", game_key=game_key,
                game_title=game_title, filename=path.name, title=row['title'],
                artist=game_title, source_kind='file', source_path=str(path),
                duration=duration, sample_rate=rate, channels=channels,
                byte_rate=rate * channels * 2,
            )
        if track:
            track.id = f"{game_key}:{row['file'].lower()}"
            track.title = row['title']
            loop_file = path if path.suffix == '.wav' else path.with_suffix('.sfl')
            if loop_file.is_file():
                start, end = file_loop(loop_file, track.sample_rate)
                if 0 <= start < end <= track.duration + 0.05:
                    track.loop_start, track.loop_end = start, end
            tracks.append(track)
    return tracks


def _th06_loop_points(game_dir, tracks, scratch_root):
    missing = [t for t in tracks if not 0 <= t.loop_start < t.loop_end <= t.duration + 0.05]
    if not missing:
        return
    output = Path(scratch_root) / 'th6-loop-points'
    output.mkdir(parents=True, exist_ok=True)
    names = [Path(t.filename).stem + '.pos' for t in missing]
    for archive in sorted(Path(game_dir).iterdir()):
        if archive.is_file() and archive.name.lower().endswith('md.dat'):
            _run_thdat(['-x', 'd', str(archive), *names], str(output), 20, 'th6')
    points = {p.name.lower(): p for p in output.rglob('*') if p.is_file() and p.suffix.lower() == '.pos'}
    for track in missing:
        pos = points.get((Path(track.filename).stem + '.pos').lower())
        if pos is None:
            continue
        try:
            start, end = struct.unpack('<II', pos.read_bytes()[:8])
            start, end = start / track.sample_rate, end / track.sample_rate
            if 0 <= start < end <= track.duration + 0.05:
                track.loop_start, track.loop_end = start, end
        except (OSError, struct.error):
            continue


def discover_tracks(assigned, scratch_root):
    tracks, error = _discover_tracks(assigned, scratch_root)
    for track in tracks:
        apply_titles(track)
    return tracks, error


def _discover_tracks(assigned, scratch_root):
    key = assigned["key"]
    title = assigned["title"]
    game_dir = _game_dir(assigned)
    if key == "th6":
        bgm_dir = Path(game_dir) / "bgm"
        if not bgm_dir.is_dir():
            return [], "No bgm folder was found in the assigned game."
        wavs = sorted(
            bgm_dir.glob("*.wav"),
            key=lambda p: (int(re.search(r"_(\d+)", p.stem).group(1)) if re.search(r"_(\d+)", p.stem) else 9999, p.name.lower()),
        )
        tracks = []
        for index, path in enumerate(wavs):
            track = _wav_info(path, key, title, index)
            if track:
                tracks.append(track)
        _th06_loop_points(game_dir, tracks, scratch_root)
        return tracks, "" if tracks else "No playable WAV tracks were found in the game's bgm folder."

    number = _game_number(key)
    if not number:
        return [], "This game's music format is not recognized yet."
    whole, decimal = number

    if not decimal and whole in (1, 2, 3, 4, 5):
        return pc98_bgm.discover(assigned, scratch_root, GameTrack)

    if key in {"th13.5", "th14.5", "th15.5", "th17.5"}:
        return tasofro_bgm.archive_tracks(assigned, game_dir, GameTrack)

    compact = f"{whole}{decimal}"
    special_bgm = None
    if compact == "75":
        special_bgm = Path(game_dir) / "th075bgm.dat"
    elif decimal and compact in {"105", "123"}:
        special_bgm = Path(game_dir) / f"th{compact}b.dat"

    if special_bgm and special_bgm.is_file():
        tracks = _archive_audio_tracks(special_bgm, key, title, scratch_root, game_dir)
        if tracks:
            return tracks, ""
        return [], f"The BGM archive {special_bgm.name} could not be read. This archive uses the Twilight Frontier BGM format rather than the standard Team Shanghai Alice format."

    thbgm_candidates = [Path(game_dir) / "thbgm.dat", Path(game_dir) / "thbgm_tr.dat"]
    thbgm = next((p for p in thbgm_candidates if p.is_file()), None)
    if thbgm is None:
        return [], "This game does not contain a supported BGM archive."
    fmt = _find_or_extract_fmt(game_dir, key, scratch_root)
    if not fmt:
        if _tool_path("thdat") is None:
            if IS_WINDOWS:
                return [], "BGM metadata is packed inside the game's .dat archive. Put thdat.exe in tools/thtk/bin/ (see README.md) to enable Game BGM for this game."
            return [], "BGM metadata is packed inside the game's .dat archive. Run scripts/install_thtk.sh in the launcher folder once to enable Game BGM for this game."
        return [], "The game's BGM metadata could not be extracted from its .dat archive."
    tracks = _parse_fmt(fmt, key, title, game_dir)
    if not tracks:
        return [], "The game's BGM metadata could not be read."
    return tracks, ""


def materialize_track(track, scratch_dir):
    if track.source_kind == "tasofro":
        return tasofro_bgm.materialize(track, scratch_dir), True
    if track.source_kind == "file":
        return track.source_path, False
    if track.source_kind in ("pc98_pmd", "pc98_mdt"):
        return pc98_bgm.render(track, scratch_dir), True
    source = Path(track.source_path)
    if not source.is_file():
        raise FileNotFoundError(f"Missing BGM archive: {source}")
    output = Path(scratch_dir) / (re.sub(r"[^A-Za-z0-9._-]+", "_", track.filename) + ".wav")
    if output.exists() and output.stat().st_size >= track.length + 44:
        return str(output), True
    output.parent.mkdir(parents=True, exist_ok=True)
    riff_size = 36 + track.length
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        riff_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        track.channels,
        track.sample_rate,
        track.byte_rate,
        max(1, track.channels * track.bits // 8),
        track.bits,
        b"data",
        track.length,
    )
    with open(source, "rb") as src, open(output, "wb") as dst:
        src.seek(track.offset)
        dst.write(header)
        remaining = track.length
        while remaining:
            chunk = src.read(min(1024 * 1024, remaining))
            if not chunk:
                raise IOError("The BGM archive ended before the selected track finished.")
            dst.write(chunk)
            remaining -= len(chunk)
    return str(output), True
