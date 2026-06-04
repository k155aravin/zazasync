from pathlib import Path

root = Path('/home/ubuntu/zazasync_repo')
repo = root / 'src/db/repository.ts'
router = root / 'src/http/router.ts'
gen = root / 'scripts/generate-static-ui.mjs'
migration = root / 'migrations/0002_user_profile_watchlist_ui.sql'

repo_text = repo.read_text()
insert_after = '''export async function addWatchlistItem(env: Env, email: string, productSlug: string, preferredStoreCode?: string | null) {
  const userId = await createOrUpdateUser(env, email);
  const product = await env.ZAZASYNC_DB.prepare(`SELECT id FROM products WHERE slug = ?`).bind(productSlug).first<{ id: number }>();
  if (!product?.id) throw new Error("Product not found");
  let storeId: number | null = null;
  if (preferredStoreCode) {
    const store = await env.ZAZASYNC_DB.prepare(`SELECT id FROM stores WHERE store_code = ?`).bind(preferredStoreCode).first<{ id: number }>();
    storeId = store?.id ?? null;
  }
  const now = nowIso();
  await env.ZAZASYNC_DB.prepare(
    `INSERT INTO watchlist_items (user_id, product_id, preferred_store_id, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?)
     ON CONFLICT(user_id, product_id, preferred_store_id)
     DO UPDATE SET alert_on_restock = 1, updated_at = excluded.updated_at`
  ).bind(userId, product.id, storeId, now, now).run();
  return { ok: true };
}
'''
addition = r'''

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
'''
if addition.strip() not in repo_text:
    repo_text = repo_text.replace(insert_after, insert_after + addition)
repo.write_text(repo_text)

router_text = router.read_text()
router_text = router_text.replace(
'import { addWatchlistItem, getProductBySlug, listProducts } from "../db/repository";',
'import { addWatchlistItem, createLocalSession, getProductBySlug, getWatchlistForEmail, listProducts, removeWatchlistItem, saveUserProfile, setWatchlistAlert } from "../db/repository";'
)
insert_api = r'''
    if (path === "/api/auth/local" && request.method === "POST") {
      const body = await request.json().catch(() => null) as null | { email?: string; password?: string; firstName?: string; lastName?: string; ageConfirmed?: boolean; consentAccepted?: boolean };
      if (!body?.email || !validEmail(body.email)) return withCors(json({ error: "A valid email is required." }, { status: 400 }), env, request);
      if (!body.password || body.password.length < 1) return withCors(json({ error: "Password is required." }, { status: 400 }), env, request);
      if (body.ageConfirmed === false || body.consentAccepted === false) return withCors(json({ error: "Age confirmation and consent are required." }, { status: 400 }), env, request);
      const result = await createLocalSession(env, {
        email: body.email,
        firstName: body.firstName || null,
        lastName: body.lastName || null,
        ageConfirmed: body.ageConfirmed !== false
      });
      return withCors(json(result, { status: 200 }), env, request);
    }

    if (path === "/api/profile" && request.method === "POST") {
      const body = await request.json().catch(() => null) as null | { email?: string; profile?: { age?: string; region?: string; freq?: string; lang?: string; stores?: string[] } };
      if (!body?.email || !validEmail(body.email)) return withCors(json({ error: "A valid email is required." }, { status: 400 }), env, request);
      return withCors(json(await saveUserProfile(env, body.email, body.profile || {})), env, request);
    }

    if (path === "/api/watchlist" && request.method === "GET") {
      const email = url.searchParams.get("email") || "";
      if (!validEmail(email)) return withCors(json({ error: "A valid email is required." }, { status: 400 }), env, request);
      return withCors(json(await getWatchlistForEmail(env, email), { headers: { "cache-control": "no-store" } }), env, request);
    }

    if (path === "/api/watchlist" && request.method === "PATCH") {
      const body = await request.json().catch(() => null) as null | { email?: string; watchlistId?: number; enabled?: boolean };
      if (!body?.email || !validEmail(body.email)) return withCors(json({ error: "A valid email is required." }, { status: 400 }), env, request);
      if (!body.watchlistId) return withCors(json({ error: "watchlistId is required." }, { status: 400 }), env, request);
      return withCors(json(await setWatchlistAlert(env, body.email, Number(body.watchlistId), Boolean(body.enabled))), env, request);
    }

    if (path === "/api/watchlist" && request.method === "DELETE") {
      const body = await request.json().catch(() => null) as null | { email?: string; watchlistId?: number };
      if (!body?.email || !validEmail(body.email)) return withCors(json({ error: "A valid email is required." }, { status: 400 }), env, request);
      if (!body.watchlistId) return withCors(json({ error: "watchlistId is required." }, { status: 400 }), env, request);
      return withCors(json(await removeWatchlistItem(env, body.email, Number(body.watchlistId))), env, request);
    }
'''
marker = '    if (path === "/api/products" && request.method === "GET") {'
if insert_api.strip() not in router_text:
    router_text = router_text.replace(marker, insert_api + '\n' + marker)
router_text = router_text.replace(
'headers.set("access-control-allow-methods", "GET,POST,OPTIONS");',
'headers.set("access-control-allow-methods", "GET,POST,PATCH,DELETE,OPTIONS");'
)
router_text = router_text.replace(
'const uiFallbackRoutes = new Set(["/inventory", "/new-drops", "/back-in-stock", "/stores", "/privacy", "/terms", "/contact"]);\n      const staticAsset = getStaticAsset(path) ?? (path.startsWith("/products/") || uiFallbackRoutes.has(path) ? getStaticAsset("/") : null);',
'const uiFallbackRoutes = new Set(["/inventory", "/new-drops", "/back-in-stock", "/stores", "/privacy", "/terms", "/contact", "/responsible-use"]);\n      const staticAsset = getStaticAsset(path) ?? (path.startsWith("/products/") || uiFallbackRoutes.has(path) ? getStaticAsset("/") : null);'
)
router.write_text(router_text)

migration.write_text('''-- UI/auth/profile support for migrated prototype flows.\nALTER TABLE users ADD COLUMN first_name TEXT;\nALTER TABLE users ADD COLUMN last_name TEXT;\nALTER TABLE users ADD COLUMN onboarding_json TEXT;\n''')

text = gen.read_text()
# Insert replacement for generic hash navs is handled by scripts below.
old_hydration = text[text.index('const apiHydrationScript = `'):text.index('function injectHomepageHydration')]
new_hydration = r'''const apiHydrationScript = `
<script>
(function () {
  const grid = document.querySelector('.products-grid');
  const searchInput = document.querySelector('.search-input');
  const searchButton = document.querySelector('.search-btn');
  const trackedStat = Array.from(document.querySelectorAll('.stat-pill span')).find((el) => el.textContent && el.textContent.includes('products tracked'));

  function currentUser() {
    try { return JSON.parse(localStorage.getItem('zazasyncUser') || 'null'); } catch (_) { return null; }
  }
  function money(cents) { return typeof cents === 'number' ? '$' + (cents / 100).toFixed(2) : 'Price TBA'; }
  function safe(value, fallback) { return value == null || value === '' ? fallback : String(value); }
  function statusClass(count) { return Number(count || 0) > 0 ? 'stock-in' : 'stock-out'; }
  function statusText(count) { const n = Number(count || 0); if (n > 1) return n + ' stores'; if (n === 1) return '1 store'; return 'Watch item'; }
  function productEmoji(category) { const c = String(category || '').toLowerCase(); if (c.includes('oil') || c.includes('capsule')) return '💚'; if (c.includes('pre') || c.includes('roll')) return '💨'; if (c.includes('vape')) return '🔥'; return '🌿'; }
  function escapeHtml(value) { return safe(value, '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }

  function card(product) {
    const slug = encodeURIComponent(product.slug || product.source_product_id || 'product');
    return '<a class="product-card" href="/products/' + slug + '" style="text-decoration:none;color:inherit;display:block">'
      + '<button class="wishlist-btn" data-product-slug="' + slug + '" aria-label="Add to watchlist">♡</button>'
      + '<div class="product-img">' + (product.image_url ? '<img src="' + product.image_url + '" alt="" loading="lazy" style="width:100%;height:100%;object-fit:cover;border-radius:18px">' : productEmoji(product.category)) + '</div>'
      + '<div class="product-brand">' + escapeHtml(product.brand || 'SQDC') + '</div>'
      + '<div class="product-name">' + escapeHtml(product.name || 'Unnamed product') + '</div>'
      + '<div class="product-meta"><span class="meta-tag">' + escapeHtml(product.category || product.format || 'Product') + '</span><span class="meta-tag">' + escapeHtml(product.thc || product.cbd || 'Snapshot') + '</span></div>'
      + '<div class="product-footer"><span class="product-price">' + money(product.price_cents) + '</span><span class="stock-badge ' + statusClass(product.available_store_count) + '">' + statusText(product.available_store_count) + '</span></div>'
      + '</a>';
  }

  async function loadProducts(query) {
    if (!grid) return;
    const url = '/api/products?limit=12' + (query ? '&q=' + encodeURIComponent(query) : '');
    try {
      const response = await fetch(url, { headers: { accept: 'application/json' } });
      if (!response.ok) return;
      const data = await response.json();
      const products = Array.isArray(data.products) ? data.products : [];
      if (!products.length) return;
      grid.innerHTML = products.map(card).join('');
      if (trackedStat) trackedStat.innerHTML = '🟢 <b>' + products.length + '+</b> cached products';
      bindWishlistButtons();
    } catch (error) { console.warn('ZazaSync product hydration failed; keeping bundled fallback.', error); }
  }

  function bindWishlistButtons() {
    document.querySelectorAll('.wishlist-btn').forEach(function (btn) {
      if (btn.dataset.bound === '1') return;
      btn.dataset.bound = '1';
      btn.addEventListener('click', async function (event) {
        event.preventDefault(); event.stopPropagation();
        const user = currentUser();
        if (!user || !user.email) {
          localStorage.setItem('zazasyncPendingProduct', btn.dataset.productSlug || '');
          window.location.href = '/signin?next=' + encodeURIComponent(window.location.pathname);
          return;
        }
        btn.disabled = true;
        try {
          const response = await fetch('/api/watchlist', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ email: user.email, productSlug: decodeURIComponent(btn.dataset.productSlug || ''), ageConfirmed: true, consentAccepted: true }) });
          if (!response.ok) throw new Error((await response.json()).error || 'Unable to add watchlist item.');
          btn.textContent = '♥'; btn.style.color = 'var(--green)'; btn.title = 'Saved to watchlist';
        } catch (error) { alert(error.message || 'Could not save this product yet.'); }
        finally { btn.disabled = false; }
      });
    });
  }

  if (searchButton && searchInput) {
    searchButton.addEventListener('click', function () { loadProducts(searchInput.value.trim()); });
    searchInput.addEventListener('keydown', function (event) { if (event.key === 'Enter') loadProducts(searchInput.value.trim()); });
  }
  bindWishlistButtons();
  loadProducts();
})();
</script>`;

'''
text = text.replace(old_hydration, new_hydration)

inject_funcs = r'''
const authScript = `
<script>
(function () {
  function setError(id, message) { const el = document.getElementById(id); if (el) { el.textContent = message; el.style.display = 'block'; } }
  function clearError(id) { const el = document.getElementById(id); if (el) el.style.display = 'none'; }
  function saveUser(payload) { localStorage.setItem('zazasyncUser', JSON.stringify(payload.user || { email: payload.email })); }
  async function submitAuth(mode) {
    const email = document.getElementById(mode + '-email')?.value.trim();
    const pw = document.getElementById(mode === 'signin' ? 'signin-pw' : 'signup-pw')?.value || '';
    const first = document.getElementById('signup-first')?.value.trim() || '';
    const last = document.getElementById('signup-last')?.value.trim() || '';
    const age = mode === 'signin' ? true : Boolean(document.getElementById('age-confirm')?.checked);
    const errorId = mode + '-error';
    clearError(errorId);
    if (!email || !pw) return setError(errorId, 'Please enter your email and password.');
    if (mode === 'signup' && !first) return setError(errorId, 'Please enter your first name.');
    if (mode === 'signup' && !age) return setError(errorId, 'You must confirm you are 21 or older to continue.');
    if (mode === 'signup' && pw.length < 8) return setError(errorId, 'Password must be at least 8 characters.');
    try {
      const response = await fetch('/api/auth/local', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ email, password: pw, firstName: first, lastName: last, ageConfirmed: age, consentAccepted: true }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Unable to continue.');
      saveUser(data);
      const pending = localStorage.getItem('zazasyncPendingProduct');
      if (pending) {
        localStorage.removeItem('zazasyncPendingProduct');
        await fetch('/api/watchlist', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ email, productSlug: decodeURIComponent(pending), ageConfirmed: true, consentAccepted: true }) }).catch(() => null);
      }
      if (mode === 'signup') window.location.href = '/onboarding';
      else window.location.href = new URLSearchParams(window.location.search).get('next') || '/watchlist';
    } catch (error) { setError(errorId, error.message || 'Unable to continue.'); }
  }
  window.doSignIn = function () { submitAuth('signin'); };
  window.doSignUp = function () { submitAuth('signup'); };
  window.oauthClick = function () { alert('Google sign-in still needs the Supabase/Firebase OAuth public client config. Email sign-in is wired for staging now.'); };
  if (window.location.pathname === '/signup') switchTab('signup');
})();
</script>`;

const onboardingScript = `
<script>
(function () {
  const originalGoStep = window.goStep;
  window.goStep = async function (n) {
    if (n === 5) {
      const user = JSON.parse(localStorage.getItem('zazasyncUser') || 'null');
      localStorage.setItem('zazasyncProfile', JSON.stringify(window.selected || selected));
      if (user && user.email) {
        await fetch('/api/profile', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ email: user.email, profile: window.selected || selected }) }).catch(() => null);
      }
    }
    return originalGoStep(n);
  };
})();
</script>`;

const watchlistScript = `
<script>
(function () {
  function user() { try { return JSON.parse(localStorage.getItem('zazasyncUser') || 'null'); } catch (_) { return null; } }
  function money(cents) { return typeof cents === 'number' ? '$' + (cents / 100).toFixed(2) : 'Price TBA'; }
  function emoji(category) { const c = String(category || '').toLowerCase(); if (c.includes('oil') || c.includes('capsule')) return '💚'; if (c.includes('pre') || c.includes('roll')) return '💨'; if (c.includes('vape')) return '🔥'; return '🌿'; }
  function esc(value) { return String(value || '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
  function row(item) {
    const inStock = Number(item.available_store_count || 0) > 0;
    return '<tr data-watchlist-id="' + item.watchlist_id + '"><td><div class="product-cell"><div class="product-emoji">' + emoji(item.category) + '</div><div><div class="product-name-cell">' + esc(item.name) + '</div><div class="product-brand-cell">' + esc([item.brand, item.category, item.thc || item.cbd].filter(Boolean).join(' · ')) + '</div></div></div></td><td><div class="price-cell">' + money(item.price_cents) + '</div></td><td><span class="badge ' + (inStock ? 'badge-green' : 'badge-red') + '">' + (inStock ? 'In stock' : 'Out of stock') + '</span></td><td><div class="alert-toggle"><div class="toggle ' + (item.alert_on_restock ? 'on' : '') + '" data-id="' + item.watchlist_id + '"><div class="toggle-thumb"></div></div><span class="alert-label">' + (item.alert_on_restock ? 'On' : 'Off') + '</span></div></td><td><div class="actions-cell"><a href="/products/' + encodeURIComponent(item.slug) + '" class="view-btn">View →</a><button class="action-btn" data-remove="' + item.watchlist_id + '">Remove</button></div></td></tr>';
  }
  function setStats(stats) {
    const nums = document.querySelectorAll('.stats-row .stat-num');
    if (nums[0]) nums[0].textContent = stats.total || 0;
    if (nums[1]) nums[1].textContent = stats.inStock || 0;
    if (nums[2]) nums[2].textContent = stats.outOfStock || 0;
    if (nums[3]) nums[3].textContent = stats.alertsSent || 0;
    const badges = document.querySelectorAll('.section-title .badge');
    if (badges[0]) badges[0].textContent = stats.inStock || 0;
    if (badges[1]) badges[1].textContent = stats.outOfStock || 0;
  }
  async function load() {
    const current = user();
    if (!current || !current.email) { window.location.href = '/signin?next=/watchlist'; return; }
    document.querySelectorAll('.setting-sub')[0].textContent = current.email;
    const response = await fetch('/api/watchlist?email=' + encodeURIComponent(current.email));
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Unable to load watchlist.');
    setStats(data.stats || {});
    const inRows = (data.items || []).filter(i => Number(i.available_store_count || 0) > 0).map(row).join('');
    const outRows = (data.items || []).filter(i => Number(i.available_store_count || 0) <= 0).map(row).join('');
    const bodies = document.querySelectorAll('.watchlist-table tbody');
    if (bodies[0]) bodies[0].innerHTML = inRows || '<tr><td colspan="5"><div class="empty-sub">No watched products are in stock right now.</div></td></tr>';
    if (bodies[1]) bodies[1].innerHTML = outRows || '<tr><td colspan="5"><div class="empty-sub">No watched products are waiting for restock.</div></td></tr>';
    bindActions();
  }
  function bindActions() {
    document.querySelectorAll('.toggle[data-id]').forEach(el => el.onclick = async function () {
      const current = user(); const enabled = !el.classList.contains('on');
      el.classList.toggle('on', enabled); const label = el.nextElementSibling; if (label) label.textContent = enabled ? 'On' : 'Off';
      await fetch('/api/watchlist', { method: 'PATCH', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ email: current.email, watchlistId: Number(el.dataset.id), enabled }) }).catch(() => null);
    });
    document.querySelectorAll('[data-remove]').forEach(btn => btn.onclick = async function () {
      if (!confirm('Remove this product from your watchlist?')) return;
      const current = user();
      await fetch('/api/watchlist', { method: 'DELETE', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ email: current.email, watchlistId: Number(btn.dataset.remove) }) });
      load();
    });
  }
  load().catch(error => alert(error.message));
})();
</script>`;

function injectAuth(html) { return html.replace("</body>", () => `${authScript}\n</body>`); }
function injectOnboarding(html) { return html.replace("</body>", () => `${onboardingScript}\n</body>`); }
function injectWatchlist(html) { return html.replace("</body>", () => `${watchlistScript}\n</body>`); }

'''
if 'const authScript = `' not in text:
    old_inject = '''function injectHomepageHydration(html) {
  return html.replace("</body>", () => `${apiHydrationScript}\\n</body>`);
}
'''
    new_inject = '''function injectHomepageHydration(html) {
  return html.replace("</body>", () => `${apiHydrationScript}\\n</body>`);
}

''' + inject_funcs
    text = text.replace(old_inject, new_inject)
text = text.replace('{ route: "/signin", file: "zazasync-auth.html" },', '{ route: "/signin", file: "zazasync-auth.html", transform: injectAuth },')
text = text.replace('{ route: "/signup", file: "zazasync-auth.html" },', '{ route: "/signup", file: "zazasync-auth.html", transform: injectAuth },')
text = text.replace('{ route: "/auth", file: "zazasync-auth.html" },', '{ route: "/auth", file: "zazasync-auth.html", transform: injectAuth },')
text = text.replace('{ route: "/onboarding", file: "zazasync-onboarding.html" },', '{ route: "/onboarding", file: "zazasync-onboarding.html", transform: injectOnboarding },')
text = text.replace('{ route: "/watchlist", file: "zazasync-watchlist.html" },', '{ route: "/watchlist", file: "zazasync-watchlist.html", transform: injectWatchlist },')
gen.write_text(text)
print('Applied functional UI migration changes.')
