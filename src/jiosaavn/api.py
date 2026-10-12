"""Client for the unofficial saavn.sumit.co API."""

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from jiosaavn.song import Song, clean_title

log = logging.getLogger(__name__)

_TIMEOUT = 30
_MALFORMED = (LookupError, ValueError, TypeError, AttributeError)


def parse_song(d: dict) -> Song:
    """Build a Song from one API song dict. Raises on malformed input."""
    name = clean_title(d["name"])[0]
    base, from_ = clean_title(d["album"]["name"])
    best_audio = max(d["downloadUrl"], key=lambda x: int(x["quality"].removesuffix("kbps")))
    images = d.get("image") or []
    best_image = max(images, key=lambda x: int(x["quality"].split("x")[0]), default=None)
    artists = d.get("artists") or {}
    return Song(
        id=d["id"],
        name=name,
        album=from_ or base,
        year=_parse_year(d.get("year")),
        media_url=best_audio["url"],
        image_url=best_image["url"] if best_image else "",
        primary_artists=tuple(a["name"] for a in artists.get("primary") or []),
        artists=tuple(a["name"] for a in artists.get("all") or []),
    )


def _parse_year(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _parse_songs(items: list[dict]) -> list[Song]:
    songs = []
    for item in items:
        try:
            songs.append(parse_song(item))
        except _MALFORMED as e:
            log.warning("Skipping malformed song %r: %r", item.get("id") if isinstance(item, dict) else item, e)
    if items and not songs:
        raise RuntimeError(f"all {len(items)} songs in the response are malformed; has the API changed?")
    return songs


def _default_session() -> requests.Session:
    # Ignore Retry-After: a long one would stall the cron job; the backoff is enough.
    retry = Retry(
        total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504), respect_retry_after_header=False
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


class SaavnClient:
    BASE_URL = "https://saavn.sumit.co/api"

    def __init__(self, session: requests.Session | None = None, min_interval: float = 1.5) -> None:
        self.session = session or _default_session()
        self.min_interval = min_interval
        self._last_call: float | None = None

    def playlist(self, id_or_link: str) -> list[Song]:
        if id_or_link.startswith(("http", "www")):
            link = id_or_link if id_or_link.startswith("http") else f"https://{id_or_link}"
            params = {"link": link, "limit": 1000}
        else:
            params = {"id": id_or_link, "limit": 1000}
        data = self._get("/playlists", **params)
        log.debug("Playlist %s: %s songs", data.get("name"), data.get("songCount"))
        return _parse_songs(data["songs"])

    def song(self, url: str) -> Song:
        data = self._get("/songs", link=url)
        if not data:
            raise RuntimeError(f"No song found for {url}")
        return parse_song(data[0])

    def search(self, query: str, limit: int = 10) -> list[Song]:
        data = self._get("/search/songs", query=query, limit=limit)
        return _parse_songs(data["results"])

    def _get(self, path: str, **params: object) -> dict | list:
        """GET `path` (throttled) and return the response's `data` payload."""
        if self._last_call is not None:
            wait = self.min_interval - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
        self._last_call = time.monotonic()
        res = self.session.get(self.BASE_URL + path, params=params, timeout=_TIMEOUT)
        res.raise_for_status()
        body = res.json()
        if not body.get("success"):
            raise RuntimeError(f"API call to {path} failed: {body.get('message') or body}")
        return body["data"]
