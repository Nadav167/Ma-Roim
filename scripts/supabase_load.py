# Load the catalog into Supabase (table public.titles) via the REST API, upserting in batches.
# Needs .secrets/supabase_url and .secrets/supabase_secret (secret/service key; never commit).
import json, time, requests

URL = open(".secrets/supabase_url").read().strip().rstrip("/")
KEY = open(".secrets/supabase_secret").read().strip()
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
     "Prefer": "resolution=merge-duplicates,return=minimal"}

rows = json.load(open("out/what_to_watch_titles.json", encoding="utf-8"))

def num(v, cast):
    try: return cast(v) if v not in ("", None) else None
    except (TypeError, ValueError): return None

out, seen_imdb = [], set()
for r in rows:
    if "Adult" in (r["genres"] or ""):
        continue
    imdb = r["imdb_url"].rstrip("/").rsplit("/", 1)[1] if r["imdb_url"] else None
    if imdb in seen_imdb: imdb = None
    if imdb: seen_imdb.add(imdb)
    out.append({
        "id": r["wikidata_id"], "imdb_id": imdb, "tmdb_id": num(r["tmdb_id"], int), "tmdb_type": r["tmdb_type"] or None,
        "type": "tv" if r["type"] == "TV series" else "movie",
        "title": r["title"], "title_he": r["title_he"] or None, "original_title": r["original_title"] or None,
        "year": num(r["year"], int), "end_year": num(r["end_year"], int),
        "israeli": "Israel" in r["country"], "us": "United States" in r["country"],
        "genres": [g for g in (r["genres"] or "").split(", ") if g],
        "runtime_min": num(r["runtime_min"], int), "seasons": num(r["seasons"], int), "episodes": num(r["episodes"], int),
        "imdb_rating": num(r["imdb_rating"], float), "imdb_votes": num(r["imdb_votes"], int) or 0,
        "poster_en": r["poster_en"] or None, "poster_he": r["poster_he"] or None, "backdrop": r["backdrop"] or None,
        "overview_en": r["overview_en"] or None, "overview_he": r["overview_he"] or None,
        "imdb_url": r["imdb_url"] or None, "wikipedia_en": r["wikipedia_en"] or None, "wikipedia_he": r["wikipedia_he"] or None,
        "metacritic_url": r["metacritic_url"] or None,
        "rt_score": num(r.get("rt_score"), int), "mc_score": num(r.get("mc_score"), int), "rt_url": r.get("rt_url") or None,
        "same_name_flag": r["same_name_flag"] or None,
    })
print("rows to load", len(out), flush=True)

B = 1000
for i in range(0, len(out), B):
    batch = out[i:i + B]
    for a in range(5):
        r = requests.post(f"{URL}/rest/v1/titles?on_conflict=id", headers=H, data=json.dumps(batch), timeout=120)
        if r.status_code < 300: break
        print("retry", i, r.status_code, r.text[:300], flush=True); time.sleep(3 * (a + 1))
    else:
        raise SystemExit(f"failed at batch {i}")
    print("loaded", min(i + B, len(out)), flush=True)

c = requests.get(f"{URL}/rest/v1/titles?select=id", headers={**H, "Prefer": "count=exact", "Range": "0-0"}, timeout=60)
print("rows in database:", c.headers.get("content-range"))
