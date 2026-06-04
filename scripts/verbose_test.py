import urllib.request
import urllib.error
import json
import time

url = "https://zazasync-staging.k155-aravin.workers.dev/"
headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print("1. Sending GET to home...")
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        print("Status:", resp.status)
        print("Read first 100 bytes:", resp.read(100))
except Exception as e:
    print("Error:", e)

print("2. Sending GET to products api...")
req = urllib.request.Request(url + "api/products?limit=2", headers=headers)
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        print("Status:", resp.status)
        print("Read response:")
        print(resp.read().decode("utf-8")[:200])
except Exception as e:
    print("Error:", e)
