from pathlib import Path
import pickle
from jiosaavn.debugger import ic

class Cache:
    def __init__(self, filepath: str) -> None:
        self.filepath = Path(filepath)
        self.cache_data = None
    
    def __str__(self) -> str:
        return f"Cache file for Jiosaavn downloaded from {self.filepath.name}\n\nData:\n{self.cache_data}"
    
    def __repr__(self) -> str:
        return f"Cache({self.filepath})"
    
    @property
    def data(self) -> list:
        if self.cache_data is None:
            if not self.filepath.is_file():
                self.cache_data = self._write_to_pickle([])
            else:
                with open(self.filepath, 'rb') as f:
                    self.cache_data = pickle.load(f)
        return self.cache_data
    
    def write(self, data: list) -> list:
        """Write the `data` to cache file

        Returns:
            list: `data`
        """
        self.cache_data = self._write_to_pickle(data)
        return self.data
    
    def _write_to_pickle(self, data: list) -> list:
        with open(self.filepath, 'wb') as f:
            pickle.dump(data, f)
        ic('Cache Updated')
        return data
        