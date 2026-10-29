# Titles TMDB couldn't match by IMDb ID (or that have no IMDb ID) and so have no poster:
# search TMDB by name and year, and accept a result only when it is clearly the same title:
#   same type (movie / series), same year (series ±1), and the name matches exactly (English, original,
#   or for Israeli titles the Hebrew name), and exactly one result fits.
# Resumable cache: raw/tmdb/search.jsonl {"q": wikidata id, ...same fields as results.jsonl, or no tmdb_id}.
# merge_tmdb.py uses these when the IMDb match is missing.
import json, os, re, time, threading, unicodedata, requests
from concurrent.futures import ThreadPoolExecutor

T = open(".secrets/tmdb_token").read().strip()
s = requests.Session(); s.headers.update({"Authorization": f"Bearer {T}", "accept": "application/json"})
B = "https://api.themoviedb.org/3"
OUT = "raw/tmdb/search.jsonl"
os.makedirs("raw/tmdb", exist_ok=True)

matched = set()
for line in open("raw/tmdb/results.jsonl", encoding="utf-8"):
    try:
        x = json.loads(line)
        if x.get("tmdb_id") and x.get("poster_en"): matched.add(x["imdb"])
    except Exception: pass
rows = json.load(open("raw/base_titles.json", encoding="utf-8"))
imdb_of = lambda r: r["imdb_url"].rstrip("/").rsplit("/", 1)[1] if r["imdb_url"] else None
todo = [r for r in rows if imdb_of(r) not in matched and "Adult" not in (r.get("genres") or "") and r["wikidata_id"].startswith("Q")]   # M/S ids come from TMDB already
done = set()
if os.path.exists(OUT):
    for line in open(OUT, encoding="utf-8"):
        try: done.add(json.loads(line)["q"])
        except Exception: pass
todo = [r for r in todo if r["wikidata_id"] not in done]
print("to search", len(todo), flush=True)

def get(url, params):
    for a in range(6):
        try:
            r = s.get(url, params=params, timeout=30)
            if r.status_code == 429: time.sleep(int(r.headers.get("Retry-After", 2)) + a); continue
            if r.status_code == 404: return None
            r.raise_for_status(); return r.json()
        except Exception: time.sleep(2 * (a + 1))
    raise RuntimeError("failed " + url)

def norm(x):
    x = unicodedata.normalize("NFKD", x or "").lower()
    x = "".join(c for c in x if not unicodedata.combining(c))
    x = re.sub(r"\s*\((19|20)\d\d\)\s*$", "", x)            # "Monster (2022)"
    x = re.sub(r"[^\w\s]", " ", x).replace("&", " and ")
    x = re.sub(r"^(the|a|an)\s+", "", x.strip())
    return " ".join(x.split())

def best(posters, lang):
    p = [x for x in posters if x.get("iso_639_1") == lang]
    p.sort(key=lambda x: (x.get("vote_average", 0), x.get("vote_count", 0)), reverse=True)
    return p[0]["file_path"] if p else None

def details(kind, tid):
    d = get(f"{B}/{kind}/{tid}", {"language": "en-US", "append_to_response": "translations,images", "include_image_language": "he,en,null"}) or {}
    tr = {t["iso_639_1"]: t["data"] for t in d.get("translations", {}).get("translations", [])}
    he = tr.get("he", {})
    posters = d.get("images", {}).get("posters", [])
    orig_lang = d.get("original_language"); orig_title = d.get("original_title") or d.get("original_name")
    return {"tmdb_id": tid, "tmdb_type": kind, "title_en": d.get("title") or d.get("name"),
            "title_he": he.get("title") or he.get("name") or (orig_title if orig_lang == "he" else None),
            "original_title": orig_title, "original_language": orig_lang,
            "poster_en": best(posters, "en") or d.get("poster_path"), "poster_he": best(posters, "he"),
            "backdrop": d.get("backdrop_path"), "overview_en": d.get("overview") or "", "overview_he": he.get("overview") or "",
            "tmdb_genres": [g["name"] for g in d.get("genres", [])], "seasons": d.get("number_of_seasons"),
            "episodes": d.get("number_of_episodes"), "status": d.get("status"), "via": "search"}

def work(r):
    tv = r["type"] == "TV series"; kind = "tv" if tv else "movie"
    names = {norm(r["title"])}
    if r.get("title_he") and "Israel" in r["country"]: names.add(norm(r["title_he"]))
    names.discard("")
    res = {"q": r["wikidata_id"]}
    try:
        hits = {}
        for name, lang in ((r["title"], "en-US"), (r.get("title_he") if "Israel" in r["country"] else None, "he-IL")):
            if not name or not r.get("year"): continue
            p = {"query": name, "language": lang, "include_adult": "false"}
            d = get(f"{B}/search/{kind}", p) or {}
            for h in d.get("results", [])[:20]:
                date = h.get("first_air_date" if tv else "release_date") or ""
                y = int(date[:4]) if date[:4].isdigit() else None
                if y is None or abs(y - r["year"]) > (1 if tv else 0): continue
                if names & {norm(h.get("name") or h.get("title")), norm(h.get("original_name") or h.get("original_title"))}:
                    hits[h["id"]] = h
        if len(hits) == 1:
            tid = next(iter(hits))
            res.update(details(kind, tid))
            if not res.get("poster_en"): res = {"q": r["wikidata_id"]}   # same title but no poster either: not worth it
    except Exception:
        return
    with lock:
        fh.write(json.dumps(res, ensure_ascii=False) + "\n"); n[0] += 1
        if n[0] % 1000 == 0: fh.flush(); print("searched", n[0], flush=True)

lock = threading.Lock(); n = [0]
fh = open(OUT, "a", encoding="utf-8")
with ThreadPoolExecutor(10) as ex: list(ex.map(work, todo))
fh.close()
found = sum(1 for line in open(OUT, encoding="utf-8") if '"tmdb_id"' in line)
print("titles matched by name and year:", found, flush=True)
