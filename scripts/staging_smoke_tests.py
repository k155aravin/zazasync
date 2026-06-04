#!/usr/bin/env python3
import json
import sys
import time
from pathlib import Path
from urllib import request, parse, error

import os
BASE_URL = os.environ.get("BASE_URL", "https://zazasync-staging.k155-aravin.workers.dev")
OUT_PATH = Path(os.environ.get("OUT_PATH", "/home/ubuntu/zazasync_repo/staging_smoke_test_results.json"))

def http(method, path, body=None, expected=(200,), timeout=15):
    url = BASE_URL + path
    data = None
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["content-type"] = "application/json"
    
    req = request.Request(url, data=data, headers=headers, method=method)
    started = time.time()
    try:
        print(f"  [HTTP] {method} {path}...")
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            text = raw.decode("utf-8", errors="replace")
            status = resp.status
            ok = status in expected
            print(f"  [HTTP] Response {status} ({len(raw)} bytes)")
            return {"ok": ok, "status": status, "url": url, "ms": round((time.time() - started) * 1000), "text": text}
    except error.HTTPError as exc:
        raw = exc.read(1024)
        text = raw.decode("utf-8", errors="replace")
        print(f"  [HTTP] HTTPError {exc.code}")
        return {"ok": exc.code in expected, "status": exc.code, "url": url, "ms": round((time.time() - started) * 1000), "text": text}
    except Exception as exc:
        print(f"  [HTTP] Exception: {exc}")
        return {"ok": False, "status": None, "url": url, "ms": round((time.time() - started) * 1000), "error": str(exc), "text": ""}

def parse_json(step):
    try:
        return json.loads(step.get("text") or "{}")
    except Exception as exc:
        step["json_error"] = str(exc)
        return {}

def assert_condition(results, name, condition, details):
    results.append({"name": name, "ok": bool(condition), **details})

def main():
    print("Starting verbose smoke tests...")
    results = []
    route_paths = [
        "/", "/signin", "/auth", "/onboarding", "/watchlist", "/inventory",
        "/new-drops", "/back-in-stock", "/stores", "/privacy", "/terms",
        "/contact", "/responsible-use"
    ]
    
    for path in route_paths:
        print(f"Testing route: {path}")
        step = http("GET", path)
        title = ""
        marker = "<title>"
        if marker in step.get("text", ""):
            title = step["text"].split(marker, 1)[1].split("</title>", 1)[0]
        assert_condition(results, f"route {path}", step["ok"] and "ZazaSync" in step.get("text", ""), {
            "status": step["status"], "ms": step["ms"], "title": title, "url": step["url"]
        })

    print("Testing products API...")
    products_step = http("GET", f"/api/products?limit=10&smoke={int(time.time())}")
    products = parse_json(products_step)
    product_rows = products.get("products") or []
    assert_condition(results, "api products list", products_step["ok"] and isinstance(product_rows, list), {
        "status": products_step["status"], "count": len(product_rows), "url": products_step["url"]
    })

    slug = None
    if product_rows:
        slug = product_rows[0].get("slug")
    
    if not slug:
        print("Warning: No product slug found!")
        assert_condition(results, "product slug available", False, {
            "reason": "No products returned from staging /api/products, so product detail and watchlist API tests cannot complete."
        })
    else:
        print(f"Testing product detail API for slug: {slug}")
        detail_step = http("GET", "/api/products/" + parse.quote(slug))
        detail = parse_json(detail_step)
        assert_condition(results, "api product detail", detail_step["ok"] and bool(detail.get("product")), {
            "status": detail_step["status"], "slug": slug, "inventory_count": len(detail.get("inventory") or []), "url": detail_step["url"]
        })

        print("Testing Google Auth URL generator...")
        google_url_step = http("GET", "/api/auth/google/url", expected=(200, 503))
        google_url_data = parse_json(google_url_step)
        assert_condition(results, "api auth google url generator", google_url_step["ok"], {
            "status": google_url_step["status"], "has_url": "url" in google_url_data or "error" in google_url_data
        })

        email = f"staging-smoke-{int(time.time())}@example.com"
        print(f"Testing auth API with email: {email}")
        auth_step = http("POST", "/api/auth/local", {
            "email": email,
            "password": "password123",
            "firstName": "Staging",
            "lastName": "Smoke",
            "ageConfirmed": True,
            "consentAccepted": True,
        })
        auth = parse_json(auth_step)
        assert_condition(results, "api auth local", auth_step["ok"] and auth.get("ok") is True and (auth.get("user") or {}).get("email") == email, {
            "status": auth_step["status"], "email": email, "url": auth_step["url"]
        })

        print("Testing profile API...")
        profile_body = {"age": "25-34", "region": "montreal", "freq": "daily", "lang": "en-CA", "stores": ["staging"]}
        profile_step = http("POST", "/api/profile", {"email": email, "profile": profile_body})
        profile = parse_json(profile_step)
        assert_condition(results, "api profile save", profile_step["ok"] and profile.get("ok") is True, {
            "status": profile_step["status"], "url": profile_step["url"]
        })

        print("Testing watchlist add...")
        add1_step = http("POST", "/api/watchlist", {"email": email, "productSlug": slug, "ageConfirmed": True, "consentAccepted": True}, expected=(200, 201))
        add1 = parse_json(add1_step)
        
        print("Testing watchlist add (idempotent duplicate)...")
        add2_step = http("POST", "/api/watchlist", {"email": email, "productSlug": slug, "ageConfirmed": True, "consentAccepted": True}, expected=(200, 201))
        add2 = parse_json(add2_step)
        
        assert_condition(results, "api watchlist add idempotent", add1_step["ok"] and add2_step["ok"] and add1.get("watchlistId") == add2.get("watchlistId"), {
            "status1": add1_step["status"], "status2": add2_step["status"], "watchlist_id_1": add1.get("watchlistId"), "watchlist_id_2": add2.get("watchlistId")
        })

        watch_path = "/api/watchlist?email=" + parse.quote(email)
        print("Testing watchlist load...")
        watch_step = http("GET", watch_path)
        watch = parse_json(watch_step)
        items = watch.get("items") or []
        watchlist_id = items[0].get("watchlist_id") if items else None
        onboarding_saved = bool((watch.get("user") or {}).get("onboarding_json"))
        
        assert_condition(results, "api watchlist load", watch_step["ok"] and len(items) == 1 and onboarding_saved, {
            "status": watch_step["status"], "items": len(items), "watchlist_id": watchlist_id, "onboarding_saved": onboarding_saved, "url": watch_step["url"]
        })

        if watchlist_id:
            print("Testing watchlist alert toggle...")
            patch_step = http("PATCH", "/api/watchlist", {"email": email, "watchlistId": watchlist_id, "enabled": False})
            patch = parse_json(patch_step)
            
            after_patch = parse_json(http("GET", watch_path))
            patched_value = ((after_patch.get("items") or [{}])[0]).get("alert_on_restock")
            assert_condition(results, "api watchlist alert toggle", patch_step["ok"] and patch.get("ok") is True and int(patched_value) == 0, {
                "status": patch_step["status"], "patched_alert_on_restock": patched_value
            })

            print("Testing watchlist delete...")
            delete_step = http("DELETE", "/api/watchlist", {"email": email, "watchlistId": watchlist_id})
            deleted = parse_json(delete_step)
            
            after_delete = parse_json(http("GET", watch_path))
            remaining = len(after_delete.get("items") or [])
            assert_condition(results, "api watchlist delete", delete_step["ok"] and deleted.get("ok") is True and remaining == 0, {
                "status": delete_step["status"], "remaining": remaining
            })

    summary = {
        "base_url": BASE_URL,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "passed": sum(1 for row in results if row["ok"]),
        "failed": sum(1 for row in results if not row["ok"]),
        "results": results,
    }
    
    OUT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Done! Passed: {summary['passed']}, Failed: {summary['failed']}")
    return 0 if summary["failed"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
