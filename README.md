# Career Headlines

A personal daily digest covering **careers, employment, skills and the future
of work**. It pulls headlines from a defined set of UK, Australian and
international sources, filters and de-duplicates them, summarises each in one
line via the Claude API, and renders a clean static web page — grouped into
thematic sections with filter chips — that you can skim as part of your morning
routine.

Built to be **read**, not just run — the pipeline is split into small,
single-purpose modules so you can follow (and learn from) exactly what happens
at each step.

The page is organised into sections (Careers & Guidance · Employment & Labour
Market · Skills, VET & Apprenticeships · Higher & Further Education · Future of
Work · Policy & International), with filter chips to focus on one at a time and
an "AI" badge on AI-related stories, since that theme cuts across all of them.

---

## How it works

The pipeline is five stages. Each takes a list of articles and returns a list
of articles, so it reads straight down:

```
config      load the source list + settings        career_headlines/sources.yaml
  │
fetch       pull each RSS/Atom feed                 career_headlines/fetch.py
  │         (a broken feed is skipped, never fatal)
filter      keep recent, on-topic items             career_headlines/filter.py
  │         (48h window + topic keywords; flags AI stories)
dedupe      collapse the same story across sources  career_headlines/dedupe.py
  │
summarise   one-line summary per story via Claude   career_headlines/summarise.py
  │         (batched + capped to control cost)
render      write a static HTML page                career_headlines/render.py
```

`career_headlines/__main__.py` runs them in order.

## Quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Optional but recommended — add your key for real Claude summaries:
cp .env.example .env      # then edit .env
export ANTHROPIC_API_KEY=sk-ant-...

python -m career_headlines            # writes docs/index.html
open docs/index.html                  # (macOS; use xdg-open on Linux)
```

Without `ANTHROPIC_API_KEY` the page still builds — it just uses each feed's
own description instead of a Claude summary, so you can try everything first
and add the key later.

### Useful commands

```bash
python -m career_headlines --check-sources   # test every feed, no page/API calls
python -m career_headlines --limit 15        # cap stories this run
python -m career_headlines -o out.html       # write somewhere else
python -m career_headlines -v                # verbose logging
```

## Configuring it

Everything you'd tune day-to-day lives in
[`career_headlines/sources.yaml`](career_headlines/sources.yaml) — no code
changes needed:

- **`sources`** — add/remove a feed (name, category, feed URL).
- **`keywords.topics`** — what counts as "relevant".
- **`keywords.ai`** — what earns an "AI" badge.
- **`settings`** — recency window, per-run item cap, model, batch size, timezone.

Feed URLs are best-effort; a source whose feed is unreachable is skipped with a
warning (the run still succeeds). Run `--check-sources` to see which resolve and
correct any as needed.

## Cost

Defaults to **Claude Haiku 4.5** with batched calls and a hard per-run item cap
(`settings.max_items`). At ~20–40 one-line summaries a day that's on the order
of a cent or two per run.

## Publishing to GitHub Pages

A GitHub Actions workflow ([`.github/workflows/build.yml`](.github/workflows/build.yml))
builds the digest and deploys it to Pages — on a weekday-morning schedule, on
push, and on manual trigger. Two one-time repo settings are required:

1. **Add the API key** — *Settings → Secrets and variables → Actions → New
   repository secret* → name `ANTHROPIC_API_KEY`. (Optional at first: without
   it the page still deploys using feed descriptions, so you can confirm Pages
   works before adding the key.)
2. **Turn on Pages** — *Settings → Pages → Build and deployment → Source:
   **GitHub Actions***.

Then run it from the **Actions** tab ("Build & deploy Career Headlines" →
*Run workflow*), or let the schedule fire. The scheduled run is `0 6 * * 1-5`
(06:00 UTC — ~07:00 BST / 06:00 GMT, weekday mornings); adjust the cron in the
workflow if you want a different time.

> The Pages deploy runs only from `main` (the default branch), which is what the
> `github-pages` environment's protection rules allow. Develop on a feature
> branch, then merge to `main` to publish. A manual run dispatched from another
> branch will build but skip the deploy by design.

## Project layout

```
career_headlines/
  __main__.py        entry point (python -m career_headlines)
  config.py          load sources.yaml
  sources.yaml       ← the file you edit day-to-day
  models.py          the Article dataclass
  fetch.py           stage 1: feeds → Articles
  filter.py          stage 2: recency + topic relevance
  dedupe.py          stage 3: collapse duplicates
  summarise.py       stage 4: one-line summaries via Claude
  render.py          stage 5: Articles → HTML
  templates/
    digest.html.j2   the page template (light/dark, responsive)
.github/workflows/
  build.yml          scheduled build + GitHub Pages deploy
```

## Roadmap (deliberately out of v1)

Email/Slack delivery · fuller per-story synthesis or a "top 3" tier ·
priority ranking · a light Claude relevance pass · a historical archive.
