import datetime as dt
import json
from pathlib import Path, PureWindowsPath
from typing import Any

from jiosaavn.utils import log


class Cache:
    """Append-only JSON Lines record of downloaded songs, one song per line.

    Built to live in git: adding a song appends one line, and duplicate ids
    (e.g. from a `merge=union` merge) are ignored on load.
    """

    def __init__(self, filepath: str | Path) -> None:
        self.filepath = Path(str(filepath))
        self._ids: set[str] | None = None
        self.initialize()
        log.info(f'Initialized Cache Object at {self.filepath}')

    def __str__(self) -> str:
        return f"Cache file for Jiosaavn downloaded from {self.filepath.name} ({len(self.ids)} songs)"

    def __repr__(self) -> str:
        return f"Cache({self.filepath})"

    @property
    def ids(self) -> set[str]:
        if self._ids is None:
            self._ids = {record["id"] for record in self.records()}
        return self._ids

    def records(self) -> list[dict[str, Any]]:
        """All records in file order, skipping blank or unreadable lines."""
        records = []
        with open(self.filepath, encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    log.warning(f'Skipping unreadable line {lineno} in {self.filepath}')
                    continue
                if isinstance(record, dict) and record.get("id"):
                    records.append(record)
        return records

    def is_downloaded(self, song_id: str) -> bool:
        return str(song_id) in self.ids

    def add(self, song: Any) -> None:
        """Append `song` to the cache file, unless its id is already recorded."""
        record = to_record(song)
        if record["id"] in self.ids:
            log.debug(f'{record["id"]} already in cache, not adding')
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
        log.debug('Cache Updated')

    def initialize(self) -> None:
        """Creates the database file if not exist"""
        if not self.filepath.is_file():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self.filepath.touch()
            log.info('Cache file created')


def to_record(song: Any) -> dict[str, Any]:
    filepath = None if song.filepath is None else str(song.filepath)
    download_date = song.download_date
    if isinstance(download_date, (dt.datetime, dt.date)):
        download_date = download_date.isoformat()
    # Key order is the field order on disk; keep it stable so git diffs stay readable.
    return {
        "id": str(song.id),
        "name": song.name,
        "album": song.album,
        "year": song.year,
        "media_url": song.media_url,
        "image_url": song.image_url,
        "primary_artists": list(song.primary_artists or []),
        "artists": list(song.artists or []),
        "download_date": download_date,
        "filepath": filepath,
        # PureWindowsPath splits on both "\" and "/", so this works for old and new paths.
        "filename": PureWindowsPath(filepath).name if filepath else None,
    }
