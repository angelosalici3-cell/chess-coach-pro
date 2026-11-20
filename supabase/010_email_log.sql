-- Registro delle email inviate: impedisce di mandare due volte la stessa mail (benvenuto, grazie abbonamento).
create table if not exists email_log (
  user_email text not null,
  kind text not null,
  sent_at timestamptz not null default now(),
  primary key (user_email, kind)
);
alter table email_log enable row level security;   -- solo il backend (service role) vi accede
