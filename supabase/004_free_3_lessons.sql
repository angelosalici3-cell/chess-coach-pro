-- Free passa a 3 lezioni/mese (esegui dopo 003)
-- Quota lezioni: rispetta la scadenza dell'abbonamento/prova e usa le lezioni bonus quando il limite mensile è finito.
create or replace function consume_gm_lesson(p_email text) returns boolean
language plpgsql security definer set search_path = public as $$
declare v_month text := to_char(now(), 'YYYY-MM'); v_tier text; v_exp date; v_limit int; v_used int; v_bonus int;
begin
  select tier, data_scadenza into v_tier, v_exp from config_utenti where user_email = p_email;
  if v_tier is null or (v_tier <> 'Free' and v_exp is not null and v_exp < current_date) then v_tier := 'Free'; end if;
  v_limit := case v_tier when 'Free' then 3 when 'Plus' then 20 else null end;
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
  v_limit := case v_tier when 'Free' then 3 when 'Plus' then 20 else null end;
  select ai_analyses_used into v_used from quota_usage where user_email = p_email and quota_month = v_month;
  if v_used is null or v_used <= 0 then return; end if;
  if v_limit is not null and v_used > v_limit then
    update config_utenti set bonus_lessons = bonus_lessons + 1 where user_email = p_email;
  end if;
  update quota_usage set ai_analyses_used = v_used - 1 where user_email = p_email and quota_month = v_month;
end $$;

revoke execute on function consume_gm_lesson(text), refund_gm_lesson(text) from public, anon, authenticated;
grant execute on function consume_gm_lesson(text), refund_gm_lesson(text) to service_role;
