import json
import math
import re
from pathlib import Path

SNAPSHOT = Path('restored_snapshot.json')
OUT_DIR = Path('seed_sql')
OUT_DIR.mkdir(exist_ok=True)
data = json.loads(SNAPSHOT.read_text())
now = data.get('lastUpdatedAt') or data.get('extractedAt')

def sql(value):
    if value is None:
        return 'NULL'
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return 'NULL'
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"

def cents(price):
    if price is None:
        return None
    try:
        return int(round(float(price) * 100))
    except Exception:
        return None

def slug_from_product(p):
    slug = p.get('slug') or p.get('id') or p.get('name') or 'product'
    slug = str(slug).strip().lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    return slug or str(p.get('id') or 'product')

files = []
reset = OUT_DIR / '000_reset_and_run.sql'
reset.write_text("""PRAGMA foreign_keys=OFF;
DELETE FROM inventory_snapshots;
DELETE FROM change_events;
DELETE FROM products;
DELETE FROM stores;
DELETE FROM crawl_runs;
PRAGMA foreign_keys=ON;
INSERT INTO crawl_runs (started_at, finished_at, status, pages_scanned, products_seen, inventory_rows_seen, changes_detected, alerts_queued, error_json)
VALUES ({now}, {now}, 'success', 0, {products}, {inventory}, {products}, 0, '[]');
""".format(now=sql(now), products=len(data['products']), inventory=sum(len(p.get('availability') or []) for p in data['products'])))
files.append(reset)

store_lines = []
for s in data['stores']:
    raw = json.dumps(s, ensure_ascii=False, separators=(',', ':'))
    code = s.get('id') or ('sqdc-store-' + str(s.get('sqdcStoreId') or s.get('name')))
    store_lines.append(
        "INSERT INTO stores (store_code, name, city, region, address, raw_json, first_seen_at, last_seen_at, updated_at) VALUES "
        f"({sql(code)}, {sql(s.get('name') or s.get('city') or code)}, {sql(s.get('city'))}, {sql(s.get('province'))}, {sql(s.get('address'))}, {sql(raw)}, {sql(s.get('lastCheckedAt') or now)}, {sql(s.get('lastCheckedAt') or now)}, {sql(s.get('lastCheckedAt') or now)}) "
        "ON CONFLICT(store_code) DO UPDATE SET name=excluded.name, city=excluded.city, region=excluded.region, address=excluded.address, raw_json=excluded.raw_json, last_seen_at=excluded.last_seen_at, updated_at=excluded.updated_at;"
    )
store_file = OUT_DIR / '010_stores.sql'
store_file.write_text('\n'.join(store_lines) + '\n')
files.append(store_file)

product_lines = []
used_slugs = {}
source_slug = {}
for p in data['products']:
    raw_obj = dict(p)
    raw_obj.pop('availability', None)
    raw = json.dumps(raw_obj, ensure_ascii=False, separators=(',', ':'))
    source_id = p.get('id') or p.get('sourceProductId') or p.get('sqdcUrl') or slug_from_product(p)
    base_slug = slug_from_product(p)
    if base_slug in used_slugs:
        used_slugs[base_slug] += 1
        # Several SQDC entries share a marketing slug. Preserve readability while making the D1 unique key stable.
        suffix = re.sub(r'[^a-z0-9]+', '-', str(source_id).lower()).strip('-')[-24:] or str(used_slugs[base_slug])
        unique_slug = f'{base_slug}-{suffix}'
    else:
        used_slugs[base_slug] = 1
        unique_slug = base_slug
    source_slug[source_id] = unique_slug
    product_lines.append(
        "INSERT INTO products (source_product_id, slug, name, brand, category, product_url, image_url, price_cents, thc, cbd, format, raw_json, first_seen_at, last_seen_at, updated_at) VALUES "
        f"({sql(source_id)}, {sql(unique_slug)}, {sql(p.get('name') or source_id)}, {sql(p.get('brand'))}, {sql(p.get('category') or p.get('subcategory'))}, {sql(p.get('sqdcUrl') or p.get('productUrl') or '')}, {sql(p.get('imageUrl'))}, {sql(cents(p.get('price')))}, {sql(p.get('thcLabel'))}, {sql(p.get('cbdLabel'))}, {sql(p.get('format') or p.get('weight'))}, {sql(raw)}, {sql(p.get('firstSeenAt') or p.get('lastSeenAt') or now)}, {sql(p.get('lastSeenAt') or now)}, {sql(p.get('lastSeenAt') or now)}) "
        "ON CONFLICT(source_product_id) DO UPDATE SET slug=excluded.slug, name=excluded.name, brand=excluded.brand, category=excluded.category, product_url=excluded.product_url, image_url=excluded.image_url, price_cents=excluded.price_cents, thc=excluded.thc, cbd=excluded.cbd, format=excluded.format, raw_json=excluded.raw_json, last_seen_at=excluded.last_seen_at, updated_at=excluded.updated_at;"
    )
for idx in range(0, len(product_lines), 100):
    f = OUT_DIR / f'020_products_{idx//100+1:02d}.sql'
    f.write_text('\n'.join(product_lines[idx:idx+100]) + '\n')
    files.append(f)

inventory_lines = []
for p in data['products']:
    source_id = p.get('id') or p.get('sourceProductId') or p.get('sqdcUrl') or slug_from_product(p)
    for a in p.get('availability') or []:
        store_code = a.get('storeId')
        if not store_code:
            continue
        raw_evidence = a.get('quantityLabel') or a.get('extractionStatus') or a.get('state')
        status = a.get('state') or 'unknown'
        if status not in {'in_stock','low_stock','out_of_stock','unknown'}:
            status = 'unknown'
        ts = a.get('checkedAt') or p.get('lastSeenAt') or now
        inventory_lines.append(
            "INSERT INTO inventory_snapshots (product_id, store_id, status, quantity_hint, evidence_text, first_seen_at, last_seen_at, updated_at) "
            f"VALUES ((SELECT id FROM products WHERE source_product_id={sql(source_id)}), (SELECT id FROM stores WHERE store_code={sql(store_code)}), {sql(status)}, {sql(a.get('quantityLabel'))}, {sql(raw_evidence)}, {sql(ts)}, {sql(ts)}, {sql(ts)}) "
            "ON CONFLICT(product_id, store_id) DO UPDATE SET status=excluded.status, quantity_hint=excluded.quantity_hint, evidence_text=excluded.evidence_text, last_seen_at=excluded.last_seen_at, updated_at=excluded.updated_at;"
        )
for idx in range(0, len(inventory_lines), 250):
    f = OUT_DIR / f'030_inventory_{idx//250+1:02d}.sql'
    f.write_text('\n'.join(inventory_lines[idx:idx+250]) + '\n')
    files.append(f)

manifest = OUT_DIR / 'manifest.txt'
manifest.write_text('\n'.join(str(f) for f in files) + '\n')
print(json.dumps({'files': len(files), 'stores': len(data['stores']), 'products': len(data['products']), 'inventory': len(inventory_lines), 'manifest': str(manifest)}, indent=2))
