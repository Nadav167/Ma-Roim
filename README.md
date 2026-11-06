# Ma Roim · מה רואים

A bilingual (Hebrew / English) catalog of about 58,000 US and Israeli movies and TV series from 1980 to today, with ratings, where to watch in Israel, and an AI assistant that recommends what to watch.

**Live:** https://ma-roim-site.vercel.app

## Features

- **Catalog** with posters, synopses, cast, trailers, IMDb / Rotten Tomatoes / Metacritic scores, season tables and links to IMDb, Wikipedia and Metacritic — in Hebrew first, English on request.
- **Where to watch:** pick your streaming services (Netflix, HBO Max, Prime Video, Apple TV, Disney+) and filter by them.
- **Search** in both languages, including by actor or director, and across US/Israeli versions of the same show (Survivor finds הישרדות).
- **Accounts:** "My list" and likes, stored per user in Supabase with Row Level Security.
- **Ask AI:** a chat that recommends titles by searching the real database through tools, so it can only suggest titles that exist on the site. It weighs in the user's services and liked titles, and has a per-user daily limit.

## Architecture

```
 Wikidata · IMDb datasets · TMDB · Wikipedia (EN/HE) · OMDb
                │  scripts/*.py   (weekly, GitHub Actions; API answers cached on the pipeline-cache branch)
                ▼
 data/titles.json.gz  ──►  Supabase (PostgreSQL: titles, cast, tags, where to watch, users' lists)
                │                         ▲
                ▼                         │ SQL functions (search, browse)
 site/  (static site on Vercel)  ─────────┘
   index.html  — vanilla JS single-page app
   api/ask.js  — serverless AI endpoint: Claude API tool-use loop over database search tools
   api/t.js    — link previews for shared titles
```

| Layer | Choice |
|---|---|
| Data pipeline | Python, run weekly by GitHub Actions |
| Database | Supabase (PostgreSQL), SQL migrations in `supabase/` |
| Website | Vanilla JavaScript single-page app, PWA |
| Hosting & API | Vercel (static site + serverless functions) |
| AI | Anthropic Claude API with tool use |

Hard parts worth noting: matching the same title across five sources with different IDs and languages; deciding which
titles count as Israeli (`scripts/languages.py`); never borrowing a poster or Hebrew name from a different title
that shares its name (ambiguous cases go to a manual-review file); and keeping the AI grounded in the catalog.

## Data

`data/` holds the current dataset (gzip-compressed):

| File | What it is |
|---|---|
| `titles.json.gz` | All titles, one object per title — what the website reads |
| `titles.csv.gz` | The same data as CSV |
| `same_name_review.csv` | US/Israeli titles that share a name, for manual review |
| `hewiki_poster_review.csv` | Probable Hebrew posters from Hebrew Wikipedia, for manual review (`use_it` column) |

About 58,000 titles: ~42,000 movies and ~16,000 TV series. Each has English and (where available) Hebrew title, year, genres, runtime, seasons, IMDb rating and votes, Rotten Tomatoes and Metacritic scores (mostly movies), English and Hebrew posters, English and Hebrew synopses, and links to IMDb, English/Hebrew Wikipedia and Metacritic.

### Rules

- **Scope:** country of origin United States or Israel; movies released 1980–2026; TV series that started 1980–2026 or were still running in 1980 or later. Short films, single episodes and pilots are excluded.
- **Hebrew site:** each title shows only its *own* Hebrew title and poster (matched by its own IMDb ID). If it has none, the Hebrew site shows the English title/poster. Use `display_title_he` and `display_poster_he`.
- **Same-name titles:** when a US title and an Israeli title share a name (English or Hebrew), nothing is changed. Both are flagged in `same_name_flag` and listed in `same_name_review.csv` for a manual decision.

## Pipeline

**Everything at once:** `bash scripts/update_all.sh` rebuilds the catalog from the sources, writes the site files and loads the database. It runs every Sunday on GitHub Actions (`.github/workflows/weekly-update.yml`, needs the `TMDB_TOKEN` and `SUPABASE_SECRET` repository secrets) and commits the new site files; Vercel then redeploys. Cached TMDB answers are kept on the `pipeline-cache` branch.

Extra steps it runs besides the list below: `tmdb_search_fill.py` (name-and-year TMDB match for titles the IMDb lookup missed), `wikidata_posters.py` (official posters from Wikidata), `providers.py` / `networks.py` / `us_services.py` / `watch_files.py` (where to watch).

The individual steps, in order:

1. `scripts/stage1.py` — Wikidata: IDs and dates of US/Israeli films and series
2. `scripts/stage2.py` — Wikidata: titles (EN/HE), IMDb/Metacritic IDs, Wikipedia links, genres
3. `scripts/build.py` — joins IMDb datasets (ratings, votes, runtime), filters scope
4. `scripts/tmdb_enrich.py` — TMDB: posters (EN/HE), Hebrew titles, synopses, seasons
5. `scripts/merge_tmdb.py` — merges TMDB data, applies the Hebrew and same-name rules; then `scripts/languages.py` — of the titles connected to Israel, any Hebrew spoken makes it Israeli, otherwise American (TMDB languages)
6. `scripts/hewiki_posters.py` — Hebrew Wikipedia: lead images for titles still missing a Hebrew poster
7. `scripts/hewiki_apply.py` — adds those posters where they're clearly Hebrew (Israeli titles, or the file says so) and lists the rest in `data/hewiki_poster_review.csv`
8. `scripts/scores.py` — Wikidata: Rotten Tomatoes (Tomatometer) and Metacritic scores, and Rotten Tomatoes page links
9. `scripts/cast.py`, `scripts/people_he.py`, `scripts/people_photos.py` — cast and crew from IMDb, Hebrew names from Wikidata, photos from TMDB
10. `scripts/tags.py` — tags per title: Wikidata detailed genres + TMDB keywords
11. `scripts/site_catalog.py` — builds `site/catalog.json` for the website
12. `scripts/xlsx_build.py` — Excel version for browsing

Step 3 needs `title.basics.tsv.gz` and `title.ratings.tsv.gz` from https://datasets.imdbws.com in `raw/imdb/`.
Step 4 needs a TMDB API Read Access Token in `.secrets/tmdb_token` (not committed).

## Sources and attribution

- [Wikidata](https://www.wikidata.org) — CC0
- [IMDb non-commercial datasets](https://developer.imdb.com/non-commercial-datasets/) — personal and non-commercial use only
- [TMDB](https://www.themoviedb.org) — This product uses the TMDB API but is not endorsed or certified by TMDB.
- [Hebrew Wikipedia](https://he.wikipedia.org) — poster images there are hosted under fair use and are not licensed for reuse; treat them as provisional.
