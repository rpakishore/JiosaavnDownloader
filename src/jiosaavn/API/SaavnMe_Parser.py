from ak_requests import RequestsSession
import brotli

from jiosaavn.file_parser import Song
import json

from jiosaavn.utils import log

class SaavnMe:
    BASEURL: str = 'https://saavn.me/'
    SESSION = RequestsSession()
    log.info('SaavnMe Instance Initialized')
    
    def __init__(self) -> None:
        self.SESSION.MIN_REQUEST_GAP = 1.5  #To prevent Ratelimit in free API
    
    def __str__(self) -> str:
        return 'Instance of SaavnMe class for saavn.me parser'
    
    def __repr__(self) -> str:
        return 'SaavnMe()'
    
    def playlist(self, id: int|str) -> list[Song]:
        """Provides a list of Song dataclass from the playlist id"""
        log.info(f'Extracting Playlist Info with ID: {id}')
        url: str = f'{self.BASEURL}playlists?id={id}'
        _res = self.SESSION.get(url)
        try:
            data: dict = json.loads(_res.content)['data']
        except Exception:
            data: dict = json.loads(brotli.decompress(_res.content))['data']
        
        log.debug(f'Playlist: {data.get("name")}\nSongCount:{data.get("songCount")}\nFollowers:{data.get("followerCount")}\nURL:{data.get("url")}')
                
        return _parse_playlist_results(
            song_list=data['songs']
            )
    
    def song(self, url: str) -> Song:
        """Returns Song dataclass from provided jiosaavn url"""
        req_url: str = f'{self.BASEURL}songs?link={url}'
        log.info(f'Extracting Song from URL: {url}')
        data: dict = self.SESSION.get(req_url).json()['data']
        return _parse_song_dict(song_dict=data)
    
def _parse_song_dict(song_dict: dict) -> Song:
    # get media url
    download_urls: list[dict] = song_dict['downloadUrl']
    _currentkbps: int = 0
    media_url: str = ''
    
    for download_url in download_urls:
        __curr = int(download_url['quality'].replace('kbps',''))
        if __curr > _currentkbps:
            media_url = download_url['link']
            _currentkbps = __curr

    #primary_artists
    primary_artists = song_dict['primaryArtists'].split(', ')
    
    # get image url
    urls: list[dict] = song_dict['image']
    _currentkbps: int = 0
    image_url: str = ''
    
    for url in urls:
        __curr = int(url['quality'].split('x')[0])
        if __curr > _currentkbps:
            image_url = url['link']
            _currentkbps = __curr

    return Song(
                song_id=song_dict['id'],
                name=song_dict['name'],
                album=song_dict['album']['name'],
                media_url=media_url,
                primary_artists=primary_artists,
                artists=primary_artists,
                year=int(song_dict['year']),
                image_url=image_url
            )

def _parse_playlist_results(song_list: list[dict]) -> list[Song]:
    return [_parse_song_dict(song_dict) for song_dict in song_list]