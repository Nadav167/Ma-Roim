# Hebrew names for people (Wikidata labels), looked up by IMDb person ID in batches. Updates out/people.json.
import json, requests, time
from concurrent.futures import ThreadPoolExecutor

EP = "https://query.wikidata.org/sparql"
H = {"User-Agent": "WhatToWatchDataset/0.1 (nadav167@gmail.com)", "Accept": "application/sparql-results+json"}
Q = """SELECT ?imdb ?he WHERE { VALUES ?imdb { %s } ?p wdt:P345 ?imdb ; rdfs:label ?he . FILTER(LANG(?he) = "he") }"""

people = {p["id"]: p for p in json.load(open("out/people.json", encoding="utf-8"))}
ids = sorted(people)
B = 2000
batches = [ids[i:i + B] for i in range(0, len(ids), B)]
done = [0]

def run(batch):
    vals = " ".join(f'"{x}"' for x in batch)
    out = {}
    for a in range(5):
        try:
            r = requests.post(EP, data={"query": Q % vals}, headers=H, timeout=120)
            r.raise_for_status()
            out = {b["imdb"]["value"]: b["he"]["value"] for b in r.json()["results"]["bindings"]}
            break
        except Exception as e:
            print("retry:", str(e)[:80], flush=True)
            time.sleep(5 * (a + 1))
    done[0] += 1
    if done[0] % 10 == 0:
        print(f"progress {done[0]}/{len(batches)} batches", flush=True)
    return out

found = 0
with ThreadPoolExecutor(3) as ex:
    for res in ex.map(run, batches):
        for pid, he in res.items():
            if not people[pid].get("name_he"):
                people[pid]["name_he"] = he
                found += 1
json.dump(list(people.values()), open("out/people.json", "w", encoding="utf-8"), ensure_ascii=False)
print("Hebrew names:", found, "of", len(people))
for n in ("James McAvoy", "Lior Raz", "Gal Gadot", "Bryan Cranston", "Natalie Portman"):
    print(" ", [(p["name"], p["name_he"]) for p in people.values() if p["name"] == n][:1])
