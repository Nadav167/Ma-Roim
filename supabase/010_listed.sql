-- Ma Roim: hide titles without a poster; find both US and Israeli versions of a show in search.
-- Run once in Supabase → SQL Editor. Safe to run again.

-- Titles without any poster are not shown on the site (set by the weekly update, scripts/supabase_load_tags.py)
alter table public.titles add column if not exists listed boolean not null default true;

-- Search-only alias: the other version's names (e.g. the US "Survivor" can also be found as "הישרדות").
-- The search text is rebuilt to include it (scripts/versions.py fills it).
alter table public.titles add column if not exists search_alias text;
drop index if exists public.titles_search_trgm;
alter table public.titles drop column if exists search_text;
alter table public.titles add column search_text text generated always as
  (lower(title || ' ' || coalesce(title_he, '') || ' ' || coalesce(original_title, '') || ' ' || coalesce(search_alias, ''))) stored;
create index if not exists titles_search_trgm on public.titles using gin (search_text gin_trgm_ops);
analyze public.titles;
