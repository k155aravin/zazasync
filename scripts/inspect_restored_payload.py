import re
import urllib.request

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

for path in ["/", "/inventory", "/new-drops", "/radar-picks"]:
    url = "https://zazasync.com" + path
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            text = response.read().decode("utf-8", "replace")
    except Exception as exc:
        print("ERR", path, repr(exc))
        continue

    print("\n===", path, "len", len(text), "===")
    for needle in [
        "sqdcProduct",
        "productsTracked",
        "marketplace",
        "newestProducts",
        "radarPicks",
        "availability",
        "storeDisplayName",
        "price",
        "sqdcUrl",
        "sourceProductId",
        "productId",
        "snapshotId",
    ]:
        index = text.find(needle)
        if index != -1:
            snippet = text[max(0, index - 500): index + 1400]
            snippet = re.sub(r"\s+", " ", snippet)
            print("\n--", needle, "--")
            print(snippet[:1900])
