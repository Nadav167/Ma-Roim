# Owner's rule: a title with no poster from any source (TMDB, Wikidata, Hebrew/English Wikipedia, IMDb via OMDb)
# is dropped from the catalog
# (not in the site files, not in the database). If a later weekly run finds a poster for one, it comes back.
# Safety net: a title that had a poster in last week's dataset (data/titles.json.gz) keeps that poster, so a
# poster source that is down for a week (or a missing key) doesn't drop titles that have one.
import json, csv, gzip, os
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
prev = {}
if os.path.exists("data/titles.json.gz"):
    for p in json.load(gzip.open("data/titles.json.gz", "rt", encoding="utf-8")):
        if p.get("poster_en") or p.get("poster_he"): prev[p["wikidata_id"]] = p
F = ["poster_en", "poster_he", "poster_en_source", "poster_he_source", "display_poster_he"]
restored = 0
for r in rows:
    p = prev.get(r["wikidata_id"])
    if not (r["poster_en"] or r["poster_he"]) and p:
        for f in F:
            if f in p: r[f] = p[f]
        restored += 1
def drop(r):
    return not (r["poster_en"] or r["poster_he"])
keep = [r for r in rows if not drop(r)]
json.dump(keep, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
with open("out/ma_roim_titles.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(keep[0].keys()), extrasaction="ignore"); w.writeheader(); w.writerows(keep)
kept = {r["wikidata_id"] for r in keep}
json.dump(sorted(r["wikidata_id"] for r in rows if r["wikidata_id"] not in kept), open("out/dropped_ids.json", "w"))
print("kept last week's poster:", restored, "| dropped (no poster):", len(rows) - len(keep), "| catalog:", len(keep))
