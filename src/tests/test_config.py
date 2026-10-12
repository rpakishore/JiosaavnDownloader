from pathlib import Path

import pytest

from jiosaavn.config import load_config

EXAMPLE = Path(__file__).parent.parent.parent / 'config.example.toml'


@pytest.fixture(autouse=True)
def no_gotify_env(monkeypatch):
    monkeypatch.delenv('GOTIFY_URL', raising=False)
    monkeypatch.delenv('GOTIFY_TOKEN', raising=False)


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / 'config.toml'
    path.write_text(text, encoding='utf-8')
    return path


def test_example_config_parses():
    assert EXAMPLE.is_file()
    config = load_config(EXAMPLE)
    assert config.db_path == EXAMPLE.parent / 'songs.jsonl'
    assert config.gotify_url == 'https://gotify.example.com'
    assert config.playlists == ()


def test_missing_file_gives_defaults(tmp_path):
    config = load_config(tmp_path / 'nope.toml')
    assert config.db_path == tmp_path / 'songs.jsonl'
    assert config.destination is None
    assert config.playlists == ()
    assert config.gotify_url == '' and config.gotify_token == ''


def test_empty_destination_is_none(tmp_path):
    assert load_config(write(tmp_path, '[paths]\ndestination = ""\n')).destination is None


def test_relative_paths_resolve_against_config_dir(tmp_path):
    path = write(tmp_path, '[paths]\ndb_folder = "db"\ndestination = "music"\n')
    config = load_config(path)
    assert config.db_path == tmp_path / 'db' / 'songs.jsonl'
    assert config.destination == tmp_path / 'music'


def test_absolute_and_home_paths(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    path = write(tmp_path, f'[paths]\ndb_folder = "{tmp_path / "abs"}"\ndestination = "~/music"\n')
    config = load_config(path)
    assert config.db_path == tmp_path / 'abs' / 'songs.jsonl'
    assert config.destination == tmp_path / 'home' / 'music'


def test_playlists_are_stringified(tmp_path):
    config = load_config(write(tmp_path, '[schedule]\nplaylists = [109815423, "abc"]\n'))
    assert config.playlists == ('109815423', 'abc')


def test_gotify_from_toml(tmp_path):
    config = load_config(write(tmp_path, '[gotify]\nurl = "https://g.example"\napp_key = "k"\napp_name = "x"\n'))
    assert (config.gotify_url, config.gotify_token) == ('https://g.example', 'k')


def test_gotify_env_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv('GOTIFY_URL', 'https://env.example')
    monkeypatch.setenv('GOTIFY_TOKEN', 'envtoken')
    config = load_config(write(tmp_path, '[gotify]\nurl = ""\napp_key = ""\n'))
    assert (config.gotify_url, config.gotify_token) == ('https://env.example', 'envtoken')


def test_toml_wins_over_env(tmp_path, monkeypatch):
    monkeypatch.setenv('GOTIFY_TOKEN', 'envtoken')
    assert load_config(write(tmp_path, '[gotify]\napp_key = "k"\n')).gotify_token == 'k'
