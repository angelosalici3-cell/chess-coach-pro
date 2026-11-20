-- Memoria condivisa delle valutazioni del motore, una riga per posizione.
-- Serve a non rifare la stessa analisi: aperture comuni, partite di giocatori già aggiunti da altri, partite tra due utenti dell'app.
-- Esegui nel SQL Editor di Supabase. Finché non esiste, l'analisi funziona come prima.
create table if not exists eval_cache (
  fen         text primary key,                -- primi 4 campi del FEN: posizione, turno, arrocchi, en passant
  eval_pawns  real not null,                   -- in pedoni, dal punto di vista del Bianco; matto = ±100
  best_san    text,                            -- miglior mossa in notazione SAN
  depth       smallint not null default 12,
  src         text not null default 'chess_api',   -- 'chess_api' oppure, in futuro, 'lichess_db'
  created_at  timestamptz not null default now()
);
alter table eval_cache enable row level security;   -- nessuna policy: solo il backend (service role) la legge
