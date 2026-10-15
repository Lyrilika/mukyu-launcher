from mukyu.paths import ASSETS_DIR

import json
from pathlib import Path


with (ASSETS_DIR / 'catalogs' / 'bgm_titles.json').open(encoding='utf-8') as source:
    TITLES = json.load(source)


def apply_titles(track):

    filename = track.filename.replace('\\', '/').lower()
    game_titles = TITLES.get(track.game_key, {})
    names = game_titles.get(filename) or game_titles.get(Path(filename).name)
    if names:
        track.title_en = names['en'] + names.get('suffix_en', '')
        track.title_ja = names['ja'] + names.get('suffix_ja', '')
    else:


        stem = Path(filename).stem
        track.title_en = f'Track {stem}'
        track.title_ja = track.title or f'トラック {stem}'
    track.title = track.title_en


def display_title(track, language='en'):
    return (track.title_ja if language == 'ja' else track.title_en) or track.title


def _read_preferences(path):
    try:
        preferences = json.loads(Path(path).read_text(encoding='utf-8'))
        return preferences if isinstance(preferences, dict) else {}
    except (OSError, ValueError):
        return {}


def load_title_language(path):
    language = _read_preferences(path).get('title_language', 'en')
    return language if language in ('en', 'ja') else 'en'


def save_title_language(path, language):

    import os
    import tempfile

    if language not in ('en', 'ja'):
        raise ValueError('Unsupported title language')
    path = Path(path)
    preferences = _read_preferences(path)
    preferences['title_language'] = language
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=path.name + '.', delete=False) as output:
            temporary = output.name
            json.dump(preferences, output, ensure_ascii=False, indent=2)
            output.write('\n')
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
