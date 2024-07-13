import typer
from pathlib import Path
from jiosaavn import JiosaavnDownload

import tomllib

#Default import to globally enable/disable debugger
from . import ic
ic.configureOutput(prefix=f'{Path(__file__).name} -> ')


app = typer.Typer()

@app.command()
def playlist(
    id: str,
    final_path: str = ''):
    """Downloads the songs from specified playlist
    """
    final_path = get_final_path(final_path)
    saavn = JiosaavnDownload(final_location=final_path)
    saavn.playlist(id, skip_downloaded=True)

@app.command()
def song(
    url: str,
    final_path: str = ''):
    """Downloads the songs from specified playlist
    """
    final_path = get_final_path(final_path)
    saavn = JiosaavnDownload(final_location=final_path)
    saavn.song(url, skip_downloaded=True)

def get_final_path(final_path: str = '') -> Path:
    config_path: Path = Path(__file__).parent.parent.parent / 'config.toml'
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = tomllib.loads(f.read())
    else: 
        config = {}
    
    if final_path == '':
        final_path = config.get('paths', {}).get('destination', '')
    
    if final_path == '':
        raise Exception('Please create a config.toml file in the root directory or pass in `final_path`')
    
    return final_path