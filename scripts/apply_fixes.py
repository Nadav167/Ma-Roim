# Apply the site owner's review decisions (Supabase table title_fixes, from the review screen) to the catalog:
#   hide -> the title is removed;  no_title_he / no_poster_he -> the English name / poster is shown instead;
#   poster_url -> the poster picked by hand. Rewrites out/ma_roim_titles.{json,csv}.
import json, csv, requests
URL = open(".secrets/supabase_url").read().strip().rstrip("/")
KEY = open(".secrets/supabase_secret").read().strip()
try:
    r = requests.get(f"{URL}/rest/v1/title_fixes?select=*", headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"}, timeout=60)
    fixes = {f["title_id"]: f for f in r.json()} if r.ok else {}
except Exception:
    fixes = {}
if not fixes: print("no review decisions"); raise SystemExit
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
out, n = [], {"hide": 0, "no_title_he": 0, "no_poster_he": 0, "poster_url": 0}
for r in rows:
    f = fixes.get(r["wikidata_id"])
    if not f: out.append(r); continue
    if f["hide"]: n["hide"] += 1; continue
    if f["poster_url"]: r["poster_en"], r["poster_en_source"] = f["poster_url"], "review"; n["poster_url"] += 1
    if f["no_title_he"]: r["title_he"] = ""; n["no_title_he"] += 1
    if f["no_poster_he"]: r["poster_he"] = ""; n["no_poster_he"] += 1
    r["display_title_he"] = r["title_he"] or r["title"]
    r["display_poster_he"] = r["poster_he"] or r["poster_en"]
    out.append(r)
json.dump(out, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
with open("out/ma_roim_titles.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()), extrasaction="ignore"); w.writeheader(); w.writerows(out)
print("review decisions applied:", n)
