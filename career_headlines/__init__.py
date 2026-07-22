"""Career Headlines — a personal daily digest of careers & employability news.

The package is deliberately split into small, single-purpose modules so the
pipeline reads top-to-bottom like a story:

    config      -> load the source list and settings (sources.yaml)
    fetch       -> pull each source's RSS/Atom feed into Article objects
    filter      -> keep only recent, on-topic items
    dedupe      -> collapse the same story reported by several sources
    summarise   -> ask the Claude API for a one-line summary of each item
    render      -> write a clean static HTML page

`python -m career_headlines` runs them in that order (see __main__.py).
"""

__version__ = "0.1.0"
