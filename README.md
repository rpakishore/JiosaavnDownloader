<div align="center">
  <h1>Jiosaavn Downloader</h1>
  <p>Download Jiosaavn songs and playlists as tagged mp3 files, using an unofficial API.</p>
  <h4>
    <a href="https://github.com/rpakishore/JiosaavnDownloader/issues/">Report Bug</a>
    <span> | </span>
    <a href="https://github.com/rpakishore/JiosaavnDownloader/issues/">Request Feature</a>
  </h4>
</div>

## Features

- Downloads songs, playlists and search results as 320k mp3 with ID3 tags and cover art.
- Remembers what it downloaded (`songs.jsonl`), so nothing is downloaded twice.
- One failing song never stops a run: it is logged, skipped and retried next time.
- Optional Gotify notification per downloaded song.

## Install

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/) and `ffmpeg` on the `PATH`.

```bash
git clone https://github.com/rpakishore/JiosaavnDownloader.git
cd JiosaavnDownloader
uv sync
```

## Configure

Copy `config.example.toml` to `config.toml` and edit it:

| Key | Meaning |
| --- | --- |
| `paths.destination` | Folder the mp3 files are written to |
| `paths.db_folder` | Folder holding `songs.jsonl` |
| `gotify.url`, `gotify.app_key` | Gotify server and app token (optional; falls back to env `GOTIFY_URL` / `GOTIFY_TOKEN`) |
| `schedule.playlists` | Playlist ids downloaded by `app sync` |

Relative paths are resolved against the config file's folder.

## Usage

```bash
uv run app sync                                  # every playlist in config.toml
uv run app playlist 109815423                    # a playlist id or link
uv run app song https://www.jiosaavn.com/song/houdini/OgwhbhtDRwM
uv run app search "houdini" --limit 5            # top 5 results

uv run app --dest ~/Music --dry-run -v playlist 109815423
```

Global options go before the command:

| Option | Meaning |
| --- | --- |
| `--config PATH` | Config file (default `config.toml`) |
| `--dest DIR` | Destination folder, overrides `paths.destination` |
| `--dry-run` | Show what would be downloaded; downloads and caches nothing |
| `-v`, `--verbose` | Debug logging |

Logs go to stderr. Exit code is 0 on success, 1 if any song or playlist failed, 2 on bad usage or setup (no destination, no playlists, ffmpeg missing).

## Download database

Downloaded songs are recorded in `songs.jsonl` (one JSON object per line, append-only), which is committed to this repo. `.gitattributes` sets `merge=union` on it, so concurrent appends from different machines merge without conflicts; duplicate ids are ignored on load.

## Weekly schedule (Linux)

`scripts/weekly.sh` pulls the repo, runs `app sync` (downloads every playlist under `[schedule] playlists` in `config.toml`), then commits and pushes `songs.jsonl` only. It holds a `flock` so runs never overlap, refuses to run if other tracked files have local changes, commits whatever was downloaded even if a playlist fails, and sends a Gotify alert on any failure when `GOTIFY_URL` and `GOTIFY_TOKEN` are set.

One-time setup on the Linux machine:

1. Create an SSH key and add it to this repo as a deploy key with **write access** (Settings, Deploy keys), then clone over SSH.
2. Copy `config.example.toml` to `config.toml` and set `destination` and `[schedule] playlists`.
3. Add a crontab entry (`crontab -e`), using absolute paths since cron's `PATH` is minimal. The log output goes to stderr, which the redirect captures:

```cron
0 3 * * 0  UV=/home/USER/.local/bin/uv GOTIFY_URL=https://gotify.example.com GOTIFY_TOKEN=xxxx /path/to/JiosaavnDownloader/scripts/weekly.sh >> /path/to/weekly.log 2>&1
```

## Development

```bash
uv sync --extra test
uv run pytest -q                 # offline tests
uv run pytest -m live            # also hits the real API
```

## License

See LICENSE.

## Contact

Arun Kishore - [@rpakishore](mailto:pypi@rpakishore.co.in)

## Acknowledgements

- [saavn.sumit.co](https://github.com/sumitkolhe/jiosaavn-api)
