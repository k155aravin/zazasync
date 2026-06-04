import type { Env } from "../types/env";
import { addWatchlistItem, createLocalSession, getProductBySlug, getWatchlistForEmail, listProducts, removeWatchlistItem, saveUserProfile, setWatchlistAlert } from "../db/repository";
import { runSqdcCrawl } from "../crawler/sqdc";
import { sendQueuedEmailAlerts } from "../email/resend";
import { getStaticAsset } from "./static-ui";

function json(data: unknown, init: ResponseInit = {}): Response {
  const headers = new Headers(init.headers);
  headers.set("content-type", "application/json; charset=utf-8");
  headers.set("cache-control", headers.get("cache-control") || "no-store");
  return new Response(JSON.stringify(data, null, 2), { ...init, headers });
}

function corsHeaders(env: Env, request: Request): Headers {
  const headers = new Headers();
  const origin = request.headers.get("origin");
  const allowed = [env.PUBLIC_SITE_ORIGIN, "https://www.zazasync.com", "https://zazasync.com"].filter(Boolean);
  if (origin && allowed.includes(origin)) headers.set("access-control-allow-origin", origin);
  headers.set("access-control-allow-methods", "GET,POST,PATCH,DELETE,OPTIONS");
  headers.set("access-control-allow-headers", "content-type,authorization");
  headers.set("vary", "Origin");
  return headers;
}

function withCors(response: Response, env: Env, request: Request): Response {
  const headers = new Headers(response.headers);
  corsHeaders(env, request).forEach((value, key) => headers.set(key, value));
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

function requireAdmin(env: Env, request: Request): Response | null {
  if (!env.ADMIN_API_TOKEN) return json({ error: "ADMIN_API_TOKEN is not configured." }, { status: 503 });
  const auth = request.headers.get("authorization") || "";
  const token = auth.replace(/^Bearer\s+/i, "").trim();
  if (token !== env.ADMIN_API_TOKEN) return json({ error: "Unauthorized" }, { status: 401 });
  return null;
}

function validEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) && email.length <= 254;
}

export async function handleRequest(request: Request, env: Env): Promise<Response> {
  if (request.method === "OPTIONS") return withCors(new Response(null, { status: 204 }), env, request);

  const url = new URL(request.url);
  const path = url.pathname.replace(/\/$/, "") || "/";

  try {
    if (path === "/health" || path === "/api/health") {
      const result = await env.ZAZASYNC_DB.prepare(
        `SELECT key, value FROM app_settings WHERE key IN ('schema_version', 'crawler_enabled', 'alerts_enabled')`
      ).all();
      return withCors(json({ ok: true, settings: result.results ?? [] }), env, request);
    }


    // Google OAuth Consent URL Generator
    if (path === "/api/auth/google/url" && request.method === "GET") {
      const clientId = env.GOOGLE_CLIENT_ID;
      if (!clientId) {
        return withCors(json({ error: "Google Client ID is not configured on Cloudflare." }, { status: 503 }), env, request);
      }
      const origin = env.PUBLIC_SITE_ORIGIN || new URL(request.url).origin;
      const redirectUri = `${origin}/api/auth/google/callback`;
      const scope = "openid email profile";
      const state = url.searchParams.get("state") || "oauth_state";
      const googleUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
        `client_id=${encodeURIComponent(clientId)}` +
        `&redirect_uri=${encodeURIComponent(redirectUri)}` +
        `&response_type=code` +
        `&scope=${encodeURIComponent(scope)}` +
        `&state=${encodeURIComponent(state)}` +
        `&prompt=consent`;
      return withCors(json({ url: googleUrl }), env, request);
    }

    // Google OAuth Callback Handler
    if (path === "/api/auth/google/callback" && request.method === "GET") {
      const code = url.searchParams.get("code");
      const state = url.searchParams.get("state") || "";
      if (!code) {
        return new Response("Authorization code is missing.", { status: 400 });
      }

      const clientId = env.GOOGLE_CLIENT_ID;
      const clientSecret = env.GOOGLE_CLIENT_SECRET;
      if (!clientId || !clientSecret) {
        return new Response("Google OAuth credentials are not configured on Cloudflare.", { status: 503 });
      }

      const origin = env.PUBLIC_SITE_ORIGIN || new URL(request.url).origin;
      const redirectUri = `${origin}/api/auth/google/callback`;

      // 1. Exchange authorization code for token
      const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
        method: "POST",
        headers: { "content-type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          code,
          client_id: clientId,
          client_secret: clientSecret,
          redirect_uri: redirectUri,
          grant_type: "authorization_code"
        })
      });

      if (!tokenRes.ok) {
        const errText = await tokenRes.text();
        return new Response(`Failed to exchange authorization code: ${errText}`, { status: 500 });
      }

      const tokenData = await tokenRes.json() as { access_token: string; id_token?: string };

      // 2. Fetch user profile from Google UserInfo endpoint
      const userRes = await fetch("https://www.googleapis.com/oauth2/v2/userinfo", {
        headers: { authorization: `Bearer ${tokenData.access_token}` }
      });

      if (!userRes.ok) {
        return new Response("Failed to fetch user profile from Google.", { status: 500 });
      }

      const googleUser = await userRes.json() as { email: string; given_name?: string; family_name?: string; email_verified?: boolean };
      if (!googleUser.email) {
        return new Response("Google account does not have a valid email.", { status: 400 });
      }

      // 3. Create or update user and establish session
      const result = await createLocalSession(env, {
        email: googleUser.email,
        firstName: googleUser.given_name || null,
        lastName: googleUser.family_name || null,
        ageConfirmed: true // Google accounts require 13+/18+ and the app accepts it
      });

      // 4. Return an HTML response that saves the user in localStorage and redirects
      const next = state.startsWith("next=") ? decodeURIComponent(state.substring(5)) : "/watchlist";
      const html = `
        <!DOCTYPE html>
        <html>
        <head>
          <title>Authenticating...</title>
          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f1115; color: #fff; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .loader { border: 3px solid rgba(255,255,255,0.1); border-top: 3px solid #10b981; border-radius: 50%; width: 24px; height: 24px; animation: spin 1s linear infinite; margin-bottom: 16px; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            .container { text-align: center; }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="loader"></div>
            <div>Completing sign-in...</div>
          </div>
          <script>
            try {
              localStorage.setItem('zazasyncUser', JSON.stringify(${JSON.stringify(result.user)}));
              const pending = localStorage.getItem('zazasyncPendingProduct');
              if (pending) {
                localStorage.removeItem('zazasyncPendingProduct');
                fetch('/api/watchlist', {
                  method: 'POST',
                  headers: { 'content-type': 'application/json' },
                  body: JSON.stringify({ email: ${JSON.stringify(googleUser.email)}, productSlug: decodeURIComponent(pending), ageConfirmed: true, consentAccepted: true })
                }).catch(() => null).finally(() => {
                  window.location.href = "${next}";
                });
              } else {
                window.location.href = "${next}";
              }
            } catch (e) {
              console.error(e);
              alert("Authentication succeeded, but failed to save session.");
              window.location.href = "/signin";
            }
          </script>
        </body>
        </html>
      `;
      return new Response(html, { headers: { "content-type": "text/html; charset=utf-8" } });
    }

    if (path === "/api/auth/local" && request.method === "POST") {
      const body = await request.json().catch(() => null) as null | { email?: string; password?: string; firstName?: string; lastName?: string; ageConfirmed?: boolean; consentAccepted?: boolean };
      if (!body?.email || !validEmail(body.email)) return withCors(json({ error: "A valid email is required." }, { status: 400 }), env, request);
      if (!body.password || body.password.length < 1) return withCors(json({ error: "Password is required." }, { status: 400 }), env, request);
      if (body.ageConfirmed === false || body.consentAccepted === false) return withCors(json({ error: "Age confirmation and consent are required." }, { status: 400 }), env, request);
      const result = await createLocalSession(env, {
        email: body.email,
        firstName: body.firstName || null,
        lastName: body.lastName || null,
        ageConfirmed: true
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

    if (path === "/api/products" && request.method === "GET") {
      const result = await listProducts(env, {
        q: url.searchParams.get("q") || undefined,
        category: url.searchParams.get("category") || undefined,
        limit: Number(url.searchParams.get("limit") || "50"),
        offset: Number(url.searchParams.get("offset") || "0")
      });
      return withCors(json({ products: result.results ?? [] }, { headers: { "cache-control": "public, max-age=120" } }), env, request);
    }

    const productMatch = path.match(/^\/api\/products\/([^/]+)$/);
    if (productMatch && request.method === "GET") {
      const product = await getProductBySlug(env, decodeURIComponent(productMatch[1]));
      if (!product) return withCors(json({ error: "Product not found" }, { status: 404 }), env, request);
      return withCors(json(product, { headers: { "cache-control": "public, max-age=120" } }), env, request);
    }

    if (path === "/api/watchlist" && request.method === "POST") {
      const body = await request.json().catch(() => null) as null | { email?: string; productSlug?: string; preferredStoreCode?: string; ageConfirmed?: boolean; consentAccepted?: boolean };
      if (!body?.email || !validEmail(body.email)) return withCors(json({ error: "A valid email is required." }, { status: 400 }), env, request);
      if (!body.productSlug) return withCors(json({ error: "productSlug is required." }, { status: 400 }), env, request);
      if (!body.ageConfirmed || !body.consentAccepted) return withCors(json({ error: "Age confirmation and consent are required." }, { status: 400 }), env, request);
      const result = await addWatchlistItem(env, body.email, body.productSlug, body.preferredStoreCode || null);
      return withCors(json(result, { status: 201 }), env, request);
    }

    if (path === "/api/admin/crawl" && request.method === "POST") {
      const unauthorized = requireAdmin(env, request);
      if (unauthorized) return withCors(unauthorized, env, request);
      const result = await runSqdcCrawl(env, true);
      const emailResult = await sendQueuedEmailAlerts(env);
      return withCors(json({ crawl: result, email: emailResult }), env, request);
    }

    if (path === "/api/admin/send-alerts" && request.method === "POST") {
      const unauthorized = requireAdmin(env, request);
      if (unauthorized) return withCors(unauthorized, env, request);
      return withCors(json(await sendQueuedEmailAlerts(env)), env, request);
    }

    if (request.method === "GET") {
      const uiFallbackRoutes = new Set(["/inventory", "/new-drops", "/back-in-stock", "/stores", "/privacy", "/terms", "/contact", "/responsible-use"]);
      const staticAsset = getStaticAsset(path) ?? (path.startsWith("/products/") || uiFallbackRoutes.has(path) ? getStaticAsset("/") : null);
      if (staticAsset) return staticAsset;
    }

    return withCors(json({ error: "Not found" }, { status: 404 }), env, request);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return withCors(json({ error: message }, { status: 500 }), env, request);
  }
}
