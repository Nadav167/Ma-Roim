-- Cast and crew, plus the search function the AI helper uses.
-- Run once in Supabase: SQL Editor → New query → paste → Run.

create table if not exists public.people (
  id          text primary key,            -- IMDb person ID, e.g. nm0564215
  name        text not null,
  name_he     text,
  birth_year  integer,
  death_year  integer
);
create index if not exists people_name_trgm on public.people using gin (lower(name) gin_trgm_ops);
create index if not exists people_name_he_trgm on public.people using gin (lower(coalesce(name_he, '')) gin_trgm_ops);

create table if not exists public.credits (
  title_id   text not null references public.titles (id) on delete cascade,
  person_id  text not null references public.people (id) on delete cascade,
  role       text not null check (role in ('cast', 'director', 'writer', 'creator', 'composer')),
  ord        integer not null,               -- billing order on IMDb
  character  text,
  primary key (title_id, person_id, role)
);
create index if not exists credits_person on public.credits (person_id);

alter table public.people enable row level security;
alter table public.credits enable row level security;
drop policy if exists "Anyone can read people" on public.people;
create policy "Anyone can read people" on public.people for select using (true);
drop policy if exists "Anyone can read credits" on public.credits;
create policy "Anyone can read credits" on public.credits for select using (true);

-- Find titles by any combination of filters. Every argument is optional.
-- Example: horror after 2020 with James McAvoy rated 8.0+ on IMDb:
--   select * from find_titles(person => 'james mcavoy', genre => 'horror', min_year => 2021, min_imdb => 8.0);
create or replace function public.find_titles(
  person      text    default null,   -- actor/director/writer name, English or Hebrew, any case
  person_role text    default null,   -- 'cast' | 'director' | 'writer' | 'creator' | 'composer'
  genre       text    default null,   -- e.g. 'horror', 'comedy', 'science fiction'
  title_type  text    default null,   -- 'movie' | 'tv'
  min_year    integer default null,
  max_year    integer default null,
  min_imdb    numeric default null,
  min_rt      integer default null,   -- Rotten Tomatoes %
  min_mc      integer default null,   -- Metacritic
  israeli     boolean default null,
  min_votes   integer default null,
  lim         integer default 20
)
returns setof public.titles
language sql stable
as $$
  select t.* from public.titles t
  where (find_titles.genre is null or exists (select 1 from unnest(t.genres) g where g ilike find_titles.genre || '%'))
    and (title_type is null or t.type = title_type)
    and (min_year is null or t.year >= min_year)
    and (max_year is null or t.year <= max_year)
    and (min_imdb is null or t.imdb_rating >= min_imdb)
    and (min_rt is null or t.rt_score >= min_rt)
    and (min_mc is null or t.mc_score >= min_mc)
    and (find_titles.israeli is null or t.israeli = find_titles.israeli)
    and (min_votes is null or t.imdb_votes >= min_votes)
    and (find_titles.person is null or exists (
          select 1 from public.credits c join public.people p on p.id = c.person_id
          where c.title_id = t.id
            and (person_role is null or c.role = person_role)
            and (lower(p.name) like '%' || lower(trim(find_titles.person)) || '%'
                 or lower(coalesce(p.name_he, '')) like '%' || lower(trim(find_titles.person)) || '%')))
  order by t.imdb_votes desc
  limit least(coalesce(lim, 20), 100);
$$;
