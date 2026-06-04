-- ZazaSync Cloudflare D1 schema
-- Purpose: serve zazasync.com from cached SQDC snapshots and support watchlist/email alerts.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS crawl_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL CHECK (status IN ('running', 'success', 'partial', 'failed')),
  pages_scanned INTEGER NOT NULL DEFAULT 0,
  products_seen INTEGER NOT NULL DEFAULT 0,
  inventory_rows_seen INTEGER NOT NULL DEFAULT 0,
  changes_detected INTEGER NOT NULL DEFAULT 0,
  alerts_queued INTEGER NOT NULL DEFAULT 0,
  error_json TEXT
);

CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_product_id TEXT NOT NULL UNIQUE,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  brand TEXT,
  category TEXT,
  product_url TEXT NOT NULL,
  image_url TEXT,
  price_cents INTEGER,
  thc TEXT,
  cbd TEXT,
  format TEXT,
  raw_json TEXT,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_last_seen ON products(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);

CREATE TABLE IF NOT EXISTS stores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  store_code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  city TEXT,
  region TEXT,
  address TEXT,
  raw_json TEXT,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_stores_region ON stores(region);

CREATE TABLE IF NOT EXISTS inventory_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('in_stock', 'low_stock', 'out_of_stock', 'unknown')),
  quantity_hint TEXT,
  evidence_text TEXT,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(product_id, store_id)
);

CREATE INDEX IF NOT EXISTS idx_inventory_product_status ON inventory_snapshots(product_id, status);
CREATE INDEX IF NOT EXISTS idx_inventory_store_status ON inventory_snapshots(store_id, status);
CREATE INDEX IF NOT EXISTS idx_inventory_last_seen ON inventory_snapshots(last_seen_at);

CREATE TABLE IF NOT EXISTS change_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  crawl_run_id INTEGER REFERENCES crawl_runs(id) ON DELETE SET NULL,
  product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
  store_id INTEGER REFERENCES stores(id) ON DELETE SET NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('new_product', 'price_change', 'restock', 'stock_loss', 'status_change', 'product_update')),
  previous_value TEXT,
  new_value TEXT,
  occurred_at TEXT NOT NULL,
  alertable INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_change_events_product ON change_events(product_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_change_events_type ON change_events(event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_change_events_alertable ON change_events(alertable, occurred_at DESC);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  email_verified_at TEXT,
  preferred_language TEXT NOT NULL DEFAULT 'fr-CA',
  age_confirmed_at TEXT,
  consent_version TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS watchlist_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  preferred_store_id INTEGER REFERENCES stores(id) ON DELETE SET NULL,
  alert_on_restock INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(user_id, product_id, preferred_store_id)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_product ON watchlist_items(product_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist_items(user_id);

CREATE TABLE IF NOT EXISTS alert_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  store_id INTEGER REFERENCES stores(id) ON DELETE SET NULL,
  change_event_id INTEGER REFERENCES change_events(id) ON DELETE SET NULL,
  channel TEXT NOT NULL CHECK (channel IN ('email')),
  recipient TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued', 'sent', 'failed', 'skipped')),
  provider_message_id TEXT,
  error_text TEXT,
  created_at TEXT NOT NULL,
  sent_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_alert_log_status ON alert_log(status, created_at);
CREATE INDEX IF NOT EXISTS idx_alert_log_user_product ON alert_log(user_id, product_id, created_at DESC);

CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

INSERT OR IGNORE INTO app_settings(key, value, updated_at)
VALUES
  ('schema_version', '0001', datetime('now')),
  ('crawler_enabled', 'true', datetime('now')),
  ('alerts_enabled', 'false', datetime('now'));
