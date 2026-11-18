-- Codici promo per creatori e community, con tracciamento (esegui dopo 007)
create table if not exists promo_codes (
  code text primary key,
  creator text not null,
  channel text,
  discount_pct int not null default 0 check (discount_pct between 0 and 100),
  months int not null default 1 check (months between 1 and 12),
  commission_pct int not null default 0 check (commission_pct between 0 and 100),
  stripe_coupon_id text,
  stripe_promotion_id text,
  active boolean not null default true,
  note text,
  created_at timestamptz not null default now()
);
create table if not exists promo_events (
  id bigserial primary key,
  code text not null,
  kind text not null check (kind in ('click','signup','paid','renewal')),
  user_email text,
  plan text,
  amount numeric(10,2) not null default 0,
  ref_id text,
  created_at timestamptz not null default now()
);
create unique index if not exists promo_events_ref on promo_events (kind, ref_id) where ref_id is not null;
create index if not exists promo_events_code on promo_events (code, kind);
create index if not exists promo_events_user on promo_events (user_email, kind);
alter table promo_codes enable row level security;    -- il browser parla solo con il backend
alter table promo_events enable row level security;
