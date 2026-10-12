"""Append-only JSON Lines record of downloaded songs, one song per line.

Built to live in git: adding a song appends one line, and duplicate ids
(e.g. from a `merge=union` merge) are ignored on load.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jiosaavn.song import Song

log = logging.getLogger(__name__)


class Cache:
    def __init__(self, filepath: Path) -> None:
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.filepath.touch()
        self.ids: set[str] = self._load_ids()
        log.debug("Loaded %d ids from %s", len(self.ids), self.filepath)

    def __contains__(self, song_id: object) -> bool:
        return song_id in self.ids

    def __len__(self) -> int:
        return len(self.ids)

    def _load_ids(self) -> set[str]:
        """Ids of all readable records, skipping blank, bad and id-less lines."""
        ids: set[str] = set()
        with open(self.filepath, encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    log.warning("Skipping unreadable line %d in %s", lineno, self.filepath)
                    continue
                if isinstance(record, dict) and record.get("id"):
                    ids.add(str(record["id"]))
        return ids

    def add(self, song: Song, filepath: Path | None, downloaded_at: datetime | None) -> None:
        """Append `song` to the file, unless its id is already recorded."""
        record = to_record(song, filepath, downloaded_at)
        if record["id"] in self.ids:
            log.debug("%s already in cache, not adding", record["id"])
            return
        line = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
        with open(self.filepath, "ab+") as f:
            # Don't glue onto a partial last line left by an interrupted write.
            if f.seek(0, 2) > 0:
                f.seek(-1, 2)
                if f.read(1) != b"\n":
                    line = b"\n" + line
            f.write(line)
        self.ids.add(record["id"])


def to_record(song: Song, filepath: Path | None, downloaded_at: datetime | None) -> dict[str, Any]:
    path = None if filepath is None else str(filepath)
    # Key order is the field order on disk; keep it stable so git diffs stay readable.
    return {
        "id": str(song.id),
        "name": song.name,
        "album": song.album,
        "year": song.year,
        "media_url": song.media_url,
        "image_url": song.image_url,
        "primary_artists": list(song.primary_artists),
        "artists": list(song.artists),
        "download_date": None if downloaded_at is None else downloaded_at.isoformat(),
        "filepath": path,
        # PureWindowsPath splits on both "\" and "/", so this works for old and new paths.
        "filename": PureWindowsPath(path).name if path else None,
    }
