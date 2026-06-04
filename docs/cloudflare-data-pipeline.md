# ZazaSync Cloudflare Data Pipeline Plan

Author: **Manus AI**  
Status: Draft implementation prepared on a feature branch.  
Scope: Cloudflare Worker, Cloudflare D1, scheduled SQDC public snapshot collection, cached public API, watchlist storage, and email alerts.

## Executive summary

This repository now contains a Cloudflare-native implementation path for making `zazasync.com` read from a controlled local cache instead of scraping SQDC during public user browsing. The proposed production flow is **scheduled collection → D1 snapshot database → change detection → cached public API → watchlist alerts**. This keeps the public website fast, reduces dependency on SQDC page latency, and avoids turning user traffic into direct traffic against SQDC.

The implementation is intentionally conservative. The scheduled crawler uses a clear user agent, a small maximum page limit per run, and a minimum interval guard. It stores only public snapshot evidence and queues alerts only when a product or inventory row changes to an alertable state.

## Target architecture

| Layer | Cloudflare component | Purpose |
|---|---|---|
| **Scheduled collection** | Worker cron trigger | Runs every two hours by default and collects a limited public snapshot from SQDC pages. |
| **Snapshot database** | D1 database named `zazasync_snapshot` | Stores products, stores, current inventory rows, crawl logs, change events, watchlists, users, and alert history. |
| **Change detector** | Worker code during crawl | Compares new product, price, and inventory states against the previous D1 snapshot. |
| **Public read API** | Worker HTTP routes | Serves `/api/products`, `/api/products/:slug`, and `/api/watchlist` from D1 only. |
| **Alerts** | Worker + Resend API | Queues restock alerts and sends emails when `RESEND_API_KEY` and `ALERTS_ENABLED=true` are configured. |
| **Deployment** | GitHub Actions + Wrangler | Type-checks, applies D1 migrations, and deploys the Worker on pushes to `main`. |

## Files added

| File | Purpose |
|---|---|
| `package.json` | Adds Wrangler, TypeScript, and deployment scripts. |
| `tsconfig.json` | Adds strict TypeScript configuration for Cloudflare Workers. |
| `wrangler.jsonc` | Defines the `zazasync` Worker, cron schedule, D1 binding, and environment variables. |
| `migrations/0001_zazasync_snapshot_schema.sql` | Creates D1 tables for crawl runs, products, stores, inventory, changes, users, watchlists, and alerts. |
| `src/worker.ts` | Worker entry point for HTTP and scheduled events. |
| `src/crawler/sqdc.ts` | Conservative SQDC public snapshot crawler and parser. |
| `src/db/repository.ts` | D1 repository functions and change-detection persistence. |
| `src/http/router.ts` | Cached product API, watchlist API, admin crawl route, and health route. |
| `src/email/resend.ts` | Email alert sender for queued restock alerts. |
| `.github/workflows/cloudflare-worker.yml` | GitHub Actions validation and deployment workflow. |

## Required Cloudflare resources

The current account previously showed a Worker named `zazasync` and one unrelated or empty D1 database named `ams_invoices`. The new pipeline should use a dedicated D1 database named `zazasync_snapshot` so invoices and inventory intelligence do not get mixed.

| Resource | Required? | Notes |
|---|---:|---|
| Worker `zazasync` | Yes | Existing Worker can be replaced only after reviewing the currently deployed production source or after creating a safe staging Worker first. |
| D1 `zazasync_snapshot` | Yes | Must be created, then its `database_id` must replace the placeholder in `wrangler.jsonc`. |
| D1 `zazasync_snapshot_staging` | Recommended | Used for staging validation before touching production. |
| KV | Optional | Not required in the first version because D1 stores both snapshots and metadata. |
| R2 | No | Not required unless product images or raw crawl artifacts need to be archived later. |

## Required GitHub secrets

| Secret | Required? | Purpose |
|---|---:|---|
| `CLOUDFLARE_API_TOKEN` | Yes | Allows GitHub Actions to apply migrations and deploy the Worker. The token should be scoped only to the target account and Worker/D1 resources. |
| `CLOUDFLARE_ACCOUNT_ID` | Yes | Identifies the Cloudflare account for Wrangler. |
| `RESEND_API_KEY` | Required for live alerts | Should be added to Cloudflare Worker secrets with `wrangler secret put RESEND_API_KEY`, not stored in GitHub. |
| `ADMIN_API_TOKEN` | Recommended | Protects manual admin routes such as `/api/admin/crawl`. |

## Setup sequence

### 1. Create a staging D1 database

Create `zazasync_snapshot_staging` first. Put the returned database ID into `wrangler.jsonc` under `env.staging.d1_databases[0].database_id`.

```bash
npx wrangler d1 create zazasync_snapshot_staging
```

### 2. Create the production D1 database

Create `zazasync_snapshot` only after staging succeeds. Put the returned database ID into the production `d1_databases[0].database_id` field.

```bash
npx wrangler d1 create zazasync_snapshot
```

### 3. Apply migrations

Apply schema migrations before the first deployment.

```bash
npm run db:migrate:remote
```

For staging:

```bash
npx wrangler d1 migrations apply ZAZASYNC_DB --env staging --remote
```

### 4. Configure Worker secrets

Email alerts should remain disabled until the database and watchlist flow are tested.

```bash
npx wrangler secret put ADMIN_API_TOKEN
npx wrangler secret put RESEND_API_KEY
npx wrangler secret put ALERTS_ENABLED
```

Set `ALERTS_ENABLED` to `false` for staging and first production deploy. Change it to `true` only after verifying that queued alerts are correct.

### 5. Deploy staging

```bash
npm run deploy:staging
```

Then run a manual crawl with an admin token:

```bash
curl -X POST https://zazasync-staging.<your-subdomain>.workers.dev/api/admin/crawl \
  -H "Authorization: Bearer $ADMIN_API_TOKEN"
```

### 6. Validate cached reads

Check these endpoints before routing public pages to them.

```bash
curl https://zazasync-staging.<your-subdomain>.workers.dev/api/health
curl https://zazasync-staging.<your-subdomain>.workers.dev/api/products?limit=10
```

### 7. Deploy production

Production deployment should happen only after confirming that the current `zazasync.com` Worker source has been backed up or that the new Worker is deployed to a staging route first.

```bash
npm run deploy
```

## Safety guardrails

The crawler should remain polite and conservative. It should not bypass login, age gates, CAPTCHAs, bot protections, or access controls. It should collect only public web data, identify itself with a clear user agent, and serve ZazaSync users from the D1 cache instead of triggering SQDC fetches per visitor.

| Guardrail | Current implementation |
|---|---|
| User-triggered scraping avoided | Public routes read only D1. |
| Scheduled batch collection | Worker cron runs every two hours by default. |
| Max pages per run | `CRAWL_MAX_PAGES_PER_RUN=20` by default. |
| Minimum interval | `CRAWL_MIN_INTERVAL_MINUTES=120` by default. |
| Manual crawl protected | `/api/admin/crawl` requires `ADMIN_API_TOKEN`. |
| Alerts disabled by default | `ALERTS_ENABLED` is false unless configured. |
| Public accuracy language | Use “latest captured snapshot,” “last checked,” and “availability evidence,” not guaranteed real-time claims. |

## Important limitation

The current crawler is a starter implementation. SQDC page structure and store-level availability behavior must be validated with a staging crawl. If SQDC exposes inventory through client-side JSON or a store-specific endpoint, the parser should be upgraded to use that stable public response format instead of generic HTML text parsing. Do not scale crawl frequency until staging confirms reliable parsing and acceptable request volume.

## Recommended next decision

Before deploying this to production, choose one of these paths:

| Option | Recommendation | Why |
|---|---|---|
| **Staging-first deployment** | Strongly recommended | Safest. Creates D1 staging, deploys `zazasync-staging`, validates crawler output, then promotes. |
| **Direct production replacement** | Not recommended | Risky because the deployed `zazasync` Worker source could not be recovered through the connector. |
| **Manual code handoff only** | Acceptable if GitHub/Cloudflare write access is not ready | Keeps the implementation ready but avoids production changes. |
