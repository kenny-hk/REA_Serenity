# Serenity Watch

An independent, public research dashboard for stock commentary by [Serenity (@aleabitoreddit)](https://x.com/aleabitoreddit). Inspired by the publicly described features of [Serenity Stock Tracker](https://capafy.ai/agent/serenity-stock-tracker/2521387714); independently implemented. Not affiliated with Serenity or Capafy. Not investment advice.

**Website:** https://kenny-hk.github.io/REA_Serenity/

## Current status

The dashboard and daily workflow are implemented. **Live collection is not configured yet.** The site deliberately contains no fabricated posts or sentiment. API-backed collection and classification require the credentials below and a successful run before this is a working live tracker.

## Features

- Daily, rolling 7-day, 28-day, and 90-day windows, with a selectable end date (UTC).
- Search by ticker/company; filter by latest stance in the window; sort by recency, mention count, or ticker.
- Per-stock collected stance history, source links, concise paraphrases, evidence excerpts, and explicit risks.
- Bullish, bearish, neutral, and unclassified labels. No mention is never interpreted as neutral.
- CSV export, responsive layout, keyboard-accessible stock dialogs, and collection freshness/status.
- GitHub Actions collects daily at **00:17 UTC / 08:17 Hong Kong time**, commits derived data, and publishes GitHub Pages. Scheduled runs can be delayed by GitHub.

## Enable daily updates

In [repository Actions settings](https://github.com/kenny-hk/REA_Serenity/settings/secrets/actions), add:

| Type | Name | Purpose |
| --- | --- | --- |
| Secret | `X_BEARER_TOKEN` | X API access to user lookup and user posts |
| Secret | `ANTHROPIC_API_KEY` | Claude API access for per-post stock extraction and classification |
| Variable | `ANTHROPIC_MODEL` | A Messages API model available to your account; explicitly selected by you |
| Variable, optional | `MAX_POSTS_PER_RUN` | Classification cap; default 100 posts |

Do not put keys in source files, issues, or chat. API access and usage can incur provider charges. The cap bounds classified posts, not the cost of fetching timeline pages. A first run requests up to 90 days of available posts and at most 32 pages of 100; provider limits may restrict history. Backlog is processed oldest-first over subsequent runs.

Open [Actions → Collect and publish](https://github.com/kenny-hk/REA_Serenity/actions/workflows/publish.yml) and select **Run workflow**. Verify the collection log and the site's last-success timestamp. A push deploys code without consuming API calls. Missing credentials publish an awaiting-configuration status. A collection error preserves data and cursor, publishes error status, and marks the workflow failed after deployment.

GitHub Pages publishing source must be **GitHub Actions**. For a fork, enable Pages and Actions, then update the account-specific repository links in `site/index.html` and `site/app.js`.

## Data and methodology

The collector resolves the exact handle `aleabitoreddit`, fetches authored posts (including replies, excluding reposts), and requests extended text. It uses the official [X user-posts endpoint](https://docs.x.com/x-api/users/get-posts) and [Claude Messages API](https://platform.claude.com/docs/en/api/messages/create). Full posts are processed transiently, not committed. Derived summaries, short evidence excerpts, post IDs, and links are public in `site/data/tracker.json`, including its Git history.

The classifier prompt is versioned in `scripts/update.py`. It separates stock stances, avoids treating a quotation as endorsement, and marks ambiguity as unclassified. It can identify unambiguous company names without cashtags, but ticker mapping remains AI-inferred. Evidence must be a literal substring of the fetched post. This verifies the excerpt's origin, **not** that the model's interpretation is correct. Human review of the linked post remains essential.

The cursor advances only after an entire selected batch validates. A failure leaves the previous cursor and records intact. Source text is untrusted data, and frontend values are HTML-escaped; CSV values are protected against formula injection.

## Limits and differences from the reference

- No access to Capafy's private dataset, prompts, backend, or historical labels; no exact parity is claimed.
- No price chart or live stock Q&A yet. The current stock dialog provides source-linked history and per-post risks, not an invented synthesized thesis.
- No image, video, linked-article, quoted-post expansion, or surrounding-thread analysis. This can miss important context.
- No guarantee of complete historical coverage, correct ticker identity, or perfect sentiment. Edited/deleted posts are not currently reconciled automatically; removal requests require an explicit data correction, including Git history if needed.
- Daily rather than hourly collection, as requested. GitHub may delay schedules and may disable scheduled workflows in inactive public repositories; monitor Actions and freshness.
- External feed/model calls have unit coverage with mocks but cannot be live-verified until credentials are configured.

## Local development

Python 3.12+; no pip dependencies or Node build step:

```sh
python -m unittest discover -s tests -v
python -m http.server 8000 --directory site
```

Open http://localhost:8000. To collect locally, provide the three environment variables above, then run `python scripts/update.py`.

Read [the REA assessment](docs/rea-assessment.md) for the tool review and project evidence boundaries.
