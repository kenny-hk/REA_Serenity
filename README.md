# Serenity Watch

An independent, public research dashboard for stock commentary by [Serenity (@aleabitoreddit)](https://x.com/aleabitoreddit). Inspired by the publicly described features of [Serenity Stock Tracker](https://capafy.ai/agent/serenity-stock-tracker/2521387714); independently implemented. Not affiliated with Serenity or Capafy. Not investment advice.

**Website:** https://kenny-hk.github.io/REA_Serenity/

## Current status

The dashboard and daily workflow are implemented. **Live X collection is not configured yet.** Anthropic has been replaced with OpenAI. Local Codex subscription classification was smoke-tested successfully with synthetic input; no test data was published. Choose the subscription or API mode below.

## Features

- Daily, rolling 7-day, 28-day, and 90-day windows, with a selectable end date (UTC).
- Search by ticker/company; filter by latest stance in the window; sort by recency, mention count, or ticker.
- Per-stock collected stance history, source links, concise paraphrases, evidence excerpts, and explicit risks.
- Bullish, bearish, neutral, and unclassified labels. No mention is never interpreted as neutral.
- CSV export, responsive layout, keyboard-accessible stock dialogs, and collection freshness/status.
- GitHub Actions collects daily at **00:17 UTC / 08:17 Hong Kong time**, commits derived data, and publishes GitHub Pages. Scheduled runs can be delayed by GitHub.

## Enable daily updates

### Recommended for subscription use: local Codex → GitHub Pages

This mode uses Codex's **Sign in with ChatGPT** session and included plan usage. It does not require an OpenAI API key or fall back to API billing. Plan limits still apply. Your computer runs classification and pushes derived data to GitHub; GitHub Actions publishes the public site.

Codex CLI is already installed and signed in with ChatGPT on the initial development machine. On another machine install the [official CLI](https://developers.openai.com/codex/cli) and run `codex login`, choosing ChatGPT. A recent CLI supporting `--ignore-user-config` and `--ephemeral` is required. `codex login status` must report ChatGPT, not API-key authentication.

On Windows, in this checkout:

```powershell
# One-time setup: prompts for the X token with hidden input.
.\scripts\run-local.ps1 -ConfigureXToken
# Collect, validate, commit the data, and push to GitHub Pages.
.\scripts\run-local.ps1
```

The X token is encrypted with Windows user protection in `%LOCALAPPDATA%\SerenityWatch\x-token.xml`, outside the repo. Git/GitHub authentication must already work. Start with a clean checkout. Optional `OPENAI_MODEL` selects a Codex-supported model; otherwise the CLI default is used. The wrapper runs manually; a Windows daily task has **not** been installed. A local daily task requires this computer to be awake and connected.

Codex runs from a temporary directory with user configuration ignored, shell tools and web search disabled, read-only sandboxing, a structured-output schema, and forced ChatGPT authentication. X/GitHub/API secrets are excluded from its environment. Source evidence is independently validated before saving. No cached ChatGPT credentials are exported to GitHub.

OpenAI's [non-interactive guidance](https://developers.openai.com/codex/noninteractive) says not to use its ChatGPT account-auth CI workflow for public/open-source repositories. Accordingly, subscription mode refuses to execute in GitHub Actions. A dedicated private runner is a separate deployment option, not configured here.

### Optional: entirely GitHub-hosted, separately billed OpenAI API

Only choose this if you want API billing. In [repository Actions settings](https://github.com/kenny-hk/REA_Serenity/settings/secrets/actions), add:

| Type | Name | Purpose |
| --- | --- | --- |
| Secret | `X_BEARER_TOKEN` | X API access to user lookup and user posts |
| Secret | `OPENAI_API_KEY` | OpenAI Platform API key; billed separately from ChatGPT |
| Variable | `OPENAI_MODEL` | A Responses API model supporting structured output, available to your account |
| Variable, optional | `MAX_POSTS_PER_RUN` | Classification cap; default 100 posts |

The public GitHub workflow explicitly selects `CLASSIFIER_PROVIDER=openai`; local runs default to `codex`. Neither mode switches billing automatically. If using local subscription mode, disable the collection schedule by setting repository variable `COLLECTION_MODE` to `local`; pushes continue to publish normally.

Do not put keys in source files, issues, or chat. **X API access is separate and can cost money in either mode.** The cap bounds classified posts, not the cost of fetching timeline pages. A first run requests up to 90 days of available posts and at most 32 pages of 100; provider limits may restrict history. Backlog is processed oldest-first over subsequent runs. See [X token setup](docs/x-token-setup.md).

Open [Actions → Collect and publish](https://github.com/kenny-hk/REA_Serenity/actions/workflows/publish.yml) and select **Run workflow**. Verify the collection log and the site's last-success timestamp. A push deploys code without consuming API calls. Missing credentials publish an awaiting-configuration status. A collection error preserves data and cursor, publishes error status, and marks the workflow failed after deployment.

GitHub Pages publishing source must be **GitHub Actions**. For a fork, enable Pages and Actions, then update the account-specific repository links in `site/index.html` and `site/app.js`.

## Data and methodology

The collector resolves the exact handle `aleabitoreddit`, fetches authored posts (including replies, excluding reposts), and requests extended text. It uses the official [X user-posts endpoint](https://docs.x.com/x-api/users/get-posts) and either signed-in Codex CLI or the [OpenAI Responses API](https://developers.openai.com/api/docs/guides/text). Full posts are processed transiently, not committed. Derived summaries, short evidence excerpts, post IDs, and links are public in `site/data/tracker.json`, including its Git history.

The classifier prompt is versioned in `scripts/update.py`. It separates stock stances, avoids treating a quotation as endorsement, and marks ambiguity as unclassified. It can identify unambiguous company names without cashtags, but ticker mapping remains AI-inferred. Evidence must be a literal substring of the fetched post. This verifies the excerpt's origin, **not** that the model's interpretation is correct. Human review of the linked post remains essential.

The cursor advances only after an entire selected batch validates. A failure leaves the previous cursor and records intact. Source text is untrusted data, and frontend values are HTML-escaped; CSV values are protected against formula injection.

## Limits and differences from the reference

- No access to Capafy's private dataset, prompts, backend, or historical labels; no exact parity is claimed.
- No price chart or live stock Q&A yet. The current stock dialog provides source-linked history and per-post risks, not an invented synthesized thesis.
- No image, video, linked-article, quoted-post expansion, or surrounding-thread analysis. This can miss important context.
- No guarantee of complete historical coverage, correct ticker identity, or perfect sentiment. Edited/deleted posts are not currently reconciled automatically; removal requests require an explicit data correction, including Git history if needed.
- Daily rather than hourly collection, as requested. GitHub may delay schedules and may disable scheduled workflows in inactive public repositories; monitor Actions and freshness.
- X collection and the optional OpenAI API mode have mock coverage but are not live-verified. Local Codex subscription mode passed a synthetic end-to-end classification smoke test.
- Dashboard logic is tested with a lightweight DOM stub; visual/browser interaction QA was unavailable in the authoring session.

## Local development

Python 3.12+; no pip dependencies or Node build step:

```sh
python -m unittest discover -s tests -v
python -m http.server 8000 --directory site
```

Open http://localhost:8000. For direct local collection, provide `X_BEARER_TOKEN`, sign Codex in with ChatGPT, then run `python scripts/update.py`. Use `scripts/run-local.ps1` to also commit and publish. For explicit API mode set `CLASSIFIER_PROVIDER=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL`.

Read [the REA assessment](docs/rea-assessment.md) for the tool review and project evidence boundaries.
