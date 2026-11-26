"""Analisi condivisa: la stessa partita (stessa piattaforma e stesso id) analizzata una volta sola.
Se un altro utente ha già l'analisi della stessa partita con lo stesso colore, la riga `games` del nuovo utente punta a quella
(`games.analysis_of`) invece di rifare l'analisi e duplicare le mosse. Gli errori restano personali (si copiano poche righe).
Finché il database non ha la colonna (supabase/019_shared_analysis.sql) tutto funziona come prima."""
import logging
import time

from .db import sb

log = logging.getLogger("shared")
_st = {"ok": None, "t": 0.0}


def on() -> bool:
    """True se la colonna games.analysis_of esiste. Si rilegge ogni 2 minuti finché manca."""
    if _st["ok"] is None or (not _st["ok"] and time.time() - _st["t"] > 120):
        try:
            sb.table("games").select("analysis_of").limit(1).execute()
            _st["ok"] = True
        except Exception:
            _st["ok"] = False
        _st["t"] = time.time()
    return bool(_st["ok"])


def extra() -> str:
    """Da aggiungere agli elenchi di colonne di games che servono a trovare le mosse."""
    return ",analysis_of" if on() else ""


def mid(g: dict) -> str:
    """L'id della partita che contiene le mosse: quella condivisa se c'è, altrimenti la propria."""
    return g.get("analysis_of") or g["id"]


def reuse(game: dict, color: str, now: str) -> bool:
    """Se la stessa partita è già analizzata (stesso colore) la collega e copia gli errori. True = fatto, niente motore."""
    if not on() or not game.get("source_game_id") or not game.get("source"):
        return False
    try:
        rows = (sb.table("games").select("id,user_email,accuracy_user,highlights,analysis_depth,analysis_of")
                .eq("source", game["source"]).eq("source_game_id", game["source_game_id"]).eq("user_color", color)
                .not_.is_("analyzed_at", "null").neq("id", game["id"]).limit(10).execute().data)
    except Exception as e:
        log.warning("ricerca analisi condivisa: %s", e)
        return False
    for r in sorted(rows, key=lambda x: bool(x.get("analysis_of"))):
        real = r.get("analysis_of") or r["id"]
        try:
            if not sb.table("moves").select("ply").eq("game_id", real).limit(1).execute().data:
                continue
            errs = sb.table("errori_utenti").select("*").eq("game_id", r["id"]).eq("user_email", r["user_email"]).execute().data or []
            copy = [{"user_email": game["user_email"], "game_id": game["id"], "ply": e["ply"], "fen": e.get("fen"),
                     "mossa_critica": e.get("mossa_critica"), "best_move": e.get("best_move"), "categoria_errore": e.get("categoria_errore"),
                     "classification": e.get("classification"), "eval_loss_cp": e.get("eval_loss_cp"), "apertura": game.get("opening_name"), "data": now}
                    for e in errs]
            if copy:
                sb.table("errori_utenti").upsert(copy, on_conflict="user_email,game_id,ply").execute()
            base = {"analyzed_at": now, "accuracy_user": r.get("accuracy_user"), "analysis_of": real}
            ext = {"analysis_depth": r.get("analysis_depth"), "highlights": r.get("highlights")}
            for payload in ({**base, **ext}, {**base, "highlights": ext["highlights"]}, base):
                try:
                    sb.table("games").update(payload).eq("id", game["id"]).execute()
                    log.info("analisi condivisa: %s riusa %s (%d errori copiati)", game["id"], real, len(copy))
                    return True
                except Exception:
                    continue
        except Exception as e:
            log.warning("riuso analisi %s: %s", real, e)
    return False


def release_moves(ids: list[str]) -> list[str]:
    """Prima di cancellare le partite di un utente: se altri puntano alle sue mosse, le mosse passano a uno di loro.
    Restituisce gli id le cui mosse si possono cancellare davvero."""
    if not on() or not ids:
        return ids
    keep: list[str] = []
    try:
        for i in range(0, len(ids), 100):
            deps = sb.table("games").select("id,analysis_of").in_("analysis_of", ids[i:i + 100]).execute().data or []
            by: dict = {}
            for d in deps:
                by.setdefault(d["analysis_of"], []).append(d["id"])
            for old, dl in by.items():
                new = dl[0]
                sb.table("moves").update({"game_id": new}).eq("game_id", old).execute()
                sb.table("games").update({"analysis_of": None}).eq("id", new).execute()
                for j in range(0, len(dl) - 1, 100):
                    sb.table("games").update({"analysis_of": new}).in_("id", dl[1:][j:j + 100]).execute()
                keep.append(old)
    except Exception as e:
        log.warning("passaggio mosse: %s", e)
        return []          # nel dubbio non si cancella niente: meglio righe in più che analisi perse per altri
    return [x for x in ids if x not in keep]
