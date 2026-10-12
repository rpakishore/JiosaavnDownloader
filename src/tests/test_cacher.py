import datetime as dt
import json
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

import pytest

from jiosaavn.utils import Cache

REPO_DB = Path(__file__).parent.parent.parent / 'songs.jsonl'


def make_song(song_id: str = 'abc123', **kwargs) -> SimpleNamespace:
    fields = dict(
        id=song_id, name='Song', album='Album', year=2024,
        media_url='https://example.com/a.mp4', image_url='',
        primary_artists=['A', 'B'], artists=[],
        download_date=dt.datetime(2026, 10, 12, 8, 30),
        filepath=PurePosixPath('/srv/music/Song-Album(2024).mp3'),
    )
    fields.update(kwargs)
    return SimpleNamespace(**fields)


@pytest.fixture
def cache(tmp_path) -> Cache:
    return Cache(tmp_path / 'db' / 'songs.jsonl')


def lines(cache: Cache) -> list[str]:
    return cache.filepath.read_text(encoding='utf-8').splitlines()


def test_creates_empty_file(cache):
    assert cache.filepath.is_file()
    assert cache.ids == set()


def test_add_and_lookup_persist(cache):
    cache.add(make_song('one'))
    assert cache.is_downloaded('one')
    assert not cache.is_downloaded('two')
    assert Cache(cache.filepath).is_downloaded('one')


def test_add_skips_known_id(cache):
    cache.add(make_song('one'))
    cache.add(make_song('one', name='Other'))
    assert len(lines(cache)) == 1


def test_record_format(cache):
    cache.add(make_song('one', filepath='Y:\\Music\\x.mp3', name='Ünï'))
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
    cache.add(make_song('one'))
    cache.add(make_song('two', filepath=None, download_date=None))
    first, second = (json.loads(line) for line in lines(cache))
    assert first['filepath'] == '/srv/music/Song-Album(2024).mp3'
    assert first['filename'] == 'Song-Album(2024).mp3'
    assert second['filepath'] is None and second['filename'] is None


def test_tolerates_duplicates_blanks_and_bad_lines(cache):
    good = json.dumps({'id': 'one'})
    cache.filepath.write_text(f'{good}\n\nnot json\n{good}\n{{"no_id": 1}}\n', encoding='utf-8')
    assert cache.ids == {'one'}


def test_append_after_partial_last_line(cache):
    cache.filepath.write_text('{"id": "one"}\n{"id": "trunc', encoding='utf-8')
    cache.add(make_song('two'))
    assert lines(cache)[1] == '{"id": "trunc'
    assert json.loads(lines(cache)[2])['id'] == 'two'
    assert Cache(cache.filepath).ids == {'one', 'two'}


def test_writes_lf_only(cache):
    cache.add(make_song('one'))
    assert b'\r' not in cache.filepath.read_bytes()


@pytest.mark.skipif(not REPO_DB.exists(), reason='no songs.jsonl in repo')
def test_repo_database_is_valid():
    ids = []
    for line in REPO_DB.read_text(encoding='utf-8').splitlines():
        ids.append(json.loads(line)['id'])
    assert len(ids) == len(set(ids))
