-- Adds the title's main countries (up to two, origin first) for the line under the poster.
-- Run once in Supabase: SQL Editor → New query → paste → Run.
alter table public.titles add column if not exists countries text[];
