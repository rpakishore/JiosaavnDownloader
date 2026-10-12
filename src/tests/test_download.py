import json
import shutil
import subprocess
from pathlib import Path

import pytest

from jiosaavn.download import build_command, download
from jiosaavn.song import Song


def make_song(**kw) -> Song:
    fields = dict(
        id="1", name="Ünï", album="Alb", year=2020, media_url="in.m4a", image_url="cover.jpg",
        primary_artists=("A", "B"), artists=("A", "B", "C"),
    )  # fmt: skip
    return Song(**{**fields, **kw})


def meta_pairs(cmd: list[str]) -> list[str]:
    return [cmd[i + 1] for i, a in enumerate(cmd) if a == "-metadata"]


# --- build_command: pure, no ffmpeg needed ---------------------------------------------------


def test_build_command_with_image():
    cmd = build_command(make_song(), Path("/d/.x.part"), "320k")
    assert cmd[0] == "ffmpeg"
    assert cmd[-3:] == ["-f", "mp3", "/d/.x.part"]
    assert [cmd[i + 1] for i, a in enumerate(cmd) if a == "-i"] == ["in.m4a", "cover.jpg"]
    assert ["-map", "0:a", "-map", "1:v", "-c:v", "copy"] == cmd[cmd.index("-map") : cmd.index("-map") + 6]
    assert "attached_pic" in cmd
    assert cmd[cmd.index("-b:a") + 1] == "320k"
    assert cmd[cmd.index("-id3v2_version") + 1] == "3"
    assert cmd[cmd.index("-map_metadata") + 1] == "-1"
    assert meta_pairs(cmd) == ["title=Ünï", "artist=A, B", "album=Alb", "album_artist=A, B, C", "date=2020"]


def test_build_command_without_image():
    cmd = build_command(make_song(image_url=""), Path("o.part"), "128k")
    assert cmd.count("-i") == 1
    assert "-map" in cmd and "1:v" not in cmd
    assert "attached_pic" not in cmd and "-c:v" not in cmd
    assert cmd[cmd.index("-b:a") + 1] == "128k"


def test_build_command_omits_date_when_year_unknown():
    assert not any(m.startswith("date=") for m in meta_pairs(build_command(make_song(year=0), Path("o"), "320k")))


def test_build_command_keeps_special_characters_unquoted():
    name = 'a "quoted" $x; name'
    assert f"title={name}" in build_command(make_song(name=name), Path("o"), "320k")


# --- integration: real ffmpeg ----------------------------------------------------------------

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def run(*args: str) -> None:
    subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )  # fmt: skip
    return json.loads(out.stdout)


@pytest.fixture
def media(tmp_path: Path) -> tuple[Path, Path]:
    audio, image = tmp_path / "in.m4a", tmp_path / "cover.jpg"
    run("-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:a", "aac", "-b:a", "320k", str(audio))
    run("-f", "lavfi", "-i", "color=c=red:s=64x64", "-frames:v", "1", str(image))
    return audio, image


@needs_ffmpeg
def test_download_with_cover(media, tmp_path):
    audio, image = media
    dest = tmp_path / "out" / "nested"
    song = make_song(media_url=str(audio), image_url=str(image))

    path = download(song, dest)

    assert path == dest / song.filename
    info = probe(path)
    assert info["format"]["format_name"] == "mp3"
    tags = {k.lower(): v for k, v in info["format"]["tags"].items()}
    assert tags["title"] == "Ünï"
    assert tags["artist"] == "A, B"
    assert tags["album"] == "Alb"
    assert tags["album_artist"] == "A, B, C"
    assert tags["date"] == "2020"
    assert "major_brand" not in tags  # source container tags are not copied over
    audio_stream, video_stream = info["streams"]
    assert audio_stream["codec_name"] == "mp3"
    assert int(audio_stream["bit_rate"]) == pytest.approx(320_000, rel=0.05)
    assert video_stream["disposition"]["attached_pic"] == 1
    assert list(dest.glob(".*")) == [] and list(dest.iterdir()) == [path]


@needs_ffmpeg
def test_download_without_image(media, tmp_path):
    audio, _ = media
    song = make_song(media_url=str(audio), image_url="", year=0)
    path = download(song, tmp_path / "out")

    info = probe(path)
    assert [s["codec_type"] for s in info["streams"]] == ["audio"]
    assert "date" not in {k.lower() for k in info["format"]["tags"]}
    assert path.name == song.filename


@needs_ffmpeg
def test_download_failure_leaves_nothing_behind(tmp_path):
    dest = tmp_path / "out"
    song = make_song(media_url=str(tmp_path / "missing.m4a"), image_url="")

    with pytest.raises(RuntimeError, match="missing.m4a"):
        download(song, dest)

    assert list(dest.iterdir()) == []


@needs_ffmpeg
def test_download_failure_keeps_existing_final_file(tmp_path):
    song = make_song(media_url=str(tmp_path / "missing.m4a"), image_url="")
    final = tmp_path / song.filename
    final.write_bytes(b"old")

    with pytest.raises(RuntimeError):
        download(song, tmp_path)

    assert final.read_bytes() == b"old"
    assert not list(tmp_path.glob(".*"))


def test_download_timeout_cleans_up_part(tmp_path, monkeypatch):
    def fake_run(cmd, **kw):
        Path(cmd[-1]).write_bytes(b"partial")
        raise subprocess.TimeoutExpired(cmd, 1, stderr="slow")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="timed out"):
        download(make_song(), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_download_keyboard_interrupt_cleans_up_part(tmp_path, monkeypatch):
    def fake_run(cmd, **kw):
        Path(cmd[-1]).write_bytes(b"partial")
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(KeyboardInterrupt):
        download(make_song(), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_download_error_contains_only_stderr_tail(tmp_path, monkeypatch):
    stderr = "\n".join(f"line{i}" for i in range(100))

    def fake_run(cmd, **kw):
        raise subprocess.CalledProcessError(1, cmd, stderr=stderr)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(RuntimeError) as exc:
        download(make_song(), tmp_path)
    assert "line99" in str(exc.value) and "line80" in str(exc.value) and "line79" not in str(exc.value)
