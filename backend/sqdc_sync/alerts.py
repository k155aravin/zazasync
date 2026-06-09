#!/usr/bin/env python3
"""Process pending ZazaSync restock events and send email alerts through Resend."""

from __future__ import annotations

import fcntl
import logging
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from typing import Any, Iterator

import requests
from dotenv import load_dotenv
from supabase import Client, create_client

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

LOCK_FILE = "/tmp/zazasync_alerts.lock"
PUBLIC_SITE_ORIGIN = os.getenv("PUBLIC_SITE_ORIGIN", "https://zazasync.com").rstrip("/")

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(ROOT / "alerts.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("alerts")


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
            log.warning("Another alert processor is active; exiting.")
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


def valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value)) and len(value) <= 254


def matching_alert(alert: dict[str, Any], event: dict[str, Any]) -> bool:
    product_matches = alert.get("product_sku") in (None, event["product_sku"])
    store_matches = alert.get("store_id") in (None, event["store_id"])
    return bool(alert.get("is_active", True) and product_matches and store_matches)


def sent_recently(db: Client, email: str, product_sku: str, store_id: str) -> bool:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    response = (
        db.table("alert_log")
        .select("id")
        .eq("user_email", email)
        .eq("product_sku", product_sku)
        .eq("store_id", store_id)
        .eq("success", True)
        .gte("sent_at", cutoff)
        .limit(1)
        .execute()
    )
    return bool(response.data)


def email_html(product_name: str, store_name: str, product_url: str) -> str:
    return f"""<!doctype html>
<html lang="en">
  <body style="font-family:Arial,sans-serif;line-height:1.5;color:#17201a">
    <h1 style="font-size:22px">Back in stock</h1>
    <p><strong>{escape(product_name)}</strong> appears available at
       <strong>{escape(store_name)}</strong> in the latest ZazaSync check.</p>
    <p><a href="{escape(product_url, quote=True)}"
          style="display:inline-block;padding:10px 16px;background:#24d338;color:#071008;text-decoration:none;border-radius:5px">
       View product
    </a></p>
    <p style="font-size:12px;color:#667069">
      Availability can change quickly. Verify directly with SQDC before travelling.
      ZazaSync does not sell cannabis.
    </p>
  </body>
</html>"""


def send_alert_email(
    to_email: str,
    product_name: str,
    store_name: str,
    product_url: str,
) -> str | None:
    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {require_env('RESEND_API_KEY')}",
            "Content-Type": "application/json",
        },
        json={
            "from": require_env("ALERT_FROM_EMAIL"),
            "to": [to_email],
            "subject": f"Back in stock: {product_name}",
            "html": email_html(product_name, store_name, product_url),
        },
        timeout=20,
    )
    text = response.text
    if not response.ok:
        raise RuntimeError(f"Resend returned {response.status_code}: {text[:500]}")
    try:
        return response.json().get("id")
    except ValueError:
        return None


def write_alert_log(
    db: Client,
    event: dict[str, Any],
    email: str,
    success: bool,
    provider_message_id: str | None = None,
    error: str | None = None,
) -> None:
    db.table("alert_log").insert(
        {
            "restock_event_id": event["id"],
            "user_email": email,
            "product_sku": event["product_sku"],
            "store_id": event["store_id"],
            "sent_at": utc_now(),
            "success": success,
            "provider_message_id": provider_message_id,
            "error": error[:2000] if error else None,
        }
    ).execute()


def process_event(
    db: Client,
    event: dict[str, Any],
    user_alerts: list[dict[str, Any]],
) -> tuple[int, int, int]:
    matches = [alert for alert in user_alerts if matching_alert(alert, event)]
    sent = 0
    skipped = 0
    failed = 0

    for alert in matches:
        email = str(alert.get("user_email", "")).strip().lower()
        if not valid_email(email):
            skipped += 1
            write_alert_log(db, event, email or "(invalid)", False, error="Invalid recipient email.")
            if alert.get("id") is not None:
                db.table("user_alerts").update({"is_active": False}).eq("id", alert["id"]).execute()
            continue
        if sent_recently(db, email, event["product_sku"], event["store_id"]):
            skipped += 1
            continue
        try:
            message_id = send_alert_email(
                email,
                event["product_name"],
                event["store_name"],
                event.get("product_url")
                or f"{PUBLIC_SITE_ORIGIN}/inventory?q={event['product_sku']}",
            )
            write_alert_log(db, event, email, True, provider_message_id=message_id)
            sent += 1
        except Exception as exc:
            failed += 1
            write_alert_log(db, event, email, False, error=str(exc))
            log.exception("Alert delivery failed for %s", email)

    if failed == 0:
        db.table("restock_events").update({"alerted": True}).eq("id", event["id"]).execute()
    return sent, skipped, failed


def process_alerts() -> bool:
    db = get_db()
    pending = db.table("pending_alerts").select("*").order("detected_at").limit(200).execute()
    alerts = db.table("user_alerts").select("*").eq("is_active", True).execute()
    events = pending.data or []
    user_alerts = alerts.data or []

    total_sent = 0
    total_skipped = 0
    total_failed = 0
    for event in events:
        sent, skipped, failed = process_event(db, event, user_alerts)
        total_sent += sent
        total_skipped += skipped
        total_failed += failed

    log.info(
        "Alert processing completed: %s events, %s sent, %s duplicate skips, %s failed",
        len(events),
        total_sent,
        total_skipped,
        total_failed,
    )
    return total_failed == 0


def main() -> int:
    try:
        with process_lock() as acquired:
            if not acquired:
                return 0
            return 0 if process_alerts() else 1
    except Exception:
        log.exception("Alert processor failed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
