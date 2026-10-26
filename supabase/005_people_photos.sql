-- Adds headshots for cast and crew (TMDB profile image path, e.g. /abc123.jpg).
-- Run once in Supabase: SQL Editor → New query → paste → Run.
alter table public.people add column if not exists photo text;
