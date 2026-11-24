-- Donazioni una tantum (esegui dopo 013)
create table if not exists public.donations (
  id bigserial primary key,
  user_email text,
  amount numeric(10,2) not null,
  currency text not null default 'eur',
  stripe_session_id text unique,
  created_at timestamptz not null default now()
);
create index if not exists donations_user on public.donations (user_email);
alter table public.donations enable row level security;
