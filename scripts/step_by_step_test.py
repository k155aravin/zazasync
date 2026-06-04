import urllib.request
import urllib.parse
import json
import time

BASE_URL = "https://zazasync-staging.k155-aravin.workers.dev"
headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "content-type": "application/json"
}

def request_json(method, path, body=None):
    url = BASE_URL + path
    print(f"-> {method} {path}...")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"<- Status {resp.status}")
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"<- Error: {e}")
        if hasattr(e, "read"):
            print("Response body:", e.read().decode("utf-8", errors="replace"))
        return None

# Step 1: Products
products = request_json("GET", "/api/products?limit=2")
if products and products.get("products"):
    slug = products["products"][0]["slug"]
    print("Found slug:", slug)
    
    # Step 2: Auth
    email = f"staging-smoke-{int(time.time())}@example.com"
    auth = request_json("POST", "/api/auth/local", {
        "email": email,
        "password": "password123",
        "firstName": "Staging",
        "lastName": "Smoke",
        "ageConfirmed": True,
        "consentAccepted": True
    })
    
    if auth:
        # Step 3: Profile
        profile = request_json("POST", "/api/profile", {
            "email": email,
            "profile": {"age": "25-34", "region": "montreal"}
        })
        
        # Step 4: Add Watchlist
        watchlist = request_json("POST", "/api/watchlist", {
            "email": email,
            "productSlug": slug,
            "ageConfirmed": True,
            "consentAccepted": True
        })

# Step 5: Get Watchlist
watch_path = f"/api/watchlist?email={urllib.parse.quote(email)}"
watch = request_json("GET", watch_path)
if watch and watch.get("items"):
    watchlist_id = watch["items"][0]["watchlist_id"]
    print("Found watchlist_id:", watchlist_id)
    
    # Step 6: Toggle Alert
    patch = request_json("PATCH", "/api/watchlist", {
        "email": email,
        "watchlistId": watchlist_id,
        "enabled": False
    })
    
    # Step 7: Get Watchlist after Patch
    after_patch = request_json("GET", watch_path)
    
    # Step 8: Delete Watchlist Item
    delete = request_json("DELETE", "/api/watchlist", {
        "email": email,
        "watchlistId": watchlist_id
    })
    
    # Step 9: Get Watchlist after Delete
    after_delete = request_json("GET", watch_path)
    print("Final watchlist items count:", len((after_delete or {}).get("items") or []))
