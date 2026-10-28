# YouTube trailers from TMDB, in English and Hebrew. Picks per language: official Trailer > Trailer > Teaser,
# newest first. Hebrew = videos TMDB marks as Hebrew (usually Hebrew-subtitled trailers from Israeli distributors).
# Resumable: raw/tmdb/videos.jsonl. Output: adds trailer_en / trailer_he (YouTube keys) to out/ma_roim_titles.json.
import json, os, time, threading, requests
from concurrent.futures import ThreadPoolExecutor

T = open(".secrets/tmdb_token").read().strip()
s = requests.Session(); s.headers.update({"Authorization": f"Bearer {T}", "accept": "application/json"})
OUT = "raw/tmdb/videos.jsonl"
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

def get(url, params):
    for a in range(6):
        try:
            r = s.get(url, params=params, timeout=30)
            if r.status_code == 429: time.sleep(int(r.headers.get("Retry-After", 2)) + a); continue
            if r.status_code == 404: return None
            r.raise_for_status(); return r.json()
        except Exception: time.sleep(2 * (a + 1))
    return None

def work(t):
    q, kind, tid = t
    d = get(f"https://api.themoviedb.org/3/{kind}/{tid}/videos", {"include_video_language": "he,en,null"}) or {}
    vids = [[v.get("key"), v.get("iso_639_1"), v.get("type"), bool(v.get("official")), v.get("published_at") or "", v.get("name")]
            for v in d.get("results", []) if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser")]
    with lock:
        fh.write(json.dumps({"q": q, "v": vids}, ensure_ascii=False) + "\n"); n[0] += 1
        if n[0] % 5000 == 0: fh.flush(); print(f"progress {n[0]}/{len(todo)}", flush=True)

with ThreadPoolExecutor(12) as ex: list(ex.map(work, todo))
fh.close()

def best(vids, lang):
    c = [v for v in vids if v[1] == lang]
    c.sort(key=lambda v: (v[2] == "Trailer" and v[3], v[2] == "Trailer", v[3], v[4]), reverse=True)
    return c[0][0] if c else None

vids = {}
for line in open(OUT, encoding="utf-8"):
    x = json.loads(line); vids[x["q"]] = x["v"]
for r in rows:
    v = vids.get(r["wikidata_id"], [])
    r["trailer_en"] = best(v, "en") or ""
    r["trailer_he"] = best(v, "he") or ""
json.dump(rows, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
top = rows[:5000]
for k in ("trailer_en", "trailer_he"):
    print(f"{k}: {sum(1 for r in rows if r[k])} titles; top 5,000: {sum(1 for r in top if r[k]) / 50:.0f}%", flush=True)
il = [r for r in rows if "Israel" in r["country"]]
print("Israeli with Hebrew trailer:", sum(1 for r in il if r["trailer_he"]), "of", len(il), flush=True)
for t in ("Oppenheimer", "Barbie", "Fauda", "Dune: Part Two", "Inception"):
    r = next((r for r in rows if r["title"] == t), None); print(" ", t, r and (r["trailer_en"], r["trailer_he"]), flush=True)
