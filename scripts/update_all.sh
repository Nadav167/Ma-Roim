#!/usr/bin/env bash
# Rebuild the whole catalog from the sources and publish it. Run from the repo root.
# Used every week by .github/workflows/weekly-update.yml; can also be run by hand.
#   FRESH=1 (default)  re-query Wikidata, re-download IMDb, refetch where-to-watch, refresh recent titles
#   LOAD=1  (default)  upload to Supabase at the end
# Needs .secrets/tmdb_token, .secrets/supabase_secret and .secrets/supabase_url.
set -euo pipefail
FRESH=${FRESH:-1}; LOAD=${LOAD:-1}
step() { echo; echo "=== $(date -u +%H:%M:%S) $*"; }
mkdir -p raw/imdb raw/tmdb out data

if [ "$FRESH" = 1 ]; then
  step "Fresh sources"
  rm -rf raw/stage1 raw/stage2 raw/items.json raw/scores.json
  rm -f raw/tmdb/providers.jsonl
  for f in title.basics title.ratings title.principals name.basics; do
    curl -sSfL --retry 3 -A "MaRoimDataset/0.1" -o "raw/imdb/$f.tsv.gz" "https://datasets.imdbws.com/$f.tsv.gz"
  done
  python3 scripts/weekly_prune.py
fi

step "Wikidata titles";          python3 scripts/stage1.py; python3 scripts/stage2.py
step "IMDb join";                python3 scripts/build.py; cp out/ma_roim_titles.json raw/base_titles.json
step "TMDB details";             python3 scripts/tmdb_enrich.py; python3 scripts/tmdb_search_fill.py; python3 scripts/merge_tmdb.py
step "More posters";             python3 scripts/hewiki_posters.py; python3 scripts/hewiki_apply.py; python3 scripts/wikidata_posters.py; python3 scripts/enwiki_posters.py
step "Critics' scores";          python3 scripts/scores.py
step "Cast and crew";            python3 scripts/cast.py; python3 scripts/people_he.py; python3 scripts/people_photos.py
step "Tags and trailers";        python3 scripts/tags.py; python3 scripts/trailers.py
step "Where to watch";           python3 scripts/providers.py; python3 scripts/networks.py; python3 scripts/us_services.py
step "Versions of the same show"; python3 scripts/versions.py
step "Site files";               python3 scripts/watch_files.py; python3 scripts/site_catalog.py
step "Dataset copies"
gzip -9 -c out/ma_roim_titles.json > data/titles.json.gz
gzip -9 -c out/ma_roim_titles.csv > data/titles.csv.gz
cp out/same_name_review.csv out/hewiki_poster_review.csv data/

if [ "$LOAD" = 1 ]; then
  step "Database"
  python3 scripts/supabase_load.py
  python3 scripts/supabase_load_cast.py
  python3 scripts/supabase_load_tags.py --with-stream
fi
step "Done: $(python3 -c 'import json;print(len(json.load(open("out/ma_roim_titles.json"))))') titles"
