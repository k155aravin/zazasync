import re
import json
import urllib.request
from urllib.parse import urljoin

BASE = "https://zazasync.com/"
HEADERS = {"User-Agent": "zazasync-live-contract-inspector/1.0", "Accept": "text/html,application/javascript,application/json,*/*"}

def fetch(url: str) -> tuple[int, str, str, str]:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=45) as r:
        body = r.read().decode("utf-8", errors="replace")
        return r.status, r.geturl(), r.headers.get("content-type", ""), body

status, final_url, ctype, html = fetch(BASE)
assets = sorted(set(re.findall(r'(?:src|href)=["\']([^"\']+)["\']', html)))
asset_urls = [urljoin(BASE, a) for a in assets if a.startswith("/assets/") or a.startswith("assets/")]

endpoint_patterns = [
    r'["\'](/api/[^"\']+)["\']',
    r'["\'](/trpc/[^"\']+)["\']',
    r'["\'](/__[^"\']+)["\']',
    r'fetch\(([^\)]+)\)',
    r'axios\.get\(([^\)]+)\)',
]

findings = {
    "home": {"status": status, "final_url": final_url, "content_type": ctype, "bytes": len(html), "title_match": re.findall(r"<title>(.*?)</title>", html[:10000], flags=re.I|re.S)[:3]},
    "assets": asset_urls[:80],
    "endpoints_in_html": [],
    "assets_scanned": [],
}
for pat in endpoint_patterns:
    findings["endpoints_in_html"].extend(re.findall(pat, html))

for url in asset_urls[:20]:
    try:
        s, f, ct, body = fetch(url)
        endpoints = []
        for pat in endpoint_patterns:
            endpoints.extend(re.findall(pat, body))
        lower_markers = [m for m in ["d1", "sqlite", "inventory", "product", "sqdc", "store", "scrape", "search", "tanstack", "convex", "firebase", "supabase"] if m in body.lower()]
        findings["assets_scanned"].append({
            "url": url,
            "status": s,
            "content_type": ct,
            "bytes": len(body),
            "markers": lower_markers,
            "endpoints": sorted(set(endpoints))[:200],
            "sample_endpoint_contexts": []
        })
        for key in ["fetch(", "/api/", "inventory", "products", "sqdc"]:
            idx = body.lower().find(key.lower())
            if idx >= 0:
                findings["assets_scanned"][-1]["sample_endpoint_contexts"].append(body[max(0, idx-160):idx+360])
    except Exception as e:
        findings["assets_scanned"].append({"url": url, "error": repr(e)})

print(json.dumps(findings, indent=2))
