# Merge TMDB results into the dataset; write CSV + JSON
import json, csv

IMG = "https://image.tmdb.org/t/p/w500"
rows = json.load(open("raw/base_titles.json", encoding="utf-8"))
tm = {}
for line in open("raw/tmdb/results.jsonl", encoding="utf-8"):
    x = json.loads(line); tm[x["imdb"]] = x
# matches found by name and year (scripts/tmdb_search_fill.py) for titles the IMDb lookup missed
import os
found = {}
for f in ("raw/tmdb/search.jsonl", "raw/tmdb/extra.jsonl"):   # extra: Israeli titles added from TMDB (tmdb_israeli.py)
    if os.path.exists(f):
        for line in open(f, encoding="utf-8"):
            x = json.loads(line)
            if x.get("tmdb_id"): found[x["q"]] = x

import re
NOT_ADULT = {"From Straight A's to XXX", "Thinking XXX", "Mommy XXX"}   # a TV drama and documentaries about the industry
def is_adult_parody(t):
    if t in NOT_ADULT: return False
    return bool(re.search(r"XXX", t, re.I) and re.search(r"parody|porn|orgasm", t, re.I)) \
        or bool(re.search(r"(?<!^)\bXXX\b", t)) or "XXXorcist" in t
out = []
for r in rows:
    imdb = r["imdb_url"].rstrip("/").rsplit("/", 1)[1] if r["imdb_url"] else None
    t = tm.get(imdb, {})
    if not (t.get("tmdb_id") and t.get("poster_en")) and r["wikidata_id"] in found: t = found[r["wikidata_id"]]
    # titles added from TMDB (M/S ids) keep their own TMDB entry: the IMDb lookup can land on another entry
    # (Fleabag's IMDb ID also finds the filmed stage show)
    if r["wikidata_id"][:1] in "MS" and found.get(r["wikidata_id"], {}).get("tmdb_id"): t = found[r["wikidata_id"]]
    title_he = t.get("title_he") or r["title_he"]
    o = {
        "title": r["title"],
        "title_he": title_he or "",
        "original_title": t.get("original_title") or "",
        "type": r["type"], "year": r["year"], "end_year": r["end_year"],
        "country": r["country"],
        "genres": ", ".join(t.get("tmdb_genres") or []) or r["imdb_genres"] or r["genres"],
        "runtime_min": r["runtime_min"],
        "seasons": t.get("seasons") or "", "episodes": t.get("episodes") or "",
        "imdb_rating": r["imdb_rating"], "imdb_votes": r["imdb_votes"],
        "poster_en": IMG + t["poster_en"] if t.get("poster_en") else "",
        "poster_he": IMG + t["poster_he"] if t.get("poster_he") else "",
        "backdrop": "https://image.tmdb.org/t/p/w1280" + t["backdrop"] if t.get("backdrop") else "",
        "overview_en": t.get("overview_en") or "",
        "overview_he": t.get("overview_he") or "",
        "imdb_url": r["imdb_url"], "wikipedia_en": r["wikipedia_en"], "wikipedia_he": r["wikipedia_he"],
        "metacritic_url": r["metacritic_url"],
        "tmdb_id": t.get("tmdb_id") or "", "tmdb_type": t.get("tmdb_type") or "",
        "wikidata_id": r["wikidata_id"], "all_countries": r["all_countries"],
    }
    # adult parodies ("Batman XXX: A Porn Parody", "This Ain't Glee XXX") aren't always tagged: mark them Adult so the site skips them
    if is_adult_parody(o["title"]): o["genres"] = ", ".join([g for g in o["genres"].split(", ") if g] + ["Adult"])
    out.append(o)

# Hebrew-site rule: each title uses only its OWN Hebrew title/poster (matched by its own IMDb ID).
# US/Israeli same-name rule (user's call): when a US-only title and an Israeli title share a name
# (English or Hebrew), change NOTHING — just flag both and list the pairs for the user to decide.
import re
def norm(s):
    s = re.sub(r"[^\w\s]", " ", (s or "").lower())
    s = re.sub(r"^\s*the\s+", "", s)
    return " ".join(s.split())
il = [o for o in out if "Israel" in o["country"]]
us = [o for o in out if o["country"] == "United States"]
idx = {}
for o in il:
    for key, val in (("English title", norm(o["title"])), ("Hebrew title", o["title_he"].strip())):
        if val: idx.setdefault((key, val), []).append(o)
pairs, seen = [], set()
for u in us:
    for key, val in (("English title", norm(u["title"])), ("Hebrew title", u["title_he"].strip())):
        for i in idx.get((key, val), []) if val else []:
            pk = (u["wikidata_id"], i["wikidata_id"])
            if pk in seen:
                continue
            seen.add(pk)
            pairs.append((key, u, i))
for o in out:
    o["same_name_flag"] = ""
for _, u, i in pairs:
    u["same_name_flag"] = "Has an Israeli title with the same name — see review list"
    i["same_name_flag"] = "Has a US title with the same name — see review list"
for o in out:
    # What the Hebrew site shows: own Hebrew title/poster if it exists, else the English one
    o["display_title_he"] = o["title_he"] or o["title"]
    o["display_poster_he"] = o["poster_he"] or o["poster_en"]
rev_fields = ["us_id", "il_id", "both_tv", "matched_on", "us_title", "us_title_he", "us_type", "us_year", "us_poster_en", "us_poster_he", "us_imdb",
              "il_title", "il_title_he", "il_type", "il_year", "il_poster_en", "il_poster_he", "il_imdb", "decision"]
pairs.sort(key=lambda p: (not (p[1]["type"] == p[2]["type"] == "TV series"), -((p[1]["imdb_votes"] or 0) + (p[2]["imdb_votes"] or 0))))
with open("out/same_name_review.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh); w.writerow(rev_fields)
    for key, u, i in pairs:
        w.writerow([u["wikidata_id"], i["wikidata_id"], "yes" if u["type"] == i["type"] == "TV series" else "", key, u["title"], u["title_he"], u["type"], u["year"], u["poster_en"], u["poster_he"], u["imdb_url"],
                    i["title"], i["title_he"], i["type"], i["year"], i["poster_en"], i["poster_he"], i["imdb_url"], ""])
print("same-name pairs:", len(pairs), "| TV-TV pairs:", sum(1 for _, u, i in pairs if u["type"] == i["type"] == "TV series"))

fields = list(out[0].keys())
with open("out/ma_roim_titles.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(out)
json.dump(out, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
n = len(out)
print(n, "rows")
for k in ["title_he", "poster_en", "poster_he", "overview_en", "overview_he", "tmdb_id", "metacritic_url", "wikipedia_he"]:
    print(f"{k}: {sum(1 for o in out if o[k]) / n:.0%}")
il = [o for o in out if "Israel" in o["country"]]
for k in ["title_he", "poster_en", "poster_he", "overview_he"]:
    print(f"Israel {k}: {sum(1 for o in il if o[k]) / len(il):.0%}")
