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

-- Salvataggio che sostituisce una posizione solo se la nuova valutazione è più profonda (usato dal motore locale e, in futuro, dal dataset Lichess).
create or replace function eval_cache_put(p jsonb) returns void
language sql security definer set search_path = public as $$
  insert into eval_cache (fen, eval_pawns, best_san, depth, src)
  select x->>'fen', (x->>'eval_pawns')::real, x->>'best_san', (x->>'depth')::smallint, coalesce(x->>'src', 'chess_api')
  from jsonb_array_elements(p) x
  on conflict (fen) do update
    set eval_pawns = excluded.eval_pawns, best_san = excluded.best_san, depth = excluded.depth, src = excluded.src, created_at = now()
    where excluded.depth > eval_cache.depth;
$$;
revoke all on function eval_cache_put(jsonb) from public, anon, authenticated;
