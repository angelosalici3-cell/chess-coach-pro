-- Esegui nel SQL Editor di Supabase dopo 001_production.sql.
-- Le lezioni del Gran Maestro vivono in colonne dedicate: `spiegazione` conteneva anche testi
-- automatici del vecchio worker ("Perdita X CP"), per questo la pagina Lezioni mostrava tutti gli errori.
alter table errori_utenti add column if not exists gm_lesson text;
alter table errori_utenti add column if not exists gm_lesson_at timestamptz;

-- Recupera le vere lezioni GM generate dalla vecchia app (erano HTML con classe gm-card) e le ripulisce.
update errori_utenti set
  gm_lesson = btrim(regexp_replace(regexp_replace(regexp_replace(spiegazione, '</div>', E'\n', 'g'), '<[^>]+>', '', 'g'), E'\n{2,}', E'\n', 'g')),
  gm_lesson_at = coalesce(data, now())
where gm_lesson is null and spiegazione like '%gm-card%';

create index if not exists errori_gm_idx on errori_utenti (user_email, gm_lesson_at desc) where gm_lesson is not null;
