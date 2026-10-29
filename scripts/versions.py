# US and Israeli versions of the same show (e.g. Survivor / הישרדות, The Office / המשרד) should both come up
# whichever name someone searches. Each version gets the other's names as a search-only alias ("search_alias"):
# the name and poster shown stay its own.
# Pairs come from Wikidata ("based on" / "derivative work" links between TV series in the catalog)
# and from data/versions.csv (well-known formats: US English title, Israeli Hebrew title; add rows as needed).
import json, csv, re, time, collections, requests
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
by = {r["wikidata_id"]: r for r in rows}
tv = [r for r in rows if r["type"] == "TV series" and "Adult" not in (r["genres"] or "")]
us = {r["wikidata_id"] for r in tv if "United States" in r["country"]}
il = {r["wikidata_id"] for r in tv if "Israel" in r["country"]}
pairs = set()

# 1) Wikidata links
H = {"User-Agent": "MaRoimDataset/0.1 (nadav167@gmail.com)", "Accept": "application/sparql-results+json"}
def ask(q):
    for a in range(6):
        try:
            r = requests.post("https://query.wikidata.org/sparql", data={"query": q}, headers=H, timeout=180)
            if r.status_code in (429, 502, 503, 504): time.sleep(10 * (a + 1)); continue
            r.raise_for_status(); return r.json()["results"]["bindings"]
        except requests.exceptions.RequestException: time.sleep(10 * (a + 1))
    return []
links = collections.defaultdict(set)
ids = sorted(q for q in us | il if q.startswith("Q"))   # titles added from TMDB have no Wikidata item
for prop in ("P144", "P4969"):        # based on / has derivative work
    for i in range(0, len(ids), 400):
        vals = " ".join("wd:" + q for q in ids[i:i + 400])
        for b in ask(f"SELECT ?a ?b WHERE {{ VALUES ?a {{ {vals} }} ?a wdt:{prop} ?b }}"):
            a, s = b["a"]["value"].rsplit("/", 1)[1], b["b"]["value"].rsplit("/", 1)[1]
            links[a].add(s); links[s].add(a)
for a in il:
    for s in links.get(a, ()):
        if s in us: pairs.add((s, a))
        for b in links.get(s, ()):        # both based on the same format
            if b in us and b != a: pairs.add((b, a))
wd = len(pairs)

# 2) Well-known formats
n = lambda s: re.sub(r"[^\w ]", "", (s or "").lower()).strip()
for v in csv.DictReader(open("data/versions.csv", encoding="utf-8")):
    U = [q for q in us if n(by[q]["title"]) == n(v["us_title"])]
    I = [q for q in il if (n(v["il_title_he"]) and n(by[q]["title_he"]).startswith(n(v["il_title_he"])))
         or n(by[q]["title"]) in (n(v["us_title"]) + " israel", n(v["us_title"]).replace("the ", "", 1) + " israel")]
    pairs |= {(u, i) for u in U for i in I if u != i}

alias = collections.defaultdict(set)
for u, i in pairs:
    U, I = by[u], by[i]
    alias[u] |= {I["title_he"], I["title"]}
    alias[i] |= {U["title"], U["title_he"]}
for r in rows:
    own = {r["title"], r["title_he"], r.get("original_title")}
    r["search_alias"] = " | ".join(sorted(x for x in alias.get(r["wikidata_id"], ()) if x and x not in own))
json.dump(rows, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"versions of the same show: {len(pairs)} pairs ({wd} from Wikidata) | titles with a search alias: {sum(1 for r in rows if r['search_alias'])}")
