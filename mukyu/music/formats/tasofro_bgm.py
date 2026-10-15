from mukyu.paths import ASSETS_DIR

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from mukyu.platform_compat import no_window_kwargs
from mukyu.music.metadata import ogg_info, riff_loop
from mukyu.music.formats.tasofro_archive import Member, name_hash, read_cga, read_tfpk

CATALOG = json.loads((ASSETS_DIR / 'catalogs' / 'bgm_catalog.json').read_text(encoding='utf-8'))


def archive_tracks(game, game_dir, track_cls):
    key = game['key']
    compact = key.replace('.', '')
    if key == 'th17.5':

        paths = [Path(game_dir) / p for p in ('game.exe', 'data.cga', 'data.cgb')]
        reader = read_cga
    else:
        paths = [Path(game_dir) / (compact + suffix + '.pak') for suffix in ('', 'b', 'c')]
        if '_beta' in Path(game['path']).stem:
            paths.append(Path(game_dir) / (compact + 'b_beta.pak'))
        reader = read_tfpk
    archives = []
    errors = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            archives.append(reader(path)[:2])
        except (OSError, ValueError) as exc:

            if path.suffix != '.exe':
                errors.append(f'{path.name}: {exc}')
    if not archives:
        return [], '; '.join(errors) or 'No supported Twilight Frontier music archive was found.'

    def lookup(name):
        for version, members in reversed(archives):
            member = members.get(name_hash(name, version))
            if member:
                return member
        return None

    tracks = []
    for entry in CATALOG[key]:
        name = entry['file']
        member = lookup(name)
        if member is None:
            continue
        try:
            duration, rate, channels = ogg_info(member.read, member.size)
            start = end = 0.0
            loop = lookup(name[:-4] + '.sfl')
            if loop:
                start, end = riff_loop(loop.read, loop.size, rate)
            ini = lookup(name + '.ini')
            if ini:
                text = ini.read().decode('ascii', errors='replace')
                values = dict(re.findall(r'(?m)^\s*(repeatstart|repeatend)\s*=\s*(\d+)', text))
                if 'repeatstart' in values and 'repeatend' in values:
                    start, end = int(values['repeatstart']) / rate, int(values['repeatend']) / rate
            if not 0 <= start < end <= duration + 0.05:
                start = end = 0.0
        except (OSError, ValueError) as exc:
            errors.append(f'{Path(name).name}: {exc}')
            continue
        tracks.append(track_cls(
            id=f'{key}:{name.lower()}', game_key=key, game_title=game['title'],
            filename=Path(name).name, title=entry['title'], artist=game['title'],
            source_kind='tasofro', source_path=member.archive,
            offset=member.offset, length=member.size,
            sample_rate=rate, channels=channels, byte_rate=rate * channels * 2,
            duration=duration, loop_start=start, loop_end=end,
            archive_version=member.version, archive_key=member.key,
        ))
    return tracks, '; '.join(errors)


def materialize(track, scratch_dir):
    member = Member(track.source_path, track.offset, track.length, track.archive_version, track.archive_key)
    stat = Path(track.source_path).stat()
    identity = f'{track.id}|{track.source_path}|{stat.st_size}|{stat.st_mtime_ns}|{track.offset}|{track.length}'
    token = hashlib.sha256(identity.encode()).hexdigest()[:24]
    out = Path(scratch_dir) / (token + '.ogg')
    if out.is_file() and out.stat().st_size == member.size:
        return str(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    temp = out.with_suffix('.part')
    try:
        if member.version == 2:
            result = subprocess.run([
                sys.executable, str(Path(__file__).with_name('tasofro_archive.py')),
                str(member.archive), str(member.offset), str(member.size),
                str(member.version), member.key.hex(), str(temp),
            ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                timeout=300, check=False, **no_window_kwargs())
            if result.returncode != 0:
                detail = result.stderr.strip().splitlines()
                raise RuntimeError(detail[-1] if detail else 'The music archive decoder failed')
        else:
            member.extract_ogg(temp)
        os.replace(temp, out)
    finally:
        temp.unlink(missing_ok=True)
    return str(out)
