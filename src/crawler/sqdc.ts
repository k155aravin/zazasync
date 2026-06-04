import type { Env, CrawlResult, InventorySnapshot, ProductSnapshot } from "../types/env";
import {
  finishCrawlRun,
  getRecentCrawl,
  queueAlertsForRecentRestocks,
  startCrawlRun,
  upsertInventory,
  upsertProduct
} from "../db/repository";

const DEFAULT_SEARCH_PATHS = [
  "/fr-CA/Rechercher?keywords=*&sortBy=Created&sortDirection=desc&page=1",
  "/fr-CA/Rechercher?keywords=*&sortBy=Created&sortDirection=desc&page=2",
  "/en-CA/Search?keywords=*&sortBy=Created&sortDirection=desc&page=1"
];

const USER_AGENT = "ZazaSyncBot/0.1 (+https://zazasync.com; contact: support@zazasync.com; public snapshot crawler)";

function toAbsoluteUrl(baseUrl: string, href: string): string {
  return new URL(href, baseUrl).toString();
}

function uniq<T>(items: T[]): T[] {
  return [...new Set(items)];
}

function slugFromUrl(url: string): string {
  const parsed = new URL(url);
  const clean = parsed.pathname.split("/").filter(Boolean).pop() || parsed.pathname;
  return decodeURIComponent(clean).replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-|-$/g, "").toLowerCase();
}

function sourceIdFromUrl(url: string): string {
  const parsed = new URL(url);
  const bySku = parsed.pathname.match(/\/p\/(\d+)|productId=(\d+)|sku=(\d+)/i);
  return bySku?.[1] || bySku?.[2] || bySku?.[3] || slugFromUrl(url);
}

function decodeHtml(value: string): string {
  return value
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\s+/g, " ")
    .trim();
}

function stripTags(value: string): string {
  return decodeHtml(value.replace(/<script[\s\S]*?<\/script>/gi, " ").replace(/<style[\s\S]*?<\/style>/gi, " ").replace(/<[^>]+>/g, " "));
}

function extractProductLinks(baseUrl: string, html: string): string[] {
  const links: string[] = [];
  const hrefRegex = /href=["']([^"']+)["']/gi;
  let match: RegExpExecArray | null;
  while ((match = hrefRegex.exec(html))) {
    const href = decodeHtml(match[1]);
    if (/\/Products?\/|\/produit\/|\/Product\//i.test(href) || /\/p\//i.test(href)) {
      try {
        const url = toAbsoluteUrl(baseUrl, href);
        if (new URL(url).hostname.endsWith("sqdc.ca")) links.push(url.split("#")[0]);
      } catch {
        // Ignore malformed links.
      }
    }
  }
  return uniq(links).slice(0, 200);
}

function extractJsonLdProducts(html: string): Partial<ProductSnapshot>[] {
  const outputs: Partial<ProductSnapshot>[] = [];
  const regex = /<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(html))) {
    try {
      const parsed = JSON.parse(match[1].trim());
      const nodes = Array.isArray(parsed) ? parsed : [parsed];
      for (const node of nodes) {
        const graph = Array.isArray(node?.["@graph"]) ? node["@graph"] : [node];
        for (const item of graph) {
          if (String(item?.["@type"] || "").toLowerCase().includes("product")) {
            const offer = Array.isArray(item.offers) ? item.offers[0] : item.offers;
            outputs.push({
              name: item.name,
              brand: typeof item.brand === "string" ? item.brand : item.brand?.name,
              productUrl: item.url,
              imageUrl: Array.isArray(item.image) ? item.image[0] : item.image,
              priceCents: offer?.price ? Math.round(Number(String(offer.price).replace(",", ".")) * 100) : null,
              rawJson: item
            });
          }
        }
      }
    } catch {
      // Some pages contain invalid or unrelated structured data. Ignore it and fall back to meta tags.
    }
  }
  return outputs;
}

function extractMeta(html: string, property: string): string | null {
  const escaped = property.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`<meta[^>]+(?:property|name)=["']${escaped}["'][^>]+content=["']([^"']+)["'][^>]*>`, "i");
  const altRegex = new RegExp(`<meta[^>]+content=["']([^"']+)["'][^>]+(?:property|name)=["']${escaped}["'][^>]*>`, "i");
  return decodeHtml(regex.exec(html)?.[1] || altRegex.exec(html)?.[1] || "") || null;
}

function parsePriceCents(text: string): number | null {
  const match = text.match(/(\d{1,3}(?:[,.]\d{2}))\s*\$/);
  if (!match) return null;
  return Math.round(Number(match[1].replace(",", ".")) * 100);
}

function parseProductPage(productUrl: string, html: string): ProductSnapshot | null {
  const structured = extractJsonLdProducts(html)[0] || {};
  const title = structured.name || extractMeta(html, "og:title") || html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i)?.[1];
  const name = title ? stripTags(String(title)).replace(/\s*\|\s*SQDC.*$/i, "") : null;
  if (!name || /Bienvenue|date de naissance|not authorized/i.test(name)) return null;

  const plain = stripTags(html);
  const priceCents = structured.priceCents ?? parsePriceCents(plain);
  const thc = plain.match(/THC\s*[:]?\s*([^\n|]{1,40})/i)?.[1]?.trim() ?? null;
  const cbd = plain.match(/CBD\s*[:]?\s*([^\n|]{1,40})/i)?.[1]?.trim() ?? null;
  const imageUrl = structured.imageUrl || extractMeta(html, "og:image");
  const category = plain.match(/Cat[ée]gorie\s*[:]?\s*([^\n|]{2,60})/i)?.[1]?.trim() ?? null;

  return {
    sourceProductId: sourceIdFromUrl(productUrl),
    slug: slugFromUrl(productUrl),
    name,
    brand: structured.brand ?? null,
    category,
    productUrl,
    imageUrl: imageUrl ? toAbsoluteUrl(productUrl, String(imageUrl)) : null,
    priceCents,
    thc,
    cbd,
    format: plain.match(/Format\s*[:]?\s*([^\n|]{1,40})/i)?.[1]?.trim() ?? null,
    rawJson: structured.rawJson ?? null
  };
}

function parseInventory(product: ProductSnapshot, html: string): InventorySnapshot[] {
  const plain = stripTags(html).toLowerCase();
  const evidenceText = stripTags(html).slice(0, 500);
  const hasAvailableSignal = /en stock|disponible|available|ramassage|pickup/i.test(plain);
  const hasUnavailableSignal = /non disponible|rupture|out of stock|unavailable/i.test(plain);
  const status: InventorySnapshot["status"] = hasAvailableSignal && !hasUnavailableSignal
    ? "in_stock"
    : hasUnavailableSignal
      ? "out_of_stock"
      : "unknown";

  return [{
    sourceProductId: product.sourceProductId,
    storeCode: "online-snapshot",
    storeName: "SQDC public snapshot",
    status,
    evidenceText,
    quantityHint: null
  }];
}

async function fetchSqdc(url: string): Promise<string> {
  const response = await fetch(url, {
    headers: {
      "user-agent": USER_AGENT,
      "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "accept-language": "fr-CA,fr;q=0.9,en-CA;q=0.8,en;q=0.7"
    }
  });
  if (!response.ok) throw new Error(`SQDC fetch failed ${response.status} for ${url}`);
  return response.text();
}

async function shouldSkipCrawl(env: Env): Promise<boolean> {
  const recent = await getRecentCrawl(env);
  if (!recent || recent.status === "running") return false;
  const minMinutes = Number(env.CRAWL_MIN_INTERVAL_MINUTES || "120");
  const last = Date.parse(recent.started_at);
  return Number.isFinite(last) && Date.now() - last < minMinutes * 60_000;
}

export async function runSqdcCrawl(env: Env, force = false): Promise<CrawlResult> {
  if (!force && await shouldSkipCrawl(env)) {
    const now = new Date().toISOString();
    return {
      crawlId: 0,
      startedAt: now,
      finishedAt: now,
      pagesScanned: 0,
      productsSeen: 0,
      inventoryRowsSeen: 0,
      changesDetected: 0,
      alertsQueued: 0,
      errors: ["Skipped because minimum crawl interval has not elapsed."]
    };
  }

  const startedAt = new Date().toISOString();
  const crawlId = await startCrawlRun(env);
  const errors: string[] = [];
  let pagesScanned = 0;
  let productsSeen = 0;
  let inventoryRowsSeen = 0;
  let changesDetected = 0;
  let alertsQueued = 0;

  try {
    const baseUrl = env.SQDC_BASE_URL || "https://www.sqdc.ca";
    const maxPages = Math.min(Math.max(Number(env.CRAWL_MAX_PAGES_PER_RUN || "20"), 1), 100);
    const productLinks: string[] = [];

    for (const path of DEFAULT_SEARCH_PATHS) {
      if (pagesScanned >= maxPages) break;
      const url = toAbsoluteUrl(baseUrl, path);
      try {
        const html = await fetchSqdc(url);
        pagesScanned += 1;
        productLinks.push(...extractProductLinks(baseUrl, html));
      } catch (error) {
        errors.push(error instanceof Error ? error.message : String(error));
      }
    }

    for (const url of uniq(productLinks).slice(0, Math.max(0, maxPages - pagesScanned))) {
      try {
        const html = await fetchSqdc(url);
        pagesScanned += 1;
        const product = parseProductPage(url, html);
        if (!product) continue;
        productsSeen += 1;
        const { productId, changes } = await upsertProduct(env, crawlId, product);
        changesDetected += changes;
        const inventory = parseInventory(product, html);
        inventoryRowsSeen += inventory.length;
        for (const inventoryRow of inventory) {
          changesDetected += await upsertInventory(env, crawlId, productId, inventoryRow);
        }
      } catch (error) {
        errors.push(error instanceof Error ? error.message : String(error));
      }
      if (pagesScanned >= maxPages) break;
    }

    alertsQueued = await queueAlertsForRecentRestocks(env);
    const status = errors.length ? "partial" : "success";
    await finishCrawlRun(env, crawlId, {
      status,
      pagesScanned,
      productsSeen,
      inventoryRowsSeen,
      changesDetected,
      alertsQueued,
      errors
    });
    return { crawlId, startedAt, finishedAt: new Date().toISOString(), pagesScanned, productsSeen, inventoryRowsSeen, changesDetected, alertsQueued, errors };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    errors.push(message);
    await finishCrawlRun(env, crawlId, {
      status: "failed",
      pagesScanned,
      productsSeen,
      inventoryRowsSeen,
      changesDetected,
      alertsQueued,
      errors
    });
    return { crawlId, startedAt, finishedAt: new Date().toISOString(), pagesScanned, productsSeen, inventoryRowsSeen, changesDetected, alertsQueued, errors };
  }
}
