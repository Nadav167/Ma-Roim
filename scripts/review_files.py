# Lists for the owner's review screen (only shown to the owner's account):
#   site/review/pairs.json   US/Israeli titles with the same name
#   site/review/posters.json popular titles still without a poster, with possible posters
import json, csv, os
os.makedirs("site/review", exist_ok=True)
rows = {r["wikidata_id"]: r for r in json.load(open("out/ma_roim_titles.json", encoding="utf-8"))}
def c(r):
    return {"id": r["wikidata_id"], "t": r["title"], "th": r["title_he"] or None, "y": r["year"], "ty": "tv" if r["type"] == "TV series" else "movie",
            "p": r["poster_en"] or None, "ph": r["poster_he"] or None, "v": r["imdb_votes"] or 0, "imdb": r["imdb_url"] or None, "il": "Israel" in r["country"]}
pairs = []
for p in csv.DictReader(open("out/same_name_review.csv", encoding="utf-8-sig")):
    u, i = rows.get(p["us_id"]), rows.get(p["il_id"])
    # owner's rule: only pairs where both titles are popular (1,000+ votes) need a look; the rest are fine
    if u and i and min(u["imdb_votes"] or 0, i["imdb_votes"] or 0) >= 1000: pairs.append({"on": "he" if p["matched_on"].startswith("Hebrew") else "en", "us": c(u), "il": c(i)})
cand = {}
if os.path.exists("raw/tmdb/candidates.jsonl"):
    for line in open("raw/tmdb/candidates.jsonl", encoding="utf-8"):
        x = json.loads(line); cand[x["q"]] = x["c"]
listed = lambda r: (r["imdb_votes"] or 0) >= 100 and "Short" not in (r["genres"] or "")   # hidden ones don't need a poster
posters = [{**c(rows[q]), "c": cand[q]} for q in sorted(cand, key=lambda q: -(rows[q]["imdb_votes"] or 0) if q in rows else 0) if q in rows and not rows[q]["poster_en"] and listed(rows[q])]
json.dump(pairs, open("site/review/pairs.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump(posters, open("site/review/posters.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("review: pairs", len(pairs), "| posters", len(posters))
