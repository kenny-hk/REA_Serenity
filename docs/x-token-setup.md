# Get the X Bearer Token

Checked against X documentation on 18 October 2026.

1. Open [console.x.com](https://console.x.com) and sign in with your own X account.
2. Complete developer registration, review the Developer Agreement, and explain the use case truthfully: an independent public dashboard summarizing stock commentary from `@aleabitoreddit`, with sentiment labels and links back to the posts.
3. Select **New App**. Name it **Serenity Watch** and provide the requested description/use case. If asked for a website, use `https://kenny-hk.github.io/REA_Serenity/`.
4. Open the app's **Keys and tokens** section. Find **Bearer Token** and choose **Generate** (or copy the token shown during app creation). The app-only Bearer Token reads public data; this tracker does not need user write permissions, DMs, or a user OAuth callback.
5. Save the token in your password manager immediately. X may only display it once. Regenerating a token invalidates its previous value.
6. Review the console's API credits/billing screen. A token authenticates the app but does not provide free data access. Ensure user lookup and user timeline reads are available and sufficiently funded. Set a spending limit where available.
7. For local subscription classification, run `.\scripts\run-local.ps1 -ConfigureXToken` and paste the token into the hidden prompt. For GitHub-hosted API classification, save it as repository Actions secret **X_BEARER_TOKEN** under Settings → Secrets and variables → Actions → New repository secret.

Do not paste the token in chat or commit it. Do not put `Bearer ` in the saved value; save just the token.

The X key is independent of OpenAI authentication. A ChatGPT subscription does not pay X's data costs. The current X pricing page lists $0.005 per post read and $0.010 per user read; check the console before purchase. For example, 1,000 unique post reads would be $5 at that rate, before user lookups or other calls. The collector's initial historical scan and later retries/backlog processing can fetch more posts than are classified in one run.

## Troubleshooting

- HTTP 401: check the copied token and whether it has been regenerated.
- HTTP 403: check your app/account access to the endpoint and any restrictions.
- HTTP 429: check rate limits and retry later.
- Credits/access error: check the console billing and usage details; a correctly generated token alone does not guarantee access.

## Official sources

- [Getting X API access](https://docs.x.com/x-api/getting-started/getting-access)
- [Generate an app-only Bearer Token](https://docs.x.com/fundamentals/authentication/oauth-2-0/bearer-tokens)
- [X API pricing](https://docs.x.com/x-api/getting-started/pricing)
