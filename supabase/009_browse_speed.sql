-- Ma Roim: fast browse pages + Hebrew as the default language.
-- Run once in Supabase → SQL Editor. Safe to run again.

-- Browse pages sort by date (newest / oldest) or by name. Without these indexes the database
-- reads the whole titles table first, which can pass the 3-second limit on the first visit.
create index if not exists titles_year_new         on public.titles (year desc nulls last, imdb_votes desc);
create index if not exists titles_type_year_new    on public.titles (type, year desc nulls last, imdb_votes desc);
create index if not exists titles_type_il_year_new on public.titles (type, israeli, year desc nulls last, imdb_votes desc);
create index if not exists titles_type_year_old    on public.titles (type, year asc nulls last, imdb_votes desc);
create index if not exists titles_type_il_year_old on public.titles (type, israeli, year asc nulls last, imdb_votes desc);
create index if not exists titles_type_title       on public.titles (type, title);
create index if not exists titles_type_il_title    on public.titles (type, israeli, title);
create index if not exists titles_type_title_he    on public.titles (type, title_he asc nulls last, title);
create index if not exists titles_type_il_title_he on public.titles (type, israeli, title_he asc nulls last, title);
analyze public.titles;

-- A little more room for visitors' queries (the default is 3 seconds)
alter role anon set statement_timeout = '8s';
alter role authenticated set statement_timeout = '8s';
notify pgrst, 'reload config';

-- New accounts start in Hebrew
alter table public.profiles alter column lang set default 'he';
