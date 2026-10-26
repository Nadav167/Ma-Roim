# Headshots for cast and crew from TMDB. For each title, fetch TMDB's cast/crew (which include profile photos)
# and match people to our IMDb-based credits by name within that title.
# Resumable: raw/tmdb/credits.jsonl. Output: adds "photo" (TMDB profile path) to out/people.json.
import json, os, re, time, threading, unicodedata, requests
from concurrent.futures import ThreadPoolExecutor

T = open(".secrets/tmdb_token").read().strip()
s = requests.Session(); s.headers.update({"Authorization": f"Bearer {T}", "accept": "application/json"})
OUT = "raw/tmdb/credits.jsonl"

rows = json.load(open("out/what_to_watch_titles.json", encoding="utf-8"))
todo = [(r["wikidata_id"], r["tmdb_type"], int(r["tmdb_id"])) for r in rows if r["tmdb_id"]]
done = set()
if os.path.exists(OUT):
    for line in open(OUT, encoding="utf-8"):
        try: done.add(json.loads(line)["q"])
        except Exception: pass
todo = [t for t in todo if t[0] not in done]
print("titles to fetch", len(todo), "already done", len(done), flush=True)

lock = threading.Lock(); fh = open(OUT, "a", encoding="utf-8"); n = [0]
def get(url):
    for a in range(6):
        try:
            r = s.get(url, timeout=30)
            if r.status_code == 429: time.sleep(int(r.headers.get("Retry-After", 2)) + a); continue
            if r.status_code == 404: return None
            r.raise_for_status(); return r.json()
        except Exception: time.sleep(2 * (a + 1))
    return None

def work(t):
    q, kind, tid = t
    path = f"https://api.themoviedb.org/3/movie/{tid}/credits" if kind == "movie" else f"https://api.themoviedb.org/3/tv/{tid}/aggregate_credits"
    d = get(path) or {}
    people = [[p.get("name"), p.get("profile_path")] for p in (d.get("cast") or []) + (d.get("crew") or []) if p.get("profile_path")]
    with lock:
        fh.write(json.dumps({"q": q, "p": people}, ensure_ascii=False) + "\n")
        n[0] += 1
        if n[0] % 2000 == 0: fh.flush(); print(f"progress {n[0]}/{len(todo)}", flush=True)

with ThreadPoolExecutor(12) as ex: list(ex.map(work, todo))
fh.close()

def norm(name):
    name = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", name).strip()

photos_by_title = {}
for line in open(OUT, encoding="utf-8"):
    x = json.loads(line)
    photos_by_title[x["q"]] = {norm(nm): p for nm, p in x["p"]}
people = {p["id"]: p for p in json.load(open("out/people.json", encoding="utf-8"))}
matched = 0
for c in json.load(open("out/credits.json", encoding="utf-8")):
    p = people.get(c["person_id"])
    if not p or p.get("photo"): continue
    ph = photos_by_title.get(c["title_id"], {}).get(norm(p["name"]))
    if ph: p["photo"] = ph; matched += 1
json.dump(list(people.values()), open("out/people.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"people with photos: {matched} of {len(people)}", flush=True)
for nm in ("James McAvoy", "Lior Raz", "Christopher Nolan", "Gal Gadot"):
    print(" ", [(p["name"], p.get("photo")) for p in people.values() if p["name"] == nm][:1], flush=True)
