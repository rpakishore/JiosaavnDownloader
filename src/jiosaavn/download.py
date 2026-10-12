"""Download a song with a single ffmpeg pass: encode to mp3, write ID3 tags, embed cover art."""

import logging
import os
import subprocess
import time
from pathlib import Path

from jiosaavn.song import Song

log = logging.getLogger(__name__)

TIMEOUT = 900  # seconds
STDERR_LINES = 20


def build_command(song: Song, out_path: Path, bitrate: str) -> list[str]:
    """Return the ffmpeg argv. Metadata values are separate list items, so no quoting is needed."""
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", song.media_url]
    if song.image_url:
        cmd += ["-i", song.image_url]
    cmd += ["-map", "0:a"]
    if song.image_url:
        cmd += [
            "-map", "1:v", "-c:v", "copy", "-disposition:v", "attached_pic",
            "-metadata:s:v", "title=Album cover", "-metadata:s:v", "comment=Cover (front)",
        ]  # fmt: skip
    cmd += [
        "-c:a", "libmp3lame", "-b:a", bitrate, "-id3v2_version", "3",
        "-metadata", f"title={song.name}",
        "-metadata", f"artist={', '.join(song.primary_artists)}",
        "-metadata", f"album={song.album}",
        "-metadata", f"album_artist={', '.join(song.artists)}",
    ]  # fmt: skip
    if song.year:
        cmd += ["-metadata", f"date={song.year}"]
    return [*cmd, "-f", "mp3", str(out_path)]


def _tail(stderr: str | bytes | None) -> str:
    if isinstance(stderr, bytes):
        stderr = stderr.decode(errors="replace")
    return "\n".join((stderr or "").strip().splitlines()[-STDERR_LINES:])


def download(song: Song, dest_dir: Path, bitrate: str = "320k") -> Path:
    """Download `song` into `dest_dir` and return the final path.

    ffmpeg writes a hidden `.part` file which is atomically renamed on success
    and removed on any failure.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    final = dest_dir / song.filename
    part = dest_dir / f".{song.filename}.part"
    start = time.monotonic()
    try:
        try:
            subprocess.run(
                build_command(song, part, bitrate),
                check=True, capture_output=True, text=True, timeout=TIMEOUT,
            )  # fmt: skip
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg failed for {song.name!r} (exit {e.returncode}):\n{_tail(e.stderr)}") from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"ffmpeg timed out after {TIMEOUT}s for {song.name!r}:\n{_tail(e.stderr)}") from e
        os.replace(part, final)
    finally:
        part.unlink(missing_ok=True)
    log.info("Downloaded %s (%.2f MB) in %.1fs", final.name, final.stat().st_size / 2**20, time.monotonic() - start)
    return final
