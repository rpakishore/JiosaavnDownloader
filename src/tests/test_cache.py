import datetime as dt
import json
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

import pytest

from jiosaavn.cache import Cache, to_record

REPO_DB = Path(__file__).parent.parent.parent / 'songs.jsonl'


def make_song(song_id: str = 'abc123', **kwargs) -> SimpleNamespace:
    fields = dict(
        id=song_id, name='Song', album='Album', year=2024,
        media_url='https://example.com/a.mp4', image_url='',
        primary_artists=('A', 'B'), artists=(),
    )
    fields.update(kwargs)
    return SimpleNamespace(**fields)


DATE = dt.datetime(2026, 10, 12, 8, 30)
PATH = PurePosixPath('/srv/music/Song-Album(2024).mp3')


def add(cache: Cache, song_id: str = 'abc123', filepath=PATH, date=DATE, **kwargs) -> None:
    cache.add(make_song(song_id, **kwargs), filepath, date)


@pytest.fixture
def cache(tmp_path) -> Cache:
    return Cache(tmp_path / 'db' / 'songs.jsonl')


def lines(cache: Cache) -> list[str]:
    return cache.filepath.read_text(encoding='utf-8').splitlines()


def test_creates_empty_file(cache):
    assert cache.filepath.is_file()
    assert cache.ids == set()
    assert len(cache) == 0


def test_add_and_lookup_persist(cache):
    add(cache, 'one')
    assert 'one' in cache
    assert 'two' not in cache
    assert len(cache) == 1
    assert 'one' in Cache(cache.filepath)


def test_add_skips_known_id(cache):
    add(cache, 'one')
    add(cache, 'one', name='Other')
    assert len(lines(cache)) == 1


def test_record_format(cache):
    add(cache, 'one', filepath='Y:\\Music\\x.mp3', name='Ünï')
    raw = lines(cache)[0]
    assert 'Ünï' in raw  # stored as UTF-8, not \u escapes
    record = json.loads(raw)
    assert list(record) == [
        'id', 'name', 'album', 'year', 'media_url', 'image_url',
        'primary_artists', 'artists', 'download_date', 'filepath', 'filename',
    ]
    assert record['download_date'] == '2026-10-12T08:30:00'
    assert record['filename'] == 'x.mp3'
    assert record['primary_artists'] == ['A', 'B']


def test_posix_path_and_missing_path(cache):
    add(cache, 'one')
    add(cache, 'two', filepath=None, date=None)
    first, second = (json.loads(line) for line in lines(cache))
    assert first['filepath'] == '/srv/music/Song-Album(2024).mp3'
    assert first['filename'] == 'Song-Album(2024).mp3'
    assert second['filepath'] is None and second['filename'] is None
    assert second['download_date'] is None


def test_tolerates_duplicates_blanks_and_bad_lines(cache):
    good = json.dumps({'id': 'one'})
    cache.filepath.write_text(f'{good}\n\nnot json\n{good}\n{{"no_id": 1}}\n', encoding='utf-8')
    assert Cache(cache.filepath).ids == {'one'}


def test_append_after_partial_last_line(cache):
    cache.filepath.write_text('{"id": "one"}\n{"id": "trunc', encoding='utf-8')
    add(cache, 'two')
    assert lines(cache)[1] == '{"id": "trunc'
    assert json.loads(lines(cache)[2])['id'] == 'two'
    assert Cache(cache.filepath).ids == {'one', 'two'}


def test_writes_lf_only(cache):
    add(cache, 'one')
    assert b'\r' not in cache.filepath.read_bytes()


@pytest.mark.skipif(not REPO_DB.exists(), reason='no songs.jsonl in repo')
def test_repo_database_is_valid():
    ids = []
    for line in REPO_DB.read_text(encoding='utf-8').splitlines():
        ids.append(json.loads(line)['id'])
    assert len(ids) == len(set(ids))
    assert len(Cache(REPO_DB)) == len(ids)


@pytest.mark.skipif(not REPO_DB.exists(), reason='no songs.jsonl in repo')
def test_repo_database_round_trips_byte_for_byte():
    """Re-serializing every real record must reproduce the original line."""
    for lineno, line in enumerate(REPO_DB.read_text(encoding='utf-8').splitlines(), start=1):
        record = json.loads(line)
        song = SimpleNamespace(**{k: record[k] for k in (
            'id', 'name', 'album', 'year', 'media_url', 'image_url', 'primary_artists', 'artists')})
        date = dt.datetime.fromisoformat(record['download_date']) if record['download_date'] else None
        rebuilt = to_record(song, record['filepath'], date)
        assert json.dumps(rebuilt, ensure_ascii=False) == line, f'line {lineno}'
