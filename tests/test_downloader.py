import pytest

from app.pipeline.downloader import parse_shortcode


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.instagram.com/reel/CxYz123-_a/", "CxYz123-_a"),
        ("https://instagram.com/reels/AbC123/", "AbC123"),
        ("https://www.instagram.com/p/DeF456/?img_index=1", "DeF456"),
        ("https://www.instagram.com/tv/GhI789/", "GhI789"),
        ("HTTPS://WWW.INSTAGRAM.COM/REEL/MixedCase1/", "MixedCase1"),
        ("https://www.instagram.com/reel/Trailing", "Trailing"),
    ],
)
def test_parse_shortcode_accepts_reel_urls(url, expected):
    assert parse_shortcode(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://www.instagram.com/jakis_uzytkownik/",
        "https://www.tiktok.com/@user/video/123",
        "https://youtube.com/watch?v=abc",
        "zwykly tekst",
        "",
    ],
)
def test_parse_shortcode_rejects_other_urls(url):
    assert parse_shortcode(url) is None
