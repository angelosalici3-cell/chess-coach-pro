-- Esegui nel SQL Editor di Supabase (una volta sola).
-- 1) Vincoli di unicità: senza questi gli upsert on_conflict dell'app vecchia non funzionavano.
create unique index if not exists games_uq on games (user_email, source, source_game_id);
create unique index if not exists moves_uq on moves (game_id, ply);
create unique index if not exists errori_uq on errori_utenti (user_email, game_id, ply);
create unique index if not exists rating_uq on storico_rating (user_email, partita_id);
create unique index if not exists profili_uq on profili_scacchi (user_email, piattaforma, lower(username));

-- 2) Sicurezza: il browser parla solo con il backend. RLS attiva e nessuna policy = l'anon key non legge nulla.
alter table games enable row level security;
alter table moves enable row level security;
alter table errori_utenti enable row level security;
alter table storico_rating enable row level security;
alter table profili_scacchi enable row level security;
alter table config_utenti enable row level security;
alter table quota_usage enable row level security;
alter table storico_abbonamenti enable row level security;
alter table ai_usage_log enable row level security;
alter table user_profiles enable row level security;

-- 3) Quota lezioni GM atomica, limite deciso dal server.
create or replace function consume_gm_lesson(p_email text) returns boolean
language plpgsql security definer set search_path = public as $$
declare v_month text := to_char(now(), 'YYYY-MM'); v_tier text; v_limit int; v_used int;
begin
  select tier into v_tier from config_utenti where user_email = p_email;
  v_limit := case coalesce(v_tier, 'Free') when 'Free' then 5 when 'Plus' then 20 else null end;
  insert into quota_usage (user_email, quota_month) values (p_email, v_month) on conflict do nothing;
  update quota_usage set ai_analyses_used = ai_analyses_used + 1
   where user_email = p_email and quota_month = v_month
     and (v_limit is null or ai_analyses_used < v_limit)
  returning ai_analyses_used into v_used;
  return v_used is not null;
end $$;

create or replace function refund_gm_lesson(p_email text) returns void
language sql security definer set search_path = public as $$
  update quota_usage set ai_analyses_used = greatest(ai_analyses_used - 1, 0)
  where user_email = p_email and quota_month = to_char(now(), 'YYYY-MM');
$$;

revoke execute on function consume_gm_lesson(text), refund_gm_lesson(text) from public, anon, authenticated;
grant execute on function consume_gm_lesson(text), refund_gm_lesson(text) to service_role;
