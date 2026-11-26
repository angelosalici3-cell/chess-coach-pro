-- Analisi condivisa: la stessa partita analizzata una sola volta, anche se più utenti la caricano.
-- games.analysis_of = id della partita che contiene le mosse (vuoto = le mosse sono di questa riga).
-- Esegui nel SQL Editor di Supabase PRIMA di pubblicare v3.40. Non cambia niente di ciò che esiste già.
alter table public.games add column if not exists analysis_of text;

-- Ricerca veloce della stessa partita analizzata da altri utenti
create index if not exists games_src_gid_done on public.games (source, source_game_id) where analyzed_at is not null;
create index if not exists games_analysis_of on public.games (analysis_of) where analysis_of is not null;
