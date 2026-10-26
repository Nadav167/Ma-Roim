-- Adds YouTube trailer keys (English and Hebrew) to titles.
-- Run once in Supabase: SQL Editor → New query → paste → Run.
alter table public.titles add column if not exists trailer_en text;
alter table public.titles add column if not exists trailer_he text;
