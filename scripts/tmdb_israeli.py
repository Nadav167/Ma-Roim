# Israeli movies and series that are on TMDB but not on Wikidata (e.g. The Voice Israel, X Factor Israel):
# add them to the catalog. Runs right after build.py (adds rows to out/ma_roim_titles.json) and before merge_tmdb.py,
# which takes their TMDB details from raw/tmdb/extra.jsonl.
#   ids: "M<tmdb movie id>" / "S<tmdb series id>" (Wikidata titles keep their Q ids)
#   skipped: titles already in the catalog (same TMDB id, same IMDb id, or same name and year), no poster, adult, before 1980
import json, os, re, gzip, time, datetime, threading, requests
from concurrent.futures import ThreadPoolExecutor

T = open(".secrets/tmdb_token").read().strip()
s = requests.Session(); s.headers.update({"Authorization": f"Bearer {T}", "accept": "application/json"})
B = "https://api.themoviedb.org/3"
EXTRA = "raw/tmdb/extra.jsonl"
YEAR = datetime.date.today().year

def get(url, params=None):
    for a in range(6):
        try:
            r = s.get(url, params=params or {}, timeout=30)
            if r.status_code == 429: time.sleep(int(r.headers.get("Retry-After", 2)) + a); continue
            if r.status_code == 404: return None
            r.raise_for_status(); return r.json()
        except requests.exceptions.RequestException: time.sleep(2 * (a + 1))
    return None

# 1) everything TMDB lists as Israeli
found = {}
for kind, date_key in (("tv", "first_air_date"), ("movie", "primary_release_date")):
    page, pages = 1, 1
    while page <= min(pages, 500):
        d = get(f"{B}/discover/{kind}", {"with_origin_country": "IL", "include_adult": "false", "sort_by": "popularity.desc",
                                          f"{date_key}.gte": "1980-01-01", f"{date_key}.lte": f"{YEAR}-12-31", "page": page}) or {}
        pages = d.get("total_pages", 0)
        for h in d.get("results", []):
            if h.get("poster_path"): found[(kind, h["id"])] = h
        page += 1
print("Israeli titles with a poster on TMDB:", len(found), flush=True)

# 2) what the catalog already has
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
# TMDB ids of the Wikidata titles (matched by IMDb ID or by name and year)
have_imdb = {r["imdb_url"].rstrip("/").rsplit("/", 1)[1] for r in rows if r["imdb_url"]}
qids = {r["wikidata_id"] for r in rows}
have_tmdb = set()
for f, key, ok in (("raw/tmdb/results.jsonl", "imdb", have_imdb), ("raw/tmdb/search.jsonl", "q", qids)):
    if os.path.exists(f):
        for line in open(f, encoding="utf-8"):
            x = json.loads(line)
            if x.get("tmdb_id") and x.get(key) in ok: have_tmdb.add((x["tmdb_type"], int(x["tmdb_id"])))
# names without "(TV series)"-style notes, for spotting the same title under another spelling (same type, year +-1)
norm = lambda x: re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", re.sub(r"\s*\(.*?\)", "", (x or "")).lower())).strip()
have_name = {(norm(n), r["type"], y) for r in rows if r["year"] for n in (r["title"], r["title_he"]) if norm(n) for y in (r["year"] - 1, r["year"], r["year"] + 1)}
JUNK = re.compile(r"\||college|school|academy|מכללת|בית הספר|סטודנט", re.I)   # student films and course exercises
todo = [k for k in found if k not in have_tmdb]

# 3) details for the new ones (cached)
cache = {}
if os.path.exists(EXTRA):
    for line in open(EXTRA, encoding="utf-8"):
        x = json.loads(line); cache[x["q"]] = x
def best(posters, lang):
    p = sorted([x for x in posters if x.get("iso_639_1") == lang], key=lambda x: (x.get("vote_average", 0), x.get("vote_count", 0)), reverse=True)
    return p[0]["file_path"] if p else None
def detail(key):
    kind, tid = key
    q = ("S" if kind == "tv" else "M") + str(tid)
    if q in cache: return
    d = get(f"{B}/{kind}/{tid}", {"language": "en-US", "append_to_response": "translations,images,external_ids", "include_image_language": "he,en,null"})
    if not d: return
    tr = {t["iso_639_1"]: t["data"] for t in d.get("translations", {}).get("translations", [])}
    he = tr.get("he", {})
    posters = d.get("images", {}).get("posters", [])
    orig_lang, orig_title = d.get("original_language"), d.get("original_title") or d.get("original_name")
    date = d.get("first_air_date" if kind == "tv" else "release_date") or ""
    end = (d.get("last_air_date") or "")[:4] if kind == "tv" and d.get("status") in ("Ended", "Canceled") else ""
    x = {"q": q, "tmdb_id": tid, "tmdb_type": kind, "via": "tmdb-il",
         "title_en": d.get("title") or d.get("name"), "title_he": he.get("title") or he.get("name") or (orig_title if orig_lang == "he" else None),
         "original_title": orig_title, "original_language": orig_lang,
         "poster_en": best(posters, "en") or d.get("poster_path"), "poster_he": best(posters, "he"),
         "backdrop": d.get("backdrop_path"), "overview_en": d.get("overview") or "", "overview_he": he.get("overview") or "",
         "tmdb_genres": [g["name"] for g in d.get("genres", [])], "seasons": d.get("number_of_seasons"), "episodes": d.get("number_of_episodes"),
         "status": d.get("status"), "year": int(date[:4]) if date[:4].isdigit() else None, "end_year": int(end) if end.isdigit() else None,
         "runtime": d.get("runtime") or ((d.get("episode_run_time") or [None])[0]),
         "imdb": (d.get("external_ids") or {}).get("imdb_id") or d.get("imdb_id"),
         "countries": [c.get("name") for c in d.get("production_countries", [])] or d.get("origin_country") or []}
    with lock: fh.write(json.dumps(x, ensure_ascii=False) + "\n"); cache[q] = x
lock = threading.Lock(); fh = open(EXTRA, "a", encoding="utf-8")
with ThreadPoolExecutor(10) as ex: list(ex.map(detail, todo))
fh.close()

# 4) IMDb ratings for them
want = {x["imdb"] for x in cache.values() if x.get("imdb")}
ratings = {}
if os.path.exists("raw/imdb/title.ratings.tsv.gz"):
    with gzip.open("raw/imdb/title.ratings.tsv.gz", "rt") as f:
        next(f)
        for line in f:
            t, r, v = line.rstrip("\n").split("\t")
            if t in want: ratings[t] = (float(r), int(v))

# 5) new catalog rows (same fields build.py writes)
added = 0
for (kind, tid) in todo:
    x = cache.get(("S" if kind == "tv" else "M") + str(tid))
    if not x or not x.get("poster_en") or not x.get("year") or not (1980 <= x["year"] <= YEAR): continue
    if x.get("imdb") and x["imdb"] in have_imdb: continue
    kind_name = "TV series" if kind == "tv" else "Movie"
    if any((norm(n), kind_name, x["year"]) in have_name for n in (x["title_en"], x["title_he"], x["original_title"]) if norm(n)): continue
    if any(JUNK.search(n or "") for n in (x["title_en"], x["original_title"])): continue
    if kind == "movie" and x.get("runtime") and x["runtime"] < 40: continue   # shorts
    rt = ratings.get(x.get("imdb"))
    rows.append({
        "title": x["title_en"] or x["original_title"], "title_he": x["title_he"] or "",
        "type": "TV series" if kind == "tv" else "Movie", "year": x["year"], "end_year": x["end_year"] or "",
        "country": "Israel", "all_countries": ", ".join(sorted(set(x["countries"]))) or "Israel",
        "genres": ", ".join(x["tmdb_genres"]), "imdb_genres": "", "runtime_min": x["runtime"] or "",
        "imdb_rating": rt[0] if rt else "", "imdb_votes": rt[1] if rt else "",
        "imdb_url": f"https://www.imdb.com/title/{x['imdb']}/" if x.get("imdb") else "",
        "wikipedia_en": "", "wikipedia_he": "", "metacritic_url": "", "wikidata_id": x["q"],
    })
    if x.get("imdb"): have_imdb.add(x["imdb"])
    added += 1
json.dump(rows, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
print("Israeli titles added from TMDB:", added, flush=True)
