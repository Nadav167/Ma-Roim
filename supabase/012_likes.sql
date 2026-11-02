-- Ma Roim: "I liked this" marks (signed-in users). The AI helper gives some weight to titles similar to the liked ones.
-- Run once in Supabase → SQL Editor. Safe to run again.
create table if not exists public.likes (
  user_id   uuid not null references auth.users (id) on delete cascade,
  title_id  text not null references public.titles (id) on delete cascade,
  liked_at  timestamptz not null default now(),
  primary key (user_id, title_id)
);
alter table public.likes enable row level security;
drop policy if exists "Own rows" on public.likes;
create policy "Own rows" on public.likes for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
