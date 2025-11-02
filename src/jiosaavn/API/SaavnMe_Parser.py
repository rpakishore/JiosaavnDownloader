import html
import json
import re
from typing import Literal

from ak_requests import RequestsSession

from jiosaavn.file_parser import Song
from jiosaavn.utils import log


class SaavnMe:
    BASEURL: str = "https://saavn.sumit.co/"
    SESSION = RequestsSession()
    log.info("SaavnMe Instance Initialized")

    def __init__(self) -> None:
        self.SESSION.MIN_REQUEST_GAP = 1.5  # To prevent Ratelimit in free API

    def __str__(self) -> str:
        return "Instance of SaavnMe class for saavn.me parser"

    def __repr__(self) -> str:
        return "SaavnMe()"

    def url(self, type: Literal["playlist", "song"]) -> str:
        match type:
            case "playlist":
                return f"{self.BASEURL}api/playlists"
            case "song":
                return f"{self.BASEURL}api/songs"
            case "search_song":
                return f"{self.BASEURL}api/search/songs"

    def search_song(self, query: str) -> list[Song]:
        """Returns a list of Song dataclass from the search query"""
        req_url: str = f"{self.url(type='search_song')}?query={query}&limit=1000"
        _res = self.SESSION.get(req_url)
        data: dict = json.loads(_res.content.decode())["data"]
        return _parse_playlist_results(data["results"])

    def playlist(
        self, id: int | str | None = None, link: str | None = None
    ) -> list[Song]:
        """Provides a list of Song dataclass from the playlist id"""
        if id is None and link is None:
            raise Exception("Playlist ID or Link is required")
        if id is not None and link is not None:
            raise Exception("Provide only one of playlist or link")
        if id is not None:
            log.info(f"Extracting Playlist Info with ID: {id}")
            url: str = f"{self.url(type='playlist')}?id={id}&limit=1000"
        else:
            if link.startswith("www"):
                link = f"https://{link}"
            log.info(f"Extracting Playlist Info with Link: {link}")
            url: str = f"{self.url(type='playlist')}?link={link}&limit=1000"
        _res = self.SESSION.get(url)
        data: dict = json.loads(_res.content.decode())["data"]

        log.debug(
            f"Playlist: {data.get('name')}\nSongCount:{data.get('songCount')}\nFollowers:{data.get('followerCount')}\nURL:{data.get('url')}"
        )

        return _parse_playlist_results(song_list=data["songs"])

    def song(self, url: str) -> Song:
        """Returns Song dataclass from provided jiosaavn url"""
        req_url: str = f"{self.url(type='song')}?link={url}"
        log.info(f"Extracting Song from URL: {url}")
        _res = self.SESSION.get(req_url)
        data: dict = json.loads(_res.content.decode())["data"][0]
        return _parse_song_dict(song_dict=data)


def _parse_song_dict(song_dict: dict) -> Song:
    return Song(
        song_id=song_dict["id"],
        name=song_name(song_dict=song_dict),
        album=album_name(song_dict=song_dict),
        media_url=media_url(song_dict=song_dict),
        primary_artists=artists(song_dict=song_dict, type="primary"),
        artists=artists(song_dict=song_dict, type="all"),
        year=int(song_dict["year"]),
        image_url=image_url(song_dict=song_dict),
    )


def _parse_playlist_results(song_list: list[dict]) -> list[Song]:
    return [_parse_song_dict(song_dict) for song_dict in song_list]


def media_url(song_dict: dict) -> str:
    media_url: str = ""
    download_urls: list[dict] = song_dict["downloadUrl"]
    _currentkbps: int = 0

    for download_url in download_urls:
        __curr = int(download_url["quality"].replace("kbps", ""))
        if __curr > _currentkbps:
            media_url = download_url["url"]
            _currentkbps = __curr

    return media_url


def artists(song_dict: dict, type: Literal["primary", "all"]) -> list[str]:
    return [artist["name"] for artist in song_dict["artists"].get(type)]


def image_url(song_dict: dict) -> str:
    urls: list[dict] = song_dict["image"]
    _currentkbps: int = 0
    image_url: str = ""

    for url in urls:
        __curr = int(url["quality"].split("x")[0])
        if __curr > _currentkbps:
            image_url = url["url"]
            _currentkbps = __curr
    return image_url


def song_name(song_dict: dict) -> str:
    name: str = html.unescape(song_dict["name"])
    if match := re.match(r'^(.*) \(From "(.*)"\)$', name.strip()):
        return match.group(1)
    return name.strip()


def album_name(song_dict: dict) -> str:
    name: str = html.unescape(song_dict["album"]["name"])
    if match := re.match(r'^(.*) \(From "(.*)"\)$', name.strip()):
        return match.group(2)
    return name.strip()
