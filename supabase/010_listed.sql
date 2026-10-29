-- Ma Roim: titles shown in lists. Run once in Supabase → SQL Editor. Safe to run again.
-- Titles without any poster are not shown on the site (set by the weekly update, scripts/supabase_load_tags.py).
alter table public.titles add column if not exists listed boolean not null default true;
