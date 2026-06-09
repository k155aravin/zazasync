BEGIN;

CREATE TABLE IF NOT EXISTS stores (
  store_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  city TEXT,
  address TEXT,
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
  sku TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  brand TEXT,
  category TEXT,
  price_cad NUMERIC(8,2),
  thc_pct NUMERIC(5,2),
  cbd_pct NUMERIC(5,2),
  format TEXT,
  image_url TEXT,
  product_url TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stock (
  product_sku TEXT NOT NULL REFERENCES products(sku) ON DELETE CASCADE,
  store_id TEXT NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
  in_stock BOOLEAN NOT NULL DEFAULT FALSE,
  quantity INTEGER,
  synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (product_sku, store_id)
);

CREATE TABLE IF NOT EXISTS restock_events (
  id BIGSERIAL PRIMARY KEY,
  product_sku TEXT NOT NULL REFERENCES products(sku) ON DELETE CASCADE,
  store_id TEXT NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
  event_type TEXT NOT NULL CHECK (event_type IN ('restock', 'out_of_stock')),
  detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  alerted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS user_alerts (
  id BIGSERIAL PRIMARY KEY,
  user_email TEXT NOT NULL,
  product_sku TEXT REFERENCES products(sku) ON DELETE CASCADE,
  store_id TEXT REFERENCES stores(store_id) ON DELETE CASCADE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE NULLS NOT DISTINCT (user_email, product_sku, store_id)
);

CREATE TABLE IF NOT EXISTS alert_log (
  id BIGSERIAL PRIMARY KEY,
  restock_event_id BIGINT REFERENCES restock_events(id) ON DELETE SET NULL,
  user_email TEXT NOT NULL,
  product_sku TEXT NOT NULL,
  store_id TEXT NOT NULL,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  success BOOLEAN NOT NULL,
  provider_message_id TEXT,
  error TEXT
);

CREATE TABLE IF NOT EXISTS products_vision (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  brand TEXT,
  category TEXT,
  price_cad NUMERIC(8,2),
  thc_pct NUMERIC(5,2),
  cbd_pct NUMERIC(5,2),
  format TEXT,
  in_stock BOOLEAN,
  store_count INTEGER,
  sync_source TEXT NOT NULL DEFAULT 'vision_fallback',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE NULLS NOT DISTINCT (name, brand)
);

CREATE TABLE IF NOT EXISTS sync_health (
  id BIGSERIAL PRIMARY KEY,
  synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  method TEXT NOT NULL,
  success BOOLEAN NOT NULL,
  products_found INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  stale_since TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_stock_product_sku ON stock(product_sku);
CREATE INDEX IF NOT EXISTS idx_stock_store_id ON stock(store_id);
CREATE INDEX IF NOT EXISTS idx_stock_in_stock ON stock(in_stock);
CREATE INDEX IF NOT EXISTS idx_restock_events_alerted ON restock_events(alerted);
CREATE INDEX IF NOT EXISTS idx_restock_events_product_sku ON restock_events(product_sku);
CREATE INDEX IF NOT EXISTS idx_restock_events_detected_at ON restock_events(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_alerts_product_sku ON user_alerts(product_sku);
CREATE INDEX IF NOT EXISTS idx_user_alerts_store_id ON user_alerts(store_id);
CREATE INDEX IF NOT EXISTS idx_user_alerts_active ON user_alerts(is_active);
CREATE INDEX IF NOT EXISTS idx_alert_log_lookup
  ON alert_log(user_email, product_sku, store_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_products_vision_category ON products_vision(category);
CREATE INDEX IF NOT EXISTS idx_products_vision_updated_at ON products_vision(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_health_method ON sync_health(method);
CREATE INDEX IF NOT EXISTS idx_sync_health_synced_at ON sync_health(synced_at DESC);

CREATE OR REPLACE VIEW sync_status AS
SELECT DISTINCT ON (method)
  method,
  synced_at,
  success,
  products_found,
  error,
  stale_since
FROM sync_health
ORDER BY method, synced_at DESC;

CREATE OR REPLACE VIEW products_in_stock AS
SELECT
  p.*,
  COUNT(s.store_id) AS store_count
FROM products p
JOIN stock s
  ON p.sku = s.product_sku
 AND s.in_stock = TRUE
GROUP BY p.sku;

CREATE OR REPLACE VIEW pending_alerts AS
SELECT
  re.*,
  p.name AS product_name,
  p.product_url,
  st.name AS store_name
FROM restock_events re
JOIN products p ON re.product_sku = p.sku
JOIN stores st ON re.store_id = st.store_id
WHERE re.alerted = FALSE
  AND re.event_type = 'restock';

ALTER TABLE stores ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock ENABLE ROW LEVEL SECURITY;
ALTER TABLE restock_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE products_vision ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_health ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public read stores" ON stores;
CREATE POLICY "Public read stores" ON stores FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS "Public read products" ON products;
CREATE POLICY "Public read products" ON products FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS "Public read stock" ON stock;
CREATE POLICY "Public read stock" ON stock FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS "Public read fallback products" ON products_vision;
CREATE POLICY "Public read fallback products" ON products_vision FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS "Public read sync health" ON sync_health;

GRANT SELECT ON stores, products, stock, products_vision TO anon, authenticated;
GRANT SELECT ON sync_status, products_in_stock TO anon, authenticated;

REVOKE ALL ON restock_events, user_alerts, alert_log FROM anon;
REVOKE ALL ON restock_events, user_alerts, alert_log FROM authenticated;
REVOKE ALL ON pending_alerts FROM anon, authenticated;

COMMIT;
