from jiosaavn.debugger import ic
from jiosaavn.api_parser import SaavnAPI
from jiosaavn.file_parser import Song
from jiosaavn.Cacher import Cache
from pathlib import Path

class MainApp():
    def __init__(self, baseurl: str, port: str, song_urls: list[str] = [], 
                 playlist_urls: list[str] = [], cache_filepath: str= None, 
                 skip_downloaded: bool = True, final_location: str = None
                 ) -> None:
        self.song_urls = song_urls
        self.playlist_urls = playlist_urls
        self.cache_filepath = cache_filepath
        self.skip_downloaded = skip_downloaded
        self.final_location = final_location
        self.cache = Cache(Path(str(cache_filepath)))
        self.saavn = SaavnAPI(baseurl=baseurl, port=port)

        
    def run(self) -> list[Song]:
        cache_data = self.cache.data
        for song in self.songlist:
            try:
                with song as f:
                    f.download(final_name=f"")
                    f.embed_metadata()
                    if self.final_location:
                        f.move(finalpath=Path(self.final_location))
                    if self.skip_downloaded:
                        cache_data.append(song)
                        self.cache.write(cache_data)
            except Exception as e:
                print(str(e))
            
    @property
    def songlist(self) -> list[Song]:
        song_list = []
        for url in self.song_urls:
            try:
                _song = self.saavn.song(url)
            except Exception as e:
                print(str(e))
            if self.skip_downloaded and _song in self.cache.data:
                continue
            else:
                song_list.append(_song)
        
        for url in self.playlist_urls:
            for _song in self.saavn.song(url):
                if self.skip_downloaded and _song in self.cache.data:
                    continue
                else:
                    song_list.append(_song)
        return song_list
    
    def __str__(self) -> str:
        return "MainApp Class for downloading from JioSaavn"
    
    def __repr__(self) -> str:
        return f"MainApp({self.song_urls=},{self.playlist_urls=}, {self.cache_filepath=}, {self.skip_downloaded}, {self.final_location=})"