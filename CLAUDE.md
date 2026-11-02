# Ma Roim · מה רואים — notes for every session

A bilingual (Hebrew-first, English) catalog of US and Israeli movies and TV series from 1980 to today,
with posters, scores (IMDb, Rotten Tomatoes, Metacritic), where to watch in Israel, user accounts and an AI helper.
Live at **https://ma-roim-site.vercel.app**. Owner: Nadav (doesn't write code; describes what he wants,
judges the result on the site, often from his phone). Talk to him in plain language, in Hebrew when he writes Hebrew.

## Where things live
- **Code**: this repo (GitHub `Nadav167/Ma-Roim`, private). The whole site is `site/index.html` (vanilla JS, one file).
- **Hosting**: Vercel project `ma-roim`, root directory `site`, deploys on every push to `main`.
  Commits must be authored as `Nadav167 <173299564+Nadav167@users.noreply.github.com>` or Vercel blocks the deploy.
- **Database**: Supabase (`prnfnqvjirwuyafvsulk`). Schema changes are SQL files in `supabase/` (numbered);
  Nadav runs them himself in Supabase → SQL Editor. The publishable key in the site code is public by design.
- **Serverless functions**: `site/api/ask.js` (AI helper, needs `ANTHROPIC_API_KEY` in Vercel),
  `site/api/t.js` (shared-link previews for WhatsApp: `/t/<id>`).
- **Secrets** (never commit): `.secrets/tmdb_token`, `.secrets/supabase_secret`, `.secrets/supabase_url`,
  `.secrets/omdb_key`. In GitHub Actions they are the repository secrets `TMDB_TOKEN`, `SUPABASE_SECRET`, `OMDB_KEY`.

## Data pipeline
`bash scripts/update_all.sh` rebuilds everything from Wikidata, IMDb datasets, TMDB, Hebrew/English Wikipedia and
OMDb, writes the site files (`site/home.json`, `site/index.json`, `site/watch/*`), the dataset copies in `data/`,
and loads Supabase. It runs every Sunday via `.github/workflows/weekly-update.yml`; TMDB/Wikipedia/OMDb answers are
cached on the `pipeline-cache` branch. README.md lists every step.

Title ids: `Q…` = Wikidata titles; `M…`/`S…` = Israeli movies/series added from TMDB (`scripts/tmdb_israeli.py`).

## Rules Nadav set (keep them)
- **Hebrew first**: the site opens in Hebrew; English only if the visitor picks it.
- **Own poster and name only**: a title shows only its OWN Hebrew title/poster, otherwise the English one —
  never borrowed from another title (e.g. an Israeli remake with the same name).
- **No title without a poster**: titles with no poster from any source are dropped (`scripts/drop_unknown.py`)
  and come back automatically if a poster appears later.
- **US/Israeli versions of the same show** (Survivor / הישרדות, The Office / המשרד) both stay, and each is found
  in search by the other's name (`search_alias`, `scripts/versions.py`, `data/versions.csv`). Same-name titles
  that are simply different works are left as they are.
- **Rows**: every row shows at most 18 titles plus a "Show all" card; full lists sorted by date or name are the
  only exception.
- **Years**: a series still running shows only its first year ("2023", never "2023–").
- **Titles**: no Wikipedia disambiguation notes in names ("(סרט)", "(סדרת טלוויזיה עתידית)", "(TV series)"):
  `scripts/clean_titles.py`.
- **Season table** on every series page (season, episodes, first/last episode date), like Wikipedia's
  "Series overview": English Wikipedia's table first (Nadav trusts it more, `scripts/enwiki_seasons.py`), TMDB as the
  fallback (`scripts/seasons.py`). English Wikipedia answers 429 from the cloud sandbox; it works from GitHub Actions
  and from Nadav's linked computer.
- **Only American and Israeli titles**, plus Nadav's hand-picked exceptions: titles not in English/Hebrew are removed
  unless Israeli, partly in English or made by an American company (`scripts/drop_foreign.py`). Exceptions he chose
  (Money Heist, big non-US series, BBC/UK nature documentaries) are listed in `data/keep_titles.csv` and added from
  TMDB by `scripts/tmdb_israeli.py`; to add more, append rows there (tmdb_type, tmdb_id).
- **Streaming services in the picker**: Netflix, HBO Max, Prime Video, Apple TV, Disney+ (Disney+ from its US catalog).
- **Likes** ("אהבתי", signed-in users only, table `likes`, `supabase/012_likes.sql`): Ask AI gives about 25% weight to titles
  similar to the liked ones (TMDB co-recommendations from `site/taste/*.json`, `site/api/ask.js` LIKE_WEIGHT). The button stays
  hidden until the table exists.
- **My list** can be sorted by streaming service (a title shows under every service it's on; the visitor's services first)
  and filtered by Netflix / Apple TV (subscription + store) / Disney+ / HBO Max (chips under the sort).
- **Phone layout**: no sideways page scrolling, no visible scrollbars, solid top bar, bottom bar flush to the bottom.
- Design direction: "Marquee" palette (chosen 2026-10-31 to get away from the Stremio look): warm cinema black `#100d0a`, one amber accent `#ffb547` for actions only, white rating stars, IMDb yellow kept. Speech bubbles (from the logo) only in Discover and Ask AI. Design reviews: Claude docs "מה רואים: תוכנית עיצוב" and "מה רואים: בדיקת עיצוב 2".

## Working habits
- Test changes in a phone-sized browser (Playwright, 390×844) before pushing; check the Vercel deploy status after.
- Don't do things Nadav didn't ask for; when a choice is his (deleting data, design direction), ask first.
- Explain what changed in a few plain sentences, not code.
