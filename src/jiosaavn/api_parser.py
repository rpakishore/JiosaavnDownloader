from dataclasses import dataclass
from jiosaavn.file_parser import Song
from pathlib import Path
from ak_requests import RequestsSession
from . import log, ic
ic.configureOutput(prefix=f'{Path(__file__).name} -> ')


class SaavnAPI:
    session = RequestsSession()
    def __init__(self, baseurl: str, port: int = 80):
        self.baseurl = baseurl
        self.port = port
        self.url = f"http://{baseurl}:{port}"
        
    def __str__(self) -> str:
        return f"SaavnAPI class for {self.url}"
    
    def __repr__(self) -> str:
        return f"SaavnAPI({self.baseurl}, {self.port})"
    
    def song(self, url: str) -> Song:
        data = self.session.get(f"{self.url}/song/?query={url}").json()
        return _song_from_json(data)
    
    def playlist(self, url: str) -> list[Song]:
        data = self.session.get(f"{self.url}/result/?query={url}").json()
        return [_song_from_json(song) for song in data.get('songs')]

            
def _song_from_json(data: dict) -> Song:
    if isinstance(_artist_map:=data.get('artistMap'), dict):
        artists = list(_artist_map.keys())
    else:
        artists = []

    return Song(
        song_id = data['id'],
        name = data['song'],
        album = data['album'],
        media_url= data['media_url'],
        primary_artists= data['primary_artists'].split(', '),
        artists= artists,
        year = int(data.get('year', 0)),
        image_url= data.get('image') # type: ignore
    )