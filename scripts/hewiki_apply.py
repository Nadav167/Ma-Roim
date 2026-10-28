# Add Hebrew posters found on Hebrew Wikipedia (from scripts/hewiki_posters.py).
# Images can't be downloaded from this environment to check for Hebrew text, so:
#   accept  – the title is Israeli, or the file name says it's the Hebrew/Israeli poster
#   review  – the file name is in Hebrew (often the Hebrew poster, not confirmed), or the title
#             is on the US/Israeli same-name list (left untouched by rule)
#   skip    – file name in English letters (usually the original English poster)
# Only poster-shaped images (portrait) count. Rewrites out/ma_roim_titles.{json,csv}.
import json, csv, re

rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
imgs = json.load(open("raw/hewiki/images.json", encoding="utf-8"))
heb = lambda s: bool(re.search(r"[א-ת]", s or ""))

for r in rows:
    r.setdefault("poster_he_source", "tmdb" if r["poster_he"] else "")

accepted, review = 0, []
for r in rows:
    v = imgs.get(r["wikidata_id"])
    if r["poster_he"] or not v or not v.get("url") or not v.get("h") or v["h"] <= v["w"] * 1.2:
        continue
    url = v["url"].split("?")[0]
    explicit = bool(re.search(r"עברי|ישראל", v["file"] or ""))
    israeli = "Israel" in r["country"]
    if r["same_name_flag"]:
        review.append((r, url, v["file"], "On the same-name list; left untouched"))
    elif israeli or explicit:
        r["poster_he"], r["poster_he_source"] = url, "hewiki"
        r["display_poster_he"] = url
        accepted += 1
    elif heb(v["file"]):
        review.append((r, url, v["file"], "Hebrew file name; probably the Hebrew poster"))

review.sort(key=lambda x: -(x[0]["imdb_votes"] or 0))
with open("out/hewiki_poster_review.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["title", "title_he", "year", "type", "reason", "hewiki_poster", "file_name", "current_poster", "wikipedia_he", "wikidata_id", "use_it"])
    for r, url, f, why in review:
        w.writerow([r["title"], r["title_he"], r["year"], r["type"], why, url, f, r["poster_en"], r["wikipedia_he"], r["wikidata_id"], ""])

fields = list(rows[0].keys())
with open("out/ma_roim_titles.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
json.dump(rows, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
n = len(rows)
il = [r for r in rows if "Israel" in r["country"]]
print("accepted", accepted, "| for review", len(review))
print(f"Hebrew poster coverage: all {sum(1 for r in rows if r['poster_he']) / n:.1%}, "
      f"Israeli {sum(1 for r in il if r['poster_he']) / len(il):.1%}")
