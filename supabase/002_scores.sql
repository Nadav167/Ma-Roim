-- Adds Rotten Tomatoes and Metacritic scores. Run once in Supabase: SQL Editor → New query → Run.
alter table public.titles add column if not exists rt_score smallint check (rt_score between 0 and 100);
alter table public.titles add column if not exists mc_score smallint check (mc_score between 0 and 100);
alter table public.titles add column if not exists rt_url text;
