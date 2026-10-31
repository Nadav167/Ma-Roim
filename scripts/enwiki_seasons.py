# Season tables from English Wikipedia's "Series overview" (the coloured table at the top of most series articles and
# "List of … episodes" pages): per season the colour, number of episodes and first/last air date.
# The owner trusts Wikipedia's table more than TMDB's, so scripts/seasons.py uses it first and TMDB only as a fallback.
# Cache: raw/enwiki/seasons.json {wikidata_id: {"checked", "page", "ss": [[season, episodes, first, last, colour]]}}.
# A series is looked up again when it may still change (no end year, or ended in the last ~15 months) or after 6 months.
# Skips quietly when Wikipedia can't be reached (keeps the cache).
import json, os, re, time, datetime, requests
API = "https://en.wikipedia.org/w/api.php"
UA = {"User-Agent": "MaRoimDataset/0.1 (https://ma-roim-site.vercel.app; nadav167@gmail.com)"}
OUT = "raw/enwiki/seasons.json"
os.makedirs("raw/enwiki", exist_ok=True)
today = datetime.date.today()
cache = json.load(open(OUT)) if os.path.exists(OUT) else {}
rows = json.load(open(os.environ.get("SERIES", "out/ma_roim_titles.json"), encoding="utf-8"))   # SERIES: a smaller list to run elsewhere

def page_title(url): return requests.utils.unquote(url.rsplit("/wiki/", 1)[1]).replace("_", " ")
def age(d): return (today - datetime.date.fromisoformat(d)).days if d else 10 ** 6
def due(r):
    c = cache.get(r["wikidata_id"])
    if not c: return True
    if age(c["checked"]) < 6: return False
    ended = r.get("end_year") and int(r["end_year"]) < today.year - 1
    return not ended or age(c["checked"]) > 180
series = [r for r in rows if r["type"] == "TV series" and r.get("wikipedia_en") and "Adult" not in (r["genres"] or "")]
todo = [r for r in series if due(r)]
print("series with an English Wikipedia article:", len(series), "| to look up:", len(todo), flush=True)

s = requests.Session(); s.headers.update(UA)
def fetch(titles):
    """{asked title: wikitext or None}; follows redirects. False when Wikipedia can't be reached."""
    for a in range(6):
        try:
            r = s.post(API, data={"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main", "format": "json",
                                  "formatversion": 2, "redirects": 1, "titles": "|".join(titles)}, timeout=90)
            if r.status_code == 429 or r.status_code >= 500: time.sleep(int(r.headers.get("retry-after", 10)) + 5 * a); continue
            if r.status_code == 403: return False
            r.raise_for_status(); q = r.json().get("query", {})
            break
        except (requests.exceptions.RequestException, ValueError):
            time.sleep(5 * (a + 1))
    else: return False
    alias = {}
    for k in ("normalized", "redirects"):
        for x in q.get(k, []): alias[x["from"]] = x["to"]
    text = {p["title"]: (p["revisions"][0]["slots"]["main"]["content"] if p.get("revisions") else None) for p in q.get("pages", [])}
    out = {}
    for t in titles:
        u = t
        for _ in range(3): u = alias.get(u, u)
        out[t] = text.get(u)
    return out

# ---------- parsing ----------
def strip(t):
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"<ref[^>/]*/>", "", t); t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    return re.sub(r"</?(?:includeonly|onlyinclude|noinclude)>", "", t)
def overview(t):
    """The Series overview template's text, or None."""
    m = re.search(r"\{\{\s*(?:#invoke:\s*)?Series overview", t, re.I)
    if not m: return None
    i, depth = m.start(), 0
    while i < len(t):
        if t.startswith("{{", i): depth += 1; i += 2
        elif t.startswith("}}", i):
            depth -= 1; i += 2
            if depth == 0: return t[m.start():i]
        else: i += 1
    return None
def params(tpl):
    body, parts, depth, cur, i = tpl[2:-2], [], 0, "", 0
    while i < len(body):
        two = body[i:i + 2]
        if two in ("{{", "[["): depth += 1; cur += two; i += 2; continue
        if two in ("}}", "]]"): depth -= 1; cur += two; i += 2; continue
        if body[i] == "|" and depth == 0: parts.append(cur); cur = ""
        else: cur += body[i]
        i += 1
    parts.append(cur)
    return {k.strip(): v.strip() for k, v in (p.split("=", 1) for p in parts[1:] if "=" in p)}
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september",
                                       "october", "november", "december"], 1)}
def date(v):
    if not v: return None
    m = re.search(r"\{\{\s*(?:Start|End|Film)[ _]date[^|}]*\|\s*(\d{4})\s*(?:\|\s*(\d{1,2})\s*)?(?:\|\s*(\d{1,2})\s*)?", v, re.I)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}" if d else f"{y}-{int(mo):02d}" if mo else y
    v = re.sub(r"\{\{[^{}]*\}\}|\[\[|\]\]|'''?", "", v).strip()
    m = re.search(r"(\w+)\s+(\d{1,2}),\s*(\d{4})", v) or re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", v)
    if m:
        a, b, y = m.groups()
        mo, d = (a, b) if a.lower() in MONTHS else (b, a)
        if mo.lower() in MONTHS: return f"{y}-{MONTHS[mo.lower()]:02d}-{int(d):02d}"
    m = re.search(r"(\w+)\s+(\d{4})", v)
    if m and m.group(1).lower() in MONTHS: return f"{m.group(2)}-{MONTHS[m.group(1).lower()]:02d}"
    m = re.fullmatch(r"(\d{4})", v)
    return m.group(1) if m else None
def num(v):
    m = re.search(r"\d+", re.sub(r"\{\{[^{}]*\}\}", "", v or ""))
    return int(m.group()) if m else None
def colour(v):
    m = re.search(r"#?([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b", v or "")
    return "#" + m.group(1) if m else None
def table(t):
    tpl = overview(strip(t))
    if not tpl: return None
    p = params(tpl)
    seasons = {}
    for k, v in p.items():
        m = re.fullmatch(r"(color|episodes|start|end|released)(\d+)([A-R]?)", k)
        if m: seasons.setdefault(int(m.group(2)), {}).setdefault(m.group(3), {})[m.group(1)] = v
    out = []
    for n in sorted(seasons):
        parts = seasons[n]
        main, subs = parts.get("", {}), [parts[x] for x in sorted(parts) if x]
        allp = [main] + subs
        first = date(main.get("start") or main.get("released")) or next((date(x.get("start") or x.get("released")) for x in subs if x.get("start") or x.get("released")), None)
        if not first: continue                                    # announced, no date yet
        lasts = [date(x.get("end")) or (date(x.get("released")) if x.get("released") else None) for x in allp if x.get("end") or x.get("released")]
        last = (lasts[-1] if lasts else None)
        if last is None and main.get("released"): last = first
        eps = num(main.get("episodes")) or (sum(num(x.get("episodes")) or 0 for x in subs) or None)
        out.append([n, eps, first, last, colour(main.get("color") or next((x.get("color") for x in subs if x.get("color")), ""))])
    return out or None

# ---------- lookup: the article itself, then "List of … episodes" (or the episode list the article links to) ----------
def base(t): return re.sub(r"\s*\((?:[^()]*\s)?(?:TV series|series|miniseries|TV programme|TV program|TV show|game show|web series|talk show|American TV series|Israeli TV series)\)$", "", t)
B, done = 40, 0
for i in range(0, len(todo), B):
    batch = todo[i:i + B]
    arts = {r["wikidata_id"]: page_title(r["wikipedia_en"]) for r in batch}
    got = fetch(list(dict.fromkeys(arts.values())))
    if got is False: print("English Wikipedia isn't reachable from here; skipping (uses what's cached)", flush=True); break
    want = {}
    own = {}
    for qid, a in arts.items():
        t = got.get(a)
        # the episode list the article points to comes first: an article's own table can be of its shorts or spin-off
        # (Gravity Falls); the article's table is used only when no episode list has one
        own[qid] = table(t) if t else None
        links = re.findall(r"\{\{\s*[Mm]ain(?: article)?\s*\|\s*(List of [^|}{]*episodes[^|}{]*)", t or "")
        want[qid] = list(dict.fromkeys(links + [f"List of {base(a)} episodes"]))[:3]
    lists = list(dict.fromkeys(x for v in want.values() for x in v))
    got2 = {}
    for j in range(0, len(lists), 40):
        g = fetch(lists[j:j + 40])
        if g is False: break
        got2.update(g)
    for qid, cands in want.items():
        tb, pg = None, None
        for c in cands:
            if got2.get(c): tb = table(got2[c]); pg = c
            if tb: break
        if not tb and own[qid]: tb, pg = own[qid], arts[qid]
        cache[qid] = {"checked": today.isoformat(), "page": pg if tb else None, "ss": tb or []}
    done += len(batch)
    json.dump(cache, open(OUT + ".tmp", "w")); os.replace(OUT + ".tmp", OUT)   # saved every batch: safe to stop anytime
    if done % 400 < B:
        print("looked up", done, "| with a table:", sum(1 for c in cache.values() if c["ss"]), flush=True)
    time.sleep(0.5)
json.dump(cache, open(OUT, "w"))
print("series with a Wikipedia season table:", sum(1 for r in series if (cache.get(r["wikidata_id"]) or {}).get("ss")))
