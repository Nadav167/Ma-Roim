# Build the Excel workbook: Titles tab + Same-name review tab (no formulas, so no slow recalc)
import json, csv
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

base = Font(name="Arial", size=10)
link = Font(name="Arial", size=10, color="0563C1", underline="single")
hdr = Font(name="Arial", size=10, bold=True, color="FFFFFF")
fill = PatternFill("solid", start_color="1F3A5F")

def write_sheet(ws, header, data, widths):
    for i, (h, w) in enumerate(zip(header, widths), 1):
        c = ws.cell(row=1, column=i, value=h)
        c.font, c.fill = hdr, fill
        c.alignment = Alignment(vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    for r, row in enumerate(data, 2):
        for i, v in enumerate(row, 1):
            c = ws.cell(row=r, column=i, value=v if v != "" else None)
            if isinstance(v, str) and v.startswith("http"):
                c.hyperlink = v; c.font = link
            else:
                c.font = base
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(header))}{len(data) + 1}"

rows = json.load(open("out/what_to_watch_titles.json", encoding="utf-8"))
cols = [
    ("title", "Title", 36), ("title_he", "Hebrew title", 28), ("type", "Type", 10), ("year", "Year", 7),
    ("end_year", "Ended", 7), ("country", "Country", 20), ("genres", "Genres", 28),
    ("runtime_min", "Runtime (min)", 9), ("seasons", "Seasons", 8), ("imdb_rating", "IMDb rating", 9),
    ("imdb_votes", "IMDb votes", 11), ("same_name_flag", "Same-name flag", 30),
    ("poster_en", "Poster (EN)", 34), ("poster_he", "Poster (HE)", 34),
    ("imdb_url", "IMDb", 34), ("wikipedia_en", "Wikipedia (EN)", 34), ("wikipedia_he", "Wikipedia (HE)", 34),
    ("metacritic_url", "Metacritic", 34), ("overview_en", "Synopsis (EN)", 50), ("overview_he", "Synopsis (HE)", 50),
    ("original_title", "Original title", 24), ("all_countries", "All countries", 26),
    ("tmdb_id", "TMDB ID", 9), ("wikidata_id", "Wikidata ID", 11),
]
wb = Workbook()
ws = wb.active
ws.title = "Titles"
write_sheet(ws, [c[1] for c in cols], [[r[c[0]] for c in cols] for r in rows], [c[2] for c in cols])
for r in range(2, len(rows) + 2):
    ws.cell(row=r, column=11).number_format = "#,##0"

rv = list(csv.reader(open("out/same_name_review.csv", encoding="utf-8-sig")))
ws2 = wb.create_sheet("Same-name review")
nice = {"both_tv": "Both TV?", "matched_on": "Matched on", "decision": "Your decision"}
header = [nice.get(h, h.replace("us_", "US ").replace("il_", "IL ").replace("_", " ")) for h in rv[0]]
data = [[int(v) if v.isdigit() and len(v) == 4 else v for v in row] for row in rv[1:]]
write_sheet(ws2, header, data, [8, 12, 26, 22, 9, 7, 30, 30, 30, 26, 22, 9, 7, 30, 30, 30, 18])
dec = header.index("Your decision") + 1
for r in range(2, len(data) + 2):
    ws2.cell(row=r, column=dec).fill = PatternFill("solid", start_color="FFF2CC")
wb.save("out/what_to_watch_titles.xlsx")
print("saved", len(rows), "titles,", len(data), "review pairs")
