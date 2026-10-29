import pytest
from unittest.mock import patch, MagicMock
from podkstr.fetcher import fetch_feed, fetch_next_page, _extract_id, _parse_date, _is_rtve_api, _rtve_page_url

FIXTURE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Test &amp; Podcast</title>
    <description>A description with &amp; ampersand</description>
    <itunes:image href="https://example.com/cover.jpg"/>
    <item>
      <title>Episode 2 &amp; More</title>
      <enclosure url="https://ztnr.rtve.es/ztnr/67890.mp3" length="1000" type="audio/mpeg"/>
      <pubDate>Tue, 02 Jan 2024 12:00:00 GMT</pubDate>
      <itunes:duration>00:45:00</itunes:duration>
      <description>&lt;p&gt;Second episode description&lt;/p&gt;</description>
    </item>
    <item>
      <title>Episode 1</title>
      <enclosure url="https://ztnr.rtve.es/ztnr/12345.mp3" length="2000" type="audio/mpeg"/>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
      <itunes:duration>00:30:00</itunes:duration>
      <description>First episode description</description>
    </item>
    <item>
      <title>Episode Without Audio</title>
      <pubDate>Wed, 03 Jan 2024 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""


def test_fetch_feed_parses_title():
    import feedparser
    with patch("podkstr.fetcher.feedparser.parse", return_value=feedparser.parse(FIXTURE_RSS)):
        result = fetch_feed("http://fake.url/feed.rss")

    assert result["title"] == "Test & Podcast"


def test_fetch_feed_unescapes_html_in_title():
    import feedparser
    with patch("podkstr.fetcher.feedparser.parse", return_value=feedparser.parse(FIXTURE_RSS)):
        result = fetch_feed("http://fake.url/feed.rss")

    assert "&amp;" not in result["title"]


def test_fetch_feed_parses_description():
    import feedparser
    with patch("podkstr.fetcher.feedparser.parse", return_value=feedparser.parse(FIXTURE_RSS)):
        result = fetch_feed("http://fake.url/feed.rss")

    assert "ampersand" in result["description"]
    assert "&amp;" not in result["description"]


def test_fetch_feed_parses_image_url():
    import feedparser
    with patch("podkstr.fetcher.feedparser.parse", return_value=feedparser.parse(FIXTURE_RSS)):
        result = fetch_feed("http://fake.url/feed.rss")

    assert result["image_url"] == "https://example.com/cover.jpg"


def test_fetch_feed_skips_entries_without_enclosure():
    import feedparser
    with patch("podkstr.fetcher.feedparser.parse", return_value=feedparser.parse(FIXTURE_RSS)):
        result = fetch_feed("http://fake.url/feed.rss")

    titles = [ep["title"] for ep in result["episodes"]]
    assert "Episode Without Audio" not in titles


def test_fetch_feed_returns_two_valid_episodes():
    import feedparser
    with patch("podkstr.fetcher.feedparser.parse", return_value=feedparser.parse(FIXTURE_RSS)):
        result = fetch_feed("http://fake.url/feed.rss")

    assert len(result["episodes"]) == 2


def test_fetch_feed_sorts_episodes_most_recent_first():
    import feedparser
    with patch("podkstr.fetcher.feedparser.parse", return_value=feedparser.parse(FIXTURE_RSS)):
        result = fetch_feed("http://fake.url/feed.rss")

    dates = [ep["date"] for ep in result["episodes"]]
    assert dates == sorted(dates, reverse=True)


def test_fetch_feed_parses_episode_fields():
    import feedparser
    with patch("podkstr.fetcher.feedparser.parse", return_value=feedparser.parse(FIXTURE_RSS)):
        result = fetch_feed("http://fake.url/feed.rss")

    ep = result["episodes"][0]
    assert ep["id"] == "67890"
    assert ep["title"] == "Episode 2 & More"
    assert ep["date"] == "2024-01-02"
    assert ep["duration"] == "00:45:00"
    assert ep["audio_url"] == "https://ztnr.rtve.es/ztnr/67890.mp3"
    assert "image_url" in ep


def test_fetch_feed_episode_falls_back_to_feed_image_when_no_episode_image():
    import feedparser
    with patch("podkstr.fetcher.feedparser.parse", return_value=feedparser.parse(FIXTURE_RSS)):
        result = fetch_feed("http://fake.url/feed.rss")

    for ep in result["episodes"]:
        assert ep["image_url"] == "https://example.com/cover.jpg"


def test_fetch_feed_strips_html_from_episode_description():
    import feedparser
    with patch("podkstr.fetcher.feedparser.parse", return_value=feedparser.parse(FIXTURE_RSS)):
        result = fetch_feed("http://fake.url/feed.rss")

    ep = next(e for e in result["episodes"] if e["id"] == "67890")
    assert "<p>" not in ep["description"]
    assert "Second episode description" in ep["description"]


def test_extract_id_from_rtve_url():
    assert _extract_id("https://ztnr.rtve.es/ztnr/6086155.mp3") == "6086155"


def test_extract_id_from_url_with_path():
    assert _extract_id("https://example.com/audio/12345.mp3") == "12345"


def test_extract_id_returns_full_url_when_no_match():
    url = "https://example.com/audio/file-without-id"
    assert _extract_id(url) == url


def test_parse_date_returns_formatted_date():
    import time
    entry = MagicMock()
    entry.published_parsed = time.strptime("2024-01-15", "%Y-%m-%d")

    assert _parse_date(entry) == "2024-01-15"


def test_parse_date_returns_empty_string_when_no_date():
    entry = MagicMock(spec=[])

    assert _parse_date(entry) == ""


def test_is_rtve_api_returns_true_for_rtve_url():
    assert _is_rtve_api("http://www.rtve.es/api/programas/22270/audios.rss") is True


def test_is_rtve_api_returns_false_for_non_rtve_url():
    assert _is_rtve_api("https://feeds.example.com/podcast.rss") is False


def test_rtve_page_url_adds_size_and_page_params():
    url = "http://www.rtve.es/api/programas/22270/audios.rss"
    result = _rtve_page_url(url, 2)
    assert "size=20" in result
    assert "page=2" in result


def test_rtve_page_url_preserves_base_url():
    url = "http://www.rtve.es/api/programas/22270/audios.rss"
    result = _rtve_page_url(url, 0)
    assert "rtve.es/api/programas/22270/audios.rss" in result


def test_fetch_next_page_returns_episodes_for_rtve_url():
    import feedparser

    with patch("podkstr.fetcher.feedparser.parse", return_value=feedparser.parse(FIXTURE_RSS)):
        result = fetch_next_page("http://www.rtve.es/api/programas/22270/audios.rss", 1)

    assert len(result) == 2
    assert result[0]["id"] == "67890"


def test_fetch_next_page_requests_correct_page():
    import feedparser

    parsed = feedparser.parse(FIXTURE_RSS)
    captured = []

    def fake_parse(url):
        captured.append(url)
        return parsed

    with patch("podkstr.fetcher.feedparser.parse", side_effect=fake_parse):
        fetch_next_page("http://www.rtve.es/api/programas/22270/audios.rss", 3)

    assert "page=3" in captured[0]
    assert "size=20" in captured[0]


def test_fetch_next_page_returns_empty_list_for_non_rtve_url():
    result = fetch_next_page("https://feeds.example.com/podcast.rss", 1)
    assert result == []


def test_fetch_next_page_applies_fallback_image():
    import feedparser

    with patch("podkstr.fetcher.feedparser.parse", return_value=feedparser.parse(FIXTURE_RSS)):
        result = fetch_next_page(
            "http://www.rtve.es/api/programas/22270/audios.rss",
            1,
            fallback_image="https://example.com/cover.jpg",
        )

    for ep in result:
        assert ep["image_url"] == "https://example.com/cover.jpg"
