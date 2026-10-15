#!/usr/bin/env python3
_HELP_TEXT = """Verify an installed game collection without writing to the game directories.

python scripts/verify_game_music.py --config /path/to/games_config.json
Add --decode to render/decode every track (requires ffmpeg), or --only th12.3.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mukyu.music import game_bgm
from mukyu.music.formats import pc98_bgm


def main():
    parser = argparse.ArgumentParser(description=_HELP_TEXT)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--only', action='append', help='Game key; may be repeated')
    parser.add_argument('--decode', action='store_true')
    parser.add_argument('--report', type=Path, help='Write detailed JSON results')
    args = parser.parse_args()
    ffmpeg = shutil.which('ffmpeg')
    if args.decode and not ffmpeg:
        parser.error('--decode requires ffmpeg')
    config = json.loads(args.config.read_text(encoding='utf-8'))
    games = game_bgm.assigned_games(config)
    if args.only:
        games = [g for g in games if g['key'] in args.only]
    if not games:
        parser.error('No assigned games with existing files matched')
    report = {}
    failed = False
    with tempfile.TemporaryDirectory(prefix='mukyu-music-verify-') as scratch:
        pc98_bgm.CACHE_DIR = Path(scratch) / 'pc98-cache'
        for game in games:
            errors = []
            rows = []
            try:
                tracks, error = game_bgm.discover_tracks(game, scratch)
                if error:
                    errors.append(error)
                if not tracks:
                    errors.append('No tracks discovered')
                seen = set()
                for track in tracks:
                    if track.id in seen or track.duration <= 0:
                        errors.append(f'{track.id}: duplicate ID or invalid duration')
                    seen.add(track.id)
                    if args.decode:
                        path, temporary = game_bgm.materialize_track(track, Path(scratch) / 'playback')
                        try:
                            result = subprocess.run(
                                [ffmpeg, '-v', 'error', '-i', path, '-f', 'null', '-'],
                                capture_output=True, text=True, timeout=300,
                            )
                            if result.returncode or result.stderr:
                                errors.append(f'{track.id}: {result.stderr.strip()}')
                        finally:
                            if temporary:
                                Path(path).unlink(missing_ok=True)
                    rows.append({'id': track.id, 'title': track.title,
                                 'title_ja': track.title_ja,
                                 'file': track.filename, 'duration': track.duration})
            except Exception as exc:
                errors.append(str(exc))
            failed |= bool(errors)
            report[game['key']] = {'count': len(rows), 'errors': errors, 'tracks': rows}
            print(f"{game['key']}: {len(rows)} tracks — {'FAIL' if errors else 'PASS'}", flush=True)
            for error in errors:
                print(f'  {error}', flush=True)
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
