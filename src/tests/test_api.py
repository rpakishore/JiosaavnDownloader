import copy
from unittest.mock import MagicMock, patch

import pytest
import requests

from jiosaavn.api import SaavnClient, parse_song
from jiosaavn.song import Song

SONG_DICT = {
    "id": "abc123",
    "name": "Naa Ready (From &quot;Leo&quot;)",
    "year": "2023",
    "album": {"id": "1", "name": "Soundtrack (From &quot;Leo&quot;)"},
    "artists": {
        "primary": [{"name": "Anirudh Ravichander"}],
        "all": [{"name": "Anirudh Ravichander"}, {"name": "Vishal Dadlani"}],
    },
    "image": [
        {"quality": "50x50", "url": "http://img/50.jpg"},
        {"quality": "500x500", "url": "http://img/500.jpg"},
        {"quality": "150x150", "url": "http://img/150.jpg"},
    ],
    "downloadUrl": [
        {"quality": "96kbps", "url": "http://m/96.mp4"},
        {"quality": "320kbps", "url": "http://m/320.mp4"},
        {"quality": "160kbps", "url": "http://m/160.mp4"},
    ],
}


def song_dict(**overrides) -> dict:
    return {**copy.deepcopy(SONG_DICT), **overrides}


def fake_response(data, success=True, status=200):
    res = MagicMock()
    res.json.return_value = {"success": success, "data": data}
    if status >= 400:
        res.raise_for_status.side_effect = requests.HTTPError(str(status))
    return res


def client_returning(data, **kwargs):
    session = MagicMock()
    session.get.return_value = fake_response(data, **kwargs)
    return SaavnClient(session=session, min_interval=0), session


# parse_song


def test_parse_song_picks_best_quality_and_cleans_names():
    song = parse_song(SONG_DICT)
    assert song == Song(
        id="abc123",
        name="Naa Ready",
        album="Leo",
        year=2023,
        media_url="http://m/320.mp4",
        image_url="http://img/500.jpg",
        primary_artists=("Anirudh Ravichander",),
        artists=("Anirudh Ravichander", "Vishal Dadlani"),
    )


def test_parse_song_plain_album_is_kept():
    assert parse_song(song_dict(album={"name": "Leo"})).album == "Leo"


def test_parse_song_unescapes_html():
    d = song_dict(name="Say &quot;Hi&quot; &amp; Bye", album={"name": "Tom &amp; Jerry"})
    song = parse_song(d)
    assert song.name == 'Say "Hi" & Bye'
    assert song.album == "Tom & Jerry"


@pytest.mark.parametrize("year", ["", None, "unknown"])
def test_parse_song_unknown_year_is_zero(year):
    assert parse_song(song_dict(year=year)).year == 0


def test_parse_song_missing_year_is_zero():
    d = song_dict()
    del d["year"]
    assert parse_song(d).year == 0


def test_parse_song_no_image():
    assert parse_song(song_dict(image=[])).image_url == ""


@pytest.mark.parametrize("missing", ["id", "name", "album", "downloadUrl"])
def test_parse_song_missing_required_field_raises(missing):
    d = song_dict()
    del d[missing]
    with pytest.raises(KeyError):
        parse_song(d)


def test_parse_song_empty_download_urls_raises():
    with pytest.raises(ValueError):
        parse_song(song_dict(downloadUrl=[]))


# SaavnClient


def test_playlist_by_id():
    client, session = client_returning({"name": "P", "songs": [SONG_DICT]})
    songs = client.playlist("109815423")
    assert [s.id for s in songs] == ["abc123"]
    args, kwargs = session.get.call_args
    assert args[0] == "https://saavn.sumit.co/api/playlists"
    assert kwargs["params"] == {"id": "109815423", "limit": 1000}
    assert kwargs["timeout"] == 30


def test_playlist_by_link():
    client, session = client_returning({"songs": []})
    link = "https://www.jiosaavn.com/featured/x/abc"
    client.playlist(link)
    assert session.get.call_args.kwargs["params"] == {"link": link, "limit": 1000}


def test_playlist_by_www_link_gets_https_prefix():
    client, session = client_returning({"songs": []})
    client.playlist("www.jiosaavn.com/featured/x/abc")
    assert session.get.call_args.kwargs["params"]["link"] == "https://www.jiosaavn.com/featured/x/abc"


def test_playlist_skips_malformed_song_and_warns(caplog):
    bad = song_dict(id="bad")
    del bad["downloadUrl"]
    client, _ = client_returning({"songs": [bad, SONG_DICT, "garbage"]})
    with caplog.at_level("WARNING", logger="jiosaavn.api"):
        songs = client.playlist("1")
    assert [s.id for s in songs] == ["abc123"]
    assert sum("Skipping malformed song" in r.message for r in caplog.records) == 2


def test_song():
    client, session = client_returning([SONG_DICT])
    song = client.song("https://www.jiosaavn.com/song/x/y")
    assert song.id == "abc123"
    args, kwargs = session.get.call_args
    assert args[0] == "https://saavn.sumit.co/api/songs"
    assert kwargs["params"] == {"link": "https://www.jiosaavn.com/song/x/y"}


def test_song_not_found():
    client, _ = client_returning([])
    with pytest.raises(RuntimeError, match="No song found"):
        client.song("https://www.jiosaavn.com/song/x/y")


def test_search_passes_query_and_limit():
    client, session = client_returning({"results": [SONG_DICT]})
    songs = client.search("naa ready", limit=3)
    assert [s.name for s in songs] == ["Naa Ready"]
    args, kwargs = session.get.call_args
    assert args[0] == "https://saavn.sumit.co/api/search/songs"
    assert kwargs["params"] == {"query": "naa ready", "limit": 3}


def test_search_default_limit():
    client, session = client_returning({"results": []})
    client.search("x")
    assert session.get.call_args.kwargs["params"]["limit"] == 10


def test_success_false_raises_runtime_error():
    client, _ = client_returning(None, success=False)
    with pytest.raises(RuntimeError):
        client.search("x")


def test_http_error_propagates():
    client, _ = client_returning(None, status=500)
    with pytest.raises(requests.HTTPError):
        client.search("x")


def test_default_session_retries_on_server_errors():
    adapter = SaavnClient().session.get_adapter("https://saavn.sumit.co")
    assert adapter.max_retries.total == 3
    assert 429 in adapter.max_retries.status_forcelist


def test_throttle_sleeps_to_keep_min_interval():
    session = MagicMock()
    session.get.return_value = fake_response({"results": []})
    client = SaavnClient(session=session, min_interval=1.5)
    with patch("jiosaavn.api.time") as fake_time:
        fake_time.monotonic.side_effect = [100.0, 100.5, 102.0]
        client.search("a")  # first call: no sleep
        fake_time.sleep.assert_not_called()
        client.search("b")  # 0.5s elapsed since the first call -> sleep 1.0
        fake_time.sleep.assert_called_once_with(pytest.approx(1.0))


def test_throttle_does_not_sleep_when_gap_already_elapsed():
    session = MagicMock()
    session.get.return_value = fake_response({"results": []})
    client = SaavnClient(session=session, min_interval=1.5)
    with patch("jiosaavn.api.time") as fake_time:
        fake_time.monotonic.side_effect = [100.0, 110.0, 110.0]
        client.search("a")
        client.search("b")
        fake_time.sleep.assert_not_called()


@pytest.mark.live
def test_live_playlist():
    songs = SaavnClient().playlist("109815423")
    assert len(songs) > 10
    assert len({s.id for s in songs}) == len(songs)
