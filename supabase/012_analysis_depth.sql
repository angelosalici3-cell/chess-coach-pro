-- Colonna mancante: dalla v3.3 l'analisi scrive la profondità del motore, ma nessuno script la creava.
-- Senza questa colonna ogni analisi falliva all'ultimo passaggio e la partita restava "da analizzare".
alter table public.games add column if not exists analysis_depth int;
alter table public.games add column if not exists highlights jsonb;
alter table public.profili_scacchi add column if not exists history_n int default 0;
