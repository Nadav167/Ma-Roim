-- Ma Roim: the site owner's review screen (same-name US/Israeli titles, missing posters).
-- Run once in Supabase → SQL Editor. Safe to run again.

-- Only the site owner's account can make review decisions
create or replace function public.is_admin() returns boolean
language sql stable as $$ select coalesce(auth.jwt() ->> 'email', '') = 'nadav167@gmail.com' $$;

-- Decisions per title. Everyone can read them (the site applies them right away);
-- the weekly update applies them to the catalog files too (scripts/apply_fixes.py).
create table if not exists public.title_fixes (
  title_id     text primary key,
  hide         boolean not null default false,   -- remove the title from the site
  no_title_he  boolean not null default false,   -- its Hebrew name is wrong: show the English one
  no_poster_he boolean not null default false,   -- its Hebrew poster is wrong: show the English one
  poster_url   text,                             -- poster picked by hand
  updated_at   timestamptz not null default now()
);
alter table public.title_fixes enable row level security;
drop policy if exists "Anyone can read fixes" on public.title_fixes;
create policy "Anyone can read fixes" on public.title_fixes for select using (true);
drop policy if exists "Owner edits fixes" on public.title_fixes;
create policy "Owner edits fixes" on public.title_fixes for all using (public.is_admin()) with check (public.is_admin());

-- Which same-name pairs were already reviewed
create table if not exists public.pair_reviews (
  us_id      text not null,
  il_id      text not null,
  decision   text not null,
  decided_at timestamptz not null default now(),
  primary key (us_id, il_id)
);
alter table public.pair_reviews enable row level security;
drop policy if exists "Owner reviews pairs" on public.pair_reviews;
create policy "Owner reviews pairs" on public.pair_reviews for all using (public.is_admin()) with check (public.is_admin());

-- The owner's decisions also change the titles table straight away
drop policy if exists "Owner edits titles" on public.titles;
create policy "Owner edits titles" on public.titles for update using (public.is_admin()) with check (public.is_admin());
drop policy if exists "Owner removes titles" on public.titles;
create policy "Owner removes titles" on public.titles for delete using (public.is_admin());

-- Titles shown in lists. Titles with no poster and under 100 IMDb votes, and posterless short/web episodes,
-- stay searchable by name but are left out of the browse lists (owner's rule). Set by the weekly update.
alter table public.titles add column if not exists listed boolean not null default true;
