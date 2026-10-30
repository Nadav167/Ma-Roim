# Delete from the database the titles drop_unknown.py dropped (no poster and no IMDb votes).
import json, requests
URL = open(".secrets/supabase_url").read().strip().rstrip("/")
KEY = open(".secrets/supabase_secret").read().strip()
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Prefer": "return=representation"}
ids = json.load(open("out/dropped_ids.json"))
n = 0
for i in range(0, len(ids), 100):
    for a in range(5):
        r = requests.delete(f"{URL}/rest/v1/titles?id=in.({','.join(ids[i:i + 100])})", headers=H, timeout=120)
        if r.ok: n += len(r.json()); break
    else: raise SystemExit(f"delete failed: {r.status_code} {r.text[:200]}")
print("removed from the database:", n)
