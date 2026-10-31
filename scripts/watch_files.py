# Static where-to-watch files for the site (no database needed):
#   site/watch/providers.json  {provider_id: [name, logo_path, titles_streaming_in_IL]}
#   site/watch/NN.json         64 shards: {wikidata_id: {"k": "movie/123", "s": [ids], "f": [...], "r": [...], "b": [...],
#                              "ss": [[season, episodes, first date, last date], ...]}}
# Shard = numeric part of the Wikidata ID % 64 (the site computes the same).
import json, os, collections
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
os.makedirs("site/watch", exist_ok=True)
prov, stream_count, shards = {}, collections.Counter(), collections.defaultdict(dict)
for r in rows:
    w = r.get("watch_il") or {}
    if not w and not r.get("network_il") and not r.get("stream_us") and not r.get("season_table"): continue
    e = {"k": f"{r['tmdb_type']}/{r['tmdb_id']}"} if r.get("tmdb_id") else {}
    if r.get("season_table"): e["ss"] = r["season_table"]       # series overview: [season, episodes, first, last]
    if r.get("network_il"): e["o"] = r["network_il"]          # original channel(s): [en, he, service key]
    for src, dst in (("stream", "s"), ("free", "f"), ("rent", "r"), ("buy", "b")):
        ids = []
        for pid, name, logo in w.get(src) or []:
            prov.setdefault(pid, [name, logo]);
            if pid not in ids: ids.append(pid)
            if src == "stream": stream_count[pid] += 1
        if ids: e[dst] = ids
    if r.get("stream_us"): e["u"] = r["stream_us"]                # Disney+, from the US catalog (scripts/us_services.py)
    shards[(int(r["wikidata_id"][1:]) % 64)][r["wikidata_id"]] = e
for pid, (n, l) in json.load(open("raw/us_providers.json")).items():
    prov[int(pid)] = [n, l]; stream_count[int(pid)] = sum(1 for r in rows if int(pid) in (r.get("stream_us") or []))
json.dump({pid: [n, l, stream_count[pid]] for pid, (n, l) in prov.items()}, open("site/watch/providers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
for i in range(64):
    json.dump(shards.get(i, {}), open(f"site/watch/{i}.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
sizes = [os.path.getsize(f"site/watch/{i}.json") for i in range(64)]
print(f"providers: {len(prov)}; titles: {sum(len(v) for v in shards.values())}; shard size avg {sum(sizes) / 64 / 1024:.0f} KB, max {max(sizes) / 1024:.0f} KB")
print("top streaming services in Israel:", [(prov[p][0], n) for p, n in stream_count.most_common(12)])
