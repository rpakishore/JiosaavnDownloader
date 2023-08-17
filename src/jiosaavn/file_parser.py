import unicodedata, re, time
from ffmpy import FFmpeg
from datetime import datetime
from pathlib import Path
from typing import Optional
from jiosaavn.request_package import Req
from jiosaavn.debugger import ic
import eyed3

class Song:
    session = Req()
    def __init__(self, song_id: str, name: str, album: str, media_url: str,
                 primary_artists: list[str], 
                 artists: list[str], year: int, image_url: str, **kwargs) -> None:
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
            print(f"There was an {str(exc_type)} error on {self.name}({self.id}) from {self.album}.")
            print(f"\nError:\n{exc_value}")
            print(f"\nTraceback:\n{traceback}")

    
    def download(self, final_name: str, media_url: Optional[str] = None) -> Path:
        """Downloads the mp3 to local folder

        Args:
            final_name (str): Name for the mp3 file
            media_url (str, optional): url for the mp3. If none, tries to get url from `self.media_url`. Defaults to None.

        Returns:
            Path: path of the downloaded file
        """
        if media_url:
            self.media_url = media_url
        else:
            media_url = self.media_url
        
        final_name = sanitize(final_name) if final_name.endswith('.mp3') else sanitize(final_name + '.mp3')
        
        filepath = Path(final_name)
        ic(f"Downloading from {media_url} to {filepath.absolute()}")
        start = time.time()
        FFmpeg(
            inputs={media_url:None},
            outputs={final_name: None}
        ).run()
        
        self.filepath = filepath
        self.download_date = datetime.now()
        size = filepath.stat().st_size/(1024*1024)  #In MB
        time_taken = time.time() - start
        ic(f"Download completed ({size:.2f} MB) in {time_taken:.1f} sec(s) at {size/time_taken:.1f} MB/s")
        return filepath
    
    def move(self, finalpath: Path) -> Path:
        if type(finalpath) == str:
            finalpath = Path(finalpath)
            
        ic(f"Moving {self.filepath} --> {finalpath}")
        
        if finalpath.is_dir():
            finalpath = finalpath / self.filepath.name
            
        self.filepath.rename(finalpath)
        self.filepath = finalpath
        return finalpath
    
    def embed_metadata(self) -> Path:
        filepath = self.filepath
        ic(f"Writing metadata to {filepath}")
        audiofile = eyed3.load(filepath)
        audiofile.initTag()
        audiofile.tag.artist = ', '.join(self.primary_artists)
        audiofile.tag.album = self.album
        
        
        audiofile.tag.album_artist = "" if self.artists == [] else ', '.join(self.artists)
        audiofile.tag.title = self.name
        
        if self.year != 0:
            audiofile.tag.year = self.year
        
        if self.image_url:
            audiofile.tag.images.set(3, self.image, "image/jpeg", u"cover")
        audiofile.tag.save()
        
        ic(f"Metadata written for {self.name}")
        return self.filepath

    @property
    def image(self):
        if self.image_url == "":
            ic('`self.image_url` is ""')
            return None
        ic(f"Initiating requests: {self.image_url}")
        return self.session.get(url=self.image_url, timeout=10).content

def sanitize(filename: str) -> str:
    """Return a fairly safe version of the filename.

    We don't limit ourselves to ascii, because we want to keep municipality
    names, etc, but we do want to get rid of anything potentially harmful,
    and make sure we do not exceed Windows filename length limits.
    Hence a less safe blacklist, rather than a whitelist.
    """
    blacklist = ["\\", "/", ":", "*", "?", "\"", "<", ">", "|", "\0"]
    reserved = [
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
        "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
        "LPT6", "LPT7", "LPT8", "LPT9",
    ]  # Reserved words on Windows
    filename = "".join(c for c in filename if c not in blacklist)
    # Remove all charcters below code point 32
    filename = "".join(c for c in filename if 31 < ord(c))
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.rstrip(". ")  # Windows does not allow these at end
    filename = filename.strip()
    if all([x == "." for x in filename]):
        filename = "__" + filename
    if filename in reserved:
        filename = "__" + filename
    if len(filename) == 0:
        filename = "__"
    if len(filename) > 255:
        parts = re.split(r"/|\\", filename)[-1].split(".")
        if len(parts) > 1:
            ext = "." + parts.pop()
            filename = filename[:-len(ext)]
        else:
            ext = ""
        if filename == "":
            filename = "__"
        if len(ext) > 254:
            ext = ext[254:]
        maxl = 255 - len(ext)
        filename = filename[:maxl]
        filename = filename + ext
        # Re-check last character (if there was no extension)
        filename = filename.rstrip(". ")
        if len(filename) == 0:
            filename = "__"
    return filename
