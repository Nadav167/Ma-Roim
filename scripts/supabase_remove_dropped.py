# Delete from the database the titles drop_unknown.py dropped (no poster from any source).
# Safety: if more than 2% of the catalog would go at once, a source probably failed this week; delete nothing.
import json, requests
URL = open(".secrets/supabase_url").read().strip().rstrip("/")
KEY = open(".secrets/supabase_secret").read().strip()
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Prefer": "return=representation"}
ids = json.load(open("out/dropped_ids.json"))
# foreign-language titles the owner asked to remove (scripts/drop_foreign.py): always deleted, no size limit
foreign = json.load(open("out/foreign_ids.json")) if __import__("os").path.exists("out/foreign_ids.json") else []
present = []
for i in range(0, len(ids), 100):
    r = requests.get(f"{URL}/rest/v1/titles", params={"select": "id", "id": f"in.({','.join(ids[i:i + 100])})"},
                     headers={k: v for k, v in H.items() if k != "Prefer"}, timeout=120)
    r.raise_for_status(); present += [d["id"] for d in r.json()]
catalog = len(json.load(open("out/ma_roim_titles.json", encoding="utf-8")))
if len(present) > 0.02 * catalog:
    print(f"{len(present)} dropped titles are in the database; too many to remove safely, kept"); raise SystemExit
present = sorted(set(present) | set(foreign))
n = 0
for i in range(0, len(present), 100):
    for a in range(5):
        r = requests.delete(f"{URL}/rest/v1/titles?id=in.({','.join(present[i:i + 100])})", headers=H, timeout=120)
        if r.ok: n += len(r.json()); break
    else: raise SystemExit(f"delete failed: {r.status_code} {r.text[:200]}")
print("removed from the database:", n)
