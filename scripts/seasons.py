# Season table for every TV series (like Wikipedia's "Series overview"): per season the number of episodes and the
# dates of its first and last episode, from TMDB (season details, up to 20 seasons per request).
# Cache: raw/tmdb/seasons.jsonl (one line per series; the newest line wins). A series is fetched again only when it
# may still change: running or planned, an episode in the last ~15 months, or the cached answer is over 6 months old.
# Adds "season_table": [[season, episodes, "YYYY-MM-DD" first, "YYYY-MM-DD" last(, "#colour")], ...] to out/ma_roim_titles.json,
# taken from English Wikipedia's Series overview when there is one (raw/enwiki/seasons.json), otherwise from TMDB.
import json, os, time, datetime, threading, requests
from concurrent.futures import ThreadPoolExecutor
T = open(".secrets/tmdb_token").read().strip()
B = "https://api.themoviedb.org/3"
OUT = "raw/tmdb/seasons.jsonl"
os.makedirs("raw/tmdb", exist_ok=True)
today = datetime.date.today()
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
cache = {}
if os.path.exists(OUT):
    for line in open(OUT, encoding="utf-8"):
        try: c = json.loads(line); cache[c["tmdb"]] = c
        except (ValueError, KeyError): pass   # a line cut off mid-write
def days(d): return (today - datetime.date.fromisoformat(d)).days if d else 10 ** 6
def stale(c):
    return (c.get("status") in ("Returning Series", "In Production", "Planned", "Pilot") or days(c.get("last_air")) < 450
            or days(c.get("checked")) > 180)
tv = {int(r["tmdb_id"]) for r in rows if r.get("tmdb_type") == "tv" and r.get("tmdb_id") and "Adult" not in (r["genres"] or "")}
todo = sorted(i for i in tv if i not in cache or (stale(cache[i]) and days(cache[i].get("checked")) >= 6))
print("series:", len(tv), "| to fetch:", len(todo), flush=True)

s = requests.Session(); s.headers.update({"Authorization": f"Bearer {T}", "accept": "application/json"})
def get(url, params=None):
    for a in range(6):
        try:
            r = s.get(url, params=params, timeout=60)
            if r.status_code == 429: time.sleep(int(r.headers.get("Retry-After", 2)) + a); continue
            if r.status_code == 404: return None
            r.raise_for_status(); return r.json()
        except (requests.exceptions.RequestException, ValueError):
            time.sleep(2 * (a + 1))
    return False   # gave up: leave the old answer in place

lock, outf, done = threading.Lock(), open(OUT, "a", encoding="utf-8"), [0]
def work(tid):
    d = get(f"{B}/tv/{tid}")
    if d is False: return
    res = {"tmdb": tid, "checked": today.isoformat(), "ss": []}
    if d:
        res["status"], res["last_air"] = d.get("status"), d.get("last_air_date")
        nums = sorted(x["season_number"] for x in d.get("seasons") or [] if x.get("season_number"))
        info = {x["season_number"]: x for x in d.get("seasons") or []}
        for i in range(0, len(nums), 20):
            part = nums[i:i + 20]
            e = get(f"{B}/tv/{tid}", {"append_to_response": ",".join(f"season/{n}" for n in part)})
            if e is False: return
            for n in part:
                eps = [x for x in ((e or {}).get(f"season/{n}") or {}).get("episodes") or []]
                dates = sorted(x["air_date"] for x in eps if x.get("air_date"))
                first = dates[0] if dates else info[n].get("air_date")
                if not first: continue                       # announced, no date yet
                res["ss"].append([n, len(eps) or info[n].get("episode_count") or 0, first, dates[-1] if dates else None])
    with lock:
        outf.write(json.dumps(res) + "\n"); cache[tid] = res; done[0] += 1
        if done[0] % 500 == 0: outf.flush(); print("fetched", done[0], flush=True)
with ThreadPoolExecutor(8) as ex: list(ex.map(work, todo))
outf.close()

# English Wikipedia's table (scripts/enwiki_seasons.py) comes first: the owner trusts it more; TMDB fills the rest.
wiki = json.load(open("raw/enwiki/seasons.json")) if os.path.exists("raw/enwiki/seasons.json") else {}
n = nw = 0
for r in rows:
    w = (wiki.get(r["wikidata_id"]) or {}).get("ss") if r["type"] == "TV series" else None
    c = cache.get(int(r["tmdb_id"])) if r.get("tmdb_type") == "tv" and r.get("tmdb_id") else None
    if w and c and c["ss"] and abs(int(w[0][2][:4]) - int(c["ss"][0][2][:4])) > 1 and abs(int(w[0][2][:4]) - int(r["year"] or 0)) > 1:
        w = None   # Wikipedia's table is of a different show with the same name (e.g. the 2008 Merlin for the 1998 miniseries)
    if w: r["season_table"] = w; n += 1; nw += 1
    elif c and c["ss"]: r["season_table"] = c["ss"]; n += 1
    else: r.pop("season_table", None)
json.dump(rows, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
print("series with a season table:", n, "| from Wikipedia:", nw, "| from TMDB:", n - nw)
