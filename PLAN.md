# Refactor plan (temporary, deleted before merge)

Goals: KISS, DRY, YAGNI, faster. Linux only (cron box). Sequential downloads.

## Decisions (from user)
- Output stays **mp3**, but at **320k** (source is 320kbps AAC; old code produced ffmpeg's default ~128k).
- Preserve: `songs.jsonl` record format (key order, merge=union), file naming `Name-Album(Year).mp3`.
- Free to change: Python API, CLI flags, internal layout.
- Delete: unused modules, Slack, migrate.py, notebook, keyring/getpass, icecream, ak_requests, typer.
- One failing song never stops the run: log it, skip it (not cached, so retried next run), exit code 1 at end.
- CLI commands: `sync`, `playlist`, `song`, `search`.
- Offline tests + GitHub Actions; live-API tests behind `-m live` (deselected by default).

## Performance levers
1. One ffmpeg pass does encode + ID3 tags + cover art (ffmpeg reads the cover URL itself). Removes eyed3,
   the extra cover-image HTTP request and the re-open/re-write of the mp3.
2. Write straight into the destination dir as a hidden `.part` file, then `os.replace` (atomic, no cross-drive copy).
3. ~40 fewer transitive packages (yt-dlp, cryptography, rich, ...): faster `uv sync` and startup.
4. Cache check happens before any network call per song (already true, keep it).
5. Keep a 1.5s minimum gap between API calls (free API rate limit), but not between CDN downloads.

## Layout (all under `src/jiosaavn/`; logging via `logging.getLogger(__name__)`, no print)
```
__init__.py   docstring + __version__ only
song.py       Song dataclass, sanitize(), clean_title()
api.py        SaavnClient (requests), parse_song()
download.py   download(song, dest_dir, bitrate) via one ffmpeg subprocess
cache.py      Cache (append-only songs.jsonl)
config.py     Config + load_config()
notify.py     gotify()
cli.py        argparse entry point `app`, the download loop
```
Tests in `src/tests/`, one file per module: test_song.py, test_api.py, test_download.py,
test_cache.py, test_config.py, test_notify.py, test_cli.py. Shared fixtures in `src/tests/conftest.py` only if needed by 2+ files.

## Interface contract (agents must match these exactly)

### song.py
```python
@dataclass(frozen=True, slots=True)
class Song:
    id: str
    name: str            # already cleaned: html-unescaped, ' (From "X")' suffix removed
    album: str           # already cleaned: html-unescaped, 'Foo (From "X")' -> 'X'
    year: int            # 0 when unknown
    media_url: str
    image_url: str       # "" when none
    primary_artists: tuple[str, ...]
    artists: tuple[str, ...]

    @property
    def filename(self) -> str:   # sanitize(f"{name}-{album}({year or ''}).mp3")

def sanitize(filename: str) -> str     # ported from old utils/file.py, same behavior (Windows-safe chars kept: music share may be SMB)
def clean_title(name: str) -> tuple[str, str | None]
    # html.unescape + strip; if matches r'^(.*) \(From "(.*)"\)$' -> (group1, group2) else (name, None)
```
Song name rule: `clean_title(raw_name)[0]`. Album rule: `from_ or base` where `base, from_ = clean_title(raw_album)`.

### api.py
```python
class SaavnClient:
    BASE_URL = "https://saavn.sumit.co/api"
    def __init__(self, session: requests.Session | None = None, min_interval: float = 1.5) -> None
    def playlist(self, id_or_link: str) -> list[Song]   # starts with http/www -> ?link= (prefix https:// for www), else ?id= ; limit=1000
    def song(self, url: str) -> Song                     # /songs?link=
    def search(self, query: str, limit: int = 10) -> list[Song]   # /search/songs?query=&limit=
def parse_song(d: dict) -> Song   # highest-kbps downloadUrl, largest image, artists.primary / artists.all names
```
- Every request: `params=` (not string-built URLs), `timeout=30`, `raise_for_status()`, and `RuntimeError` if JSON `success` is not true.
- Session mounts `HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504)))`.
- Throttle: sleep so consecutive API calls are >= min_interval apart (`time.monotonic`).
- One malformed song dict in a playlist: log a warning and skip it, don't fail the playlist.

### download.py
```python
def download(song: Song, dest_dir: Path, bitrate: str = "320k") -> Path
```
- Final path `dest_dir / song.filename`; ffmpeg writes `dest_dir / f".{song.filename}.part"`, then `os.replace` to final. On any failure the .part is removed and the exception re-raised as `RuntimeError` with ffmpeg's stderr tail.
- `dest_dir.mkdir(parents=True, exist_ok=True)`.
- Command (a list, `subprocess.run(cmd, check=..., capture_output=True, text=True, timeout=900)`):
  `ffmpeg -nostdin -hide_banner -loglevel error -y -i <media_url> [-i <image_url>] -map 0:a [-map 1:v -c:v copy -disposition:v attached_pic -metadata:s:v title=Album\ cover -metadata:s:v comment=Cover\ (front)] -c:a libmp3lame -b:a <bitrate> -id3v2_version 3 -metadata title=.. -metadata artist=<", ".join(primary_artists)> -metadata album=.. -metadata album_artist=<", ".join(artists)> [-metadata date=<year> if year] -f mp3 <part>`
- Expose `build_command(song, out_path, bitrate) -> list[str]` so it is unit-testable without ffmpeg.

### cache.py
Port of old `utils/cacher.py`, same on-disk format and same tolerance (blank/bad lines, duplicates, partial last line, LF only, UTF-8 not \u-escaped).
```python
class Cache:
    def __init__(self, filepath: Path) -> None     # creates parent dir + empty file if missing; loads ids once
    filepath: Path
    ids: set[str]
    def __contains__(self, song_id: object) -> bool
    def __len__(self) -> int
    def add(self, song: Song, filepath: Path | None, downloaded_at: datetime | None) -> None   # no-op if id known
def to_record(song: Song, filepath, downloaded_at) -> dict   # key order: id,name,album,year,media_url,image_url,primary_artists,artists,download_date,filepath,filename
```

### config.py
```python
@dataclass(frozen=True)
class Config:
    db_path: Path                 # Path(paths.db_folder, default ".") / "songs.jsonl"
    destination: Path | None      # paths.destination; None if missing or ""
    playlists: tuple[str, ...]    # schedule.playlists, each str()-ed
    gotify_url: str               # gotify.url, else env GOTIFY_URL, else ""
    gotify_token: str             # gotify.app_key, else env GOTIFY_TOKEN, else ""
def load_config(path: Path = Path("config.toml")) -> Config   # missing file -> all defaults; relative paths resolved against the config file's dir
```
Existing user config.toml keys stay valid (`app_name` is ignored).

### notify.py
```python
def gotify(url: str, token: str, title: str, message: str, priority: int = 2) -> None
```
No-op if url or token empty. POST `{url.rstrip('/')}/message`, header `X-Gotify-Key`, markdown extras, timeout 10. Never raises (log warning).

### cli.py (entry point `app = "jiosaavn.cli:main"`)
```
app [--config PATH] [--dest DIR] [--dry-run] [-v] sync
app [...] playlist ID_OR_URL
app [...] song URL
app [...] search QUERY [--limit N=10]
```
Global options are accepted before the subcommand. Destination: `--dest` or config, else exit 2 with a clear message.
`main(argv: list[str] | None = None) -> int`. Download loop per song: skip if `song.id in cache` (debug log) -> dry-run: log and continue -> `download()` -> `cache.add(song, path, datetime.now())` -> `gotify(...)` (title `[Jiosaavn]{name}`, message `Album: {album}\n\n ![]({image_url})`). Any exception in a song: log error, count it, continue. Playlist fetch failure in sync: log, count, continue to next playlist. End: log summary `downloaded=N skipped=N failed=N`; return 1 if any failure else 0. Logging: `logging.basicConfig` to stderr, `%(asctime)s %(levelname)s %(name)s: %(message)s`, INFO (DEBUG with -v).
