# Tags for every title: detailed genres from Wikidata (e.g. "psychological horror") + TMDB keywords
# (e.g. "time travel", "heist", "based on novel or book"). The AI helper searches these.
# Resumable fetch: raw/tmdb/keywords.jsonl. Output: adds "tags" to out/ma_roim_titles.json.
import json, os, re, time, threading, requests
from concurrent.futures import ThreadPoolExecutor

T = open(".secrets/tmdb_token").read().strip()
s = requests.Session(); s.headers.update({"Authorization": f"Bearer {T}", "accept": "application/json"})
OUT = "raw/tmdb/keywords.jsonl"
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
todo = [(r["wikidata_id"], r["tmdb_type"], int(r["tmdb_id"])) for r in rows if r["tmdb_id"]]
done = set()
if os.path.exists(OUT):
    for line in open(OUT, encoding="utf-8"):
        try: done.add(json.loads(line)["q"])
        except Exception: pass
todo = [t for t in todo if t[0] not in done]
print("titles to fetch", len(todo), flush=True)
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
    d = get(f"https://api.themoviedb.org/3/{kind}/{tid}/keywords") or {}
    kw = [k["name"] for k in (d.get("keywords") or d.get("results") or [])]
    with lock:
        fh.write(json.dumps({"q": q, "k": kw}, ensure_ascii=False) + "\n"); n[0] += 1
        if n[0] % 5000 == 0: fh.flush(); print(f"progress {n[0]}/{len(todo)}", flush=True)

with ThreadPoolExecutor(12) as ex: list(ex.map(work, todo))
fh.close()

kws = {}
for line in open(OUT, encoding="utf-8"):
    x = json.loads(line); kws[x["q"]] = x["k"]
base = {r["wikidata_id"]: r for r in json.load(open("raw/base_titles.json", encoding="utf-8"))}

def clean_genre(g):   # "psychological horror film" -> "psychological horror"
    g = g.strip().lower()
    g = re.sub(r"\s+(film|television series|television program|tv series|fiction|series)$", "", g)
    return g if g and not g.startswith("q") else None

for r in rows:
    wd = [clean_genre(g) for g in (base.get(r["wikidata_id"], {}).get("genres") or "").split(",")]
    tags = []
    for x in [g for g in wd if g] + [k.lower() for k in kws.get(r["wikidata_id"], [])]:
        if x not in tags: tags.append(x)
    r["tags"] = tags[:40]
json.dump(rows, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
have = sum(1 for r in rows if r["tags"])
print(f"titles with tags: {have} ({have / len(rows):.0%}); psychological horror: {sum(1 for r in rows if any('psychological horror' in t for t in r['tags']))}", flush=True)
for t in ("Severance", "The Shining", "Fauda", "Inception"):
    r = next((r for r in rows if r["title"] == t), None); print(" ", t, r and r["tags"][:10], flush=True)
