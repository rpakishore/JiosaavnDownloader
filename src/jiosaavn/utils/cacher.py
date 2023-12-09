from pathlib import Path
import pickle

from jiosaavn.utils import log

class Cache:
    def __init__(self, filepath: str|Path) -> None:
        self.filepath = Path(str(filepath))
        self.initialize()
        self.cache_data = None
        log.info(f'Initialized Cache Object at {self.filepath}')
    
    def __str__(self) -> str:
        return f"Cache file for Jiosaavn downloaded from {self.filepath.name}\n\nData:\n{self.cache_data}"
    
    def __repr__(self) -> str:
        return f"Cache({self.filepath})"
    
    @property
    def data(self) -> list:
        if self.cache_data is None:
            with open(self.filepath, 'rb') as f:
                self.cache_data = pickle.load(f)
        return self.cache_data
    
    def write(self, data: list) -> None:
        """Write the `data` to cache file
        """
        log.debug(f'Writing cache data to {self.filepath}')
        self.cache_data = self._write_to_pickle(data)
        return None
    
    def _write_to_pickle(self, data: list) -> list:
        with open(self.filepath, 'wb') as f:
            pickle.dump(data, f)
        log.debug('Cache Updated')
        return data
    
    def initialize(self) -> None:
        """Creates the database file if not exist"""
        if not self.filepath.is_file():
            self._write_to_pickle([])
            log.info('Cache file created')