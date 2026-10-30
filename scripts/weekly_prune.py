# Before a weekly refresh: forget cached TMDB answers for recent titles (released this year or last year),
# so their posters, Hebrew names, synopses, trailers, keywords and cast photos are fetched again.
# Older titles keep their cached answers (they rarely change). Where-to-watch is refetched for every title
# by deleting raw/tmdb/providers.jsonl in scripts/update_all.sh.
import json, gzip, os, glob, datetime
# A run that was stopped midway can leave a cut-off last line in a cache file; drop such lines (they're fetched again)
for f in glob.glob("raw/tmdb/*.jsonl"):
    lines = open(f, encoding="utf-8").read().splitlines()
    good = []
    for l in lines:
        try: json.loads(l); good.append(l)
        except ValueError: pass
    if len(good) < len([l for l in lines if l.strip()]):
        open(f, "w", encoding="utf-8").write("\n".join(good) + ("\n" if good else ""))
        print(f"{f}: dropped {len([l for l in lines if l.strip()]) - len(good)} broken lines")
recent_year = datetime.date.today().year - 1
src = "out/ma_roim_titles.json" if os.path.exists("out/ma_roim_titles.json") else "data/titles.json.gz"
rows = json.load(open(src, encoding="utf-8") if src.endswith(".json") else gzip.open(src, "rt", encoding="utf-8"))
recent = [r for r in rows if (r.get("year") or 0) >= recent_year or (r.get("type") == "TV series" and not r.get("end_year"))]
q = {r["wikidata_id"] for r in recent}
imdb = {r["imdb_url"].rstrip("/").rsplit("/", 1)[1] for r in recent if r.get("imdb_url")}
for name, key, keep in (("results", "imdb", imdb), ("keywords", "q", q), ("videos", "q", q), ("credits", "q", q), ("extra", "q", q)):
    f = f"raw/tmdb/{name}.jsonl"
    if not os.path.exists(f): continue
    lines = open(f, encoding="utf-8").read().splitlines()
    # also retry titles that came back without a match or without a poster: TMDB keeps growing
    kept = [l for l in lines if l.strip() and json.loads(l).get(key) not in keep
            and not (name == "results" and not json.loads(l).get("poster_en"))]
    open(f, "w", encoding="utf-8").write("\n".join(kept) + ("\n" if kept else ""))
    print(f"{name}: refreshing {len(lines) - len(kept)} of {len(lines)}")
# name-and-year searches that found nothing are tried again
f = "raw/tmdb/search.jsonl"
if os.path.exists(f):
    lines = [l for l in open(f, encoding="utf-8").read().splitlines() if l.strip()]
    kept = [l for l in lines if json.loads(l).get("tmdb_id") and json.loads(l).get("q") not in q]
    open(f, "w", encoding="utf-8").write("\n".join(kept) + ("\n" if kept else ""))
    print(f"search: retrying {len(lines) - len(kept)} of {len(lines)}")
