-- Carte collezionabili delle tue partite (esegui dopo 005)
create table if not exists cards (
  id bigserial primary key,
  user_email text not null,
  goal text not null,
  rarity text not null check (rarity in ('common','rare','epic','legendary')),
  game_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  seen boolean not null default false
);
create unique index if not exists cards_uq on cards (user_email, goal, game_id);
create index if not exists cards_user on cards (user_email, created_at desc);
alter table cards enable row level security;   -- il browser parla solo con il backend
