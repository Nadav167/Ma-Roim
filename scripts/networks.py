# Original channel of Israeli titles (Wikidata P449, "original broadcaster"), mapped to where they can be watched now.
# Adds "network_il": [[name_en, name_he, service_key or null]] to out/ma_roim_titles.json.
import json, requests, collections
EP = "https://query.wikidata.org/sparql"
H = {"User-Agent": "MaRoimDataset/0.1 (nadav167@gmail.com)", "Accept": "application/sparql-results+json"}
Q = """SELECT ?item ?net ?en ?he WHERE { ?item wdt:P495 wd:Q801 ; wdt:P449 ?net .
 OPTIONAL { ?net rdfs:label ?en FILTER(LANG(?en)="en") } OPTIONAL { ?net rdfs:label ?he FILTER(LANG(?he)="he") } }"""
# Wikidata channel → today's streaming home (the site holds names and links for these keys)
SERVICE = {
    "Q29946049": "kan", "Q967649": "kan", "Q4773140": "kan", "Q55649840": "kan",          # Kan 11, Channel 1, Educational TV, Kan Educational
    "Q41424455": "mako", "Q2910545": "mako",                                              # Keshet 12, Keshet
    "Q41520212": "13", "Q12411482": "13", "Q1151568": "13",                               # Reshet 13, Reshet, Channel 10
    "Q16341431": "14",                                                                     # Channel 14
    "Q1541554": "yes", "Q2731324": "yes",                                                 # yes, yes series channels
    "Q1539183": "hot", "Q5909721": "hot",                                                 # HOT, HOT 3
}
r = requests.post(EP, data={"query": Q}, headers=H, timeout=180); r.raise_for_status()
nets = collections.defaultdict(list)
for b in r.json()["results"]["bindings"]:
    q = b["item"]["value"].rsplit("/", 1)[1]; n = b["net"]["value"].rsplit("/", 1)[1]
    e = [b.get("en", {}).get("value") or b.get("he", {}).get("value") or n, b.get("he", {}).get("value") or b.get("en", {}).get("value") or n, SERVICE.get(n)]
    if e not in nets[q]: nets[q].append(e)
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
for row in rows:
    row["network_il"] = nets.get(row["wikidata_id"]) or None
json.dump(rows, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
have = [x for x in rows if x["network_il"]]
print("titles with an original channel:", len(have), "| linked to a service:", sum(1 for x in have if any(e[2] for e in x["network_il"])))
for t in ("Fauda", "Shtisel", "Srugim", "Prisoners of War", "Tehran", "Arab Labor"):
    x = next((x for x in rows if x["title"] == t), None); print(" ", t, x and x["network_il"])
