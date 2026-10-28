# Stage 3: merge Wikidata details with IMDb basics/ratings, filter, write CSV + JSON
import json, glob, gzip, csv, collections

items = json.load(open("raw/items.json"))
det = {}
for f in sorted(glob.glob("raw/stage2/*.json")):
    for r in json.load(open(f)):
        det[r["item"].rsplit("/", 1)[1]] = r

need = {d.get("imdb") for d in det.values() if d.get("imdb", "").startswith("tt")}
basics = {}
with gzip.open("raw/imdb/title.basics.tsv.gz", "rt", encoding="utf-8") as fh:
    next(fh)
    for line in fh:
        p = line.rstrip("\n").split("\t")
        if p[0] in need:
            basics[p[0]] = p
ratings = {}
with gzip.open("raw/imdb/title.ratings.tsv.gz", "rt") as fh:
    next(fh)
    for line in fh:
        t, r, v = line.rstrip("\n").split("\t")
        if t in need:
            ratings[t] = (float(r), int(v))

def nn(x):
    return None if x in (None, "", "\\N") else x

DROP_IMDB = {"short", "tvShort", "videoGame", "tvEpisode", "tvPilot"}
TV_IMDB = {"tvSeries", "tvMiniSeries"}
CNAME = {"US": "United States", "IL": "Israel"}
rows, stats = [], collections.Counter()
seen_imdb = set()
for q, it in items.items():
    d = det.get(q, {})
    imdb = d.get("imdb") if d.get("imdb", "").startswith("tt") else None
    b = basics.get(imdb)
    ttype = b[1] if b else None
    if ttype in DROP_IMDB:
        stats["drop_imdb_type"] += 1; continue
    kinds = set(it["kinds"])
    if ttype in TV_IMDB: kind = "TV series"
    elif ttype in {"movie", "tvMovie", "tvSpecial", "video"}: kind = "Movie"
    else: kind = "TV series" if "tv" in kinds else "Movie"
    year, end = it["year"], it["end"]
    if b:
        sy, ey = nn(b[5]), nn(b[6])
        if year is None and sy: year = int(sy)
        if end is None and ey and kind == "TV series": end = int(ey)
    # Scope: released/started 1980–2026; TV that started earlier counts if it ran into 1980+
    if kind == "TV series":
        ok = (year and 1980 <= year <= 2026) or (year and year < 1980 and (end is None or end >= 1980) and (end is not None or (b and nn(b[6]) is None)))
    else:
        ok = year is not None and 1980 <= year <= 2026
    if not ok:
        stats["drop_year"] += 1; continue
    title = d.get("en") or (b[2] if b else None) or d.get("he")
    if not title:
        stats["drop_no_title"] += 1; continue
    if imdb and imdb in seen_imdb:
        stats["drop_dup"] += 1; continue
    if imdb: seen_imdb.add(imdb)
    rt = ratings.get(imdb)
    mc = d.get("mc")
    genres = d.get("genres", "").split("|") if d.get("genres") else []
    genres = [g for g in genres if g and not g.startswith("Q")]
    rows.append({
        "title": title,
        "title_he": d.get("he", ""),
        "type": kind,
        "year": year,
        "end_year": end if kind == "TV series" and end else "",
        "country": " & ".join(CNAME[c] for c in sorted(it["cq"], key=lambda c: c != "US")),
        "all_countries": ", ".join(sorted(x for x in d.get("countries", "").split("|") if x)),
        "genres": ", ".join(sorted(set(genres))[:6]),
        "imdb_genres": (b[8].replace(",", ", ") if b and nn(b[8]) else ""),
        "runtime_min": (int(b[7]) if b and nn(b[7]) and b[7].isdigit() else ""),
        "imdb_rating": rt[0] if rt else "",
        "imdb_votes": rt[1] if rt else "",
        "imdb_url": f"https://www.imdb.com/title/{imdb}/" if imdb else "",
        "wikipedia_en": d.get("enwiki", ""),
        "wikipedia_he": d.get("hewiki", ""),
        "metacritic_url": f"https://www.metacritic.com/{mc.strip('/')}/" if mc else "",
        "wikidata_id": q,
    })
    stats[(kind, rows[-1]["country"])] += 1

rows.sort(key=lambda r: (-(r["imdb_votes"] or 0), r["title"]))
fields = list(rows[0].keys())
with open("out/ma_roim_titles.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
json.dump(rows, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
print(len(rows), "rows"); [print(k, v) for k, v in sorted(stats.items(), key=str)]
cov = lambda k: sum(1 for r in rows if r[k]) / len(rows)
for k in ["title_he", "imdb_url", "wikipedia_en", "wikipedia_he", "metacritic_url", "imdb_rating", "genres"]:
    print(f"{k}: {cov(k):.0%}")
