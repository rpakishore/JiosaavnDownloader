"""Command line entry point: ``app [options] sync|playlist|song|search``."""

import argparse
import logging
import shutil
from collections import Counter
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path

from jiosaavn.api import SaavnClient
from jiosaavn.cache import Cache
from jiosaavn.config import Config, load_config
from jiosaavn.download import download
from jiosaavn.notify import gotify
from jiosaavn.song import Song

log = logging.getLogger(__name__)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app", description="Download Jiosaavn songs as tagged mp3 files.")
    parser.add_argument("--config", type=Path, default=Path("config.toml"), help="config file (default: config.toml)")
    parser.add_argument("--dest", type=Path, help="destination folder (default: paths.destination in the config)")
    parser.add_argument("--dry-run", action="store_true", help="list what would be downloaded, change nothing")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    commands.add_parser("sync", help="download the playlists listed in the config")
    commands.add_parser("playlist", help="download a playlist").add_argument("target", metavar="ID_OR_URL")
    commands.add_parser("song", help="download a single song").add_argument("url", metavar="URL")
    search = commands.add_parser("search", help="download the top search results")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10, help="number of results (default: 10)")
    return parser


def _download_all(songs: Iterable[Song], cache: Cache, dest: Path, dry_run: bool, config: Config) -> Counter:
    """Download every song not yet in the cache. One failing song never stops the rest."""
    counts: Counter = Counter()
    for song in songs:
        if song.id in cache:
            log.debug("skip (cached): %s", song.filename)
            counts["skipped"] += 1
            continue
        if dry_run:
            log.info("dry-run, would download: %s", song.filename)
            counts["downloaded"] += 1
            continue
        try:
            path = download(song, dest)
            cache.add(song, path, datetime.now())
            gotify(
                config.gotify_url,
                config.gotify_token,
                f"[Jiosaavn]{song.name}",
                f"Album: {song.album}\n\n ![]({song.image_url})",
            )
            log.info("downloaded: %s", song.filename)
            counts["downloaded"] += 1
        except Exception as exc:
            log.error("failed: %s: %s", song.filename, exc, exc_info=log.isEnabledFor(logging.DEBUG))
            counts["failed"] += 1
    return counts


def _sources(args: argparse.Namespace, playlists: Iterable[str], client: SaavnClient) -> list[Callable[[], list[Song]]]:
    """One fetch callable per thing to download, so each can fail on its own."""
    match args.command:
        case "sync":
            return [lambda p=p: client.playlist(p) for p in playlists]
        case "playlist":
            return [lambda: client.playlist(args.target)]
        case "song":
            return [lambda: [client.song(args.url)]]
        case _:
            return [lambda: client.search(args.query, args.limit)]


def _run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    dest = args.dest or config.destination
    if args.command == "sync" and not config.playlists:
        log.error("no playlists configured: set schedule.playlists in %s", args.config)
        return 2
    if dest is None:
        log.error("no destination: pass --dest or set paths.destination in %s", args.config)
        return 2
    if not args.dry_run and shutil.which("ffmpeg") is None:
        log.error("ffmpeg not found on PATH")
        return 2

    client, cache = SaavnClient(), Cache(config.db_path)
    counts: Counter = Counter()
    for fetch in _sources(args, config.playlists, client):
        try:
            songs = fetch()
        except Exception as exc:
            log.error("could not fetch songs: %s", exc, exc_info=args.verbose)
            counts["failed"] += 1
            continue
        counts += _download_all(songs, cache, dest, args.dry_run, config)

    log.info("%sdownloaded=%d skipped=%d failed=%d", "dry-run: " * args.dry_run,
             counts["downloaded"], counts["skipped"], counts["failed"])
    return 1 if counts["failed"] else 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        return _run(args)
    except KeyboardInterrupt:
        log.warning("interrupted")
        return 130
