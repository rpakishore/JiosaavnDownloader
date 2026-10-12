"""Settings from config.toml, with env fallbacks for the Gotify secrets."""

import logging
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Config:
    db_path: Path
    destination: Path | None
    playlists: tuple[str, ...]
    gotify_url: str
    gotify_token: str


def load_config(path: Path = Path("config.toml")) -> Config:
    """Read `path` (missing file -> defaults). Relative paths resolve against its folder."""
    path = Path(path)
    data = {}
    if path.is_file():
        with open(path, "rb") as f:
            data = tomllib.load(f)
    else:
        log.info("No config file at %s, using defaults", path)

    def resolve(value: str) -> Path:
        return path.parent / Path(value).expanduser()  # absolute paths replace the parent

    paths = data.get("paths", {})
    gotify = data.get("gotify", {})
    destination = paths.get("destination") or None
    return Config(
        db_path=resolve(paths.get("db_folder") or ".") / "songs.jsonl",
        destination=destination and resolve(destination),
        playlists=tuple(str(p) for p in data.get("schedule", {}).get("playlists", [])),
        gotify_url=gotify.get("url") or os.environ.get("GOTIFY_URL", ""),
        gotify_token=gotify.get("app_key") or os.environ.get("GOTIFY_TOKEN", ""),
    )
