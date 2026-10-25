-- What to Watch — database schema
-- Run once in Supabase: SQL Editor → New query → paste → Run.

create extension if not exists pg_trgm;

-- ---------- Catalog (read-only for visitors; loaded by the pipeline) ----------
create table if not exists public.titles (
  id              text primary key,          -- Wikidata ID, e.g. Q62276
  imdb_id         text unique,
  tmdb_id         integer,
  tmdb_type       text,                      -- 'movie' | 'tv'
  type            text not null,             -- 'movie' | 'tv'
  title           text not null,
  title_he        text,
  original_title  text,
  year            integer,
  end_year        integer,
  israeli         boolean not null default false,
  us              boolean not null default false,
  genres          text[] not null default '{}',
  runtime_min     integer,
  seasons         integer,
  episodes        integer,
  imdb_rating     numeric(3,1),
  imdb_votes      integer not null default 0,
  poster_en       text,
  poster_he       text,
  backdrop        text,
  overview_en     text,
  overview_he     text,
  imdb_url        text,
  wikipedia_en    text,
  wikipedia_he    text,
  metacritic_url  text,
  rt_score        smallint check (rt_score between 0 and 100),
  mc_score        smallint check (mc_score between 0 and 100),
  rt_url          text,
  same_name_flag  text,
  search_text     text generated always as (lower(title || ' ' || coalesce(title_he, '') || ' ' || coalesce(original_title, ''))) stored
);

create index if not exists titles_search_trgm on public.titles using gin (search_text gin_trgm_ops);
create index if not exists titles_votes on public.titles (imdb_votes desc);
create index if not exists titles_type_votes on public.titles (type, imdb_votes desc);
create index if not exists titles_israeli_votes on public.titles (israeli, imdb_votes desc);
create index if not exists titles_genres on public.titles using gin (genres);

alter table public.titles enable row level security;
drop policy if exists "Anyone can read titles" on public.titles;
create policy "Anyone can read titles" on public.titles for select using (true);

-- Search by English or Hebrew title, most popular first
create or replace function public.search_titles(q text, lim integer default 60)
returns setof public.titles
language sql stable
as $$
  select * from public.titles
  where search_text like '%' || lower(trim(q)) || '%'
  order by (lower(title) = lower(trim(q)) or lower(coalesce(title_he, '')) = lower(trim(q))) desc,
           imdb_votes desc
  limit least(lim, 200);
$$;

-- ---------- Per-user data (each user sees and changes only their own rows) ----------
create table if not exists public.profiles (
  id          uuid primary key references auth.users (id) on delete cascade,
  display_name text,
  lang        text not null default 'en' check (lang in ('en', 'he')),
  created_at  timestamptz not null default now()
);

create table if not exists public.watchlist (
  user_id   uuid not null references auth.users (id) on delete cascade,
  title_id  text not null references public.titles (id) on delete cascade,
  added_at  timestamptz not null default now(),
  primary key (user_id, title_id)
);

create table if not exists public.watched (
  user_id    uuid not null references auth.users (id) on delete cascade,
  title_id   text not null references public.titles (id) on delete cascade,
  watched_at timestamptz not null default now(),
  primary key (user_id, title_id)
);

create table if not exists public.watched_episodes (
  user_id    uuid not null references auth.users (id) on delete cascade,
  title_id   text not null references public.titles (id) on delete cascade,
  season     integer not null,
  episode    integer not null,
  watched_at timestamptz not null default now(),
  primary key (user_id, title_id, season, episode)
);

create table if not exists public.ai_suggestions (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users (id) on delete cascade,
  prompt     text not null,
  title_ids  text[] not null default '{}',
  answer     text,
  created_at timestamptz not null default now()
);

do $$
declare t text;
begin
  foreach t in array array['watchlist', 'watched', 'watched_episodes', 'ai_suggestions'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists "Own rows" on public.%I', t);
    execute format('create policy "Own rows" on public.%I for all using (auth.uid() = user_id) with check (auth.uid() = user_id)', t);
  end loop;
end $$;

alter table public.profiles enable row level security;
drop policy if exists "Own profile" on public.profiles;
create policy "Own profile" on public.profiles for all using (auth.uid() = id) with check (auth.uid() = id);

-- Create a profile automatically when someone signs up
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'full_name', split_part(new.email, '@', 1)))
  on conflict (id) do nothing;
  return new;
end $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();
