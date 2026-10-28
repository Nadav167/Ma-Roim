# Collect the lead (infobox) image from each title's Hebrew Wikipedia article,
# for titles that have a Hebrew article but no Hebrew poster from TMDB.
# Paced to respect Wikimedia rate limits. Output: raw/hewiki/images.json {wikidata_id: {...}}
import requests, json, time, urllib.parse, os

H = {"User-Agent": "MaRoimDataset/0.1 (nadav167@gmail.com; personal project)"}
API = "https://he.wikipedia.org/w/api.php"
os.makedirs("raw/hewiki", exist_ok=True)
OUT = "raw/hewiki/images.json"
res = json.load(open(OUT)) if os.path.exists(OUT) else {}

rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
todo = [r for r in rows if r["wikipedia_he"] and not r["poster_he"] and r["wikidata_id"] not in res]
print("todo", len(todo), flush=True)

def page_title(url):
    return urllib.parse.unquote(url.rsplit("/wiki/", 1)[1]).replace("_", " ")

def call(params):
    for a in range(8):
        r = requests.get(API, params=params, headers=H, timeout=30)
        if r.status_code == 429:
            time.sleep(int(r.headers.get("retry-after", 30)) + 2); continue
        r.raise_for_status(); return r.json()
    raise RuntimeError("rate limited")

for i in range(0, len(todo), 50):
    batch = todo[i:i + 50]
    t2r = {page_title(r["wikipedia_he"]): r for r in batch}
    d = call({"action": "query", "format": "json", "formatversion": 2, "prop": "pageimages",
              "piprop": "original|name", "pilicense": "any", "redirects": 1,
              "titles": "|".join(t2r)})
    q = d.get("query", {})
    alias = {}
    for k in ("normalized", "redirects"):
        for n in q.get(k, []):
            alias[n["to"]] = alias.get(n["from"], n["from"])
    for p in q.get("pages", []):
        src = alias.get(p["title"], p["title"])
        r = t2r.get(src) or t2r.get(p["title"])
        if not r: continue
        o = p.get("original") or {}
        res[r["wikidata_id"]] = {"file": p.get("pageimage"), "url": o.get("source"),
                                 "w": o.get("width"), "h": o.get("height"), "page": p["title"]}
    json.dump(res, open(OUT, "w"), ensure_ascii=False)
    print("done", min(i + 50, len(todo)), "/", len(todo), flush=True)
    time.sleep(1.5)

have = [v for v in res.values() if v.get("url")]
portrait = [v for v in have if v["w"] and v["h"] and v["h"] > v["w"] * 1.2]
print("with image", len(have), "portrait (poster-shaped)", len(portrait))
