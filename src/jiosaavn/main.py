from jiosaavn.api_parser import SaavnAPI
from jiosaavn.API import SaavnMe
from jiosaavn.file_parser import Song
from jiosaavn.utils import Cache
from pathlib import Path
from typing import Literal
import tomllib

from . import log, ic
from .notify.Gotify import notify


ic.configureOutput(prefix=f'{Path(__file__).name} -> ')

class JiosaavnDownload:
    
    GOTIFY_CHANNEL: str|None = None
    __gotify_key: str|None = None
    
    def __init__(self, cache_filepath: str|None = Path('database.pkl'), final_location: Path|None = None) -> None:
        
        config = get_config()
        if cache_filepath is None:
            cache_filepath = Path(config.get('db_folder', '.')) / 'database.pkl'
        if final_location is None:
            final_location = Path(config.get('destination', '.'))
            
        channel_name = config.get('gotify', {}).get('app_name', '')
        if channel_name != '':
            self.GOTIFY_CHANNEL = channel_name
            self.GOTIFY_URL = config.get('gotify', {}).get('url', '')
            if key:=config.get('gotify', {}).get('app_key', '') != '':
                self.__gotify_key = key
        
        self.cache_filepath: Path = Path(str(cache_filepath))
        self.cache = Cache(filepath=self.cache_filepath)
        self.set_downloader()
        self.final_location: Path = Path(str(final_location))
    
    def set_downloader(self, downloader: SaavnMe = SaavnMe()):
        self.ApiProvider = downloader
    
    def song(self, url: str, skip_downloaded: bool = True, debug_only: bool=False):
        self._download_song(song=self.ApiProvider.song(url=url), 
                            skip_downloaded=skip_downloaded, debug_only=debug_only)
    
    def _download_song(self, song: Song, skip_downloaded: bool, debug_only: bool):
        with song:
            if debug_only:
                song.debug_mode = True
            if skip_downloaded and self.check_downloaded(song):
                log.debug(f'Skipping {song.sanitized_name} from {song.sanitized_album}, Downloaded on {song.download_date}')
                return
            _download_song(song=song, final_location=self.final_location)
        
        if self.GOTIFY_CHANNEL:
            self.__gotify(song)
        if not debug_only:
            _cache_data = self.cache.data
            _cache_data.append(song)
            self.cache.write(data = _cache_data)
        else:
            log.debug('Cache will be updated here.')
            
    def __gotify(self, song:Song) -> None:
        assert self.GOTIFY_CHANNEL is not None
        _title = f'[Jiosaavn]{song.sanitized_name}'
        _msg = f'Album: {song.sanitized_album}\n\n ![]({song.image_url})'
        notify(app=self.GOTIFY_CHANNEL,title=_title, message=_msg, 
                priority=2,url=self.GOTIFY_URL, apptoken=self.__gotify_key)
    
    def playlist(self, id_link: str|int, skip_downloaded: bool = True, debug_only: bool=False):
        if id_link.startswith('http') or id_link.startswith('www'):
            songs = self.ApiProvider.playlist(link=id_link)
        else:
            songs = self.ApiProvider.playlist(id=id_link)
        for song in songs:
            self._download_song(song=song, skip_downloaded=skip_downloaded, debug_only=debug_only)
        
    def check_downloaded(self, song: Song) -> bool:
        """Checks if the specified song has previously been downloaded"""
        return song.id in [each.id for each in self.cache.data]
    
def _download_song(song: Song, final_location: Path|str) -> None:
    song.download()
    song.embed_metadata()
    song.move(finalpath=final_location)
    
def get_config() -> dict:
    config_path: Path = Path(__file__).parent.parent.parent / 'config.json'
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = tomllib.loads(f.read())
    else: 
        config = {}
    return config