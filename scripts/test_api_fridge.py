import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def req(method, url, body=None):
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if body else {},
    )
    try:
        with urllib.request.urlopen(request) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


status, body = req("GET", f"{BASE}/users/10001/fridge")
print("GET", status, "count", len(json.loads(body)))

status, body = req(
    "POST",
    f"{BASE}/users/10001/fridge/items",
    {
        "ingredient_name": "Test Tomato",
        "quantity": 2,
        "unit": "piece",
        "storage_type": "fridge",
        "days_to_expiry": 3,
    },
)
print("ADD", status)
item = json.loads(body)

status, _ = req("DELETE", f"{BASE}/users/10001/fridge/items/{item['inventory_id']}")
print("DELETE", status)

status, body = req(
    "POST",
    f"{BASE}/users/10001/fridge/from-barcode",
    {"barcode": "8000500310427"},
)
print("BARCODE", status, json.loads(body)["ingredient_name"][:40])

status, body = req("GET", f"{BASE}/users/10001/recommendations?top_k=2")
print("RECS", status, len(json.loads(body)))
print("OK")
