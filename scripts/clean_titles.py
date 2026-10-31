# Titles from Wikipedia/Wikidata sometimes keep the article's disambiguation note: "טטריס (סרט)",
# "גאווה ודעה קדומה (סדרת טלוויזיה עתידית)", "Going Dutch (TV series)", "Scrubs (2026)". The site already shows
# the type and year, so the note is removed. Real titles that end in brackets ("Live in 3D") are left alone.
import json, csv, re
HE = r"(?:סרט|סרטים|סדרה|סדרת|מיני[- ]?סדרה|תוכנית|שעשועון|טלוויזיה|אנימציה|אנימה|רשת|תיעודית|עתידית|עתידי|אמריקאית|ישראלית|רוסי|קצרים)"
NOTE = re.compile(
    r"\s+\((?:"
    rf"{HE}(?:[ ,]+{HE})*(?:,?\s*\d{{4}})?"                       # (סרט) (סדרת טלוויזיה, 1995) (סדרת טלוויזיה עתידית)
    r"|(?:\d{4}\s+)?(?:American\s+|Israeli\s+|British\s+)?(?:film|movie|TV series|TV Series|television series|TV|miniseries|"
    r"mini-series|documentary|documentary series|Documentary|talk show)(?:\s+\d{4})?"   # (film) (1992 film) (TV Series 2020)
    r"|\d{4}"                                                      # (2024)
    r")\)\s*$")
def clean(v): return NOTE.sub("", v).strip() if v else v
rows = json.load(open("out/ma_roim_titles.json", encoding="utf-8"))
n = 0
for r in rows:
    for f in ("title", "title_he", "display_title_he"):
        v = r.get(f)
        if v and clean(v) != v and clean(v): r[f] = clean(v); n += 1
json.dump(rows, open("out/ma_roim_titles.json", "w", encoding="utf-8"), ensure_ascii=False)
with open("out/ma_roim_titles.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), extrasaction="ignore"); w.writeheader(); w.writerows(rows)
print("disambiguation notes removed from titles:", n)
