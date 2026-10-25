# Build the website catalog.
#   site/catalog.json            – real site: poster/backdrop URLs from TMDB, top titles + search index
#   build/preview/catalog.json   – artifact preview: same shape, images embedded as data: URIs
#                                  (artifact pages can't load images from other hosts)
import json, os, base64, sys, requests
from concurrent.futures import ThreadPoolExecutor

rows = json.load(open("out/what_to_watch_titles.json", encoding="utf-8"))
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
    ("new", "New and popular", "חדש ופופולרי", top(lambda r: r["year"] >= 2024)),
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
json.dump(cat, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(out, len(items), "items", round(os.path.getsize(out) / 1e6, 1), "MB")
