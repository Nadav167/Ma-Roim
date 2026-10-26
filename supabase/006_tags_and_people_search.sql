-- 1) Tags on titles (detailed genres + TMDB keywords, e.g. "psychological horror", "time travel"), searchable by the AI
-- 2) People search with popularity ranking, for search suggestions
-- Run once in Supabase: SQL Editor → New query → paste → Run.

alter table public.titles add column if not exists tags text[] not null default '{}';
create index if not exists titles_tags on public.titles using gin (tags);

-- Popularity of a person = total IMDb votes of their titles (so "tom" finds Tom Hanks first)
alter table public.people add column if not exists pop bigint not null default 0;
create or replace function public.refresh_people_pop() returns void language sql as $$
  update public.people p set pop = s.v
  from (select c.person_id, sum(t.imdb_votes)::bigint v
          from public.credits c join public.titles t on t.id = c.title_id group by c.person_id) s
  where s.person_id = p.id and p.pop is distinct from s.v;
$$;
select public.refresh_people_pop();
create index if not exists people_pop on public.people (pop desc);

create or replace function public.search_people(q text, lim integer default 5)
returns table (id text, name text, name_he text, photo text, pop bigint, known_for_id text, known_for text, known_for_he text)
language sql stable as $$
  with m as (
    select p.* from public.people p
    where length(trim(coalesce(q, ''))) >= 2
      and (lower(p.name) like '%' || lower(trim(q)) || '%' or lower(coalesce(p.name_he, '')) like '%' || lower(trim(q)) || '%')
    order by (lower(p.name) = lower(trim(q)) or lower(coalesce(p.name_he, '')) = lower(trim(q))) desc, p.pop desc
    limit least(coalesce(lim, 5), 20)
  )
  select m.id, m.name, m.name_he, m.photo, m.pop, k.id, k.title, k.title_he
  from m left join lateral (
    select t.id, t.title, t.title_he from public.credits c join public.titles t on t.id = c.title_id
    where c.person_id = m.id order by t.imdb_votes desc limit 1
  ) k on true
  order by (lower(m.name) = lower(trim(q)) or lower(coalesce(m.name_he, '')) = lower(trim(q))) desc, m.pop desc;
$$;

-- find_titles gains a "tag" filter (replaces the previous version)
drop function if exists public.find_titles(text, text, text, text, integer, integer, numeric, integer, integer, boolean, integer, integer);
create or replace function public.find_titles(
  person      text    default null,
  person_role text    default null,
  genre       text    default null,
  tag         text    default null,   -- subgenre / theme, e.g. 'psychological', 'time travel', 'heist'
  title_type  text    default null,
  min_year    integer default null,
  max_year    integer default null,
  min_imdb    numeric default null,
  min_rt      integer default null,
  min_mc      integer default null,
  israeli     boolean default null,
  min_votes   integer default null,
  lim         integer default 20
)
returns setof public.titles
language plpgsql stable
as $$
declare
  q    text := lower(trim(coalesce(person, '')));
  pids text[];
  tids text[];
begin
  if q <> '' then
    select array_agg(p.id) into pids from (
      select id from public.people where lower(name) like '%' || q || '%'
      union
      select id from public.people where lower(coalesce(name_he, '')) like '%' || q || '%'
      limit 50
    ) p;
    if pids is null then
      select array_agg(s.id) into pids from (
        select id from public.people where lower(name) % q order by similarity(lower(name), q) desc limit 3
      ) s;
    end if;
    if pids is null then return; end if;
    select array_agg(distinct c.title_id) into tids
      from public.credits c where c.person_id = any (pids) and (person_role is null or c.role = person_role);
    if tids is null then return; end if;
  end if;

  return query
  select t.* from public.titles t
  where (tids is null or t.id = any (tids))
    and (find_titles.genre is null or exists (select 1 from unnest(t.genres) g where g ilike find_titles.genre || '%'))
    and (find_titles.tag is null or exists (select 1 from unnest(t.tags) x where x ilike '%' || find_titles.tag || '%'))
    and (title_type is null or t.type = title_type)
    and (min_year is null or t.year >= min_year)
    and (max_year is null or t.year <= max_year)
    and (min_imdb is null or t.imdb_rating >= min_imdb)
    and (min_rt is null or t.rt_score >= min_rt)
    and (min_mc is null or t.mc_score >= min_mc)
    and (find_titles.israeli is null or t.israeli = find_titles.israeli)
    and (min_votes is null or t.imdb_votes >= min_votes)
  order by t.imdb_votes desc
  limit least(coalesce(lim, 20), 100);
end;
$$;
