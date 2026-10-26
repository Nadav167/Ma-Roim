# Hebrew names for people (Wikidata labels), fetched in slices by IMDb ID prefix. Updates out/people.json.
import json, requests, time
EP = "https://query.wikidata.org/sparql"
H = {"User-Agent": "WhatToWatchDataset/0.1 (nadav167@gmail.com)", "Accept": "application/sparql-results+json"}
Q = """SELECT ?imdb ?he WHERE { ?p wdt:P345 ?imdb . FILTER(STRSTARTS(?imdb, "%s")) ?p rdfs:label ?he . FILTER(LANG(?he) = "he") }"""
people = {p["id"]: p for p in json.load(open("out/people.json", encoding="utf-8"))}
prefixes = [f"nm0{a}{b}" for a in range(10) for b in range(10)] + [f"nm{d}" for d in range(1, 10)]
found = 0
for i, pre in enumerate(prefixes, 1):
    for a in range(4):
        try:
            r = requests.post(EP, data={"query": Q % pre}, headers=H, timeout=200); r.raise_for_status()
            for b in r.json()["results"]["bindings"]:
                p = people.get(b["imdb"]["value"])
                if p and not p.get("name_he"): p["name_he"] = b["he"]["value"]; found += 1
            break
        except Exception as e:
            print("retry", pre, str(e)[:80], flush=True); time.sleep(5 * (a + 1))
    if i % 10 == 0: print(f"progress {i}/{len(prefixes)} slices, {found} Hebrew names so far", flush=True)
json.dump(list(people.values()), open("out/people.json", "w", encoding="utf-8"), ensure_ascii=False)
print("Hebrew names:", found, "of", len(people))
for n in ("James McAvoy", "Lior Raz", "Gal Gadot", "Bryan Cranston", "Natalie Portman"):
    print(" ", [(p["name"], p["name_he"]) for p in people.values() if p["name"] == n][:1])
