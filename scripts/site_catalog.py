# Build the website catalog.
#   site/catalog.json            – real site: poster/backdrop URLs from TMDB, top titles + search index
#   build/preview/catalog.json   – artifact preview: same shape, images embedded as data: URIs
#                                  (artifact pages can't load images from other hosts)
import json, os, base64, sys, requests, datetime
from concurrent.futures import ThreadPoolExecutor

rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
rows = [r for r in rows if "Adult" not in (r["genres"] or "")]

HE_GENRE = {
    "Drama": "דרמה", "Comedy": "קומדיה", "Documentary": "תיעודי", "Thriller": "מותחן", "Action": "אקשן",
    "Horror": "אימה", "Crime": "פשע", "Romance": "רומנטיקה", "TV Movie": "סרט טלוויזיה", "Family": "משפחה",
    "Animation": "אנימציה", "Adventure": "הרפתקאות", "Mystery": "מסתורין", "Science Fiction": "מדע בדיוני",
    "Fantasy": "פנטזיה", "Music": "מוזיקה", "Reality": "ריאליטי", "Sci-Fi & Fantasy": "מדע בדיוני ופנטזיה",
    "Action & Adventure": "אקשן והרפתקאות", "History": "היסטוריה", "Kids": "ילדים", "War": "מלחמה",
    "Western": "מערבון", "News": "חדשות", "Talk": "טוק שואו", "Soap": "אופרת סבון",
    "War & Politics": "מלחמה ופוליטיקה", "Biography": "ביוגרפיה", "Sport": "ספורט", "Musical": "מחזמר",
}

def slim(r):
    g = [x for x in (r["genres"] or "").split(", ") if x][:3]
    return {
        "id": r["wikidata_id"], "t": r["title"], "th": r["title_he"], "ty": "tv" if r["type"] == "TV series" else "movie",
        "y": r["year"], "ye": r["end_year"] or None, "il": "Israel" in r["country"],
        "g": g, "rt": r["imdb_rating"] or None, "v": r["imdb_votes"] or 0,
        "rs": r.get("rt_score") if r.get("rt_score") != "" else None, "ms": r.get("mc_score") if r.get("mc_score") != "" else None,
        "ru": r.get("rt_url") or None, "tr": r.get("trailer_en") or None, "trh": r.get("trailer_he") or None,
        "rm": r["runtime_min"] or None, "s": r["seasons"] or None,
        "p": r["poster_en"] or None, "ph": r["poster_he"] or None, "b": r["backdrop"] or None,
        "o": r["overview_en"] or "", "oh": r["overview_he"] or "",
        "imdb": r["imdb_url"] or None, "we": r["wikipedia_en"] or None, "wh": r["wikipedia_he"] or None,
        "mc": r["metacritic_url"] or None,
    }

has_poster = [r for r in rows if r["poster_en"]]
by_votes = sorted(has_poster, key=lambda r: -(r["imdb_votes"] or 0))
def top(pred, n=20):
    return [r["wikidata_id"] for r in by_votes if pred(r)][:n]
def g(r, *names): return any(n in (r["genres"] or "") for n in names)

shelves = [
    ("new", "New and popular", "חדש ופופולרי", top(lambda r: r["year"] >= datetime.date.today().year - 2)),
    ("movies", "Popular movies", "סרטים פופולריים", top(lambda r: r["type"] == "Movie")),
    ("series", "Popular series", "סדרות פופולריות", top(lambda r: r["type"] == "TV series")),
    ("il-series", "Israeli series", "סדרות ישראליות", top(lambda r: "Israel" in r["country"] and r["type"] == "TV series")),
    ("il-movies", "Israeli movies", "סרטים ישראליים", top(lambda r: "Israel" in r["country"] and r["type"] == "Movie")),
    ("top", "Highest rated", "הדירוג הגבוה ביותר",
     [r["wikidata_id"] for r in sorted([r for r in has_poster if (r["imdb_votes"] or 0) >= 250000],
                                       key=lambda r: -(r["imdb_rating"] or 0))][:20]),
    ("comedy", "Comedy", "קומדיה", top(lambda r: g(r, "Comedy") and not g(r, "Animation"))),
    ("crime", "Crime and thrillers", "פשע ומתח", top(lambda r: g(r, "Crime", "Thriller"))),
    ("scifi", "Sci-fi and fantasy", "מדע בדיוני ופנטזיה", top(lambda r: g(r, "Science Fiction", "Sci-Fi", "Fantasy"))),
    ("anim", "Animation", "אנימציה", top(lambda r: g(r, "Animation"))),
    ("docs", "Documentaries", "תיעודי", top(lambda r: g(r, "Documentary"))),
]
hero = [r["wikidata_id"] for r in by_votes if r["year"] >= 2023 and r["backdrop"] and r["overview_en"]][:5]
shelf_ids = {i for s in shelves for i in s[3]} | set(hero)

mode = sys.argv[1] if len(sys.argv) > 1 else "site"
n_index = 6000 if mode == "site" else 3000
index_ids = [r["wikidata_id"] for r in by_votes[:n_index]]
keep = shelf_ids | set(index_ids)
items = {r["wikidata_id"]: slim(r) for r in rows if r["wikidata_id"] in keep}

# Ship the cast of home-page titles with the page so it shows instantly (others load from the database).
if os.path.exists("out/credits.json") and os.path.exists("out/people.json"):
    ppl = {p["id"]: p for p in json.load(open("out/people.json", encoding="utf-8"))}
    LIMIT = {"cast": 12, "director": 4, "creator": 4, "writer": 3, "composer": 2}
    per = {}
    for c in json.load(open("out/credits.json", encoding="utf-8")):
        if c["title_id"] in shelf_ids and c["person_id"] in ppl:
            per.setdefault(c["title_id"], []).append(c)
    for tid, cs in per.items():
        cs.sort(key=lambda c: c["ord"]); seen = set(); out = []; count = {}
        for c in cs:
            k = (c["person_id"], c["role"])
            if k in seen or count.get(c["role"], 0) >= LIMIT[c["role"]]: continue
            seen.add(k); count[c["role"]] = count.get(c["role"], 0) + 1
            p = ppl[c["person_id"]]
            out.append([c["role"], c["ord"], c["character"], p["id"], p["name"], p.get("name_he"), p.get("photo")])
        if tid in items: items[tid]["cr"] = out

if mode == "preview":
    # Embed images only for shelf titles; search-only titles get a text card.
    sess = requests.Session()
    def fetch(url):
        try:
            b = sess.get(url, timeout=30); b.raise_for_status()
            return "data:image/jpeg;base64," + base64.b64encode(b.content).decode()
        except Exception:
            return None
    jobs = []
    for i, it in items.items():
        if i in shelf_ids:
            for k, size in (("p", "w185"), ("ph", "w185")):
                if it[k]: jobs.append((i, k, it[k].replace("/w500/", f"/{size}/")))
            if i in hero and it["b"]: jobs.append((i, "b", it["b"].replace("/w1280/", "/w1280/")))
        else:
            it["p"] = it["ph"] = None
        if i not in hero: it["b"] = None
    with ThreadPoolExecutor(12) as ex:
        res = list(ex.map(lambda j: (j[0], j[1], fetch(j[2])), jobs))
    for i, k, d in res: items[i][k] = d
    out = "build/preview/catalog.json"
else:
    out = "site/catalog.json"

cat = {"shelves": [{"key": k, "en": en, "he": he, "ids": ids} for k, en, he, ids in shelves],
       "hero": hero, "items": items, "genres_he": HE_GENRE, "index": index_ids}
os.makedirs(os.path.dirname(out), exist_ok=True)
if mode == "site":
    # Split for a light first load:
    #   home.json  – rows, hero and full details of the home-page titles (what the first screen needs)
    #   index.json – the 6,000 most popular titles with card fields only, loaded in the background for instant search
    # Everything else (synopsis, trailer, cast of other titles) is fetched from the database when a title is opened.
    CARD = ("t", "th", "ty", "y", "ye", "il", "g", "rt", "v", "p", "ph", "rs", "ms")
    home_items = {i: {**items[i], "f": 1} for i in shelf_ids if i in items}
    # where to watch in Israel for home titles (same compact shape as site/watch/NN.json; null = not available)
    by_id = {r["wikidata_id"]: r for r in rows}
    for i, it in home_items.items():
        w = by_id[i].get("watch_il") or {}
        if "watch_il" not in by_id[i]: continue
        if not w and not by_id[i].get("network_il") and not by_id[i].get("stream_us"): it["wa"] = None; continue
        e = {"k": f"{by_id[i]['tmdb_type']}/{by_id[i]['tmdb_id']}"} if by_id[i].get("tmdb_id") else {}
        if by_id[i].get("network_il"): e["o"] = by_id[i]["network_il"]
        for src, dst in (("stream", "s"), ("free", "f"), ("rent", "r"), ("buy", "b")):
            ids = list(dict.fromkeys(p[0] for p in (w.get(src) or [])))
            if ids: e[dst] = ids
        if by_id[i].get("stream_us"): e["u"] = by_id[i]["stream_us"]
        it["wa"] = e
    home = {k: v for k, v in cat.items() if k not in ("items", "index")}
    home["items"] = home_items
    index = {"ids": index_ids, "items": {i: {k: items[i].get(k) for k in CARD if items[i].get(k) not in (None, "", [])} for i in index_ids if i not in home_items}}
    for name, obj in (("site/home.json", home), ("site/index.json", index)):
        json.dump(obj, open(name, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print(name, round(os.path.getsize(name) / 1e6, 2), "MB")
    if os.path.exists("site/catalog.json"): os.remove("site/catalog.json")
else:
    json.dump(cat, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(out, len(items), "items", round(os.path.getsize(out) / 1e6, 1), "MB")
