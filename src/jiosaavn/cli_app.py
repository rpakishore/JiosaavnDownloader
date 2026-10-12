import typer
from pathlib import Path
from jiosaavn import JiosaavnDownload
from jiosaavn.main import get_config

import tomllib

#Default import to globally enable/disable debugger
from . import ic, log
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

@app.command()
def sync(final_path: str = ''):
    """Downloads every playlist listed under `[schedule] playlists` in config.toml
    """
    playlists = get_config().get('schedule', {}).get('playlists', [])
    if not playlists:
        raise Exception('No playlists configured under `[schedule] playlists` in config.toml')

    final_path = get_final_path(final_path)
    saavn = JiosaavnDownload(final_location=final_path)
    failed = []
    for playlist_id in playlists:
        try:
            saavn.playlist(str(playlist_id), skip_downloaded=True)
        except Exception as e:
            log.error(f'Playlist {playlist_id} failed: {e!r}')
            failed.append(str(playlist_id))

    if failed:
        log.error(f'{len(failed)}/{len(playlists)} playlist(s) failed: {", ".join(failed)}')
        raise typer.Exit(code=1)

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