# Load tags and trailers into public.titles (columns from supabase/006 and 007).
import json, time, requests, sys
URL = open(".secrets/supabase_url").read().strip().rstrip("/")
KEY = open(".secrets/supabase_secret").read().strip()
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"}
rows = [r for r in json.load(open("out/what_to_watch_titles.json", encoding="utf-8")) if "Adult" not in (r["genres"] or "")]
# id, type and title are included because they're required columns (the upsert updates them with the same values)
out = [{"id": r["wikidata_id"], "type": "tv" if r["type"] == "TV series" else "movie", "title": r["title"], "tags": r.get("tags") or [],
        "trailer_en": r.get("trailer_en") or None, "trailer_he": r.get("trailer_he") or None} for r in rows]
for i in range(0, len(out), 2000):
    for a in range(5):
        x = requests.post(f"{URL}/rest/v1/titles?on_conflict=id", headers=H, data=json.dumps(out[i:i + 2000]), timeout=180)
        if x.status_code < 300: break
        print("retry", i, x.status_code, x.text[:200], flush=True); time.sleep(3 * (a + 1))
    else: sys.exit(f"failed at {i}")
print("tags and trailers loaded for", len(out), "titles")
