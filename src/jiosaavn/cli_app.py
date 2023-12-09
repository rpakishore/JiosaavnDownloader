import typer
from rich import print
from pathlib import Path
from jiosaavn import JiosaavnDownload

#Default import to globally enable/disable debugger
from . import log, ic
ic.configureOutput(prefix=f'{Path(__file__).name} -> ')


app = typer.Typer()

@app.command()
def playlist(
    id: str,
    final_path: str = r'Y:\\Music'):
    """Downloads the songs from specified playlist
    """
    saavn = JiosaavnDownload(final_location='Y:\\Music')
    saavn.playlist(id, skip_downloaded=True)

@app.command()
def song(
    url: str,
    final_path: str = r'Y:\\Music'):
    """Downloads the songs from specified playlist
    """
    saavn = JiosaavnDownload(final_location='Y:\\Music')
    saavn.song(url, skip_downloaded=True)
