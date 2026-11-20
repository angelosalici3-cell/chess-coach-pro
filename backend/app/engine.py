"""Analisi di una partita: valutazione per posizione (una sola chiamata per FEN) e salvataggio in moves/errori_utenti."""
import datetime
import io
import logging
import time

import chess
import chess.pgn
import httpx

from .cardlogic import highlights_from_moves
from .db import sb

log = logging.getLogger("engine")
API = "https://chess-api.com/v1"
DEPTH = 12


def eval_fen(client: httpx.Client, fen: str):
    """(valutazione in pedoni dal lato del Bianco, miglior mossa SAN) oppure (None, None)."""
    for i in range(3):
        try:
            r = client.post(API, json={"fen": fen, "depth": DEPTH}, timeout=12.0)
            if r.status_code == 200:
                d = r.json()
                ev = None
                for k, div in (("eval", 1), ("centipawns", 100), ("cp", 100), ("value", 100)):
                    if d.get(k) is not None:
                        ev = float(d[k]) / div
                        break
                if ev is None and d.get("mate") is not None:
                    ev = 100.0 if int(d["mate"]) > 0 else -100.0
                return ev, d.get("san")
        except Exception as e:
            log.warning("eval fallita: %s", e)
        time.sleep(0.6 * (i + 1))
    return None, None


def analyze_game(game: dict) -> None:
    pg = chess.pgn.read_game(io.StringIO(game["pgn"]))
    color = game.get("user_color")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if not pg or not color:
        sb.table("games").update({"analyzed_at": now}).eq("id", game["id"]).execute()
        return
    board, moves, cache = pg.board(), list(pg.mainline_moves()), {}
    move_rows, err_rows, losses, prev = [], [], [], 0.0
    miss = 0  # valutazioni non ricevute dal motore (limite di richieste, rete)
    with httpx.Client(headers={"User-Agent": "ChessCoachPro/1.0"}) as c:
        def ev(fen):
            if fen not in cache:
                cache[fen] = eval_fen(c, fen)
            return cache[fen]

        for i, mv in enumerate(moves):
            white = i % 2 == 0
            fen_b, san = board.fen(), board.san(mv)
            e0, best = ev(fen_b)
            ok = e0 is not None
            e0 = prev if e0 is None else e0
            board.push(mv)
            fen_a = board.fen()
            e1, _ = ev(fen_a)
            ok = ok and e1 is not None
            miss += (not ok)
            e1 = e0 if e1 is None else e1
            prev = e1
            is_user = (white and color == "white") or (not white and color == "black")
            cls, delta = None, 0.0
            if is_user and ok:  # senza valutazione la mossa non si giudica: prima diventava "migliore" e la partita 100%
                delta = (e0 - e1) if white else (e1 - e0)
                cls = ("blunder" if delta >= 2 else "mistake" if delta >= 1 else "inaccuracy" if delta >= 0.5
                       else "best" if delta <= 0.1 else "good")
                losses.append(min(max(delta, 0.0), 5.0))
            move_rows.append({
                "game_id": game["id"], "ply": i + 1, "san": san, "uci": mv.uci(), "fen_after": fen_a,
                "eval_cp": int(max(min(e1, 10.0), -10.0) * 100), "best_move_san": best if is_user else None,
                "classification": cls, "is_user_move": is_user})
            if cls in ("mistake", "blunder"):
                if len(board.piece_map()) <= 10:
                    cat = "endgame"
                elif i < 20 and delta < 1.5:
                    cat = "opening"
                else:
                    cat = "tactical" if delta >= 1.5 else "positional"
                err_rows.append({
                    "user_email": game["user_email"], "game_id": game["id"], "ply": i + 1, "fen": fen_b,
                    "mossa_critica": f"{i // 2 + 1}{'.' if white else '...'} {san}", "best_move": best,
                    "categoria_errore": cat, "classification": cls, "eval_loss_cp": int(delta * 100),
                    "apertura": game.get("opening_name"), "data": now})
    if moves and miss > max(2, 0.1 * len(moves)):
        # troppe valutazioni mancanti: non si salva niente e la partita resta "da analizzare", così riprova alla prossima esecuzione
        raise RuntimeError(f"analisi incompleta: {miss}/{len(moves)} mosse senza valutazione")
    if move_rows:
        sb.table("moves").upsert(move_rows, on_conflict="game_id,ply").execute()
    if err_rows:
        sb.table("errori_utenti").upsert(err_rows, on_conflict="user_email,game_id,ply").execute()
    acc = round(max(0.0, 100 - 40 * (sum(losses) / len(losses))), 1) if losses else None
    upd = {"analyzed_at": now, "analysis_depth": DEPTH, "accuracy_user": acc}
    try:  # momenti salienti (rimonta, mosse brillanti); se la colonna non esiste ancora, l'analisi si salva comunque
        sb.table("games").update({**upd, "highlights": highlights_from_moves(move_rows, color)}).eq("id", game["id"]).execute()
    except Exception:
        sb.table("games").update(upd).eq("id", game["id"]).execute()
    log.info("analizzata %s: %d errori", game["id"], len(err_rows))
