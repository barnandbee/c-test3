"""Stage 1 — fetch each source's feed and normalise it into Articles.

Design choice: fetching is *resilient*. A source that times out, 404s, or
serves malformed XML is logged and skipped — one broken feed never breaks the
whole digest. That's what lets the source list in sources.yaml stay a living,
editable document rather than something that has to be perfect.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import feedparser
import httpx
from dateutil import parser as date_parser

from .config import Source
from .models import Article

log = logging.getLogger(__name__)

# A polite, real-looking User-Agent — some feeds reject the default one.
_HEADERS = {
    "User-Agent": (
        "CareerHeadlines/0.1 (+https://github.com/) "
        "personal-news-digest"
    )
}
_TIMEOUT = httpx.Timeout(15.0)


def _parse_date(entry) -> datetime | None:
    """Best-effort published date, always returned timezone-aware (UTC)."""
    # feedparser pre-parses common formats into a struct_time for us.
    for attr in ("published_parsed", "updated_parsed"):
        value = getattr(entry, attr, None)
        if value:
            return datetime(*value[:6], tzinfo=timezone.utc)
    # Fall back to parsing the raw string ourselves.
    for attr in ("published", "updated"):
        raw = entry.get(attr)
        if raw:
            try:
                dt = date_parser.parse(raw)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except (ValueError, OverflowError):
                pass
    return None


def _clean(text: str) -> str:
    """Feed summaries often contain HTML; strip tags to plain text."""
    from bs4 import BeautifulSoup

    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)


def fetch_source(source: Source, client: httpx.Client) -> list[Article]:
    """Fetch one feed. Returns [] on any failure (logged)."""
    try:
        resp = client.get(source.feed, headers=_HEADERS, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("skip %-40s (fetch failed: %s)", source.name, exc)
        return []

    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        log.warning("skip %-40s (no valid feed entries)", source.name)
        return []

    articles: list[Article] = []
    for entry in parsed.entries:
        title = (entry.get("title") or "").strip()
        url = (entry.get("link") or "").strip()
        if not title or not url:
            continue
        articles.append(
            Article(
                title=title,
                url=url,
                source=source.name,
                category=source.category,
                published=_parse_date(entry),
                raw_summary=_clean(entry.get("summary", "")),
            )
        )

    log.info("ok   %-40s (%d items)", source.name, len(articles))
    return articles


def fetch_all(sources: list[Source]) -> list[Article]:
    """Fetch every source and return the combined list of Articles."""
    articles: list[Article] = []
    with httpx.Client(timeout=_TIMEOUT) as client:
        for source in sources:
            articles.extend(fetch_source(source, client))
    log.info("fetched %d articles from %d sources", len(articles), len(sources))
    return articles
