# Israeli or American, by language: of the titles connected to Israel (Israel among their countries),
# one where any Hebrew is spoken counts as Israeli, one without Hebrew counts as American.
# Titles with no connection to Israel stay as they are. Languages from TMDB (original + spoken).
# Resumable: raw/tmdb/languages.jsonl. Rewrites "country" in out/ma_roim_titles.json.
import json, os, time, threading, requests
from concurrent.futures import ThreadPoolExecutor

T = open(".secrets/tmdb_token").read().strip()
s = requests.Session(); s.headers.update({"Authorization": f"Bearer {T}", "accept": "application/json"})
OUT = "raw/tmdb/languages.jsonl"
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
israel = lambda r: "Israel" in (r.get("country") or "") or "Israel" in (r.get("all_countries") or "")
todo = {(r["tmdb_type"], int(r["tmdb_id"])) for r in rows if r["tmdb_id"] and r["tmdb_type"] and israel(r)}
done = set()
if os.path.exists(OUT):
    for line in open(OUT, encoding="utf-8"):
        try: x = json.loads(line); done.add((x["k"], x["id"]))
        except Exception: pass
todo = [t for t in todo if t not in done]
print("titles to fetch", len(todo), flush=True)
lock = threading.Lock(); fh = open(OUT, "a", encoding="utf-8")

def get(url):
    for a in range(6):
        try:
            r = s.get(url, timeout=30)
            if r.status_code == 429: time.sleep(int(r.headers.get("Retry-After", 2)) + a); continue
            if r.status_code == 404: return {}
            r.raise_for_status(); return r.json()
        except Exception: time.sleep(2 * (a + 1))
    return None

def work(t):
    kind, tid = t
    d = get(f"https://api.themoviedb.org/3/{kind}/{tid}")
    if d is None: return   # try again next run
    langs = {x.get("iso_639_1") for x in d.get("spoken_languages", [])} | set(d.get("languages") or []) | {d.get("original_language")}
    with lock: fh.write(json.dumps({"k": kind, "id": tid, "l": sorted(l for l in langs if l)}) + "\n")

with ThreadPoolExecutor(12) as ex: list(ex.map(work, todo))
fh.close()

langs = {}
for line in open(OUT, encoding="utf-8"):
    x = json.loads(line); langs[(x["k"], x["id"])] = x["l"]
moved = {"Israel": 0, "United States": 0}
for r in rows:
    if not (r["tmdb_id"] and r["tmdb_type"] and israel(r)): continue
    l = langs.get((r["tmdb_type"], int(r["tmdb_id"])))
    if not l: continue   # no language data: leave it
    new = "Israel" if "he" in l else "United States"
    if r["country"] != new: moved[new] += 1; r["country"] = new
json.dump(rows, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
print("now Israeli:", moved["Israel"], "now American:", moved["United States"], flush=True)
