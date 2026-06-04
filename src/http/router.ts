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
