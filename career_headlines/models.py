"""The single data structure that flows through the whole pipeline.

Every stage takes a list of :class:`Article` and returns a list of
:class:`Article`. Keeping one shape from fetch to render is what makes the
pipeline easy to follow (and easy to test).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    """A single news item, enriched as it moves through the pipeline."""

    title: str
    url: str
    source: str            # human-readable name, e.g. "WonkHE"
    category: str          # thematic group, e.g. "Higher / Further Education"
    published: datetime | None = None   # timezone-aware if we could parse it
    raw_summary: str = ""  # description/summary as it came from the feed

    # Filled in by later stages:
    one_liner: str = ""    # Claude's one-sentence summary (render uses this)
    ai_related: bool = False  # flagged by the keyword filter for a badge

    def best_text(self) -> str:
        """Text used for keyword matching and as a summarise fallback."""
        return f"{self.title}. {self.raw_summary}".strip()
