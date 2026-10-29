# Load tags and trailers into public.titles (columns from supabase/006 and 007).
import json, time, requests, sys
URL = open(".secrets/supabase_url").read().strip().rstrip("/")
KEY = open(".secrets/supabase_secret").read().strip()
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"}
rows = [r for r in json.load(open("out/ma_roim_titles.json", encoding="utf-8")) if "Adult" not in (r["genres"] or "")]
# id, type and title are included because they're required columns (the upsert updates them with the same values)
out = [{"id": r["wikidata_id"], "type": "tv" if r["type"] == "TV series" else "movie", "title": r["title"], "tags": r.get("tags") or [],
        "trailer_en": r.get("trailer_en") or None, "trailer_he": r.get("trailer_he") or None} for r in rows]
if "--with-stream" in sys.argv:   # needs supabase/008_where_to_watch.sql
    by = {r["wikidata_id"]: r for r in rows}
    for o in out:
        w = by[o["id"]].get("watch_il") or {}
        o["stream_il"] = sorted({p[0] for p in (w.get("stream") or []) + (w.get("free") or [])} | set(by[o["id"]].get("stream_us") or []))
# Listing rule (owner's choice): a title without any poster is not shown on the site
has_listed = requests.get(f"{URL}/rest/v1/titles?select=listed&limit=1", headers=H, timeout=60).ok
if has_listed:
    by = {r["wikidata_id"]: r for r in rows}
    for o in out:
        r = by[o["id"]]
        o["listed"] = bool(r["poster_en"] or r["poster_he"])
    print("shown:", sum(o["listed"] for o in out), "| hidden (no poster):", sum(not o["listed"] for o in out), flush=True)
for i in range(0, len(out), 500):
    for a in range(8):
        x = requests.post(f"{URL}/rest/v1/titles?on_conflict=id", headers=H, data=json.dumps(out[i:i + 500]), timeout=180)
        if x.status_code < 300: break
        print("retry", i, x.status_code, x.text[:200], flush=True); time.sleep(3 * (a + 1))
    else: sys.exit(f"failed at {i}")
print("tags and trailers loaded for", len(out), "titles")
