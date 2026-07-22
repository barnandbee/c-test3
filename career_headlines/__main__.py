"""Entry point — ties the five pipeline stages together.

    python -m career_headlines                 # build docs/index.html
    python -m career_headlines --output x.html  # build somewhere else
    python -m career_headlines --limit 15       # cap stories this run
    python -m career_headlines --check-sources  # just test the feeds

Read top to bottom, `main()` is the whole program: load config, then run
fetch -> filter -> dedupe -> cap -> summarise -> render.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import httpx

from .config import load_config
from .dedupe import deduplicate
from .fetch import fetch_all, fetch_source
from .filter import apply_filters
from .render import render
from .summarise import summarise

DEFAULT_OUTPUT = Path("docs/index.html")


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
    )


def check_sources() -> int:
    """Report which feeds currently return usable entries."""
    config = load_config()
    ok = 0
    with httpx.Client(timeout=httpx.Timeout(15.0)) as client:
        for source in config.sources:
            articles = fetch_source(source, client)
            status = f"OK  ({len(articles):>2})" if articles else "FAIL     "
            print(f"  {status}  {source.name}")
            ok += 1 if articles else 0
    print(f"\n{ok}/{len(config.sources)} sources returned entries.")
    return 0


def build(output: Path, limit: int | None) -> int:
    config = load_config()
    if limit is not None:
        config.settings.max_items = limit

    articles = fetch_all(config.sources)
    articles = apply_filters(articles, config)
    articles = deduplicate(articles)

    # Hard cap before the paid stage — the single biggest cost control.
    cap = config.settings.max_items
    if len(articles) > cap:
        articles = _cap_by_recency(articles, cap)

    articles = summarise(articles, config.settings)
    render(articles, config.settings, output)
    print(f"\nDone. Open {output} in your browser.")
    return 0


def _cap_by_recency(articles, cap: int):
    """Keep the `cap` most recent articles (items without a date sort last)."""
    from datetime import datetime, timezone

    oldest = datetime.min.replace(tzinfo=timezone.utc)
    articles.sort(key=lambda a: a.published or oldest, reverse=True)
    return articles[:cap]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="career_headlines")
    parser.add_argument(
        "--output", "-o", type=Path, default=DEFAULT_OUTPUT,
        help="where to write the HTML page (default: docs/index.html)",
    )
    parser.add_argument(
        "--limit", "-n", type=int, default=None,
        help="cap the number of stories this run (overrides sources.yaml)",
    )
    parser.add_argument(
        "--check-sources", action="store_true",
        help="test each feed and exit (no page is written, no API calls)",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)

    if args.check_sources:
        return check_sources()
    return build(args.output, args.limit)


if __name__ == "__main__":
    sys.exit(main())
