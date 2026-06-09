#!/usr/bin/env python3
"""Vision fallback for SQDC catalog extraction when the primary API is unhealthy."""

from __future__ import annotations

import base64
import fcntl
import json
import logging
import os
import re
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import anthropic
import requests
from dotenv import load_dotenv
from playwright.sync_api import Page, sync_playwright
from supabase import Client, create_client

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

SQDC_BASE = os.getenv("SQDC_BASE_URL", "https://www.sqdc.ca").rstrip("/")
KNOWN_HEALTH_SKU = "697238000645"
LOCK_FILE = "/tmp/zazasync_vision_fallback.lock"
VISION_MODEL = os.getenv("VISION_MODEL", "claude-opus-4-5")
SQDC_CATEGORY_URLS = [
    f"{SQDC_BASE}/fr-CA/cannabis-seche",
    f"{SQDC_BASE}/fr-CA/pre-roules",
    f"{SQDC_BASE}/fr-CA/vapotage",
    f"{SQDC_BASE}/fr-CA/haschich",
    f"{SQDC_BASE}/fr-CA/boissons",
    f"{SQDC_BASE}/fr-CA/extraits",
]

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(ROOT / "vision_fallback.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("vision_fallback")

PRODUCT_EXTRACTION_PROMPT = """
You are analyzing a screenshot of the SQDC website (Quebec's official cannabis store).
Extract ALL cannabis products visible in this screenshot.
Return ONLY a valid JSON array. No markdown, no explanation, no code blocks.
If no products are visible, return [].

Fields per product:
- product_name: string
- brand: string or null
- category: one of flower/pre-roll/oil/capsule/edible/concentrate/beverage/accessory/other
- price_cad: number (no $ sign) or null
- thc_pct: number like 22.5 or null
- cbd_pct: number or null
- format: string like "3.5g" or null
- in_stock: true if add-to-cart visible, false if out of stock shown
- store_count: number or null

Do not invent hidden or unreadable values. Use null when a field is not visible.
If the same product appears twice in one screenshot, include it only once.
""".strip()


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
            log.warning("Another vision fallback run is active; exiting.")
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
    return session


def has_expected_stock_structure(value: Any) -> bool:
    if isinstance(value, list):
        return any(has_expected_stock_structure(item) for item in value)
    if not isinstance(value, dict):
        return False
    keys = {str(key).lower() for key in value}
    if (
        {"storeid", "instock"}.issubset(keys)
        or {"id", "instock"}.issubset(keys)
        or {"storeid", "quantity"}.issubset(keys)
    ):
        return True
    return any(has_expected_stock_structure(child) for child in value.values())


def check_api_health() -> bool:
    try:
        session = make_session()
        response = session.post(
            f"{SQDC_BASE}/api/storeinventory/storesinventory",
            json={"Sku": KNOWN_HEALTH_SKU},
            timeout=15,
        )
        response.raise_for_status()
        healthy = has_expected_stock_structure(response.json())
        if healthy:
            log.info("Primary SQDC inventory endpoint is healthy.")
        else:
            log.warning("Primary endpoint returned an unexpected structure.")
        return healthy
    except Exception as exc:
        log.warning("Primary API health check failed: %s", exc)
        return False


def dismiss_age_gate(page: Page) -> None:
    for text in ("J'ai 21 ans", "I am 21"):
        try:
            page.get_by_role("button", name=re.compile(re.escape(text), re.I)).click(timeout=2500)
            page.wait_for_timeout(750)
            return
        except Exception:
            continue


def screenshot_page(page: Page, url: str) -> list[str]:
    log.info("Capturing %s", url)
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)
    dismiss_age_gate(page)
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        log.info("Page did not reach networkidle; continuing with rendered content.")

    total_height = int(page.evaluate("Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"))
    viewport_height = int(page.viewport_size["height"])
    screenshots: list[str] = []
    for position in range(0, max(total_height, viewport_height), viewport_height):
        page.evaluate("(y) => window.scrollTo(0, y)", position)
        page.wait_for_timeout(500)
        image = page.screenshot(type="png")
        screenshots.append(base64.b64encode(image).decode("ascii"))
    log.info("Captured %s screenshots", len(screenshots))
    return screenshots


def parse_json_array(raw: str) -> list[dict[str, Any]]:
    cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start < 0 or end < start:
        raise ValueError("Vision response did not contain a JSON array.")
    parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, list):
        raise ValueError("Vision response root was not an array.")
    return [item for item in parsed if isinstance(item, dict) and item.get("product_name")]


def extract_products(client: anthropic.Anthropic, image_b64: str) -> list[dict[str, Any]]:
    response = client.messages.create(
        model=VISION_MODEL,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": PRODUCT_EXTRACTION_PROMPT},
                ],
            }
        ],
    )
    text = "\n".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    return parse_json_array(text)


def normalized_key(product: dict[str, Any]) -> tuple[str, str]:
    return (
        re.sub(r"\s+", " ", str(product.get("product_name", "")).strip()).casefold(),
        re.sub(r"\s+", " ", str(product.get("brand") or "").strip()).casefold(),
    )


def merge_products(batches: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for batch in batches:
        for product in batch:
            key = normalized_key(product)
            if not key[0]:
                continue
            if key not in merged:
                merged[key] = dict(product)
                continue
            existing = merged[key]
            for field, value in product.items():
                if existing.get(field) is None and value is not None:
                    existing[field] = value
    return list(merged.values())


def product_rows(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    now = utc_now()
    rows = []
    for product in products:
        rows.append(
            {
                "name": str(product["product_name"]).strip(),
                "brand": str(product["brand"]).strip() if product.get("brand") else None,
                "category": product.get("category"),
                "price_cad": product.get("price_cad"),
                "thc_pct": product.get("thc_pct"),
                "cbd_pct": product.get("cbd_pct"),
                "format": product.get("format"),
                "in_stock": product.get("in_stock"),
                "store_count": product.get("store_count"),
                "sync_source": "vision_fallback",
                "updated_at": now,
            }
        )
    return rows


def log_health(
    db: Client,
    success: bool,
    products_found: int,
    error: str | None = None,
) -> None:
    db.table("sync_health").insert(
        {
            "synced_at": utc_now(),
            "method": "vision_fallback",
            "success": success,
            "products_found": products_found,
            "error": error,
            "stale_since": None if success else utc_now(),
        }
    ).execute()


def run_vision_fallback(
    urls: list[str] | None = None,
    headless: bool = True,
    write_to_db: bool = True,
) -> list[dict[str, Any]]:
    db = get_db() if write_to_db else None
    client = anthropic.Anthropic(api_key=require_env("ANTHROPIC_API_KEY"))
    urls = urls or SQDC_CATEGORY_URLS
    all_batches: list[list[dict[str, Any]]] = []
    errors: list[str] = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="fr-CA",
            )
            page = context.new_page()
            for url in urls:
                try:
                    screenshots = screenshot_page(page, url)
                    for index, image in enumerate(screenshots, start=1):
                        log.info("Analyzing screenshot %s/%s for %s", index, len(screenshots), url)
                        all_batches.append(extract_products(client, image))
                        time.sleep(1)
                    time.sleep(2)
                except Exception as exc:
                    errors.append(f"{url}: {exc}")
                    log.exception("Vision extraction failed for %s", url)
            browser.close()

        products = merge_products(all_batches)
        rows = product_rows(products)
        if write_to_db:
            for index in range(0, len(rows), 200):
                assert db is not None
                db.table("products_vision").upsert(
                    rows[index : index + 200],
                    on_conflict="name,brand",
                ).execute()

        success = bool(rows) and not errors
        error = None if success else " | ".join(errors[:10]) or "No products extracted."
        if write_to_db:
            assert db is not None
            log_health(db, success, len(rows), error)
        log.info("Vision fallback completed: %s products, %s errors", len(rows), len(errors))
        return products
    except Exception as exc:
        log.exception("Vision fallback failed completely.")
        if write_to_db and db is not None:
            try:
                log_health(db, False, 0, str(exc)[:2000])
            except Exception:
                log.exception("Could not log fallback failure.")
        return []


def main() -> int:
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "auto"
    if mode not in {"auto", "force", "test"}:
        print("Usage: python vision_fallback.py [force|test]", file=sys.stderr)
        return 2

    with process_lock() as acquired:
        if not acquired:
            return 0
        if mode == "auto" and check_api_health():
            return 0
        if mode == "test":
            products = run_vision_fallback(
                [SQDC_CATEGORY_URLS[0]],
                headless=False,
                write_to_db=False,
            )
            print(json.dumps(products[:5], indent=2, ensure_ascii=False))
            return 0 if products else 1
        return 0 if run_vision_fallback() else 1


if __name__ == "__main__":
    raise SystemExit(main())
