# Webmaster Start Here: ZazaSync Production Sync Backend v1

This folder is the production Supabase backend package for ZazaSync inventory,
stock-change detection, and email restock alerts.

## Current Decision

Use the Supabase pipeline in this folder as the authoritative inventory source.
Do not run it beside the older Cloudflare D1 prototype unless an intentional
migration plan prevents both systems from publishing conflicting stock data.

## What Is Enabled

- SQDC store synchronization
- Product catalog synchronization
- Store-level stock synchronization every 15 minutes
- Restock and out-of-stock event detection
- Email alert processing through Resend
- Supabase health records for delayed-data messaging

## What Is Disabled

The Anthropic vision fallback is optional and is not part of the initial launch.

- Leave `ANTHROPIC_API_KEY` empty.
- Do not install the `vision_fallback.py` cron job yet.
- Do not run `vision_fallback.py force`.

The primary sync, database, restock detection, and Resend email alerts work without
Anthropic. Vision can be enabled later as a paid degraded fallback.

## Required Private Configuration

Place these values in `backend/sqdc_sync/.env` on the VPS:

```dotenv
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
SUPABASE_DB_URL=...
RESEND_API_KEY=...
ALERT_FROM_EMAIL="ZazaSync Alerts <alerts@zazasync.com>"
PUBLIC_SITE_ORIGIN=https://zazasync.com
ANTHROPIC_API_KEY=
```

Never commit `.env`. Never put the Supabase service key, database URL, or Resend key
in frontend JavaScript.

## Deployment Order

1. Read `README.md` in this folder.
2. Copy `.env.example` to `.env` on the VPS and enter the private values.
3. Keep `ANTHROPIC_API_KEY` blank; `setup.sh` will omit the vision cron job.
4. Run `setup.sh`.
5. Confirm the schema was applied in Supabase.
6. Confirm stores and products were populated.
7. Compare several product/store availability results with SQDC.
8. Create a test user alert and verify one restock email.
9. Connect the frontend alert form through a trusted server endpoint or Supabase
   Edge Function. The browser must never receive the service key.
10. Show customer-friendly delayed-data language when the latest primary sync fails
    or becomes stale.

## Required Acceptance Evidence

Provide:

- Screenshot or query result showing populated `stores`, `products`, and `stock`
- Latest successful rows from `sync_status`
- One tested `false -> true` restock event
- One successfully delivered Resend email and its `alert_log` row
- VPS `crontab -l` output with primary stock, full sync, and alerts jobs
- Confirmation that the vision fallback cron job is not installed
- Confirmation that `.env` and all private keys are absent from GitHub

## Frontend Language

Never expose technical words such as scraper, API, VPS, cron, fallback, service key,
or sync infrastructure to customers.

Use:

> Availability information may be delayed. Please verify with SQDC before travelling.

Do not imply that vision fallback data is confirmed store-level availability.
