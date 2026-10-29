# For the review screen: possible posters for the most popular titles that still have none,
# from a loose TMDB search (any year, movies and series). The owner picks the right one by eye.
# Cache: raw/tmdb/candidates.jsonl {"q": id, "c": [[tmdb kind/id, name, year, poster path], ...]}
import json, os, time, threading, requests
from concurrent.futures import ThreadPoolExecutor
T = open(".secrets/tmdb_token").read().strip()
s = requests.Session(); s.headers.update({"Authorization": f"Bearer {T}", "accept": "application/json"})
OUT, N = "raw/tmdb/candidates.jsonl", 600
rows = [r for r in json.load(open("out/ma_roim_titles.json", encoding="utf-8")) if not r["poster_en"] and "Adult" not in (r.get("genres") or "")]
rows.sort(key=lambda r: -(r["imdb_votes"] or 0)); rows = rows[:N]
done = set()
if os.path.exists(OUT):
    for line in open(OUT, encoding="utf-8"): done.add(json.loads(line)["q"])
todo = [r for r in rows if r["wikidata_id"] not in done]
def get(url, params):
    for a in range(5):
        try:
            x = s.get(url, params=params, timeout=30)
            if x.status_code == 429: time.sleep(2 + a); continue
            x.raise_for_status(); return x.json()
        except Exception: time.sleep(2 * (a + 1))
    return {}
def work(r):
    first = "tv" if r["type"] == "TV series" else "movie"
    c = []
    for kind in (first, "movie" if first == "tv" else "tv"):
        for h in get(f"https://api.themoviedb.org/3/search/{kind}", {"query": r["title"], "language": "en-US"}).get("results", [])[:6]:
            if h.get("poster_path"):
                date = h.get("release_date") or h.get("first_air_date") or ""
                c.append([f"{kind}/{h['id']}", h.get("title") or h.get("name"), date[:4], h["poster_path"]])
    with lock: fh.write(json.dumps({"q": r["wikidata_id"], "c": c[:6]}, ensure_ascii=False) + "\n")
lock = threading.Lock(); fh = open(OUT, "a", encoding="utf-8")
with ThreadPoolExecutor(8) as ex: list(ex.map(work, todo))
fh.close(); print("poster candidates for", len(rows), "titles")
