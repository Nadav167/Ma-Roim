# Rotten Tomatoes (Tomatometer %) and Metacritic (Metascore /100) from Wikidata review scores (P444).
# Keeps the most recent value per source when several are recorded.
# Writes raw/scores.json {wikidata_id: {"rt": int, "mc": int}} and adds rt_score / mc_score
# to out/what_to_watch_titles.{json,csv}.
import requests, json, csv, re, collections

EP = "https://query.wikidata.org/sparql"
H = {"User-Agent": "WhatToWatchDataset/0.1 (nadav167@gmail.com)", "Accept": "application/sparql-results+json"}
RT, MC = "Q105584", "Q150248"
TOMATOMETER, METASCORE = "Q108403393", "Q106515043"
Q = """SELECT ?item ?by ?score ?method ?date WHERE {
  ?item wdt:P495 wd:%s .
  ?item p:P444 ?st . ?st ps:P444 ?score ; pq:P447 ?by .
  VALUES ?by { wd:Q105584 wd:Q150248 }
  OPTIONAL { ?st pq:P459 ?method } OPTIONAL { ?st pq:P585 ?date }
}"""

best = collections.defaultdict(dict)  # qid -> {"rt": (date, val), "mc": (date, val)}
for country in ("Q30", "Q801"):
    r = requests.post(EP, data={"query": Q % country}, headers=H, timeout=300)
    r.raise_for_status()
    for b in r.json()["results"]["bindings"]:
        qid = b["item"]["value"].rsplit("/", 1)[1]
        by = b["by"]["value"].rsplit("/", 1)[1]
        method = b.get("method", {}).get("value", "").rsplit("/", 1)[-1]
        s = b["score"]["value"].strip()
        date = b.get("date", {}).get("value", "")
        if by == RT and method in (TOMATOMETER, "") and (m := re.fullmatch(r"(\d{1,3})\s*%", s)):
            key, val = "rt", int(m.group(1))
        elif by == MC and method in (METASCORE, "") and (m := re.fullmatch(r"(\d{1,3})\s*/\s*100", s)):
            key, val = "mc", int(m.group(1))
        else:
            continue
        if 0 <= val <= 100 and (key not in best[qid] or date >= best[qid][key][0]):
            best[qid][key] = (date, val)

scores = {q: {k: v[1] for k, v in d.items()} for q, d in best.items()}
# Rotten Tomatoes page IDs (P1258), e.g. "m/the_dark_knight" or "tv/fauda"
QR = """SELECT ?item (SAMPLE(?rid) AS ?rid) WHERE { ?item wdt:P495 wd:%s ; wdt:P1258 ?rid } GROUP BY ?item"""
for country in ("Q30", "Q801"):
    r = requests.post(EP, data={"query": QR % country}, headers=H, timeout=300); r.raise_for_status()
    for b in r.json()["results"]["bindings"]:
        scores.setdefault(b["item"]["value"].rsplit("/", 1)[1], {})["rid"] = b["rid"]["value"].strip("/")
json.dump(scores, open("raw/scores.json", "w"))

rows = json.load(open("out/what_to_watch_titles.json", encoding="utf-8"))
for r in rows:
    s = scores.get(r["wikidata_id"], {})
    r["rt_score"] = s.get("rt", "")
    r["mc_score"] = s.get("mc", "")
    r["rt_url"] = f"https://www.rottentomatoes.com/{s['rid']}" if s.get("rid") else ""
fields = list(rows[0].keys())
with open("out/what_to_watch_titles.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
json.dump(rows, open("out/what_to_watch_titles.json", "w", encoding="utf-8"), ensure_ascii=False)

n = len(rows)
for k in ("imdb_rating", "rt_score", "mc_score", "rt_url"):
    c = sum(1 for r in rows if r[k] != "")
    top = sum(1 for r in rows[:5000] if r[k] != "")
    print(f"{k}: {c} titles ({c / n:.0%}); top 5,000 by votes: {top / 5000:.0%}")
il = [r for r in rows if "Israel" in r["country"]]
print("Israeli with RT:", sum(1 for r in il if r["rt_score"] != ""), "MC:", sum(1 for r in il if r["mc_score"] != ""))
by = {r["title"]: r for r in rows}
for t in ["The Dark Knight", "Breaking Bad", "Oppenheimer", "Waltz with Bashir", "Fauda", "Friends", "Barbie"]:
    r = by.get(t); print(t, r and (r["imdb_rating"], r["rt_score"], r["mc_score"]))
