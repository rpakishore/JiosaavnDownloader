from jiosaavn.api_parser import SaavnAPI
from jiosaavn.API import SaavnMe
from jiosaavn.file_parser import Song
from jiosaavn.utils import Cache
from pathlib import Path
from typing import Literal

from . import log, ic
from .notify.Gotify import notify


ic.configureOutput(prefix=f'{Path(__file__).name} -> ')

class JiosaavnDownload:
    
    GOTIFY_CHANNEL: str|None = None
    GOTIFY_URL: str = "https://gotify.rpakishore.co.in"
    
    def __init__(self, cache_filepath: str|Path = Path('database.pkl'), final_location: Path|str = Path('.')) -> None:
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
                log.debug(f'Skipping {song.name} from {song.album}, Downloaded on {song.download_date}')
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
        _msg = f'Album: {song.sanitized_album}'
        notify(app=self.GOTIFY_CHANNEL,title=_title, message=_msg, 
                priority=2,url=self.GOTIFY_URL)
    
    def playlist(self, id: str|int, skip_downloaded: bool = True, debug_only: bool=False):
        for song in self.ApiProvider.playlist(id=id):
            self._download_song(song=song, skip_downloaded=skip_downloaded, debug_only=debug_only)
        
    def check_downloaded(self, song: Song) -> bool:
        """Checks if the specified song has previously been downloaded"""
        return song.id in [each.id for each in self.cache.data]
    
def _download_song(song: Song, final_location: Path|str) -> None:
    song.download()
    song.embed_metadata()
    song.move(finalpath=final_location)