"""Stage 4 — one-line summaries via the Claude API.

This is the only stage that costs money, so it's written to be frugal:

  * We use an efficient model (Haiku by default — see sources.yaml).
  * Articles are sent in *batches* (default 10 per call), so ~30 stories cost
    ~3 API calls rather than 30.
  * A hard per-run cap (settings.max_items) is applied before we get here.

Graceful degradation: if ANTHROPIC_API_KEY isn't set (or the SDK isn't
installed), we fall back to a trimmed version of the feed's own description as
the one-liner. That means the page still builds — locally and in CI before
you've added the API key — just without Claude's polish.
"""

from __future__ import annotations

import json
import logging
import os

from .config import Settings
from .models import Article

log = logging.getLogger(__name__)

# max_tokens is small on purpose: we only ever want single sentences back.
_MAX_TOKENS = 1024

_SYSTEM_PROMPT = (
    "You write one-line summaries for a careers and employability professional's "
    "morning news digest. For each article you are given a number, a headline and "
    "(optionally) a short description. Write ONE crisp sentence per article: what it "
    "is and why it matters to someone working in career development, employability, "
    "higher/further education, VET, or AI in careers guidance. No preamble, no "
    "'This article'. Keep each under 30 words."
)


def _fallback_one_liner(article: Article) -> str:
    """Used when Claude isn't available: trim the feed's own description."""
    text = article.raw_summary or article.title
    text = " ".join(text.split())  # collapse whitespace
    if len(text) > 200:
        text = text[:197].rsplit(" ", 1)[0] + "…"
    return text


def _chunk(items: list[Article], size: int) -> list[list[Article]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _summarise_batch(client, model: str, batch: list[Article]) -> None:
    """Ask Claude for one line per article; write results onto the Articles."""
    lines = []
    for i, art in enumerate(batch):
        desc = art.raw_summary[:400]
        lines.append(f"[{i}] {art.title}\n{desc}".strip())
    user_prompt = (
        "Summarise each of the following articles. Reply with ONLY a JSON array "
        "of strings, one per article, in the same order (index [0] first):\n\n"
        + "\n\n".join(lines)
    )

    message = client.messages.create(
        model=model,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(block.text for block in message.content if block.type == "text")

    summaries = _parse_json_array(text)
    for art, summary in zip(batch, summaries):
        art.one_liner = summary.strip()
    # If Claude returned fewer items than expected, back-fill the rest.
    for art in batch:
        if not art.one_liner:
            art.one_liner = _fallback_one_liner(art)


def _parse_json_array(text: str) -> list[str]:
    """Pull a JSON array of strings out of the model's reply, defensively."""
    text = text.strip()
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            return [str(x) for x in data]
        except json.JSONDecodeError:
            pass
    log.warning("could not parse a JSON array from the model reply")
    return []


def summarise(articles: list[Article], settings: Settings) -> list[Article]:
    """Fill in ``one_liner`` on every article, via Claude or the fallback."""
    if not articles:
        return articles

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning("ANTHROPIC_API_KEY not set — using feed descriptions instead")
        for art in articles:
            art.one_liner = _fallback_one_liner(art)
        return articles

    try:
        import anthropic
    except ImportError:
        log.warning("anthropic SDK not installed — using feed descriptions")
        for art in articles:
            art.one_liner = _fallback_one_liner(art)
        return articles

    client = anthropic.Anthropic(api_key=api_key)
    batches = _chunk(articles, settings.summary_batch_size)
    log.info("summarising %d articles in %d Claude call(s)", len(articles), len(batches))

    for batch in batches:
        try:
            _summarise_batch(client, settings.model, batch)
        except Exception as exc:  # noqa: BLE001 — never let one batch break the run
            log.warning("summary batch failed (%s) — using fallback", exc)
            for art in batch:
                if not art.one_liner:
                    art.one_liner = _fallback_one_liner(art)

    return articles
