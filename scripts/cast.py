# Cast and crew from IMDb's principals (top-billed people per title) + names, with Hebrew names from Wikidata.
# Writes out/people.json and out/credits.json, and adds cast/directors summaries to out/what_to_watch_titles.json.
import gzip, json, csv, requests, collections, re

rows = json.load(open("out/what_to_watch_titles.json", encoding="utf-8"))
imdb2q = {}
for r in rows:
    if r["imdb_url"]:
        imdb2q.setdefault(r["imdb_url"].rstrip("/").rsplit("/", 1)[1], r["wikidata_id"])

ROLE = {"actor": "cast", "actress": "cast", "self": "cast", "director": "director", "writer": "writer", "composer": "composer"}
credits = []
with gzip.open("raw/imdb/title.principals.tsv.gz", "rt", encoding="utf-8") as fh:
    next(fh)
    for line in fh:
        tconst, ordering, nconst, cat, job, chars = line.rstrip("\n").split("\t")
        q = imdb2q.get(tconst)
        if not q or cat not in ROLE:
            continue
        role = ROLE[cat]
        if role == "writer" and job != "\\N" and re.search(r"creat", job, re.I):
            role = "creator"
        ch = None
        if chars != "\\N":
            try: ch = ", ".join(json.loads(chars))[:120]
            except Exception: ch = None
        credits.append({"title_id": q, "person_id": nconst, "role": role, "ord": int(ordering), "character": ch})
print("credits", len(credits), collections.Counter(c["role"] for c in credits))

need = {c["person_id"] for c in credits}
people = {}
with gzip.open("raw/imdb/name.basics.tsv.gz", "rt", encoding="utf-8") as fh:
    next(fh)
    for line in fh:
        p = line.rstrip("\n").split("\t")
        if p[0] in need:
            people[p[0]] = {"id": p[0], "name": p[1], "name_he": None,
                            "birth_year": int(p[2]) if p[2].isdigit() else None,
                            "death_year": int(p[3]) if p[3].isdigit() else None}
print("people", len(people))

# Hebrew names: Wikidata humans with an IMDb person ID and a Hebrew label
EP = "https://query.wikidata.org/sparql"
H = {"User-Agent": "WhatToWatchDataset/0.1 (nadav167@gmail.com)", "Accept": "application/sparql-results+json"}
Q = """SELECT ?imdb ?he WHERE { ?p wdt:P345 ?imdb ; rdfs:label ?he . FILTER(LANG(?he) = "he") FILTER(STRSTARTS(?imdb, "nm")) }"""
try:
    r = requests.post(EP, data={"query": Q}, headers=H, timeout=300)
    r.raise_for_status()
    n = 0
    for b in r.json()["results"]["bindings"]:
        pid = b["imdb"]["value"]
        if pid in people and not people[pid]["name_he"]:
            people[pid]["name_he"] = b["he"]["value"]; n += 1
    print("Hebrew names", n)
except Exception as e:
    print("Hebrew names skipped:", e)

credits = [c for c in credits if c["person_id"] in people]
json.dump(list(people.values()), open("out/people.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump(credits, open("out/credits.json", "w", encoding="utf-8"), ensure_ascii=False)

# Short summaries on each title (top 6 cast, directors) for the CSV/Excel and the site catalog
by_title = collections.defaultdict(list)
for c in credits: by_title[c["title_id"]].append(c)
for r in rows:
    cs = sorted(by_title.get(r["wikidata_id"], []), key=lambda c: c["ord"])
    r["cast"] = ", ".join(people[c["person_id"]]["name"] for c in cs if c["role"] == "cast")
    r["directors"] = ", ".join(people[c["person_id"]]["name"] for c in cs if c["role"] == "director")
    r["creators"] = ", ".join(people[c["person_id"]]["name"] for c in cs if c["role"] == "creator")
fields = list(rows[0].keys())
with open("out/what_to_watch_titles.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
json.dump(rows, open("out/what_to_watch_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
with_cast = sum(1 for r in rows if r["cast"])
print(f"titles with cast: {with_cast} ({with_cast / len(rows):.0%}); top 5,000: {sum(1 for r in rows[:5000] if r['cast']) / 50:.0f}%")
for r in rows:
    if "McAvoy" in r["cast"] and r["year"] and r["year"] >= 2015:
        print("  McAvoy:", r["title"], r["year"], r["genres"], r["imdb_rating"])
