# Titles still without any poster: the IMDb poster, looked up by the title's own IMDb ID through OMDb (omdbapi.com).
# Needs .secrets/omdb_key (skipped without it). The free key allows 1,000 lookups a day, so a big backlog
# takes a few days; answers are cached in raw/omdb/posters.json and titles with no poster are retried after 30 days.
# Rewrites out/ma_roim_titles.{json,csv}; poster_en_source = "imdb".
import json, csv, os, time, datetime, requests
# Without a key, posters already found (the cache) are still applied; only new lookups are skipped.
KEY = open(".secrets/omdb_key").read().strip() if os.path.exists(".secrets/omdb_key") else None
if not KEY: print("no OMDb key: using cached posters only, no new lookups", flush=True)
os.makedirs("raw/omdb", exist_ok=True)
OUT = "raw/omdb/posters.json"
cache = json.load(open(OUT)) if os.path.exists(OUT) else {}
today = datetime.date.today()
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
imdb_of = lambda r: r["imdb_url"].rstrip("/").rsplit("/", 1)[1] if r["imdb_url"] else None
def fresh(c): return c.get("poster") or (today - datetime.date.fromisoformat(c["checked"])).days < 30
todo = [r for r in rows if not r["poster_en"] and not r["poster_he"] and imdb_of(r) and "Adult" not in (r["genres"] or "")
        and not (imdb_of(r) in cache and fresh(cache[imdb_of(r)]))] if KEY else []
todo.sort(key=lambda r: -(r["imdb_votes"] or 0))   # most popular first, in case the daily limit runs out
print("to look up:", len(todo), flush=True)
done = 0
for r in todo:
    tt = imdb_of(r)
    try:
        x = requests.get("https://www.omdbapi.com/", params={"apikey": KEY, "i": tt}, timeout=20).json()
    except (requests.exceptions.RequestException, ValueError):
        time.sleep(2); continue
    if x.get("Response") == "False" and "limit" in (x.get("Error") or "").lower():
        print("OMDb daily limit reached; the rest continue next run", flush=True); break
    if x.get("Response") == "False" and "api key" in (x.get("Error") or "").lower():
        print("OMDb key not valid:", x.get("Error"), flush=True); break
    p = x.get("Poster")
    cache[tt] = {"poster": p.replace("._V1_SX300", "._V1_SX600") if p and p != "N/A" else None, "checked": today.isoformat()}
    done += 1
    if done % 100 == 0:
        json.dump(cache, open(OUT, "w")); print("looked up", done, flush=True)
json.dump(cache, open(OUT, "w"))
added = 0
for r in rows:
    c = cache.get(imdb_of(r) or "")
    if c and c.get("poster") and not r["poster_en"] and not r["poster_he"]:
        r["poster_en"], r["poster_en_source"] = c["poster"], "imdb"
        r["display_poster_he"] = r["poster_en"]; added += 1
json.dump(rows, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
with open("out/ma_roim_titles.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), extrasaction="ignore"); w.writeheader(); w.writerows(rows)
print("posters from IMDb (OMDb):", added, "| still without any poster:", sum(1 for r in rows if not r["poster_en"] and not r["poster_he"] and "Adult" not in (r["genres"] or "")))
