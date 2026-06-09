# ZazaSync Production Sync

This folder contains the server-side Supabase inventory pipeline for ZazaSync:

- `sqdc_sync.py`: stores, product catalog, stock, and stock-change detection
- `vision_fallback.py`: paid degraded fallback when the primary inventory response breaks
- `alerts.py`: email delivery for matching restock alerts
- `schema.sql`: Supabase tables, indexes, views, RLS, and public read policies
- `setup.sh`: first installation and cron configuration on a Linux VPS

Webmaster: begin with
[`WEBMASTER_START_HERE.md`](./WEBMASTER_START_HERE.md), then use this document for
the complete technical setup.

The frontend reads Supabase. It must never display internal terms such as scraper,
API, VPS, cron, fallback, or service key.

## Important Architecture Decision

This package is a complete Supabase-based pipeline. The repository also contains an
older Cloudflare Worker/D1 prototype. Before production deployment, choose one
authoritative inventory database. Do not let two independent jobs publish conflicting
stock states.

For the current ZazaSync frontend described in the implementation brief, Supabase is
the intended source of truth.

## Requirements

- Linux VPS with Python 3.10 or newer
- `python3-venv`, `psql`, and `crontab`
- Supabase project and direct or pooler PostgreSQL connection string
- Resend account with `alerts@zazasync.com` verified for email alerts
- Anthropic key only if the vision fallback is enabled
- Permission to access and process the upstream data, plus monitoring for upstream
  format or policy changes

## First Setup

```bash
cd /home/user/zazasync/backend/sqdc_sync
cp .env.example .env
nano .env
chmod +x setup.sh
./setup.sh
```

`SUPABASE_DB_URL` is required only for applying `schema.sql`. The Supabase service
key cannot execute database DDL through the REST API.

The setup script:

1. Creates `venv/`.
2. Installs Python packages and Playwright Chromium.
3. Applies `schema.sql`.
4. Runs `stores`, `products`, then `full`.
5. installs the managed cron jobs.

If Chromium cannot launch on the VPS, install its Linux system dependencies:

```bash
sudo venv/bin/playwright install-deps chromium
venv/bin/playwright install chromium
```

## Environment

Never commit `.env`. Keep service credentials on the VPS only.

```dotenv
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_SERVICE_KEY=...
SUPABASE_DB_URL=postgresql://...
ANTHROPIC_API_KEY=...
RESEND_API_KEY=...
ALERT_FROM_EMAIL="ZazaSync Alerts <alerts@zazasync.com>"
PUBLIC_SITE_ORIGIN=https://zazasync.com
```

Send production secrets through a secure secret-sharing channel, not source control
or ordinary email. Rotate a key immediately if it is exposed.

## Manual Commands

```bash
venv/bin/python sqdc_sync.py stores
venv/bin/python sqdc_sync.py products
venv/bin/python sqdc_sync.py stock
venv/bin/python sqdc_sync.py full

venv/bin/python vision_fallback.py
venv/bin/python vision_fallback.py force
venv/bin/python vision_fallback.py test

venv/bin/python alerts.py
```

Vision `test` mode opens one visible category, prints a sample, and does not write to
Supabase. `force` can create significant Anthropic usage charges and should be used
deliberately.

## Cron Schedule

`setup.sh` installs:

```cron
*/15 * * * * sqdc_sync.py stock
0 3 * * * sqdc_sync.py full
*/5 * * * * alerts.py
```

It adds `vision_fallback.py` every 30 minutes only when a real
`ANTHROPIC_API_KEY` is present. With the key blank, vision remains disabled.

Each command uses a non-blocking Linux process lock. If an earlier run is still
active, the next overlapping run exits without changing data.

## Stock and Alerts

The first stock observation establishes a baseline and does not generate a restock
event. Later transitions generate:

- `false -> true`: `restock`
- `true -> false`: `out_of_stock`

Only restock events are sent by email. Matching supports:

- one product at one store
- one product at any store (`store_id` is null)
- any product at one store (`product_sku` is null)

A successful user/product/store email is suppressed for 24 hours. Invalid addresses
are logged and deactivated. An event remains pending if a real delivery attempt fails,
so it can be retried.

## Frontend Contract

Public frontend reads:

- `products`
- `stock`
- `stores`
- `sync_status`
- `products_vision`

The private operational tables are:

- `restock_events`
- `user_alerts`
- `alert_log`

The service-role key is server-only. The browser must use the Supabase anonymous key
and the read policies in `schema.sql`.

The public alert form needs a small trusted server endpoint or Supabase Edge Function
that validates the email and requested product/store, then creates or updates
`user_alerts`. Never expose `SUPABASE_SERVICE_KEY` in frontend JavaScript. That signup
endpoint is an integration task for the webmaster; the queue processor in this folder
handles delivery after the row exists.

When the latest primary `sync_status` row is failed or old, the frontend should show
customer language such as:

> Availability information may be delayed. Please verify with SQDC before travelling.

The vision table is product-level degraded data. It does not provide reliable
store-by-store stock and must not be presented as equivalent to confirmed primary
inventory.

## Operations Checklist

```bash
tail -f logs/sync.log
tail -f logs/full.log
tail -f logs/fallback.log
tail -f logs/alerts.log
crontab -l
```

In Supabase, verify:

```sql
select * from sync_status;
select count(*) from stores;
select count(*) from products;
select count(*) from stock;
select * from pending_alerts order by detected_at;
```

## Troubleshooting

- **No stores or products:** inspect the response shape and category HTML; upstream
  structures can change.
- **All stock calls fail:** confirm the homepage cookie request succeeds and the
  request field remains exactly `Sku`.
- **Foreign-key errors:** run `sqdc_sync.py stores`, then `products`, before stock.
- **No email:** verify the Resend domain, sender address, API key, and `alert_log`.
- **Vision does not start:** run the Playwright dependency command above.
- **Data appears stale:** inspect `sync_status` and the corresponding log before
  changing or deleting last-known-good stock.

## Production Acceptance

Before calling this live:

1. Run a full sync and confirm realistic counts.
2. Manually compare several product/store results with SQDC.
3. Create a test alert and simulate one `false -> true` transition.
4. Confirm only one email is sent within 24 hours.
5. Force a primary failure and confirm old stock remains intact.
6. Verify the frontend delayed-data message contains no backend terminology.
7. Confirm `.env`, logs, and service credentials are absent from Git.
