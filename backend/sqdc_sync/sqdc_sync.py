#!/usr/bin/env python3
"""Primary SQDC catalog, store, stock, and restock synchronization."""

from __future__ import annotations

import fcntl
import json
import logging
import os
import re
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import urljoin

import requests
import schedule
from dotenv import load_dotenv
from supabase import Client, create_client

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

SQDC_BASE = os.getenv("SQDC_BASE_URL", "https://www.sqdc.ca").rstrip("/")
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL_MINUTES", "15"))
FULL_SYNC_TIME = os.getenv("FULL_SYNC_TIME", "03:00")
LOCK_FILE = "/tmp/zazasync_sqdc_sync.lock"
KNOWN_CATEGORIES = [
    "cannabis-seche",
    "pre-roules",
    "vapotage",
    "haschich",
    "boissons",
    "extraits",
]
SKU_LINK_RE = re.compile(
    r'href=["\'](?P<href>/fr-CA/p-(?P<slug>[^/"\']+)/(?P<sku>\d+)-P/\d+)["\']',
    re.IGNORECASE,
)

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(ROOT / "sqdc_sync.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("sqdc_sync")


@dataclass
class Product:
    sku: str
    name: str
    brand: str | None
    category: str
    price_cad: float | None
    thc_pct: float | None
    cbd_pct: float | None
    format: str | None
    image_url: str | None
    product_url: str

    def row(self) -> dict[str, Any]:
        now = utc_now()
        return {
            "sku": self.sku,
            "name": self.name,
            "brand": self.brand,
            "category": self.category,
            "price_cad": self.price_cad,
            "thc_pct": self.thc_pct,
            "cbd_pct": self.cbd_pct,
            "format": self.format,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "is_active": True,
            "updated_at": now,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


def get_db() -> Client:
    return create_client(require_env("SUPABASE_URL"), require_env("SUPABASE_SERVICE_KEY"))


@contextmanager
def process_lock(path: str = LOCK_FILE) -> Iterator[bool]:
    handle = open(path, "w", encoding="utf-8")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log.warning("Another SQDC sync is already running; exiting.")
            yield False
            return
        handle.write(str(os.getpid()))
        handle.flush()
        yield True
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        handle.close()


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "fr-CA,fr;q=0.9,en;q=0.8",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{SQDC_BASE}/fr-CA/",
            "Origin": SQDC_BASE,
        }
    )
    response = session.get(f"{SQDC_BASE}/fr-CA/", timeout=15)
    response.raise_for_status()
    time.sleep(1)
    return session


def chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def strip_tags(value: str) -> str:
    value = re.sub(r"<script[\s\S]*?</script>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"<style[\s\S]*?</style>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


def meta_value(html: str, key: str) -> str | None:
    escaped = re.escape(key)
    patterns = [
        rf'<meta[^>]+(?:property|name)=["\']{escaped}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{escaped}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return unescape(match.group(1)).strip()
    return None


def first_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+(?:[.,]\d+)?", str(value))
    return float(match.group(0).replace(",", ".")) if match else None


def boolean_value(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    normalized = str(value).strip().casefold()
    if normalized in {"true", "yes", "oui", "available", "in stock", "1"}:
        return True
    if normalized in {"false", "no", "non", "unavailable", "out of stock", "0"}:
        return False
    return None


def parse_json_ld(html: str) -> dict[str, Any]:
    for raw in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>',
        html,
        re.IGNORECASE,
    ):
        try:
            parsed = json.loads(raw.strip())
        except (TypeError, json.JSONDecodeError):
            continue
        queue = parsed if isinstance(parsed, list) else [parsed]
        while queue:
            item = queue.pop(0)
            if not isinstance(item, dict):
                continue
            graph = item.get("@graph")
            if isinstance(graph, list):
                queue.extend(graph)
            if "product" in str(item.get("@type", "")).lower():
                return item
    return {}


def parse_product_page(
    sku: str, slug: str, category: str, product_url: str, html: str
) -> Product:
    structured = parse_json_ld(html)
    h1_match = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html, re.IGNORECASE)
    title = structured.get("name") or meta_value(html, "og:title")
    if not title and h1_match:
        title = strip_tags(h1_match.group(1))
    name = re.sub(r"\s*[|\-]\s*SQDC.*$", "", str(title or slug.replace("-", " ")), flags=re.I).strip()
    brand_data = structured.get("brand")
    brand = brand_data.get("name") if isinstance(brand_data, dict) else brand_data
    plain = strip_tags(html)
    offer = structured.get("offers")
    if isinstance(offer, list):
        offer = offer[0] if offer else {}
    offer = offer if isinstance(offer, dict) else {}
    image = structured.get("image") or meta_value(html, "og:image")
    if isinstance(image, list):
        image = image[0] if image else None
    thc_match = re.search(r"\bTHC\b\s*:?\s*(\d+(?:[.,]\d+)?)\s*%?", plain, re.I)
    cbd_match = re.search(r"\bCBD\b\s*:?\s*(\d+(?:[.,]\d+)?)\s*%?", plain, re.I)
    format_match = re.search(
        r"\bFormat\b\s*:?\s*([0-9]+(?:[.,][0-9]+)?\s*(?:g|mg|ml|unit\w*))",
        plain,
        re.I,
    )
    return Product(
        sku=sku,
        name=name,
        brand=str(brand).strip() if brand else None,
        category=category,
        price_cad=first_number(offer.get("price")),
        thc_pct=first_number(thc_match.group(1)) if thc_match else None,
        cbd_pct=first_number(cbd_match.group(1)) if cbd_match else None,
        format=format_match.group(1).strip() if format_match else None,
        image_url=urljoin(product_url, str(image)) if image else None,
        product_url=product_url,
    )


def category_url(slug: str, page: int) -> str:
    base = f"{SQDC_BASE}/fr-CA/{slug}"
    return base if page == 1 else f"{base}?page={page}"


def page_has_next(html: str, current_page: int) -> bool:
    if re.search(r'rel=["\']next["\']', html, re.IGNORECASE):
        return True
    if re.search(r"page suivante|suivant|next page", strip_tags(html), re.IGNORECASE):
        return True
    return bool(re.search(rf"[?&]page={current_page + 1}(?:[&\"'])", html, re.IGNORECASE))


def discover_product_refs(session: requests.Session) -> dict[str, tuple[str, str]]:
    refs: dict[str, tuple[str, str]] = {}
    for category in KNOWN_CATEGORIES:
        page = 1
        while page <= 100:
            url = category_url(category, page)
            response = session.get(url, timeout=20)
            response.raise_for_status()
            matches = list(SKU_LINK_RE.finditer(response.text))
            if not matches:
                break
            for match in matches:
                refs[match.group("sku")] = (match.group("slug"), category)
            log.info("%s page %s: %s product links", category, page, len(matches))
            if not page_has_next(response.text, page):
                break
            page += 1
            time.sleep(1.5)
        time.sleep(1.5)
    return refs


def find_dicts(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from find_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from find_dicts(child)


def sku_from_dict(item: dict[str, Any]) -> str | None:
    for key in ("Sku", "SKU", "sku", "ProductSku", "productSku", "Code"):
        value = item.get(key)
        if value and str(value).isdigit():
            return str(value)
    return None


def enrich_from_price_response(products: dict[str, Product], payload: Any) -> None:
    for item in find_dicts(payload):
        sku = sku_from_dict(item)
        if not sku or sku not in products:
            continue
        product = products[sku]
        for key in ("Price", "price", "CurrentPrice", "SalePrice", "UnitPrice"):
            value = first_number(item.get(key))
            if value is not None:
                product.price_cad = value
                break
        for keys, attr in (
            (("Thc", "THC", "thc", "ThcPercentage"), "thc_pct"),
            (("Cbd", "CBD", "cbd", "CbdPercentage"), "cbd_pct"),
            (("Format", "format", "Weight", "Size"), "format"),
            (("Brand", "brand", "ProducerName"), "brand"),
            (("Name", "name", "ProductName"), "name"),
        ):
            for key in keys:
                value = item.get(key)
                if value not in (None, ""):
                    setattr(product, attr, first_number(value) if attr.endswith("_pct") else str(value).strip())
                    break


def fetch_products(session: requests.Session) -> dict[str, Product]:
    refs = discover_product_refs(session)
    products: dict[str, Product] = {}
    for index, (sku, (slug, category)) in enumerate(refs.items(), start=1):
        url = f"{SQDC_BASE}/fr-CA/p-{slug}/{sku}-P/{sku}"
        response = session.get(url, timeout=20)
        response.raise_for_status()
        products[sku] = parse_product_page(sku, slug, category, url, response.text)
        if index % 25 == 0:
            log.info("Parsed %s/%s product pages", index, len(refs))
        time.sleep(0.8)

    skus = list(products)
    for batch in chunks(skus, 50):
        for endpoint in (
            "/api/product/calculatePrices",
            "/api/inventory/findInventoryItems",
        ):
            response = session.post(
                f"{SQDC_BASE}{endpoint}",
                json={"skus": batch},
                timeout=20,
            )
            response.raise_for_status()
            enrich_from_price_response(products, response.json())
        time.sleep(2)
    return products


def upsert_batches(db: Client, table: str, rows: list[dict[str, Any]], conflict: str, size: int = 250) -> None:
    for index in range(0, len(rows), size):
        db.table(table).upsert(rows[index : index + size], on_conflict=conflict).execute()


def fetch_store_records(session: requests.Session) -> list[dict[str, Any]]:
    response = session.post(f"{SQDC_BASE}/api/storelocator/store", json={}, timeout=20)
    response.raise_for_status()
    payload = response.json()
    candidates = payload if isinstance(payload, list) else payload.get("Stores", payload.get("stores", []))
    if not isinstance(candidates, list):
        raise ValueError("Unexpected store response structure.")
    rows = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        store_id = item.get("StoreId") or item.get("Id") or item.get("id")
        if not store_id:
            continue
        address = item.get("Address")
        if isinstance(address, dict):
            address = " ".join(str(address.get(key, "")).strip() for key in ("AddressLine1", "City", "PostalCode")).strip()
        rows.append(
            {
                "store_id": str(store_id),
                "name": item.get("DisplayName") or item.get("Name") or f"SQDC {store_id}",
                "city": item.get("City") or item.get("Municipality"),
                "address": address or item.get("FullAddress"),
                "lat": first_number(item.get("Latitude") or item.get("Lat")),
                "lng": first_number(item.get("Longitude") or item.get("Lng")),
                "updated_at": utc_now(),
            }
        )
    if not rows:
        raise ValueError("Store endpoint returned no usable stores.")
    return rows


def sync_stores(session: requests.Session, db: Client) -> int:
    rows = fetch_store_records(session)
    upsert_batches(db, "stores", rows, "store_id")
    log.info("Saved %s stores", len(rows))
    return len(rows)


def normalize_stock_records(payload: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in find_dicts(payload):
        store_id = item.get("StoreId") or item.get("storeId") or item.get("Id")
        if not store_id or str(store_id) in seen:
            continue
        has_stock_field = any(
            key in item
            for key in ("InStock", "inStock", "IsAvailable", "Available", "Quantity", "quantity")
        )
        if not has_stock_field:
            continue
        quantity = first_number(item.get("Quantity") if "Quantity" in item else item.get("quantity"))
        explicit = item.get("InStock", item.get("inStock", item.get("IsAvailable", item.get("Available"))))
        parsed_availability = boolean_value(explicit)
        in_stock = parsed_availability if parsed_availability is not None else bool(quantity and quantity > 0)
        seen.add(str(store_id))
        records.append(
            {
                "store_id": str(store_id),
                "in_stock": in_stock,
                "quantity": int(quantity) if quantity is not None else None,
            }
        )
    return records


def fetch_previous_stock(db: Client, sku: str) -> dict[str, bool]:
    response = db.table("stock").select("store_id,in_stock").eq("product_sku", sku).execute()
    return {str(row["store_id"]): bool(row["in_stock"]) for row in (response.data or [])}


def fetch_known_store_ids(db: Client) -> list[str]:
    response = db.table("stores").select("store_id").execute()
    return [str(row["store_id"]) for row in (response.data or [])]


def fetch_stock(session: requests.Session, sku: str) -> list[dict[str, Any]]:
    response = session.post(
        f"{SQDC_BASE}/api/storeinventory/storesinventory",
        json={"Sku": sku},
        timeout=20,
    )
    response.raise_for_status()
    records = normalize_stock_records(response.json())
    if not records:
        raise ValueError(f"Stock endpoint returned no usable store rows for SKU {sku}.")
    return records


def sync_one_sku(
    session: requests.Session,
    db: Client,
    sku: str,
    known_store_ids: list[str],
) -> int:
    explicit = {row["store_id"]: row for row in fetch_stock(session, sku)}
    unknown_store_ids = sorted(set(explicit) - set(known_store_ids))
    if unknown_store_ids:
        upsert_batches(
            db,
            "stores",
            [
                {
                    "store_id": store_id,
                    "name": f"SQDC {store_id}",
                    "updated_at": utc_now(),
                }
                for store_id in unknown_store_ids
            ],
            "store_id",
        )
        known_store_ids.extend(unknown_store_ids)
    previous = fetch_previous_stock(db, sku)
    now = utc_now()
    current: dict[str, dict[str, Any]] = {}

    for store_id in known_store_ids:
        source = explicit.get(store_id)
        current[store_id] = {
            "product_sku": sku,
            "store_id": store_id,
            "in_stock": bool(source and source["in_stock"]),
            "quantity": source["quantity"] if source else None,
            "synced_at": now,
        }
    for store_id, source in explicit.items():
        current.setdefault(
            store_id,
            {
                "product_sku": sku,
                "store_id": store_id,
                "in_stock": bool(source["in_stock"]),
                "quantity": source["quantity"],
                "synced_at": now,
            },
        )

    events = []
    for store_id, row in current.items():
        if store_id not in previous:
            continue
        old = previous[store_id]
        new = bool(row["in_stock"])
        if old == new:
            continue
        events.append(
            {
                "product_sku": sku,
                "store_id": store_id,
                "event_type": "restock" if new else "out_of_stock",
                "detected_at": now,
                "alerted": False,
            }
        )

    upsert_batches(db, "stock", list(current.values()), "product_sku,store_id")
    if events:
        db.table("restock_events").insert(events).execute()
    return len(events)


def log_health(
    db: Client,
    method: str,
    success: bool,
    products_found: int,
    error: str | None = None,
) -> None:
    db.table("sync_health").insert(
        {
            "synced_at": utc_now(),
            "method": method,
            "success": success,
            "products_found": products_found,
            "error": error,
            "stale_since": None if success else utc_now(),
        }
    ).execute()


def sync_products(session: requests.Session, db: Client) -> int:
    products = fetch_products(session)
    rows = [product.row() for product in products.values()]
    if not rows:
        raise RuntimeError("No products were discovered.")
    upsert_batches(db, "products", rows, "sku")
    log.info("Saved %s products", len(rows))
    return len(rows)


def existing_skus(db: Client) -> list[str]:
    response = db.table("products").select("sku").eq("is_active", True).execute()
    return [str(row["sku"]) for row in (response.data or [])]


def run_stock_sync(session: requests.Session, db: Client, method: str = "primary_stock") -> bool:
    skus = existing_skus(db)
    stores = fetch_known_store_ids(db)
    if not skus:
        raise RuntimeError("No products exist. Run products or full mode first.")
    if not stores:
        raise RuntimeError("No stores exist. Run stores mode first.")

    errors: list[str] = []
    events = 0
    for index, sku in enumerate(skus, start=1):
        try:
            events += sync_one_sku(session, db, sku, stores)
        except Exception as exc:
            message = f"{sku}: {exc}"
            errors.append(message)
            log.exception("Stock sync failed for SKU %s", sku)
        if index % 20 == 0:
            log.info("Stock progress %s/%s", index, len(skus))
        time.sleep(0.8)

    success = not errors
    note = None if success else f"{len(errors)} SKU errors. " + " | ".join(errors[:10])
    log_health(db, method, success, len(skus), note)
    log.info(
        "Stock sync completed: %s SKUs, %s change events, %s errors",
        len(skus),
        events,
        len(errors),
    )
    return success


def run_mode(mode: str) -> bool:
    db = get_db()
    method = f"primary_{mode}"
    try:
        session = make_session()
        if mode == "stores":
            count = sync_stores(session, db)
            log_health(db, method, True, count)
            return True
        if mode == "products":
            count = sync_products(session, db)
            log_health(db, method, True, count)
            return True
        if mode == "stock":
            return run_stock_sync(session, db)
        if mode == "full":
            sync_stores(session, db)
            count = sync_products(session, db)
            stock_ok = run_stock_sync(session, db, method="primary_full_stock")
            log_health(db, method, stock_ok, count, None if stock_ok else "Stock phase contained errors.")
            return stock_ok
        raise ValueError(f"Unknown mode: {mode}")
    except Exception as exc:
        log.exception("%s sync failed", mode)
        try:
            log_health(db, method, False, 0, str(exc)[:2000])
        except Exception:
            log.exception("Could not write sync failure to sync_health.")
        return False


def locked_run(mode: str) -> bool:
    with process_lock() as acquired:
        return run_mode(mode) if acquired else False


def run_scheduler() -> None:
    log.info(
        "Scheduler started: stock every %s minutes, full sync daily at %s",
        SYNC_INTERVAL,
        FULL_SYNC_TIME,
    )
    locked_run("full")
    schedule.every(SYNC_INTERVAL).minutes.do(locked_run, "stock")
    schedule.every().day.at(FULL_SYNC_TIME).do(locked_run, "full")
    while True:
        schedule.run_pending()
        time.sleep(30)


def main() -> int:
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "schedule"
    if mode == "schedule":
        run_scheduler()
        return 0
    if mode not in {"stores", "products", "stock", "full"}:
        print("Usage: python sqdc_sync.py [stores|products|stock|full]", file=sys.stderr)
        return 2
    return 0 if locked_run(mode) else 1


if __name__ == "__main__":
    raise SystemExit(main())
