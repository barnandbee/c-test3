"""Stage 3 — collapse the same story reported by several sources.

Two passes:

  1. exact  — identical URL (after light normalisation) is an obvious dupe.
  2. fuzzy  — near-identical titles across sources are almost always the same
              story picked up by multiple outlets. We compare normalised
              titles with difflib and treat >0.85 similarity as a match.

When two items are duplicates we keep the earlier one (or the first seen if
dates are missing), so the original reporting tends to win.
"""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher

from .models import Article

log = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.85


def _normalise_title(title: str) -> str:
    """Lowercase, strip punctuation and collapse whitespace for comparison."""
    title = title.lower()
    title = re.sub(r"[^a-z0-9\s]", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def _normalise_url(url: str) -> str:
    """Drop query strings/fragments so tracking params don't defeat dedupe."""
    url = url.split("#", 1)[0].split("?", 1)[0]
    return url.rstrip("/").lower()


def _earlier(a: Article, b: Article) -> Article:
    """Prefer the article with the earlier publish date (fallback: keep a)."""
    if a.published and b.published:
        return a if a.published <= b.published else b
    return a


def deduplicate(articles: list[Article]) -> list[Article]:
    kept: list[Article] = []
    seen_urls: dict[str, int] = {}   # normalised url -> index in `kept`
    norm_titles: list[str] = []      # normalised title per kept article

    for article in articles:
        url_key = _normalise_url(article.url)
        if url_key in seen_urls:
            idx = seen_urls[url_key]
            kept[idx] = _earlier(kept[idx], article)
            continue

        norm_title = _normalise_title(article.title)
        dupe_idx = None
        for i, existing in enumerate(norm_titles):
            if SequenceMatcher(None, norm_title, existing).ratio() >= SIMILARITY_THRESHOLD:
                dupe_idx = i
                break

        if dupe_idx is not None:
            kept[dupe_idx] = _earlier(kept[dupe_idx], article)
            continue

        seen_urls[url_key] = len(kept)
        norm_titles.append(norm_title)
        kept.append(article)

    log.info("deduplicated %d -> %d unique stories", len(articles), len(kept))
    return kept
