"""Song model and filename helpers."""

import html
import re
import unicodedata
from dataclasses import dataclass

_BLACKLIST = set('\\/:*?"<>|\0')
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}  # fmt: skip
_FROM_RE = re.compile(r'^(.*) \(From "(.*)"\)$')
_MAX_LEN = 255


@dataclass(frozen=True, slots=True)
class Song:
    id: str
    name: str  # cleaned: html-unescaped, ' (From "X")' suffix removed
    album: str  # cleaned: html-unescaped, 'Foo (From "X")' -> 'X'
    year: int  # 0 when unknown
    media_url: str
    image_url: str  # "" when none
    primary_artists: tuple[str, ...]
    artists: tuple[str, ...]

    @property
    def filename(self) -> str:
        return sanitize(f"{self.name}-{self.album}({self.year or ''}).mp3")


def sanitize(filename: str) -> str:
    """Return a filename that is safe on Linux and Windows/SMB shares.

    Keeps non-ASCII letters (blacklist, not whitelist), drops reserved
    characters and control characters, and caps the length at 255 while
    preserving a short extension.
    """
    filename = unicodedata.normalize("NFKD", filename)
    filename = "".join(c for c in filename if c not in _BLACKLIST and ord(c) >= 32)
    filename = filename.strip().rstrip(". ")  # Windows rejects trailing dots/spaces
    if filename in _RESERVED:
        filename = "__" + filename
    if len(filename) > _MAX_LEN:
        stem, dot, ext = filename.rpartition(".")
        if not dot or len(ext) > 10:
            stem, ext = filename, ""
        else:
            ext = "." + ext
        filename = (stem[: _MAX_LEN - len(ext)] + ext).rstrip(". ")
    return filename or "__"


def clean_title(name: str) -> tuple[str, str | None]:
    """Unescape `name`; split 'Title (From "Movie")' into ('Title', 'Movie')."""
    name = html.unescape(name).strip()
    if match := _FROM_RE.match(name):
        return match.group(1), match.group(2)
    return name, None
