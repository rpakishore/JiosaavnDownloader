# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Convert the legacy Jiosaavn `database.pkl` into a SQLite database.

Usage:
    uv run migrate.py path/to/database.pkl
    uv run migrate.py path/to/database.pkl -o path/to/database.sqlite
    uv run migrate.py path/to/database.pkl --dry-run

The pickle is only ever opened read-only and is never modified or deleted.

Safety notes:
  * Unpickling uses a restricted Unpickler. `Song` objects are rebuilt as
    plain attribute holders (the real `jiosaavn` package is NOT imported), and
    any class outside a small allowlist aborts the run instead of executing.
  * pathlib classes are mapped to their Pure* variants, so the file also loads
    on Linux/macOS (a real `WindowsPath` cannot be instantiated there).
  * The database is built in `<output>.tmp`, verified, then atomically moved
    into place. An existing output file is never touched without --force.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pickle
import sqlite3
import sys
from contextlib import closing
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE songs (
    id              TEXT PRIMARY KEY,
    name            TEXT,
    album           TEXT,
    year            INTEGER,
    media_url       TEXT,
    image_url       TEXT,
    primary_artists TEXT NOT NULL DEFAULT '[]',  -- JSON array
    artists         TEXT NOT NULL DEFAULT '[]',  -- JSON array
    download_date   TEXT,                        -- ISO 8601, naive local time
    filepath        TEXT,                        -- original path string, as stored
    filename        TEXT                         -- last path component, OS independent
);
CREATE INDEX idx_songs_download_date ON songs(download_date);
"""

INSERT = """
INSERT OR IGNORE INTO songs
    (id, name, album, year, media_url, image_url,
     primary_artists, artists, download_date, filepath, filename)
VALUES
    (:id, :name, :album, :year, :media_url, :image_url,
     :primary_artists, :artists, :download_date, :filepath, :filename)
"""


class _SongStub:
    """Stand-in for `jiosaavn.file_parser.Song`; just receives `__dict__`."""


_ALLOWED = {
    ("datetime", "datetime"),
    ("datetime", "date"),
    ("datetime", "time"),
    ("datetime", "timedelta"),
    ("datetime", "timezone"),
    ("builtins", "set"),
    ("builtins", "frozenset"),
    ("builtins", "bytearray"),
    ("builtins", "object"),
    ("collections", "OrderedDict"),
    ("copyreg", "_reconstructor"),
}

_seen_song_modules: set[str] = set()


class _RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str) -> Any:
        if module.split(".")[0] == "pathlib":
            return PurePosixPath if "Posix" in name else PureWindowsPath
        if name == "Song":
            _seen_song_modules.add(f"{module}.{name}")
            return _SongStub
        if (module, name) in _ALLOWED:
            return super().find_class(module, name)
        raise pickle.UnpicklingError(
            f"Refusing to load unexpected class {module}.{name}"
        )


def load_pickle(path: Path) -> list[Any]:
    with open(path, "rb") as f:
        data = _RestrictedUnpickler(f).load()
    if not isinstance(data, (list, tuple)):
        raise SystemExit(f"Expected a list in the pickle, got {type(data).__name__}")
    return list(data)


def _attrs(obj: Any) -> dict[str, Any] | None:
    if isinstance(obj, dict):
        return obj
    return getattr(obj, "__dict__", None)


def _text(value: Any) -> str | None:
    return None if value is None else str(value)


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _json_list(value: Any) -> str:
    if value is None:
        items: list[Any] = []
    elif isinstance(value, (list, tuple, set, frozenset)):
        items = [str(v) for v in value]
    else:
        items = [str(value)]
    return json.dumps(items, ensure_ascii=False)


def _date(value: Any) -> str | None:
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    return _text(value)


def to_row(obj: Any) -> dict[str, Any] | None:
    """Convert one unpickled entry to a DB row, or None if it has no usable id."""
    attrs = _attrs(obj)
    if attrs is None:
        return None
    song_id = attrs.get("id")
    if song_id is None or str(song_id).strip() == "":
        return None

    filepath = attrs.get("filepath")
    filepath_str = None if filepath is None else str(filepath)
    # PureWindowsPath understands both "\\" and "/" separators.
    filename = PureWindowsPath(filepath_str).name if filepath_str else None

    return {
        "id": str(song_id),
        "name": _text(attrs.get("name")),
        "album": _text(attrs.get("album")),
        "year": _int(attrs.get("year")),
        "media_url": _text(attrs.get("media_url")),
        "image_url": _text(attrs.get("image_url")),
        "primary_artists": _json_list(attrs.get("primary_artists")),
        "artists": _json_list(attrs.get("artists")),
        "download_date": _date(attrs.get("download_date")),
        "filepath": filepath_str,
        "filename": filename,
    }


def build_database(rows: list[dict[str, Any]], tmp_path: Path) -> int:
    """Write rows to `tmp_path`, verify, return the number of rows stored."""
    with closing(sqlite3.connect(tmp_path)) as conn:
        conn.executescript(SCHEMA)
        conn.executemany(INSERT, rows)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()

        stored = conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
        check = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if check != "ok":
            raise SystemExit(f"SQLite integrity_check failed: {check}")
    return stored


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("pickle", type=Path, help="path to the legacy database.pkl")
    parser.add_argument(
        "-o", "--output", type=Path,
        help="output SQLite file (default: database.sqlite next to the pickle)",
    )
    parser.add_argument("--force", action="store_true", help="overwrite an existing output file")
    parser.add_argument("--dry-run", action="store_true", help="parse and report, write nothing")
    args = parser.parse_args()

    src: Path = args.pickle
    if not src.is_file():
        print(f"error: {src} not found", file=sys.stderr)
        return 2
    out: Path = args.output or src.with_name("database.sqlite")
    if out.resolve() == src.resolve():
        print("error: output must differ from the input pickle", file=sys.stderr)
        return 2
    if out.exists() and not args.force and not args.dry_run:
        print(f"error: {out} already exists (use --force to replace it)", file=sys.stderr)
        return 2

    try:
        entries = load_pickle(src)
    except pickle.UnpicklingError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    no_id = 0
    dupes: list[str] = []
    for entry in entries:
        row = to_row(entry)
        if row is None:
            no_id += 1
        elif row["id"] in seen:
            dupes.append(row["id"])
        else:
            seen.add(row["id"])
            rows.append(row)

    print(f"Read {len(entries)} entries from {src}")
    if _seen_song_modules:
        print(f"  Song class referenced as: {', '.join(sorted(_seen_song_modules))}")
    print(f"  usable songs        : {len(rows)}")
    print(f"  skipped (no id)     : {no_id}")
    print(f"  skipped (duplicate) : {len(dupes)} (first occurrence kept)")
    if dupes:
        print(f"    e.g. {', '.join(dupes[:5])}")
    print(f"  missing download_date: {sum(r['download_date'] is None for r in rows)}")
    print(f"  missing filepath     : {sum(r['filepath'] is None for r in rows)}")

    if args.dry_run:
        print("Dry run: nothing written.")
        return 0

    tmp = out.with_name(out.name + ".tmp")
    tmp.unlink(missing_ok=True)
    try:
        stored = build_database(rows, tmp)
        if stored != len(rows):
            print(f"error: verification failed, stored {stored} rows, expected {len(rows)}", file=sys.stderr)
            return 1
        os.replace(tmp, out)
    finally:
        tmp.unlink(missing_ok=True)

    print(f"Wrote {stored} songs to {out} (schema version {SCHEMA_VERSION}).")
    print(f"Original pickle left untouched: {src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
