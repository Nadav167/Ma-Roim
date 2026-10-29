# Titles still without any poster: use the lead (infobox) image of the title's own English Wikipedia article
# (linked from Wikidata). Only poster-shaped images count (portrait, not SVG logos). For movies that's
# almost always the poster. Cache: raw/enwiki/images.json. Rewrites out/ma_roim_titles.{json,csv};
# poster_en_source = "enwiki". Wikipedia hosts these posters under fair use; like the Hebrew ones, treat as provisional.
import json, csv, os, time, urllib.parse, requests
H = {"User-Agent": "MaRoimDataset/0.1 (nadav167@gmail.com; personal project)"}
API = "https://en.wikipedia.org/w/api.php"
os.makedirs("raw/enwiki", exist_ok=True)
OUT = "raw/enwiki/images.json"
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
todo = [r for r in rows if r["wikipedia_en"] and not r["poster_en"] and not r["poster_he"] and r["wikidata_id"] not in res]
print("to look up", len(todo), flush=True)
page_title = lambda url: urllib.parse.unquote(url.rsplit("/wiki/", 1)[1]).replace("_", " ")
def call(params):
    for a in range(8):
        r = requests.get(API, params=params, headers=H, timeout=30)
        if r.status_code == 429: time.sleep(int(r.headers.get("retry-after", 30)) + 2); continue
        r.raise_for_status(); return r.json()
    raise RuntimeError("rate limited")
for i in range(0, len(todo), 50):
    batch = todo[i:i + 50]
    try:
        requests.head(API, headers=H, timeout=15) if i == 0 else None
    except requests.exceptions.RequestException:
        print("English Wikipedia isn't reachable from here; skipping (uses what's cached)", flush=True); break
    t2r = {page_title(r["wikipedia_en"]): r for r in batch}
    d = call({"action": "query", "format": "json", "formatversion": 2, "prop": "pageimages", "piprop": "original|thumbnail|name",
              "pithumbsize": 500, "pilicense": "any", "redirects": 1, "titles": "|".join(t2r)})
    q = d.get("query", {}); alias = {}
    for k in ("normalized", "redirects"):
        for n in q.get(k, []): alias[n["to"]] = alias.get(n["from"], n["from"])
    for p in q.get("pages", []):
        r = t2r.get(alias.get(p["title"], p["title"])) or t2r.get(p["title"])
        if not r: continue
        o, th = p.get("original") or {}, p.get("thumbnail") or {}
        res[r["wikidata_id"]] = {"file": p.get("pageimage"), "url": th.get("source") or o.get("source"), "w": o.get("width"), "h": o.get("height")}
    for r in batch: res.setdefault(r["wikidata_id"], {})
    json.dump(res, open(OUT, "w"), ensure_ascii=False)
    if (i // 50) % 20 == 0: print("looked up", min(i + 50, len(todo)), "/", len(todo), flush=True)
    time.sleep(1)
added = 0
for r in rows:
    v = res.get(r["wikidata_id"]) or {}
    if r["poster_en"] or r["poster_he"] or not v.get("url") or not v.get("w") or not v.get("h"): continue
    if v["h"] <= v["w"] * 1.2 or (v.get("file") or "").lower().endswith(".svg"): continue   # logos and title cards
    r["poster_en"], r["poster_en_source"] = v["url"], "enwiki"
    r["display_poster_he"] = r["poster_he"] or r["poster_en"]
    added += 1
json.dump(rows, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
with open("out/ma_roim_titles.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), extrasaction="ignore"); w.writeheader(); w.writerows(rows)
print("posters from English Wikipedia:", added, "| still without any poster:", sum(1 for r in rows if not r["poster_en"] and not r["poster_he"]))
