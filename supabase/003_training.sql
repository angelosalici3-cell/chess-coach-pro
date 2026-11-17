-- Esegui nel SQL Editor di Supabase DOPO 001 e 002.
-- Allenamento, puzzle, ricompense, orologio delle partite.

alter table games add column if not exists has_clock boolean not null default false;
alter table config_utenti add column if not exists bonus_lessons int not null default 0;

-- Puzzle (popolata dallo script backend/scripts/import_puzzles.py, dati Lichess CC0)
create table if not exists puzzles (
  id text primary key,
  fen text not null,
  moves text not null,            -- UCI; la prima mossa è dell'avversario, poi tocca all'utente
  rating int not null,
  popularity int,
  themes text[] not null default '{}',
  opening_tags text[]
);
create index if not exists puzzles_rating_idx on puzzles (rating);
create index if not exists puzzles_themes_gin on puzzles using gin (themes);

create table if not exists training_stats (
  user_email text primary key,
  puzzle_rating int not null default 1200,
  puzzles_solved int not null default 0,
  puzzles_failed int not null default 0,
  mistakes_fixed int not null default 0,
  current_streak int not null default 0,
  best_streak int not null default 0,
  training_days int not null default 0,
  last_train_date date
);

-- Ripasso degli errori con ripetizione a intervalli (caselle di Leitner 1..5)
create table if not exists mistake_cards (
  user_email text not null,
  error_id text not null,
  box int not null default 1,
  due_at timestamptz not null default now(),
  attempts int not null default 0,
  correct int not null default 0,
  last_at timestamptz,
  primary key (user_email, error_id)
);

create table if not exists puzzle_attempts (
  id bigserial primary key,
  user_email text not null,
  puzzle_id text not null,
  solved boolean not null,
  rating_before int not null,
  rating_after int not null,
  created_at timestamptz not null default now()
);
create index if not exists puzzle_attempts_user on puzzle_attempts (user_email, created_at desc);

-- Ricompense già riscattate (una sola volta per livello)
create table if not exists rewards (
  id bigserial primary key,
  user_email text not null,
  code text not null,
  kind text not null,
  detail jsonb,
  claimed_at timestamptz not null default now(),
  unique (user_email, code)
);

alter table puzzles enable row level security;
alter table training_stats enable row level security;
alter table mistake_cards enable row level security;
alter table puzzle_attempts enable row level security;
alter table rewards enable row level security;

-- Quota lezioni: rispetta la scadenza dell'abbonamento/prova e usa le lezioni bonus quando il limite mensile è finito.
create or replace function consume_gm_lesson(p_email text) returns boolean
language plpgsql security definer set search_path = public as $$
declare v_month text := to_char(now(), 'YYYY-MM'); v_tier text; v_exp date; v_limit int; v_used int; v_bonus int;
begin
  select tier, data_scadenza into v_tier, v_exp from config_utenti where user_email = p_email;
  if v_tier is null or (v_tier <> 'Free' and v_exp is not null and v_exp < current_date) then v_tier := 'Free'; end if;
  v_limit := case v_tier when 'Free' then 5 when 'Plus' then 20 else null end;
  insert into quota_usage (user_email, quota_month) values (p_email, v_month) on conflict do nothing;
  update quota_usage set ai_analyses_used = ai_analyses_used + 1
   where user_email = p_email and quota_month = v_month and (v_limit is null or ai_analyses_used < v_limit)
  returning ai_analyses_used into v_used;
  if v_used is not null then return true; end if;
  -- limite mensile finito: prova con le lezioni bonus
  update config_utenti set bonus_lessons = bonus_lessons - 1 where user_email = p_email and bonus_lessons > 0 returning bonus_lessons into v_bonus;
  if v_bonus is null then return false; end if;
  update quota_usage set ai_analyses_used = ai_analyses_used + 1 where user_email = p_email and quota_month = v_month;
  return true;
end $$;

create or replace function refund_gm_lesson(p_email text) returns void
language plpgsql security definer set search_path = public as $$
declare v_month text := to_char(now(), 'YYYY-MM'); v_tier text; v_exp date; v_limit int; v_used int;
begin
  select tier, data_scadenza into v_tier, v_exp from config_utenti where user_email = p_email;
  if v_tier is null or (v_tier <> 'Free' and v_exp is not null and v_exp < current_date) then v_tier := 'Free'; end if;
  v_limit := case v_tier when 'Free' then 5 when 'Plus' then 20 else null end;
  select ai_analyses_used into v_used from quota_usage where user_email = p_email and quota_month = v_month;
  if v_used is null or v_used <= 0 then return; end if;
  if v_limit is not null and v_used > v_limit then
    update config_utenti set bonus_lessons = bonus_lessons + 1 where user_email = p_email;
  end if;
  update quota_usage set ai_analyses_used = v_used - 1 where user_email = p_email and quota_month = v_month;
end $$;

revoke execute on function consume_gm_lesson(text), refund_gm_lesson(text) from public, anon, authenticated;
grant execute on function consume_gm_lesson(text), refund_gm_lesson(text) to service_role;
