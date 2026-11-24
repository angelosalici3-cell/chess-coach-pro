-- Il percorso del giocatore: lettere e schede del coach (esegui dopo 012)
create table if not exists public.coach_reports (
  id bigserial primary key,
  user_email text not null,
  kind text not null check (kind in ('first','week','month','season')),
  period text not null,              -- es. 2026-11, 2026-W47, 2026-Q4, first
  facts jsonb not null default '{}',
  text text not null,
  lang text not null default 'it',
  created_at timestamptz not null default now(),
  unique (user_email, kind, period)
);
create index if not exists coach_reports_user on public.coach_reports (user_email, created_at desc);
alter table public.coach_reports enable row level security;   -- il browser parla solo con il backend
