-- Studio v2: profili creator, dati fiscali, registro incassi reali e costi (esegui dopo 015)
alter table public.creators add column if not exists profile text not null default 'nano' check (profile in ('nano','standard','partner','retention'));
alter table public.creators add column if not exists cap_pct int not null default 20 check (cap_pct between 0 and 60);
alter table public.creators add column if not exists regime text check (regime in ('forfettario','ordinario','occasionale','estero'));
alter table public.creators add column if not exists tax_id text;          -- codice fiscale o partita IVA
alter table public.creators add column if not exists country text default 'IT';
alter table public.creators add column if not exists iban text;
alter table public.creators add column if not exists invoice_mode text;    -- fattura elettronica / ricevuta / nessuno
alter table public.creators add column if not exists tax_updated_at timestamptz;

alter table public.creator_payouts add column if not exists vat_amount numeric(10,2) not null default 0;
alter table public.creator_payouts add column if not exists doc_ref text;  -- numero fattura o ricevuta

-- i rimborsi degli abbonati attribuiti a un codice
alter table public.promo_events drop constraint if exists promo_events_kind_check;
alter table public.promo_events add constraint promo_events_kind_check check (kind in ('click','signup','paid','renewal','refund'));

-- registro degli incassi reali (abbonamenti, rinnovi, rimborsi, contestazioni, donazioni)
create table if not exists public.payments (
  id bigserial primary key,
  user_email text,
  kind text not null check (kind in ('payment','renewal','refund','dispute','donation')),
  amount numeric(10,2) not null,          -- positivo = incasso, negativo = rimborso o perdita
  plan text,
  code text,                              -- codice creator, se attribuito
  stripe_id text unique,
  created_at timestamptz not null default now()
);
create index if not exists payments_created on public.payments (created_at desc);
alter table public.payments enable row level security;

-- costi che inserisci tu dal pannello (server, strumenti, commercialista...)
create table if not exists public.admin_costs (
  id bigserial primary key,
  label text not null,
  amount numeric(10,2) not null check (amount >= 0),
  recurring boolean not null default true,   -- true = ogni mese, false = una tantum
  month date not null,                       -- primo giorno del mese di inizio (o del mese, se una tantum)
  ended date,
  created_at timestamptz not null default now()
);
alter table public.admin_costs enable row level security;
