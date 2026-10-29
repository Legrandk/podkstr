import html
import re
import urllib.parse
from datetime import datetime

import feedparser

_RTVE_PAGE_SIZE = 20


def _extract_id(url: str) -> str:
    match = re.search(r"/(\d+)\.mp3", url)
    if match:
        return match.group(1)
    return url


def _parse_date(entry) -> str:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:3]).strftime("%Y-%m-%d")
        except Exception:
            pass
    return ""


def _is_rtve_api(url: str) -> bool:
    return "rtve.es/api/programas" in url


def _rtve_page_url(url: str, page: int) -> str:
    parsed = urllib.parse.urlparse(url)
    params = dict(urllib.parse.parse_qsl(parsed.query))
    params["size"] = str(_RTVE_PAGE_SIZE)
    params["page"] = str(page)
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(params)))


def _parse_entries(entries: list, fallback_image: str) -> list[dict]:
    episodes = []
    for entry in entries:
        audio_url = ""
        if entry.get("enclosures"):
            audio_url = entry.enclosures[0].get("href", "")
        if not audio_url:
            continue

        duration = ""
        if hasattr(entry, "itunes_duration"):
            duration = entry.itunes_duration or ""

        description = entry.get("summary", "")
        description = re.sub(r"<br\s*/?>|</p>|</li>", "\n", description, flags=re.IGNORECASE)
        description = html.unescape(re.sub(r"<[^>]+>", "", description)).strip()
        description = re.sub(r"\n{3,}", "\n\n", description)

        ep_image = ""
        if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            ep_image = entry.media_thumbnail[0].get("url", "")
        elif hasattr(entry, "itunes_image") and entry.itunes_image:
            ep_image = entry.itunes_image.get("href", "")
        if not ep_image:
            ep_image = fallback_image

        episodes.append({
            "id": _extract_id(audio_url),
            "title": html.unescape(entry.get("title", "")),
            "date": _parse_date(entry),
            "duration": duration,
            "audio_url": audio_url,
            "description": description,
            "image_url": ep_image,
        })
    return episodes


def fetch_feed(url: str) -> dict:
    feed = feedparser.parse(url)

    image_url = ""
    if hasattr(feed.feed, "image") and hasattr(feed.feed.image, "href"):
        image_url = feed.feed.image.href
    elif hasattr(feed.feed, "itunes_image") and feed.feed.itunes_image:
        image_url = feed.feed.itunes_image.get("href", "")

    episodes = _parse_entries(feed.entries, image_url)
    episodes.sort(key=lambda e: e["date"], reverse=True)

    return {
        "title": html.unescape(feed.feed.get("title", "")),
        "description": html.unescape(re.sub(r"<[^>]+>", "", feed.feed.get("description", ""))).strip(),
        "image_url": image_url,
        "episodes": episodes,
    }


def fetch_next_page(url: str, page: int, fallback_image: str = "") -> list[dict]:
    """Fetch a subsequent page of episodes for an RTVE feed. Returns [] if not applicable."""
    if not _is_rtve_api(url):
        return []
    feed = feedparser.parse(_rtve_page_url(url, page))
    return _parse_entries(feed.entries, fallback_image)
