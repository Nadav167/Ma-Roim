# "People who liked X also liked Y": TMDB's recommendations for the well-known titles, used by Discover to rank its
# picks (site/index.html, rankTaste). Only titles that are in our catalog are kept, in TMDB's order (best first).
# Cache: raw/tmdb/recs.jsonl (one line per TMDB title; refreshed after 60 days, recent titles after 14).
# Writes site/taste/movie.json and site/taste/tv.json: {"ids": [our ids], "r": [[indexes into ids], ...]}.
import json, os, time, datetime, threading, requests
from concurrent.futures import ThreadPoolExecutor
T = open(".secrets/tmdb_token").read().strip()
B = "https://api.themoviedb.org/3"
OUT = "raw/tmdb/recs.jsonl"
MIN_VOTES = {"movie": 15000, "tv": 4000}     # the pool Discover ranks is 40,000+ / 8,000+; a bit wider for the links
today = datetime.date.today()
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
ours = {}   # (type, tmdb id) -> our id
for r in rows:
    if r.get("tmdb_id") and r.get("tmdb_type") in ("movie", "tv") and "Adult" not in (r["genres"] or ""):
        ours[(r["tmdb_type"], int(r["tmdb_id"]))] = r["wikidata_id"]
want = [r for r in rows if r.get("tmdb_id") and r.get("tmdb_type") in MIN_VOTES and (r["imdb_votes"] or 0) >= MIN_VOTES[r["tmdb_type"]]
        and "Adult" not in (r["genres"] or "")]
cache = {}
if os.path.exists(OUT):
    for line in open(OUT, encoding="utf-8"):
        try: c = json.loads(line); cache[c["k"]] = c
        except (ValueError, KeyError): pass
def due(r):
    c = cache.get(f'{r["tmdb_type"]}/{int(r["tmdb_id"])}')
    if not c: return True
    age = (today - datetime.date.fromisoformat(c["checked"])).days
    return age > 60 or (age > 14 and (r["year"] or 0) >= today.year - 1)
todo = [r for r in want if due(r)]
print("titles:", len(want), "| to fetch:", len(todo), flush=True)

s = requests.Session(); s.headers.update({"Authorization": f"Bearer {T}", "accept": "application/json"})
lock, fh, done = threading.Lock(), open(OUT, "a", encoding="utf-8"), [0]
def work(r):
    k = f'{r["tmdb_type"]}/{int(r["tmdb_id"])}'
    got = []
    for page in (1, 2):
        for a in range(6):
            try:
                x = s.get(f"{B}/{k}/recommendations", params={"page": page}, timeout=30)
                if x.status_code == 429: time.sleep(2 + a); continue
                if x.status_code == 404: return
                x.raise_for_status(); d = x.json(); break
            except (requests.exceptions.RequestException, ValueError): time.sleep(2 * (a + 1))
        else: return
        got += [h["id"] for h in d.get("results", [])]
        if page >= d.get("total_pages", 1): break
    with lock:
        fh.write(json.dumps({"k": k, "checked": today.isoformat(), "r": got}) + "\n"); cache[k] = {"k": k, "r": got}
        done[0] += 1
        if done[0] % 1000 == 0: fh.flush(); print("fetched", done[0], flush=True)
with ThreadPoolExecutor(10) as ex: list(ex.map(work, todo))
fh.close()

os.makedirs("site/taste", exist_ok=True)
for ty in ("movie", "tv"):
    ids, idx, lists = [], {}, []
    def ix(q):
        if q not in idx: idx[q] = len(ids); ids.append(q)
        return idx[q]
    src = [r for r in want if r["tmdb_type"] == ty]
    for r in src: ix(r["wikidata_id"])
    for r in src:
        c = cache.get(f'{ty}/{int(r["tmdb_id"])}') or {}
        recs = [ours[(ty, t)] for t in c.get("r", []) if (ty, t) in ours and ours[(ty, t)] != r["wikidata_id"]]
        lists.append([ix(q) for q in dict.fromkeys(recs)][:30])
    json.dump({"ids": ids, "r": lists}, open(f"site/taste/{ty}.json", "w"), separators=(",", ":"))
    print(ty, "titles:", len(src), "| with recommendations:", sum(1 for l in lists if l), "| file KB:", os.path.getsize(f"site/taste/{ty}.json") // 1024)
