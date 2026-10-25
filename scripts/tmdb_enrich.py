# Enrich every title that has an IMDb ID with TMDB data: EN/HE posters, HE title, overviews.
# Resumable: results append to raw/tmdb/results.jsonl; already-done IMDb IDs are skipped.
import requests, json, os, time, threading
from concurrent.futures import ThreadPoolExecutor

T = open(".secrets/tmdb_token").read().strip()
H = {"Authorization": f"Bearer {T}", "accept": "application/json"}
B = "https://api.themoviedb.org/3"
OUT = "raw/tmdb/results.jsonl"
os.makedirs("raw/tmdb", exist_ok=True)

rows = json.load(open("out/what_to_watch_titles.json", encoding="utf-8"))
ids = [r["imdb_url"].rstrip("/").rsplit("/", 1)[1] for r in rows if r["imdb_url"]]
done = set()
if os.path.exists(OUT):
    for line in open(OUT, encoding="utf-8"):
        try: done.add(json.loads(line)["imdb"])
        except Exception: pass
todo = [i for i in ids if i not in done]
print("total", len(ids), "done", len(done), "todo", len(todo), flush=True)

s = requests.Session()
s.headers.update(H)
lock = threading.Lock()
outf = open(OUT, "a", encoding="utf-8")
count = [0]

def get(url, params):
    for a in range(6):
        try:
            r = s.get(url, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", 2)) + a); continue
            if r.status_code == 404: return None
            r.raise_for_status(); return r.json()
        except Exception:
            time.sleep(2 * (a + 1))
    raise RuntimeError("failed " + url)

def best(posters, lang):
    p = [x for x in posters if x.get("iso_639_1") == lang]
    p.sort(key=lambda x: (x.get("vote_average", 0), x.get("vote_count", 0)), reverse=True)
    return p[0]["file_path"] if p else None

def work(imdb):
    try:
        f = get(f"{B}/find/{imdb}", {"external_source": "imdb_id"})
        res = {"imdb": imdb}
        if f:
            hit, kind = None, None
            for k, key in (("movie", "movie_results"), ("tv", "tv_results")):
                if f.get(key): hit, kind = f[key][0], k; break
            if hit:
                d = get(f"{B}/{kind}/{hit['id']}", {"language": "en-US",
                        "append_to_response": "translations,images",
                        "include_image_language": "he,en,null"}) or {}
                tr = {t["iso_639_1"]: t["data"] for t in d.get("translations", {}).get("translations", [])}
                he = tr.get("he", {})
                posters = d.get("images", {}).get("posters", [])
                orig_lang = d.get("original_language")
                orig_title = d.get("original_title") or d.get("original_name")
                he_title = he.get("title") or he.get("name") or (orig_title if orig_lang == "he" else None)
                res.update({
                    "tmdb_id": hit["id"], "tmdb_type": kind,
                    "title_en": d.get("title") or d.get("name"),
                    "title_he": he_title,
                    "original_title": orig_title, "original_language": orig_lang,
                    "poster_en": best(posters, "en") or d.get("poster_path"),
                    "poster_he": best(posters, "he"),
                    "backdrop": d.get("backdrop_path"),
                    "overview_en": d.get("overview") or "",
                    "overview_he": he.get("overview") or "",
                    "tmdb_genres": [g["name"] for g in d.get("genres", [])],
                    "seasons": d.get("number_of_seasons"),
                    "episodes": d.get("number_of_episodes"),
                    "status": d.get("status"),
                })
        line = json.dumps(res, ensure_ascii=False)
    except Exception as e:
        line = None
        print("ERR", imdb, e, flush=True)
    with lock:
        if line: outf.write(line + "\n")
        count[0] += 1
        if count[0] % 1000 == 0:
            outf.flush(); print("progress", count[0], "/", len(todo), flush=True)

with ThreadPoolExecutor(12) as ex:
    list(ex.map(work, todo))
outf.close()
print("DONE", flush=True)
