-- v3.35: percorsi di apertura e trappole (ripasso a memoria con ripetizione a intervalli).
create table if not exists opening_cards (
  user_email text not null,
  line_id text not null,
  box int not null default 1,
  due_at timestamptz not null default now(),
  attempts int not null default 0,
  correct int not null default 0,
  last_at timestamptz,
  primary key (user_email, line_id)
);
alter table opening_cards enable row level security;
