"""Stage 2 — keep only recent, on-topic items.

Two cheap, deterministic filters run here:

  * recency  — drop anything older than settings.recency_hours (items with no
               parseable date are kept, so we never silently lose a story).
  * relevance — keep an item only if its text mentions one of the topic
               keywords. This is the "is this actually careers/employability?"
               gate. Keyword matching is used (rather than a Claude call) so
               the filter is free, instant, and easy to reason about.

Each surviving Article is also flagged `ai_related` if it matches an AI
keyword, which the page uses to show a small badge.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from .config import Config
from .models import Article

log = logging.getLogger(__name__)


def _matches_any(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)


def is_recent(article: Article, cutoff: datetime) -> bool:
    if article.published is None:
        return True  # unknown date -> don't discard
    return article.published >= cutoff


def apply_filters(articles: list[Article], config: Config) -> list[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(
        hours=config.settings.recency_hours
    )

    kept: list[Article] = []
    for article in articles:
        if not is_recent(article, cutoff):
            continue

        text = article.best_text().lower()
        if not _matches_any(text, config.topic_keywords):
            continue

        article.ai_related = _matches_any(text, config.ai_keywords)
        kept.append(article)

    log.info(
        "filtered %d -> %d relevant items (last %dh)",
        len(articles),
        len(kept),
        config.settings.recency_hours,
    )
    return kept
