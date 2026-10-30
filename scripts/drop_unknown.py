# Owner's rule: a title with no poster from any source (TMDB, Wikidata, Hebrew/English Wikipedia, IMDb via OMDb)
# is dropped from the catalog
# (not in the site files, not in the database). If a later weekly run finds a poster for one, it comes back.
import json, csv
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
def drop(r):
    return not (r["poster_en"] or r["poster_he"])
keep = [r for r in rows if not drop(r)]
json.dump(keep, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
with open("out/ma_roim_titles.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(keep[0].keys()), extrasaction="ignore"); w.writeheader(); w.writerows(keep)
kept = {r["wikidata_id"] for r in keep}
json.dump(sorted(r["wikidata_id"] for r in rows if r["wikidata_id"] not in kept), open("out/dropped_ids.json", "w"))
print("dropped (no poster):", len(rows) - len(keep), "| catalog:", len(keep))
