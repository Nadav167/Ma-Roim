# Disney+ isn't in the Israel data (JustWatch doesn't track it in Israel), so the site uses its US catalog. Adds "stream_us": [provider ids] to out/ma_roim_titles.json
# and writes raw/us_providers.json {id: [name, logo]}.
import json
US = {337: "Disney+"}
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
got, logos = {}, {}
for line in open("raw/tmdb/providers.jsonl", encoding="utf-8"):
    x = json.loads(line); d = x["r"].get("US") or {}
    ids = []
    for p in (d.get("flatrate") or []) + (d.get("ads") or []):
        if p["provider_id"] in US and p["provider_id"] not in ids:
            ids.append(p["provider_id"]); logos[p["provider_id"]] = p.get("logo_path")
    if ids: got[x["q"]] = sorted(ids)
for r in rows: r["stream_us"] = got.get(r["wikidata_id"], [])
json.dump(rows, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump({pid: [US[pid], logos.get(pid)] for pid in US}, open("raw/us_providers.json", "w"))
for pid, name in US.items(): print(name, sum(1 for v in got.values() if pid in v), "titles")
