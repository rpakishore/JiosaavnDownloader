import dataclasses

import pytest

from jiosaavn.song import Song, clean_title, sanitize


def make_song(**overrides) -> Song:
    fields = dict(
        id="1",
        name="Naa Ready",
        album="Leo",
        year=2023,
        media_url="http://m",
        image_url="",
        primary_artists=("A",),
        artists=("A", "B"),
    )
    return Song(**{**fields, **overrides})


def test_filename():
    assert make_song().filename == "Naa Ready-Leo(2023).mp3"


def test_filename_unknown_year():
    assert make_song(name="X", album="Y", year=0).filename == "X-Y().mp3"


def test_filename_is_sanitized():
    assert make_song(name='A/B: "C"?').filename == "AB C-Leo(2023).mp3"


def test_song_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        make_song().name = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("plain", "plain"),
        ("a\\b/c:d*e?f\"g<h>i|j", "abcdefghij"),
        ("nul\0byte\x01\x1f", "nulbyte"),
        ("name. . ", "name"),
        ("  padded  ", "padded"),
        ("CON", "__CON"),
        ("LPT9", "__LPT9"),
        ("con", "con"),
        ("", "__"),
        ("...", "__"),
        ("é", "é"),  # NFKD
        ("a\uff1ab", "ab"),  # fullwidth colon normalizes to a colon and is then dropped
        ("Tamil தமிழ்.mp3", "Tamil தமிழ்.mp3"),
    ],
)
def test_sanitize(raw, expected):
    assert sanitize(raw) == expected


def test_sanitize_truncates_keeping_extension():
    out = sanitize("a" * 300 + ".mp3")
    assert len(out) == 255
    assert out.endswith(".mp3")


def test_sanitize_truncates_without_extension():
    out = sanitize("a" * 300)
    assert out == "a" * 255


def test_sanitize_truncation_strips_trailing_dots():
    assert sanitize("a" * 254 + " b") == "a" * 254


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Naa Ready", ("Naa Ready", None)),
        ('Naa Ready (From "Leo")', ("Naa Ready", "Leo")),
        ("Naa Ready (From &quot;Leo&quot;)", ("Naa Ready", "Leo")),
        ("Say &quot;Hi&quot;", ('Say "Hi"', None)),
        ('  Leo (From "Leo")  ', ("Leo", "Leo")),
        ("Tom &amp; Jerry", ("Tom & Jerry", None)),
        ('Trailing (From "Leo") x', ('Trailing (From "Leo") x', None)),
    ],
)
def test_clean_title(raw, expected):
    assert clean_title(raw) == expected
