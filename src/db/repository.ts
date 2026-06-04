import type { Env, InventorySnapshot, ProductSnapshot } from "../types/env";

const nowIso = () => new Date().toISOString();

export async function startCrawlRun(env: Env): Promise<number> {
  const now = nowIso();
  const result = await env.ZAZASYNC_DB.prepare(
    `INSERT INTO crawl_runs (started_at, status) VALUES (?, 'running') RETURNING id`
  ).bind(now).first<{ id: number }>();
  if (!result?.id) throw new Error("Unable to start crawl run");
  return result.id;
}

export async function finishCrawlRun(
  env: Env,
  crawlRunId: number,
  input: {
    status: "success" | "partial" | "failed";
    pagesScanned: number;
    productsSeen: number;
    inventoryRowsSeen: number;
    changesDetected: number;
    alertsQueued: number;
    errors: string[];
  }
): Promise<void> {
  await env.ZAZASYNC_DB.prepare(
    `UPDATE crawl_runs
     SET finished_at = ?, status = ?, pages_scanned = ?, products_seen = ?, inventory_rows_seen = ?,
         changes_detected = ?, alerts_queued = ?, error_json = ?
     WHERE id = ?`
  ).bind(
    nowIso(),
    input.status,
    input.pagesScanned,
    input.productsSeen,
    input.inventoryRowsSeen,
    input.changesDetected,
    input.alertsQueued,
    JSON.stringify(input.errors),
    crawlRunId
  ).run();
}

export async function getRecentCrawl(env: Env): Promise<{ started_at: string; status: string } | null> {
  const row = await env.ZAZASYNC_DB.prepare(
    `SELECT started_at, status FROM crawl_runs ORDER BY id DESC LIMIT 1`
  ).first<{ started_at: string; status: string }>();
  return row ?? null;
}

export async function upsertProduct(
  env: Env,
  crawlRunId: number,
  product: ProductSnapshot
): Promise<{ productId: number; changes: number }> {
  const existing = await env.ZAZASYNC_DB.prepare(
    `SELECT id, price_cents, name, brand, category, image_url, thc, cbd, format
     FROM products WHERE source_product_id = ?`
  ).bind(product.sourceProductId).first<{
    id: number;
    price_cents: number | null;
    name: string;
    brand: string | null;
    category: string | null;
    image_url: string | null;
    thc: string | null;
    cbd: string | null;
    format: string | null;
  }>();

  const now = nowIso();
  const rawJson = product.rawJson ? JSON.stringify(product.rawJson).slice(0, 50000) : null;

  if (!existing) {
    const inserted = await env.ZAZASYNC_DB.prepare(
      `INSERT INTO products
       (source_product_id, slug, name, brand, category, product_url, image_url, price_cents, thc, cbd, format, raw_json, first_seen_at, last_seen_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id`
    ).bind(
      product.sourceProductId,
      product.slug,
      product.name,
      product.brand ?? null,
      product.category ?? null,
      product.productUrl,
      product.imageUrl ?? null,
      product.priceCents ?? null,
      product.thc ?? null,
      product.cbd ?? null,
      product.format ?? null,
      rawJson,
      now,
      now,
      now
    ).first<{ id: number }>();

    const productId = inserted?.id;
    if (!productId) throw new Error(`Unable to insert product ${product.sourceProductId}`);
    await insertChangeEvent(env, crawlRunId, productId, null, "new_product", null, product.name, 1);
    return { productId, changes: 1 };
  }

  let changes = 0;
  if ((existing.price_cents ?? null) !== (product.priceCents ?? null)) {
    await insertChangeEvent(
      env,
      crawlRunId,
      existing.id,
      null,
      "price_change",
      existing.price_cents == null ? null : String(existing.price_cents),
      product.priceCents == null ? null : String(product.priceCents),
      0
    );
    changes += 1;
  }

  const changedMetadata =
    existing.name !== product.name ||
    existing.brand !== (product.brand ?? null) ||
    existing.category !== (product.category ?? null) ||
    existing.image_url !== (product.imageUrl ?? null) ||
    existing.thc !== (product.thc ?? null) ||
    existing.cbd !== (product.cbd ?? null) ||
    existing.format !== (product.format ?? null);

  if (changedMetadata) {
    await insertChangeEvent(env, crawlRunId, existing.id, null, "product_update", null, product.name, 0);
    changes += 1;
  }

  await env.ZAZASYNC_DB.prepare(
    `UPDATE products
     SET slug = ?, name = ?, brand = ?, category = ?, product_url = ?, image_url = ?, price_cents = ?,
         thc = ?, cbd = ?, format = ?, raw_json = ?, last_seen_at = ?, updated_at = ?
     WHERE id = ?`
  ).bind(
    product.slug,
    product.name,
    product.brand ?? null,
    product.category ?? null,
    product.productUrl,
    product.imageUrl ?? null,
    product.priceCents ?? null,
    product.thc ?? null,
    product.cbd ?? null,
    product.format ?? null,
    rawJson,
    now,
    now,
    existing.id
  ).run();

  return { productId: existing.id, changes };
}

export async function upsertStore(env: Env, storeCode: string, name?: string | null): Promise<number> {
  const existing = await env.ZAZASYNC_DB.prepare(
    `SELECT id FROM stores WHERE store_code = ?`
  ).bind(storeCode).first<{ id: number }>();
  const now = nowIso();
  if (existing?.id) {
    await env.ZAZASYNC_DB.prepare(
      `UPDATE stores SET name = COALESCE(?, name), last_seen_at = ?, updated_at = ? WHERE id = ?`
    ).bind(name ?? null, now, now, existing.id).run();
    return existing.id;
  }
  const inserted = await env.ZAZASYNC_DB.prepare(
    `INSERT INTO stores (store_code, name, first_seen_at, last_seen_at, updated_at) VALUES (?, ?, ?, ?, ?) RETURNING id`
  ).bind(storeCode, name || storeCode, now, now, now).first<{ id: number }>();
  if (!inserted?.id) throw new Error(`Unable to insert store ${storeCode}`);
  return inserted.id;
}

export async function upsertInventory(
  env: Env,
  crawlRunId: number,
  productId: number,
  row: InventorySnapshot
): Promise<number> {
  const storeId = await upsertStore(env, row.storeCode, row.storeName);
  const existing = await env.ZAZASYNC_DB.prepare(
    `SELECT id, status FROM inventory_snapshots WHERE product_id = ? AND store_id = ?`
  ).bind(productId, storeId).first<{ id: number; status: string }>();
  const now = nowIso();

  if (!existing) {
    await env.ZAZASYNC_DB.prepare(
      `INSERT INTO inventory_snapshots
       (product_id, store_id, status, quantity_hint, evidence_text, first_seen_at, last_seen_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
    ).bind(productId, storeId, row.status, row.quantityHint ?? null, row.evidenceText ?? null, now, now, now).run();
    if (row.status === "in_stock" || row.status === "low_stock") {
      await insertChangeEvent(env, crawlRunId, productId, storeId, "restock", "unknown", row.status, 1);
      return 1;
    }
    return 0;
  }

  let changes = 0;
  if (existing.status !== row.status) {
    const eventType = (row.status === "in_stock" || row.status === "low_stock")
      ? "restock"
      : row.status === "out_of_stock"
        ? "stock_loss"
        : "status_change";
    await insertChangeEvent(env, crawlRunId, productId, storeId, eventType, existing.status, row.status, eventType === "restock" ? 1 : 0);
    changes = 1;
  }

  await env.ZAZASYNC_DB.prepare(
    `UPDATE inventory_snapshots
     SET status = ?, quantity_hint = ?, evidence_text = ?, last_seen_at = ?, updated_at = ?
     WHERE id = ?`
  ).bind(row.status, row.quantityHint ?? null, row.evidenceText ?? null, now, now, existing.id).run();
  return changes;
}

async function insertChangeEvent(
  env: Env,
  crawlRunId: number,
  productId: number,
  storeId: number | null,
  eventType: "new_product" | "price_change" | "restock" | "stock_loss" | "status_change" | "product_update",
  previousValue: string | null,
  newValue: string | null,
  alertable: 0 | 1
): Promise<void> {
  await env.ZAZASYNC_DB.prepare(
    `INSERT INTO change_events
     (crawl_run_id, product_id, store_id, event_type, previous_value, new_value, occurred_at, alertable)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
  ).bind(crawlRunId, productId, storeId, eventType, previousValue, newValue, nowIso(), alertable).run();
}

export async function listProducts(env: Env, options: { q?: string; category?: string; limit?: number; offset?: number }) {
  const limit = Math.min(Math.max(options.limit ?? 50, 1), 100);
  const offset = Math.max(options.offset ?? 0, 0);
  const conditions: string[] = [];
  const bindings: unknown[] = [];

  if (options.q) {
    conditions.push(`(name LIKE ? OR brand LIKE ?)`);
    bindings.push(`%${options.q}%`, `%${options.q}%`);
  }
  if (options.category) {
    conditions.push(`category = ?`);
    bindings.push(options.category);
  }

  const where = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";
  return env.ZAZASYNC_DB.prepare(
    `SELECT p.*, 
            SUM(CASE WHEN i.status IN ('in_stock', 'low_stock') THEN 1 ELSE 0 END) AS available_store_count,
            MAX(i.updated_at) AS inventory_updated_at
     FROM products p
     LEFT JOIN inventory_snapshots i ON i.product_id = p.id
     ${where}
     GROUP BY p.id
     ORDER BY p.updated_at DESC
     LIMIT ? OFFSET ?`
  ).bind(...bindings, limit, offset).all();
}

export async function getProductBySlug(env: Env, slug: string) {
  const product = await env.ZAZASYNC_DB.prepare(`SELECT * FROM products WHERE slug = ?`).bind(slug).first();
  if (!product) return null;
  const inventory = await env.ZAZASYNC_DB.prepare(
    `SELECT s.store_code, s.name AS store_name, s.city, s.region, i.status, i.quantity_hint, i.evidence_text, i.updated_at
     FROM inventory_snapshots i
     JOIN stores s ON s.id = i.store_id
     WHERE i.product_id = ?
     ORDER BY CASE i.status WHEN 'in_stock' THEN 0 WHEN 'low_stock' THEN 1 WHEN 'unknown' THEN 2 ELSE 3 END, s.name ASC`
  ).bind((product as { id: number }).id).all();
  return { product, inventory: inventory.results ?? [] };
}

export async function createOrUpdateUser(env: Env, email: string, consentVersion = "2026-06"): Promise<number> {
  const normalized = email.trim().toLowerCase();
  const now = nowIso();
  const existing = await env.ZAZASYNC_DB.prepare(`SELECT id FROM users WHERE email = ? AND deleted_at IS NULL`).bind(normalized).first<{ id: number }>();
  if (existing?.id) {
    await env.ZAZASYNC_DB.prepare(`UPDATE users SET updated_at = ? WHERE id = ?`).bind(now, existing.id).run();
    return existing.id;
  }
  const inserted = await env.ZAZASYNC_DB.prepare(
    `INSERT INTO users (email, age_confirmed_at, consent_version, created_at, updated_at) VALUES (?, ?, ?, ?, ?) RETURNING id`
  ).bind(normalized, now, consentVersion, now, now).first<{ id: number }>();
  if (!inserted?.id) throw new Error("Unable to create user");
  return inserted.id;
}

export async function addWatchlistItem(env: Env, email: string, productSlug: string, preferredStoreCode?: string | null) {
  const userId = await createOrUpdateUser(env, email);
  const product = await env.ZAZASYNC_DB.prepare(`SELECT id FROM products WHERE slug = ?`).bind(productSlug).first<{ id: number }>();
  if (!product?.id) throw new Error("Product not found");
  let storeId: number | null = null;
  if (preferredStoreCode) {
    const store = await env.ZAZASYNC_DB.prepare(`SELECT id FROM stores WHERE store_code = ?`).bind(preferredStoreCode).first<{ id: number }>();
    storeId = store?.id ?? null;
  }
  const now = nowIso();
  const existing = await env.ZAZASYNC_DB.prepare(
    storeId === null
      ? `SELECT id FROM watchlist_items WHERE user_id = ? AND product_id = ? AND preferred_store_id IS NULL`
      : `SELECT id FROM watchlist_items WHERE user_id = ? AND product_id = ? AND preferred_store_id = ?`
  ).bind(...(storeId === null ? [userId, product.id] : [userId, product.id, storeId])).first<{ id: number }>();

  if (existing?.id) {
    await env.ZAZASYNC_DB.prepare(
      `UPDATE watchlist_items SET alert_on_restock = 1, updated_at = ? WHERE id = ?`
    ).bind(now, existing.id).run();
    return { ok: true, watchlistId: existing.id, created: false };
  }

  const inserted = await env.ZAZASYNC_DB.prepare(
    `INSERT INTO watchlist_items (user_id, product_id, preferred_store_id, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?) RETURNING id`
  ).bind(userId, product.id, storeId, now, now).first<{ id: number }>();
  return { ok: true, watchlistId: inserted?.id ?? null, created: true };
}


export async function createLocalSession(
  env: Env,
  input: { email: string; firstName?: string | null; lastName?: string | null; ageConfirmed?: boolean; consentVersion?: string }
) {
  const userId = await createOrUpdateUser(env, input.email, input.consentVersion || "2026-06");
  const now = nowIso();
  await env.ZAZASYNC_DB.prepare(
    `UPDATE users
     SET first_name = COALESCE(?, first_name),
         last_name = COALESCE(?, last_name),
         age_confirmed_at = CASE WHEN ? THEN COALESCE(age_confirmed_at, ?) ELSE age_confirmed_at END,
         updated_at = ?
     WHERE id = ?`
  ).bind(input.firstName || null, input.lastName || null, input.ageConfirmed ? 1 : 0, now, now, userId).run();
  const user = await env.ZAZASYNC_DB.prepare(
    `SELECT id, email, first_name, last_name, preferred_language, onboarding_json, created_at, updated_at
     FROM users WHERE id = ?`
  ).bind(userId).first();
  return { ok: true, user };
}

export async function saveUserProfile(
  env: Env,
  email: string,
  profile: { age?: string; region?: string; freq?: string; lang?: string; stores?: string[] }
) {
  const userId = await createOrUpdateUser(env, email);
  const now = nowIso();
  await env.ZAZASYNC_DB.prepare(
    `UPDATE users
     SET preferred_language = COALESCE(?, preferred_language), onboarding_json = ?, updated_at = ?
     WHERE id = ?`
  ).bind(profile.lang || null, JSON.stringify(profile).slice(0, 10000), now, userId).run();
  return { ok: true };
}

export async function getWatchlistForEmail(env: Env, email: string) {
  const normalized = email.trim().toLowerCase();
  const user = await env.ZAZASYNC_DB.prepare(`SELECT id, email, onboarding_json FROM users WHERE email = ? AND deleted_at IS NULL`).bind(normalized).first<{ id: number; email: string; onboarding_json: string | null }>();
  if (!user?.id) return { user: null, items: [], stats: { total: 0, inStock: 0, outOfStock: 0, alertsSent: 0 } };

  const items = await env.ZAZASYNC_DB.prepare(
    `SELECT wi.id AS watchlist_id,
            wi.alert_on_restock,
            wi.created_at,
            p.slug,
            p.name,
            p.brand,
            p.category,
            p.price_cents,
            p.thc,
            p.cbd,
            p.format,
            p.image_url,
            SUM(CASE WHEN i.status IN ('in_stock', 'low_stock') THEN 1 ELSE 0 END) AS available_store_count,
            MAX(i.updated_at) AS inventory_updated_at
     FROM watchlist_items wi
     JOIN products p ON p.id = wi.product_id
     LEFT JOIN inventory_snapshots i ON i.product_id = p.id
     WHERE wi.user_id = ?
     GROUP BY wi.id, p.id
     ORDER BY wi.updated_at DESC`
  ).bind(user.id).all();

  const alerts = await env.ZAZASYNC_DB.prepare(`SELECT COUNT(*) AS count FROM alert_log WHERE user_id = ?`).bind(user.id).first<{ count: number }>();
  const rows = items.results ?? [];
  const inStock = rows.filter((row: any) => Number(row.available_store_count || 0) > 0).length;
  return {
    user,
    items: rows,
    stats: { total: rows.length, inStock, outOfStock: rows.length - inStock, alertsSent: alerts?.count || 0 }
  };
}

export async function removeWatchlistItem(env: Env, email: string, watchlistId: number) {
  const normalized = email.trim().toLowerCase();
  await env.ZAZASYNC_DB.prepare(
    `DELETE FROM watchlist_items
     WHERE id = ? AND user_id IN (SELECT id FROM users WHERE email = ? AND deleted_at IS NULL)`
  ).bind(watchlistId, normalized).run();
  return { ok: true };
}

export async function setWatchlistAlert(env: Env, email: string, watchlistId: number, enabled: boolean) {
  const normalized = email.trim().toLowerCase();
  await env.ZAZASYNC_DB.prepare(
    `UPDATE watchlist_items
     SET alert_on_restock = ?, updated_at = ?
     WHERE id = ? AND user_id IN (SELECT id FROM users WHERE email = ? AND deleted_at IS NULL)`
  ).bind(enabled ? 1 : 0, nowIso(), watchlistId, normalized).run();
  return { ok: true };
}

export async function queueAlertsForRecentRestocks(env: Env): Promise<number> {
  const rows = await env.ZAZASYNC_DB.prepare(
    `SELECT ce.id AS change_event_id, ce.product_id, ce.store_id, u.id AS user_id, u.email
     FROM change_events ce
     JOIN watchlist_items wi ON wi.product_id = ce.product_id
       AND wi.alert_on_restock = 1
       AND (wi.preferred_store_id IS NULL OR wi.preferred_store_id = ce.store_id)
     JOIN users u ON u.id = wi.user_id AND u.deleted_at IS NULL
     LEFT JOIN alert_log al ON al.change_event_id = ce.id AND al.user_id = u.id AND al.channel = 'email'
     WHERE ce.alertable = 1
       AND ce.event_type IN ('restock', 'new_product')
       AND al.id IS NULL
     ORDER BY ce.occurred_at DESC
     LIMIT 200`
  ).all<{
    change_event_id: number;
    product_id: number;
    store_id: number | null;
    user_id: number;
    email: string;
  }>();

  let queued = 0;
  const now = nowIso();
  for (const row of rows.results ?? []) {
    await env.ZAZASYNC_DB.prepare(
      `INSERT INTO alert_log (user_id, product_id, store_id, change_event_id, channel, recipient, status, created_at)
       VALUES (?, ?, ?, ?, 'email', ?, 'queued', ?)`
    ).bind(row.user_id, row.product_id, row.store_id, row.change_event_id, row.email, now).run();
    queued += 1;
  }
  return queued;
}

export async function getQueuedAlerts(env: Env, limit = 50) {
  return env.ZAZASYNC_DB.prepare(
    `SELECT al.id, al.recipient, al.change_event_id, p.name AS product_name, p.slug, s.name AS store_name, s.store_code
     FROM alert_log al
     JOIN products p ON p.id = al.product_id
     LEFT JOIN stores s ON s.id = al.store_id
     WHERE al.status = 'queued'
     ORDER BY al.created_at ASC
     LIMIT ?`
  ).bind(limit).all<{
    id: number;
    recipient: string;
    change_event_id: number | null;
    product_name: string;
    slug: string;
    store_name: string | null;
    store_code: string | null;
  }>();
}

export async function markAlert(env: Env, id: number, status: "sent" | "failed" | "skipped", providerMessageId?: string | null, errorText?: string | null) {
  await env.ZAZASYNC_DB.prepare(
    `UPDATE alert_log SET status = ?, provider_message_id = ?, error_text = ?, sent_at = ? WHERE id = ?`
  ).bind(status, providerMessageId ?? null, errorText ?? null, status === "sent" ? nowIso() : null, id).run();
}
