# Owner's rule: the catalog is American and Israeli titles. Titles whose original language isn't English or Hebrew are
# dropped unless they are Israeli, partly in English (TMDB's spoken languages: Léon, Snowpiercer, The Young Pope), or an
# American production (an American company made it), or are listed in
# data/keep_titles.csv (e.g. Money Heist, which the owner wants despite being Spanish).
# "American production": TMDB's first production company is American, or most of its production companies are.
# Language and companies come from TMDB (cache raw/tmdb/companies.jsonl). Writes out/foreign_ids.json (removed ids).
import json, os, csv, time, threading, requests
from concurrent.futures import ThreadPoolExecutor
T = open(".secrets/tmdb_token").read().strip()
B = "https://api.themoviedb.org/3"
OUT = "raw/tmdb/companies.jsonl"
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
lang = {}
for f in ("raw/tmdb/results.jsonl", "raw/tmdb/search.jsonl", "raw/tmdb/extra.jsonl"):
    if not os.path.exists(f): continue
    for line in open(f, encoding="utf-8"):
        try: d = json.loads(line)
        except ValueError: continue
        if d.get("tmdb_id") and d.get("original_language"): lang[f'{d.get("tmdb_type")}/{int(d["tmdb_id"])}'] = d["original_language"]
key = lambda r: f'{r["tmdb_type"]}/{int(r["tmdb_id"])}' if r.get("tmdb_id") and r.get("tmdb_type") else None
keep = set()
if os.path.exists("data/keep_titles.csv"):
    for x in csv.DictReader(open("data/keep_titles.csv", encoding="utf-8")): keep.add(f'{x["tmdb_type"]}/{x["tmdb_id"]}')
cand = [r for r in rows if key(r) and lang.get(key(r)) not in (None, "en", "he") and "Israel" not in r["country"] and key(r) not in keep]
cache = {}
if os.path.exists(OUT):
    for line in open(OUT, encoding="utf-8"):
        try: c = json.loads(line); cache[c["k"]] = c if "spoken" in c else cache.get(c["k"])
        except (ValueError, KeyError): pass
s = requests.Session(); s.headers.update({"Authorization": f"Bearer {T}", "accept": "application/json"})
lock, fh = threading.Lock(), open(OUT, "a", encoding="utf-8")
def work(k):
    for a in range(6):
        try:
            x = s.get(f"{B}/{k}", timeout=30)
            if x.status_code == 429: time.sleep(2 + a); continue
            if x.status_code == 404: return
            x.raise_for_status(); d = x.json(); break
        except (requests.exceptions.RequestException, ValueError): time.sleep(2 * (a + 1))
    else: return
    c = {"k": k, "lang": d.get("original_language"), "spoken": [x.get("iso_639_1") for x in d.get("spoken_languages") or []], "companies": [[p.get("name"), p.get("origin_country") or ""] for p in d.get("production_companies") or []],
         "networks": [[p.get("name"), p.get("origin_country") or ""] for p in d.get("networks") or []]}
    with lock: fh.write(json.dumps(c, ensure_ascii=False) + "\n"); cache[k] = c
cache = {k: v for k, v in cache.items() if v}
with ThreadPoolExecutor(8) as ex: list(ex.map(work, sorted({key(r) for r in cand} - set(cache))))
fh.close()
def american(c):
    co = [x[1] for x in c["companies"] if x[1]]
    if not co: co = [x[1] for x in c["networks"] if x[1]]
    return bool(co) and (co[0] == "US" or sum(x == "US" for x in co) * 2 > len(co))
def known(c): return any(x[1] for x in c["companies"] + c["networks"])
def foreign(r, c):
    if c["lang"] in ("en", "he") or {"en", "he"} & set(c["spoken"]): return False
    # no studio on TMDB: often a wrong TMDB match (Power Rangers listed as Portuguese); trust Wikidata's "United States" then
    return not american(c) if known(c) else r["all_countries"] != "United States"
gone = [r for r in cand if key(r) in cache and foreign(r, cache[key(r)])]
ids = {r["wikidata_id"] for r in gone}
rows = [r for r in rows if r["wikidata_id"] not in ids]
json.dump(rows, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
with open("out/ma_roim_titles.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), extrasaction="ignore"); w.writeheader(); w.writerows(rows)
json.dump(sorted(ids), open("out/foreign_ids.json", "w"))
print("foreign-language titles:", len(cand), "| kept as American productions:", len(cand) - len(gone), "| removed:", len(gone))
