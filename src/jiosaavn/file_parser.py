from ak_requests import RequestsSession
import eyed3
from ffmpy import FFmpeg

from datetime import datetime
import html
from pathlib import Path
import re
import shutil
import time
from typing import Optional

from jiosaavn.utils import log, sanitize

class Song:
    session = RequestsSession()
    def __init__(self, song_id: str, name: str, album: str, media_url: str,
                    primary_artists: list[str], artists: list[str], year: int, 
                    image_url: str, debug_mode: bool = False, **kwargs) -> None:
        self.id = song_id
        self.name = name
        self.album = album
        self.media_url = media_url
        self.image_url = image_url
        self.download_date = None
        self.filepath = None
        self.primary_artists = primary_artists
        self.artists = artists
        self.year = year
        self.image_url = image_url
        self.debug_mode = debug_mode
        
    def __str__(self) -> str:
        return f"Song {self.name} from {self.album}"
    
    def __repr__(self) -> str:
        return f"Song({self.id=}, {self.name=}, {self.album=}, {self.media_url=}, {self.download_date=})"
    
    def __eq__(self, __value: object) -> bool:
        return self.id == __value
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            log.error(f"There was an {str(exc_type)} error on {self.name}({self.id}) from {self.album}.")
            log.error(f"\nError:\n{exc_value}")
            log.error(f"\nTraceback:\n{traceback}")

    def download(self, final_name: str|None=None, media_url: Optional[str] = None) -> Path:
        """Downloads the mp3 to local folder

        Args:
            final_name (str): Name for the mp3 file, can pass `None` to autoset from metadata.
            media_url (str, optional): url for the mp3. If none, tries to get url from `self.media_url`. Defaults to None.

        Returns:
            Path: path of the downloaded file
        """
        if final_name is None:
            final_name = self.filename
        if media_url:
            self.media_url = media_url
        else:
            media_url = self.media_url
        
        final_name = sanitize(final_name) if final_name.endswith('.mp3') else sanitize(final_name + '.mp3')
        
        filepath = Path(final_name)
        if not self.debug_mode:
            log.debug(f"Downloading from {media_url} to {filepath.absolute()}")
        
            start = time.time()
            FFmpeg(
                inputs={media_url:None},
                outputs={final_name: None}
            ).run()
        
            self.download_date = datetime.now()
            size = filepath.stat().st_size/(1024*1024)  #In MB
            time_taken = time.time() - start
            log.info(f"Download completed ({size:.2f} MB) in {time_taken:.1f} sec(s) at {size/time_taken:.1f} MB/s")
        else:
            log.debug(f'Run Downloaded: {self.media_url} -> {self.filepath}')
        self.filepath = filepath
        return filepath
    
    def move(self, finalpath: Path|str) -> Path:
        """Move file to final destination"""
        finalpath = Path(str(finalpath))
        assert self.filepath is not None
        
        if finalpath.is_dir():
            finalpath = finalpath / self.filepath.name
        
        if not self.debug_mode:
            log.debug(f"Moving {self.filepath} --> {finalpath}")
            #self.filepath.rename(finalpath)
            shutil.move(src=self.filepath, dst=finalpath)
        else:
            log.debug(f'Move {self.filepath} -> {finalpath}')
        self.filepath = finalpath
        return finalpath
    
    def embed_metadata(self) -> Path:
        """Write Metadata to `mp3`"""
        assert self.filepath is not None
        filepath = self.filepath
        if not self.debug_mode:
            log.debug(f"Writing metadata to {filepath}")
            audiofile = eyed3.load(filepath)
            if audiofile is None:
                return self.filepath
            audiofile.initTag()
            if audiofile.tag is None:
                return self.filepath
            audiofile.tag.artist = ', '.join(self.primary_artists)
            audiofile.tag.album = self.album
            
            audiofile.tag.album_artist = "" if self.artists == [] else ', '.join(self.artists)
            audiofile.tag.title = self.name
            
            if self.year != 0:
                audiofile.tag.year = self.year
            
            if self.image_url:
                audiofile.tag.images.set(3, self.image, "image/jpeg", u"cover")
            audiofile.tag.save()
            
            log.info(f"Metadata written for {self.name}")
        else:
            log.debug(f'Embed metadata for {self.filepath}')
        return self.filepath

    @property
    def image(self):
        """Return contents of `.image_url` url"""
        if self.image_url == "":
            log.debug('`self.image_url` is ""')
            return None
        log.debug(f"Initiating requests: {self.image_url}")
        return self.session.get(url=self.image_url, timeout=10).content
    
    @property
    def filename(self) -> str:
        log.debug(f'{self.sanitized_name=}, {self.sanitized_album=}')
        return f'{self.sanitized_name}-{self.sanitized_album}({self.year if self.year !=0 else ""}).mp3'
    
    @property
    def sanitized_name(self) -> str:
        song_name:str = html.unescape(self.name)
        song_name = re.sub(r' ?\(From ".*"\)', '', song_name)
        return song_name
    
    @property
    def sanitized_album(self) -> str:
        album_name: str = html.unescape(self.album)
        if _album:=re.findall(r'\(From "(.*)"\)',album_name):
            album_name = _album[0]
        return album_name