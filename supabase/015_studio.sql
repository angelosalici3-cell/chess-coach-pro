-- Studio creator: chi può entrare e i pagamenti già fatti (esegui dopo 014)
create table if not exists public.creators (
  email text primary key,
  name text not null,
  code text not null references public.promo_codes(code),
  active boolean not null default true,
  created_at timestamptz not null default now()
);
create table if not exists public.creator_payouts (
  id bigserial primary key,
  code text not null,
  amount numeric(10,2) not null,
  note text,
  paid_at timestamptz not null default now()
);
create index if not exists creator_payouts_code on public.creator_payouts (code);
alter table public.creators enable row level security;
alter table public.creator_payouts enable row level security;
