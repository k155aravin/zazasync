import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const root = resolve(process.cwd());
const outFile = resolve(root, "src/http/static-ui.ts");

const replacements = [
  // Nav links mapping
  [/href="#"([^>]*?)>Inventory/g, 'href="/"$1>Inventory'],
  [/href="#"([^>]*?)>New Drops/g, 'href="/new-drops"$1>New Drops'],
  [/href="#"([^>]*?)>Back in Stock/g, 'href="/back-in-stock"$1>Back in Stock'],
  [/href="#"([^>]*?)>Stores/g, 'href="/stores"$1>Stores'],
  [/href="#"([^>]*?)>Watchlist/g, 'href="/watchlist"$1>Watchlist'],
  
  // Watchlist specific nav links
  [/href="zazasync\.html"([^>]*?)>Inventory/g, 'href="/"$1>Inventory'],
  [/href="zazasync\.html"([^>]*?)>New Drops/g, 'href="/new-drops"$1>New Drops'],
  [/href="zazasync\.html"([^>]*?)>Back in Stock/g, 'href="/back-in-stock"$1>Back in Stock'],
  [/href="zazasync\.html"([^>]*?)>Stores/g, 'href="/stores"$1>Stores'],
  [/href="zazasync\.html"([^>]*?)>Watchlist/g, 'href="/watchlist"$1>Watchlist'],

  // Section and footer links
  [/href="#"([^>]*?)>View all →/g, 'href="/"$1>View all →'],
  [/href="#"([^>]*?)>All stores →/g, 'href="/stores"$1>All stores →'],

  // Header Logo clickability
  [/<div class="logo">/g, '<div class="logo" onclick="window.location.href=\'/\'" style="cursor:pointer">'],

  // Footer links
  [/<a href="#">Privacy<\/a>/g, '<a href="/privacy">Privacy</a>'],
  [/<a href="#">Terms<\/a>/g, '<a href="/terms">Terms</a>'],
  [/<a href="#">Contact<\/a>/g, '<a href="mailto:support@zazasync.com">Contact</a>'],

  // Base page links
  [/href="zazasync\.html"/g, 'href="/"'],
  [/href="zazasync-web-v2\.html"/g, 'href="/"'],
  [/href="zazasync-auth\.html"/g, 'href="/signin"'],
  [/href="zazasync-onboarding\.html"/g, 'href="/onboarding"'],
  [/href="zazasync-watchlist\.html"/g, 'href="/watchlist"'],
  [/href="zazasync-sms-upsell\.html"/g, 'href="/sms-alerts"'],
  [/href="zazasync-b2b\.html"/g, 'href="/brands"'],
  [/href="zazasync-age-gate\.html"/g, 'href="/age-gate"'],
  [/window\.location\.href='zazasync\.html'/g, "window.location.href='/'"],
  [/window\.location\.href='zazasync\.com'/g, "window.location.href='/'"],
  [/window\.location\.href='zazasync-watchlist\.html'/g, "window.location.href='/watchlist'"],
  [/window\.location\.href='zazasync-auth\.html'/g, "window.location.href='/signin'"],
  [/window\.location\.href = 'zazasync-auth\.html'/g, "window.location.href = '/signin'"],
  [/window\.location\.href = 'zazasync\.html'/g, "window.location.href = '/'"],
  [/window\.location\.href = 'zazasync-watchlist\.html'/g, "window.location.href = '/watchlist'"],
  [/zazasync-pwa-manifest\.json/g, "/manifest.json"],
  [/zazasync-sw\.js/g, "/sw.js"]
];

const apiHydrationScript = `
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
      + '<div class="product-name">' + escapeHtml(product.name) + '</div>'
      + '<div class="product-meta">' + escapeHtml([product.category, product.format, product.thc || product.cbd].filter(Boolean).join(' · ')) + '</div>'
      + '<div class="product-footer">'
      + '<div class="product-price">' + money(product.price_cents) + '</div>'
      + '<div class="stock-status ' + statusClass(product.available_store_count) + '">'
      + '<div class="stock-dot"></div>'
      + '<span>' + statusText(product.available_store_count) + '</span>'
      + '</div>'
      + '</div>'
      + '</a>';
  }

  async function loadProducts(query) {
    if (!grid) return;
    const url = '/api/products?limit=12' + (query ? '&q=' + encodeURIComponent(query) : '');
    try {
      const res = await fetch(url);
      const data = await res.json();
      const items = data.results || [];
      if (trackedStat && typeof data.meta?.total === 'number') {
        trackedStat.textContent = data.meta.total + ' products tracked';
      }
      grid.innerHTML = items.map(card).join('');
      bindWishlist();
    } catch (err) {
      grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text3);padding:2rem">Unable to load SQDC inventory.</div>';
    }
  }

  function bindWishlist() {
    document.querySelectorAll('.wishlist-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        e.stopPropagation();
        const slug = btn.dataset.productSlug;
        const user = currentUser();
        if (!user || !user.email) {
          localStorage.setItem('zazasyncPendingProduct', slug);
          window.location.href = '/signin?next=/watchlist';
          return;
        }
        btn.disabled = true;
        btn.textContent = '...';
        try {
          const res = await fetch('/api/watchlist', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ email: user.email, productSlug: decodeURIComponent(slug), ageConfirmed: true, consentAccepted: true })
          });
          if (res.ok) {
            btn.textContent = '♥';
            btn.style.color = 'var(--green)';
          } else {
            btn.textContent = '♡';
          }
        } catch (_) {
          btn.textContent = '♡';
        } finally {
          btn.disabled = false;
        }
      });
    });
  }

  // Dynamic Header State
  function hydrateHeader() {
    const user = currentUser();
    const navRight = document.querySelector('.nav-right');
    if (user && user.email && navRight) {
      navRight.innerHTML = '<span style="font-size:0.85rem;color:var(--text2);margin-right:0.75rem">' + escapeHtml(user.email) + '</span>'
        + '<button class="btn-ghost" onclick="localStorage.removeItem(\'zazasyncUser\');window.location.reload()">Sign out</button>';
    } else if (navRight) {
      navRight.innerHTML = '<button class="btn-ghost" onclick="window.location.href=\'/signin\'">Sign in</button>'
        + '<button class="btn-green" onclick="document.querySelector(\'.alert-banner\')?.scrollIntoView({behavior:\'smooth\'})">Get alerts</button>';
    }
  }

  // Functional Filter Chips
  function bindFilterChips() {
    const chips = document.querySelectorAll('.filter-chip');
    chips.forEach(chip => {
      chip.addEventListener('click', () => {
        chips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        const text = chip.textContent.trim().toLowerCase();
        if (text === 'in stock') {
          loadProducts();
        } else if (text === 'new drops' || text === 'back in stock') {
          loadProducts();
        } else if (text === 'under $25') {
          loadProducts().then(() => {
            const cards = Array.from(grid.querySelectorAll('.product-card'));
            cards.forEach(card => {
              const priceText = card.querySelector('.product-price')?.textContent || '';
              const price = parseFloat(priceText.replace('$', ''));
              if (isNaN(price) || price > 25) {
                card.style.display = 'none';
              } else {
                card.style.display = 'block';
              }
            });
          });
        } else {
          loadProducts(text);
        }
      });
    });
  }

  // Handle URL pathnames on page load
  function handlePathname() {
    const path = window.location.pathname;
    // Set correct active nav links
    document.querySelectorAll('.nav-links a').forEach(link => {
      const href = link.getAttribute('href');
      if (href === path) {
        document.querySelectorAll('.nav-links a').forEach(l => c.classList.remove('active'));
        link.classList.add('active');
      }
    });

    if (path === '/stores') {
      setTimeout(() => {
        document.querySelector('.stores-grid')?.scrollIntoView({ behavior: 'smooth' });
      }, 300);
    } else if (path === '/new-drops') {
      const chip = Array.from(document.querySelectorAll('.filter-chip')).find(c => c.textContent.trim().toLowerCase() === 'new drops');
      if (chip) chip.click();
    } else if (path === '/back-in-stock') {
      const chip = Array.from(document.querySelectorAll('.filter-chip')).find(c => c.textContent.trim().toLowerCase() === 'back in stock');
      if (chip) chip.click();
    }
  }

  // Alert Form Binding
  function bindAlertForm() {
    const alertForm = document.querySelector('.alert-form');
    if (alertForm) {
      alertForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const emailInput = alertForm.querySelector('input[type="email"]');
        const email = emailInput?.value.trim();
        if (!email) return;
        const btn = alertForm.querySelector('button');
        if (btn) btn.disabled = true;
        try {
          // Setup a session or alert preferences
          const res = await fetch('/api/auth/local', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ email, password: 'temporary_alert_user_pw_123', ageConfirmed: true, consentAccepted: true })
          });
          if (res.ok) {
            const data = await res.json();
            try { localStorage.setItem('zazasyncUser', JSON.stringify(data.user || { email })); } catch(_) {}
          }
          alert('Alerts configured for ' + email + '! You will receive notifications when new items are restocked.');
          if (emailInput) emailInput.value = '';
          hydrateHeader();
        } catch (err) {
          alert('Failed to configure alerts.');
        } finally {
          if (btn) btn.disabled = false;
        }
      });
    }
  }

  // Initialization
  hydrateHeader();
  bindFilterChips();
  bindAlertForm();
  loadProducts().then(handlePathname);

  if (searchButton && searchInput) {
    searchButton.addEventListener('click', () => loadProducts(searchInput.value.trim()));
    searchInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') loadProducts(searchInput.value.trim()); });
  }
})();
</script>`;

function injectHomepageHydration(html) {
  return html.replace("</body>", () => `${apiHydrationScript}\n</body>`);
}

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
    const items = data.items || [];
    const inRows = items.filter(i => Number(i.available_store_count || 0) > 0).map(row).join('');
    const outRows = items.filter(i => Number(i.available_store_count || 0) <= 0).map(row).join('');
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

const pages = [
  { route: "/", file: "zazasync.html", transform: injectHomepageHydration },
  { route: "/web-v2", file: "zazasync-web-v2.html" },
  { route: "/age-gate", file: "zazasync-age-gate.html" },
  { route: "/signin", file: "zazasync-auth.html", transform: injectAuth },
  { route: "/signup", file: "zazasync-auth.html", transform: injectAuth },
  { route: "/auth", file: "zazasync-auth.html", transform: injectAuth },
  { route: "/onboarding", file: "zazasync-onboarding.html", transform: injectOnboarding },
  { route: "/watchlist", file: "zazasync-watchlist.html", transform: injectWatchlist },
  { route: "/sms-alerts", file: "zazasync-sms-upsell.html" },
  { route: "/brands", file: "zazasync-b2b.html" },
  { route: "/mobile", file: "zazasync-mobile.html" },
  { route: "/mobile/signin", file: "zazasync-mobile-auth.html" },
  { route: "/mobile/onboarding", file: "zazasync-mobile-onboarding.html" },
  { route: "/mobile/product", file: "zazasync-mobile-product.html" }
];

const extraPages = [
  { route: "/privacy", title: "Privacy Policy — ZazaSync", file: "zazasync-b2b.html", content: `
    <div class="page" style="max-width:800px;margin:4rem auto;padding:0 2rem">
      <h1 style="font-size:2.5rem;font-weight:700;margin-bottom:1.5rem;letter-spacing:-0.03em">Privacy Policy</h1>
      <p style="color:var(--text3);margin-bottom:2rem">Last updated: June 3, 2026</p>
      <div style="display:flex;flex-direction:column;gap:1.5rem;line-height:1.7;color:var(--text2)">
        <p>At ZazaSync, we value your privacy. This Privacy Policy outlines how we handle data when you use our tracking services.</p>
        <h2 style="font-size:1.5rem;font-weight:600;color:var(--text);margin-top:1rem">1. Information We Collect</h2>
        <p>We only collect the email address you provide for creating your account, tracking your watchlist, and sending restock alerts. No other personal identifiers are collected.</p>
        <h2 style="font-size:1.5rem;font-weight:600;color:var(--text);margin-top:1rem">2. How We Use Data</h2>
        <p>Your email address is used solely to link your SQDC product watchlist and to dispatch email or SMS notifications when inventory updates occur. We never sell or share your information with third parties.</p>
        <h2 style="font-size:1.5rem;font-weight:600;color:var(--text);margin-top:1rem">3. Cookies & Tracking</h2>
        <p>We use local storage to persist your session securely on your device. Minimal anonymous analytics may be tracked to improve the application's response times.</p>
      </div>
    </div>`
  },
  { route: "/terms", title: "Terms of Service — ZazaSync", file: "zazasync-b2b.html", content: `
    <div class="page" style="max-width:800px;margin:4rem auto;padding:0 2rem">
      <h1 style="font-size:2.5rem;font-weight:700;margin-bottom:1.5rem;letter-spacing:-0.03em">Terms of Service</h1>
      <p style="color:var(--text3);margin-bottom:2rem">Last updated: June 3, 2026</p>
      <div style="display:flex;flex-direction:column;gap:1.5rem;line-height:1.7;color:var(--text2)">
        <p>By using ZazaSync, you agree to these Terms of Service. Please read them carefully.</p>
        <h2 style="font-size:1.5rem;font-weight:600;color:var(--text);margin-top:1rem">1. Eligibility</h2>
        <p>You must be 21 years of age or older to use ZazaSync, in compliance with the legal cannabis purchase age in Quebec.</p>
        <h2 style="font-size:1.5rem;font-weight:600;color:var(--text);margin-top:1rem">2. Service Scope</h2>
        <p>ZazaSync is an independent tracker. We are not affiliated, associated, authorized, endorsed by, or in any way officially connected with the Société québécoise du cannabis (SQDC).</p>
        <h2 style="font-size:1.5rem;font-weight:600;color:var(--text);margin-top:1rem">3. Disclaimer of Warranties</h2>
        <p>Inventory data is collected via automated crawlers. While we strive for accuracy, we make no guarantees regarding data real-timeness or stock availability at specific SQDC outlets.</p>
      </div>
    </div>`
  }
];

function build() {
  const code = [];
  code.push("// Generated by scripts/generate-static-ui.mjs - DO NOT EDIT DIRECTLY");
  code.push("export const STATIC_PAGES: Record<string, string> = {};\n");

  for (const page of pages) {
    const rawPath = resolve(root, page.file);
    let html = readFileSync(rawPath, "utf8");

    // Apply global replacements
    for (const [pattern, replacement] of replacements) {
      html = html.replace(pattern, replacement);
    }

    if (page.transform) {
      html = page.transform(html);
    }

    code.push(`STATIC_PAGES[${JSON.stringify(page.route)}] = ${JSON.stringify(html)};`);
  }

  // Build extra custom pages
  for (const page of extraPages) {
    const rawPath = resolve(root, page.file);
    let html = readFileSync(rawPath, "utf8");

    // Apply global replacements
    for (const [pattern, replacement] of replacements) {
      html = html.replace(pattern, replacement);
    }

    // Inject title and custom content
    html = html.replace(/<title>[^<]*<\/title>/, `<title>${page.title}</title>`);
    html = html.replace(/<div class="page">[\s\S]*?<\/div>\s*<footer>/, `${page.content}\n<footer>`);

    code.push(`STATIC_PAGES[${JSON.stringify(page.route)}] = ${JSON.stringify(html)};`);
  }

  // Add the helper functions and PWA static assets back
  code.push(`
const MANIFEST_JSON = "{\\n  \\"name\\": \\"ZazaSync\\",\\n  \\"short_name\\": \\"ZazaSync\\",\\n  \\"description\\": \\"SQDC cannabis product intelligence for Quebec. Track availability, get restock alerts.\\",\\n  \\"start_url\\": \\"/\\",\\n  \\"display\\": \\"standalone\\",\\n  \\"background_color\\": \\"#0d0f0e\\",\\n  \\"theme_color\\": \\"#0d0f0e\\",\\n  \\"orientation\\": \\"portrait\\",\\n  \\"icons\\": [\\n    { \\"src\\": \\"/icons/icon-192.png\\", \\"sizes\\": \\"192x192\\", \\"type\\": \\"image/png\\" },\\n    { \\"src\\": \\"/icons/icon-512.png\\", \\"sizes\\": \\"512x512\\", \\"type\\": \\"image/png\\" },\\n    { \\"src\\": \\"/icons/icon-512.png\\", \\"sizes\\": \\"512x512\\", \\"type\\": \\"image/png\\", \\"purpose\\": \\"maskable\\" }\\n  ],\\n  \\"categories\\": [\\"lifestyle\\", \\"shopping\\"],\\n  \\"lang\\": \\"fr-CA\\",\\n  \\"dir\\": \\"ltr\\",\\n  \\"scope\\": \\"/\\",\\n  \\"prefer_related_applications\\": false\\n}\\n";
const SERVICE_WORKER_JS = "// ZazaSync Service Worker — PWA offline support + push notifications\\nconst CACHE = 'zazasync-v1';\\nconst STATIC = [\\n  '/',\\n  '/inventory',\\n  '/zazasync-mobile.html',\\n  '/zazasync-mobile-auth.html',\\n  '/zazasync-mobile-onboarding.html',\\n  '/zazasync-mobile-product.html',\\n];\\n\\n// INSTALL — cache static assets\\nself.addEventListener('install', e => {\\n  e.waitUntil(\\n    caches.open(CACHE).then(c => c.addAll(STATIC)).then(() => self.skipWaiting())\\n  );\\n});\\n\\n// ACTIVATE — clear old caches\\nself.addEventListener('activate', e => {\\n  e.waitUntil(\\n    caches.keys().then(keys =>\\n      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))\\n    ).then(() => self.clients.claim())\\n  );\\n});\\n\\n// FETCH — network first, cache fallback\\nself.addEventListener('fetch', e => {\\n  if (e.request.method !== 'GET') return;\\n  e.respondWith(\\n    fetch(e.request)\\n      .then(res => {\\n        const clone = res.clone();\\n        caches.open(CACHE).then(c => c.put(e.request, clone));\\n        return res;\\n      })\\n      .catch(() => caches.match(e.request))\\n  );\\n});\\n\\n// PUSH NOTIFICATIONS — fires when Supabase/Resend sends a push\\nself.addEventListener('push', e => {\\n  const data = e.data ? e.data.json() : {};\\n  const title = data.title || '🟢 ZazaSync Alert';\\n  const options = {\\n    body: data.body || 'A product on your watchlist is back in stock.',\\n    icon: '/icons/icon-192.png',\\n    badge: '/icons/badge-72.png',\\n    tag: data.tag || 'zazasync-alert',\\n    data: { url: data.url || '/watchlist' },\\n    actions: [\\n      { action: 'view', title: 'View product' },\\n      { action: 'dismiss', title: 'Dismiss' }\\n    ]\\n  };\\n  e.waitUntil(self.registration.showNotification(title, options));\\n});\\n\\n// NOTIFICATION CLICK — open product page\\nself.addEventListener('notificationclick', e => {\\n  e.notification.close();\\n  if (e.action === 'dismiss') return;\\n  const url = e.notification.data.url || '/';\\n  e.waitUntil(\\n    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {\\n      for (const client of list) {\\n        if (client.url.includes(self.location.origin) && 'focus' in client) {\\n          client.navigate(url);\\n          return client.focus();\\n        }\\n      }\\n      if (clients.openWindow) return clients.openWindow(url);\\n    })\\n  );\\n});\\n";

function htmlResponse(body: string): Response {
  return new Response(body, {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "public, max-age=60"
    }
  });
}

export function getStaticAsset(path: string): Response | null {
  if (path === "/manifest.json") {
    return new Response(MANIFEST_JSON, {
      headers: {
        "content-type": "application/manifest+json; charset=utf-8",
        "cache-control": "public, max-age=3600"
      }
    });
  }

  if (path === "/sw.js") {
    return new Response(SERVICE_WORKER_JS, {
      headers: {
        "content-type": "application/javascript; charset=utf-8",
        "cache-control": "no-cache"
      }
    });
  }

  const html = STATIC_PAGES[path];
  if (!html) return null;
  return htmlResponse(html);
}
`);

  writeFileSync(outFile, code.join("\n"), "utf8");
  console.log(`Successfully generated static UI asset module at ${outFile}`);
}

build();
