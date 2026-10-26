# Load people and credits into Supabase (tables from supabase/003_cast.sql). Upserts, so it can be rerun.
import json, time, requests, sys

URL = open(".secrets/supabase_url").read().strip().rstrip("/")
KEY = open(".secrets/supabase_secret").read().strip()
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
     "Prefer": "resolution=merge-duplicates,return=minimal"}

def load(table, rows, conflict, B=2000):
    for i in range(0, len(rows), B):
        for a in range(6):
            r = requests.post(f"{URL}/rest/v1/{table}?on_conflict={conflict}", headers=H, data=json.dumps(rows[i:i + B]), timeout=180)
            if r.status_code < 300: break
            print("retry", table, i, r.status_code, r.text[:200], flush=True); time.sleep(3 * (a + 1))
        else:
            sys.exit(f"failed: {table} at {i}")
        if (i // B) % 25 == 0: print(f"{table}: {min(i + B, len(rows))}/{len(rows)}", flush=True)
    c = requests.get(f"{URL}/rest/v1/{table}?select=*", headers={**H, "Prefer": "count=exact", "Range": "0-0"}, timeout=60)
    print(f"{table} in database:", c.headers.get("content-range"), flush=True)

# Only titles that exist in the database (adult titles were left out)
ids, last = set(), ""
while True:   # the API returns at most 1,000 rows per request, so page by id
    r = requests.get(f"{URL}/rest/v1/titles?select=id&order=id&id=gt.{last}&limit=1000", headers=H, timeout=120)
    r.raise_for_status(); batch = r.json()
    if not batch: break
    ids |= {x["id"] for x in batch}; last = batch[-1]["id"]
credits = [c for c in json.load(open("out/credits.json", encoding="utf-8")) if c["title_id"] in ids]
# one row per (title, person, role): keep the best billing position
best = {}
for c in credits:
    k = (c["title_id"], c["person_id"], c["role"])
    if k not in best or c["ord"] < best[k]["ord"]: best[k] = c
credits = list(best.values())
used = {c["person_id"] for c in credits}
people = [p for p in json.load(open("out/people.json", encoding="utf-8")) if p["id"] in used]
print("titles", len(ids), "people", len(people), "credits", len(credits), flush=True)
load("people", people, "id")
if "--people-only" not in sys.argv:   # rerun with --people-only after updating names (e.g. Hebrew names)
    load("credits", credits, "title_id,person_id,role")
