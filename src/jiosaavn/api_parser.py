from dataclasses import dataclass
from jiosaavn.file_parser import Song
from jiosaavn.debugger import ic
from jiosaavn.request_package import Req

class SaavnAPI:
    session = Req()
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
    
    def playlist(self, url: str) -> tuple[Song]:
        data = self.session.get(f"{self.url}/result/?query={url}").json()
        return (_song_from_json(song) for song in data.get('songs'))

            
def _song_from_json(data: dict) -> Song:
    if type(data.get('artistMap')) == dict:
        artists = list(data.get('artistMap').keys())
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
        image_url= data.get('image')
    )