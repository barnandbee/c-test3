"""Load configuration from ``sources.yaml``.

Everything you'd want to tweak day-to-day — which sites to pull, the topic
keywords, how far back to look, the model, the per-run item cap — lives in
that YAML file so you never have to touch the code to re-tune the digest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# sources.yaml sits next to this file, inside the package.
CONFIG_PATH = Path(__file__).with_name("sources.yaml")


@dataclass
class Source:
    """One place we pull headlines from."""

    name: str
    category: str
    feed: str          # RSS/Atom URL
    homepage: str = "" # optional, shown in the footer / used as a fallback link


@dataclass
class Settings:
    """Global knobs, all overridable from sources.yaml -> settings."""

    recency_hours: int = 48
    max_items: int = 40
    model: str = "claude-haiku-4-5"
    summary_batch_size: int = 10
    timezone: str = "Europe/London"
    site_title: str = "Career Headlines"


@dataclass
class Config:
    settings: Settings
    topic_keywords: list[str]
    ai_keywords: list[str]
    sources: list[Source] = field(default_factory=list)


def load_config(path: Path | str = CONFIG_PATH) -> Config:
    """Parse ``sources.yaml`` into a typed :class:`Config`."""

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

    settings = Settings(**(data.get("settings") or {}))

    keywords = data.get("keywords") or {}
    topic_keywords = [k.lower() for k in keywords.get("topics", [])]
    ai_keywords = [k.lower() for k in keywords.get("ai", [])]

    sources = [Source(**entry) for entry in data.get("sources", [])]

    return Config(
        settings=settings,
        topic_keywords=topic_keywords,
        ai_keywords=ai_keywords,
        sources=sources,
    )
