# Push posters found since a snapshot to the database without a full reload.
# Usage: python3 scripts/supabase_update_posters.py <snapshot of out/ma_roim_titles.json taken before>
import json, sys, time, requests
URL = open(".secrets/supabase_url").read().strip().rstrip("/")
KEY = open(".secrets/supabase_secret").read().strip()
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"}
before = {r["wikidata_id"]: r for r in json.load(open(sys.argv[1], encoding="utf-8"))}
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
changed = [r for r in rows if "Adult" not in (r["genres"] or "") and r["poster_en"] and r["wikidata_id"] in before
           and before[r["wikidata_id"]]["poster_en"] != r["poster_en"]]
out = [{"id": r["wikidata_id"], "type": "tv" if r["type"] == "TV series" else "movie", "title": r["title"],
        "poster_en": r["poster_en"], "listed": True} for r in changed]
for i in range(0, len(out), 250):
    for a in range(6):
        x = requests.post(f"{URL}/rest/v1/titles?on_conflict=id", headers=H, data=json.dumps(out[i:i + 250]), timeout=120)
        if x.status_code < 300: break
        time.sleep(3 * (a + 1))
    else: raise SystemExit(f"failed: {x.status_code} {x.text[:200]}")
print("posters updated in the database:", len(out))
