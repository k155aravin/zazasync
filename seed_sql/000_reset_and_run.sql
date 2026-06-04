PRAGMA foreign_keys=OFF;
DELETE FROM inventory_snapshots;
DELETE FROM change_events;
DELETE FROM products;
DELETE FROM stores;
DELETE FROM crawl_runs;
PRAGMA foreign_keys=ON;
INSERT INTO crawl_runs (started_at, finished_at, status, pages_scanned, products_seen, inventory_rows_seen, changes_detected, alerts_queued, error_json)
VALUES ('2026-06-04T00:59:36.778Z', '2026-06-04T00:59:36.778Z', 'success', 0, 325, 3462, 325, 0, '[]');
