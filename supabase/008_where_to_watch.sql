-- Where to watch in Israel, for filtering ("only what's on my services") on list pages and in the AI.
-- Run once in Supabase: SQL Editor → New query → paste → Run.

alter table public.titles add column if not exists stream_il integer[] not null default '{}';   -- provider IDs streaming it in Israel (incl. free)
create index if not exists titles_stream_il on public.titles using gin (stream_il);

-- Each user's own streaming services, synced across devices
alter table public.profiles add column if not exists services integer[] not null default '{}';

-- find_titles gains an "on_services" filter (replaces the previous version)
drop function if exists public.find_titles(text, text, text, text, text, integer, integer, numeric, integer, integer, boolean, integer, integer);
create or replace function public.find_titles(
  person      text      default null,
  person_role text      default null,
  genre       text      default null,
  tag         text      default null,
  title_type  text      default null,
  min_year    integer   default null,
  max_year    integer   default null,
  min_imdb    numeric   default null,
  min_rt      integer   default null,
  min_mc      integer   default null,
  israeli     boolean   default null,
  min_votes   integer   default null,
  on_services integer[] default null,   -- only titles streaming in Israel on one of these provider IDs
  lim         integer   default 20
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
    and (on_services is null or cardinality(on_services) = 0 or t.stream_il && on_services)
  order by t.imdb_votes desc
  limit least(coalesce(lim, 20), 100);
end;
$$;
