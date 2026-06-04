export interface Env {
  ZAZASYNC_DB: D1Database;
  PUBLIC_SITE_ORIGIN: string;
  SQDC_BASE_URL: string;
  CRAWL_MAX_PAGES_PER_RUN: string;
  CRAWL_MIN_INTERVAL_MINUTES: string;
  ALERT_FROM_EMAIL: string;
  ALERT_FROM_NAME: string;
  RESEND_API_KEY?: string;
  ALERTS_ENABLED?: string;
  ADMIN_API_TOKEN?: string;
  GOOGLE_CLIENT_ID?: string;
  GOOGLE_CLIENT_SECRET?: string;
}

export interface ProductSnapshot {
  sourceProductId: string;
  slug: string;
  name: string;
  brand?: string | null;
  category?: string | null;
  productUrl: string;
  imageUrl?: string | null;
  priceCents?: number | null;
  thc?: string | null;
  cbd?: string | null;
  format?: string | null;
  rawJson?: unknown;
}

export interface InventorySnapshot {
  sourceProductId: string;
  storeCode: string;
  storeName?: string | null;
  status: "in_stock" | "low_stock" | "out_of_stock" | "unknown";
  quantityHint?: string | null;
  evidenceText?: string | null;
}

export interface CrawlResult {
  crawlId: number;
  startedAt: string;
  finishedAt: string;
  pagesScanned: number;
  productsSeen: number;
  inventoryRowsSeen: number;
  changesDetected: number;
  alertsQueued: number;
  errors: string[];
}
