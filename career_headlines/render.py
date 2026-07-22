"""Stage 5 — render the digest to a static HTML page.

We group the (already filtered, deduped, summarised) articles by their source
category, sort AI-related items to the top within each group, and hand the
result to a Jinja2 template. The output is a single self-contained HTML file
you can open locally or serve from GitHub Pages.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader

from .config import Settings
from .models import Article

log = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).with_name("templates")

# The order sections appear on the page. Any category not listed here is
# appended afterwards (alphabetically), so adding a new one never breaks.
SECTION_ORDER = [
    "Careers & Guidance",
    "Employment & Labour Market",
    "Skills, VET & Apprenticeships",
    "Higher & Further Education",
    "Future of Work",
    "Policy & International",
]


def _slug(text: str) -> str:
    """A URL/id-safe slug for section anchors and filter chips."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _group_by_category(
    articles: list[Article],
) -> list[tuple[str, str, list[Article]]]:
    groups: dict[str, list[Article]] = defaultdict(list)
    for article in articles:
        groups[article.category].append(article)

    # AI-related items first, then newest first within each category.
    def sort_key(a: Article):
        published = a.published.timestamp() if a.published else 0
        return (not a.ai_related, -published)

    def category_key(category: str):
        # Known sections keep their defined order; unknown ones sort after.
        return (SECTION_ORDER.index(category)
                if category in SECTION_ORDER else len(SECTION_ORDER), category)

    ordered = []
    for category in sorted(groups, key=category_key):
        items = sorted(groups[category], key=sort_key)
        ordered.append((category, _slug(category), items))
    return ordered


def render(articles: list[Article], settings: Settings, output: Path | str) -> Path:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        # Escape all variable output. `select_autoescape` keys on the file
        # extension, and our template ends in ".j2", so we enable it explicitly
        # — otherwise a headline containing &, < or > would break the HTML.
        autoescape=True,
    )
    template = env.get_template("digest.html.j2")

    now = datetime.now(ZoneInfo(settings.timezone))
    html = template.render(
        title=settings.site_title,
        generated_at=now.strftime("%A %d %B %Y, %H:%M %Z"),
        groups=_group_by_category(articles),
        total=len(articles),
        ai_count=sum(1 for a in articles if a.ai_related),
    )

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    log.info("wrote %s (%d stories)", output, len(articles))
    return output
