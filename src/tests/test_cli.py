import json
import logging

import pytest

from jiosaavn import cli
from jiosaavn.song import Song


def make_song(song_id: str, name: str = "Houdini") -> Song:
    return Song(
        id=song_id, name=name, album="Album", year=2024, media_url="http://m", image_url="http://i",
        primary_artists=("A",), artists=("A", "B"),
    )


class FakeClient:
    """Stands in for SaavnClient. `playlists` maps id -> songs, or an Exception to raise."""

    playlists: dict = {}
    songs: list[Song] = []

    def playlist(self, id_or_link):
        result = self.playlists[id_or_link]
        if isinstance(result, Exception):
            raise result
        return result

    def song(self, url):
        return self.songs[0]

    def search(self, query, limit=10):
        return self.songs[:limit]


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Patch network, ffmpeg and gotify; record calls. Config lives in tmp_path."""
    FakeClient.playlists, FakeClient.songs = {}, []
    downloads, notifications = [], []
    failing: set[str] = set()

    def fake_download(song, dest_dir):
        if song.id in failing:
            raise RuntimeError("ffmpeg exploded")
        downloads.append((song.id, dest_dir))
        return dest_dir / song.filename

    monkeypatch.setattr(cli, "SaavnClient", FakeClient)
    monkeypatch.setattr(cli, "download", fake_download)
    monkeypatch.setattr(cli, "gotify", lambda *args: notifications.append(args))
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/ffmpeg")

    config = tmp_path / "config.toml"
    config.write_text(
        f'[paths]\ndb_folder = "{tmp_path}"\ndestination = "{tmp_path / "music"}"\n'
        '[gotify]\nurl = "http://gotify"\napp_key = "tok"\n'
        '[schedule]\nplaylists = ["p1", "p2"]\n'
    )

    class Env:
        pass

    e = Env()
    e.config, e.db, e.music = config, tmp_path / "songs.jsonl", tmp_path / "music"
    e.downloads, e.notifications, e.failing = downloads, notifications, failing
    e.ids = lambda: [json.loads(line)["id"] for line in e.db.read_text().splitlines() if line.strip()]
    e.run = lambda *argv: cli.main(["--config", str(config), *argv])
    return e


def test_downloads_and_caches_song(env):
    FakeClient.songs = [make_song("a")]
    assert env.run("song", "http://url") == 0
    assert env.downloads == [("a", env.music)]
    assert env.ids() == ["a"]


def test_skips_cached_ids(env):
    FakeClient.playlists = {"p": [make_song("a"), make_song("b")]}
    assert env.run("playlist", "p") == 0
    env.downloads.clear()
    FakeClient.playlists = {"p": [make_song("a"), make_song("b"), make_song("c")]}
    assert env.run("playlist", "p") == 0
    assert [d[0] for d in env.downloads] == ["c"]
    assert env.ids() == ["a", "b", "c"]


def test_dry_run_downloads_nothing_and_caches_nothing(env, caplog):
    FakeClient.playlists = {"p": [make_song("a")]}
    with caplog.at_level(logging.INFO):
        assert env.run("--dry-run", "playlist", "p") == 0
    assert env.downloads == []
    assert env.notifications == []
    assert env.db.read_text() == ""
    assert "dry-run" in caplog.text


def test_dry_run_does_not_need_ffmpeg(env, monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    FakeClient.songs = [make_song("a")]
    assert env.run("--dry-run", "song", "u") == 0


def test_failing_song_does_not_stop_next_and_exit_code_is_1(env):
    FakeClient.playlists = {"p": [make_song("bad"), make_song("good")]}
    env.failing.add("bad")
    assert env.run("playlist", "p") == 1
    assert [d[0] for d in env.downloads] == ["good"]
    assert env.ids() == ["good"]  # the failed song is not cached, so it is retried next run


def test_sync_continues_past_failing_playlist(env):
    FakeClient.playlists = {"p1": RuntimeError("api down"), "p2": [make_song("a")]}
    assert env.run("sync") == 1
    assert env.ids() == ["a"]


def test_sync_downloads_every_configured_playlist(env):
    FakeClient.playlists = {"p1": [make_song("a")], "p2": [make_song("b")]}
    assert env.run("sync") == 0
    assert env.ids() == ["a", "b"]


def test_sync_without_playlists_exits_2(env):
    env.config.write_text(f'[paths]\ndestination = "{env.music}"\n')
    assert env.run("sync") == 2


def test_missing_destination_exits_2(env, caplog):
    env.config.write_text("")
    assert env.run("song", "u") == 2
    assert "--dest" in caplog.text
    assert env.downloads == []


def test_dest_option_overrides_config(env, tmp_path):
    FakeClient.songs = [make_song("a")]
    assert env.run("--dest", str(tmp_path / "other"), "song", "u") == 0
    assert env.downloads == [("a", tmp_path / "other")]


def test_missing_ffmpeg_exits_2(env, monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    FakeClient.songs = [make_song("a")]
    assert env.run("song", "u") == 2
    assert env.downloads == []


def test_gotify_called_with_title_and_message(env):
    FakeClient.songs = [make_song("a", name="Houdini")]
    env.run("song", "u")
    assert env.notifications == [
        ("http://gotify", "tok", "[Jiosaavn]Houdini", "Album: Album\n\n ![](http://i)")
    ]


def test_search_respects_limit(env):
    FakeClient.songs = [make_song(str(i)) for i in range(5)]
    assert env.run("search", "query", "--limit", "2") == 0
    assert env.ids() == ["0", "1"]


def test_global_options_before_subcommand(env, tmp_path):
    FakeClient.songs = [make_song("a")]
    dest = tmp_path / "x"
    assert cli.main(["--config", str(env.config), "--dest", str(dest), "-v", "--dry-run", "song", "u"]) == 0


def test_global_options_after_subcommand_are_rejected(env):
    with pytest.raises(SystemExit) as exc:
        env.run("song", "u", "--dry-run")
    assert exc.value.code == 2


def test_keyboard_interrupt_exits_130(env, monkeypatch):
    def interrupt(self, url):
        raise KeyboardInterrupt

    monkeypatch.setattr(FakeClient, "song", interrupt)
    assert env.run("song", "u") == 130
