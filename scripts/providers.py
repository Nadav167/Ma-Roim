# Where to watch in Israel: streaming / rent / buy availability per title from TMDB (data by JustWatch).
# Resumable: raw/tmdb/providers.jsonl. Output: adds "watch_il" to out/what_to_watch_titles.json:
#   {"link": <JustWatch/TMDB page>, "stream": [[id, name, logo]], "rent": [...], "buy": [...], "free": [...]}
import json, os, time, threading, collections, requests
from concurrent.futures import ThreadPoolExecutor

T = open(".secrets/tmdb_token").read().strip()
s = requests.Session(); s.headers.update({"Authorization": f"Bearer {T}", "accept": "application/json"})
OUT = "raw/tmdb/providers.jsonl"
rows = json.load(open("out/what_to_watch_titles.json", encoding="utf-8"))
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
    d = (get(f"https://api.themoviedb.org/3/{kind}/{tid}/watch/providers") or {}).get("results", {})
    keep = {c: d[c] for c in ("IL", "US") if c in d}   # Israel for the site; US kept for later
    with lock:
        fh.write(json.dumps({"q": q, "r": keep}, ensure_ascii=False) + "\n"); n[0] += 1
        if n[0] % 5000 == 0: fh.flush(); print(f"progress {n[0]}/{len(todo)}", flush=True)

with ThreadPoolExecutor(12) as ex: list(ex.map(work, todo))
fh.close()

def lst(x):
    out = sorted(x or [], key=lambda p: p.get("display_priority", 99))
    return [[p["provider_id"], p["provider_name"], p.get("logo_path")] for p in out]

prov = {}
for line in open(OUT, encoding="utf-8"):
    x = json.loads(line); prov[x["q"]] = x["r"].get("IL")
counts = collections.Counter()
for r in rows:
    il = prov.get(r["wikidata_id"])
    if not il:
        r["watch_il"] = None; continue
    w = {"link": il.get("link"), "stream": lst(il.get("flatrate")), "free": lst((il.get("free") or []) + (il.get("ads") or [])),
         "rent": lst(il.get("rent")), "buy": lst(il.get("buy"))}
    r["watch_il"] = w if any(w[k] for k in ("stream", "free", "rent", "buy")) else None
    for p in w["stream"]: counts[p[1]] += 1
json.dump(rows, open("out/what_to_watch_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
top = rows[:5000]
print(f"titles available in Israel: {sum(1 for r in rows if r['watch_il'])}; top 5,000: {sum(1 for r in top if r['watch_il']) / 50:.0f}%"
      f"; streaming in top 5,000: {sum(1 for r in top if r['watch_il'] and r['watch_il']['stream']) / 50:.0f}%", flush=True)
print("streaming services:", counts.most_common(15), flush=True)
for t in ("Fauda", "Oppenheimer", "Breaking Bad", "Shtisel", "Severance"):
    r = next((r for r in rows if r["title"] == t), None)
    print(" ", t, r and r["watch_il"] and {k: [p[1] for p in v] for k, v in r["watch_il"].items() if k != "link"}, flush=True)
