# Titles still without a poster: use the official film poster recorded on Wikidata (P3383, "film poster"),
# hosted on Wikimedia Commons. Safe to apply automatically: the property is only for a title's own poster.
# Rewrites out/ma_roim_titles.{json,csv}; poster_en_source = "wikidata".
import json, csv, time, urllib.parse, requests
EP = "https://query.wikidata.org/sparql"
H = {"User-Agent": "MaRoimDataset/0.1 (nadav167@gmail.com)", "Accept": "application/sparql-results+json"}
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
need = [r["wikidata_id"] for r in rows if not r["poster_en"] and r["wikidata_id"].startswith("Q")]
found = {}
for i in range(0, len(need), 400):
    vals = " ".join("wd:" + q for q in need[i:i + 400])
    q = f"SELECT ?item (SAMPLE(?img) AS ?img) WHERE {{ VALUES ?item {{ {vals} }} ?item wdt:P3383 ?img }} GROUP BY ?item"
    for a in range(6):
        r = requests.post(EP, data={"query": q}, headers=H, timeout=120)
        if r.status_code == 429: time.sleep(20 * (a + 1)); continue
        r.raise_for_status(); break
    for b in r.json()["results"]["bindings"]:
        file = urllib.parse.unquote(b["img"]["value"].rsplit("/", 1)[1])
        found[b["item"]["value"].rsplit("/", 1)[1]] = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(file) + "?width=500"
    time.sleep(1)
for r in rows:
    r.setdefault("poster_en_source", "tmdb" if r["poster_en"] else "")
    if not r["poster_en"] and r["wikidata_id"] in found:
        r["poster_en"], r["poster_en_source"] = found[r["wikidata_id"]], "wikidata"
        if not r.get("poster_he"): r["display_poster_he"] = r["poster_en"]
json.dump(rows, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
fields = list(rows[0].keys())
with open("out/ma_roim_titles.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
print("posters from Wikidata:", len(found), "| still without a poster:", sum(1 for r in rows if not r["poster_en"]))
