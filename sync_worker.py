"""
sync_worker.py — Chess Coach Pro v3

Worker di sincronizzazione notturna per utenti Pro/Diamond.
Deploy: Railway/Render cron job giornaliero (es. 03:00 UTC).

Requisiti ambiente:
    SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY   (bypassa RLS, obbligatoria)
    GEMINI_API_KEY
    GEMINI_MODEL                (default: gemini-2.5-flash)

Comportamento:
    - Per ogni utente Pro/Diamond con abbonamento attivo
    - Per ogni profilo Lichess/Chess.com collegato
    - Scarica le ultime N partite non ancora analizzate
    - Le analizza con Stockfish + Gemini
    - Salva: errori_utenti, partite_analizzate, review_items
    - Rispetta il limite mensile del tier
"""
import datetime
import io
import json
import logging
import os
import sys
import time
from typing import Optional

import chess
import chess.pgn
import httpx
from supabase import create_client

# ============================================================
# CONFIG
# ============================================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")  # NON anon!
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Limiti
GAMES_PER_PROFILE = 5
STOCKFISH_DEPTH = 10
BEST_MOVE_DEPTH = 14
MONTHLY_ANALYSES_LIMIT = {"Free": 5, "Pro": 200, "Diamond": 99999}
BLUNDER_THRESHOLD = 2.0
MISTAKE_THRESHOLD = 1.0

USER_AGENT = "ChessCoachProWorker/3.0 (support@chesscoachpro.com)"

# Logging strutturato
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("worker")

# ============================================================
# VALIDAZIONE AMBIENTE
# ============================================================
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "Variabili mancanti: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY. "
        "Nota: serve la SERVICE_ROLE key, non la anon key."
    )

sb = create_client(SUPABASE_URL, SUPABASE_KEY)


# ============================================================
# ENGINE + AI
# ============================================================
def fetch_stockfish_eval(fen: str, depth: int = STOCKFISH_DEPTH) -> Optional[float]:
    """Valutazione Stockfish. Ritorna None se fallisce dopo 3 tentativi."""
    for attempt in range(3):
        try:
            r = httpx.post(
                "https://chess-api.com/v1",
                json={"fen": fen, "depth": depth},
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
            )
            if r.status_code == 200:
                data = r.json()
                for key, divisor in (("eval", 1), ("centipawns", 100),
                                     ("cp", 100), ("value", 100)):
                    if data.get(key) is not None:
                        return float(data[key]) / divisor
                if data.get("mate") is not None:
                    m = int(data["mate"])
                    return 100.0 if m > 0 else -100.0
        except Exception as e:
            log.warning("Stockfish eval fallita (tentativo %d): %s", attempt + 1, e)
            time.sleep(0.5 * (attempt + 1))
    return None


def fetch_best_move(fen: str, depth: int = BEST_MOVE_DEPTH) -> tuple[Optional[str], Optional[str]]:
    """Mossa migliore (uci, san) per creare puzzle SRS. (None, None) se fallisce."""
    try:
        r = httpx.post(
            "https://chess-api.com/v1",
            json={"fen": fen, "depth": depth},
            headers={"User-Agent": USER_AGENT},
            timeout=10.0,
        )
        if r.status_code == 200:
            data = r.json()
            uci = data.get("bestmove") or data.get("move") or data.get("best_move")
            if uci:
                try:
                    board = chess.Board(fen)
                    return uci, board.san(chess.Move.from_uci(uci))
                except Exception:
                    return uci, uci
    except Exception as e:
        log.warning("Best move fallita: %s", e)
    return None, None


def classify_error(fen: str, san: str) -> str:
    """Classificazione AI dell'errore. Fallback 'Positional Weakness'."""
    if not GEMINI_API_KEY:
        return "Positional Weakness"

    from config_constants import ERROR_CATEGORIES  # inline per non importare l'app
    prompt = (
        f"Sei un GM. Classifica l'errore in UNA categoria tra: "
        f"{', '.join(ERROR_CATEGORIES)}.\n"
        f"FEN: {fen}\nMossa errata: {san}\n"
        f'Rispondi SOLO JSON: {{"categoria": "..."}}'
    )
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=GEMINI_API_KEY)
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json", temperature=0.0
            ),
        )
        data = json.loads(resp.text.strip())
        cat = data.get("categoria", "").strip()
        for valid in ERROR_CATEGORIES:
            if valid.lower() == cat.lower() or valid.lower() in cat.lower():
                return valid
        return "Positional Weakness"
    except Exception as e:
        log.warning("Gemini classify fallita: %s", e)
        return "Positional Weakness"


# Categorie inline (mirror di config/constants.py lato worker)
# Questo evita di importare l'intera app Streamlit nel worker.
class config_constants:
    ERROR_CATEGORIES = [
        "Fork", "Pin", "Skewer", "Hanging Piece", "Discovered Attack",
        "Double Check", "Interference", "Clearance", "Zugzwang",
        "Mate in 1", "Mate in 2", "Mate in 3+", "Back Rank Mate",
        "Smothered Mate", "Endgame", "Quiet Move", "Defensive Move",
        "Opening Mistake", "Positional Weakness",
    ]


# ============================================================
# UTILS
# ============================================================
def month_start_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    ).isoformat()


def analyses_used_this_month(user_email: str) -> int:
    try:
        res = (
            sb.table("usage_events")
            .select("id", count="exact")
            .eq("user_email", user_email)
            .eq("action", "analysis")
            .gte("created_at", month_start_iso())
            .execute()
        )
        return res.count or 0
    except Exception as e:
        log.warning("Count usage fallito per %s: %s", user_email, e)
        return 0


def record_analysis_usage(user_email: str, partita_id: str):
    try:
        sb.table("usage_events").insert({
            "user_email": user_email,
            "action": "analysis",
            "metadata": {"partita_id": partita_id, "source": "worker"},
        }).execute()
    except Exception as e:
        log.warning("Record usage fallito: %s", e)


def game_exists(user_email: str, partita_id: str) -> bool:
    try:
        res = (
            sb.table("errori_utenti")
            .select("id")
            .eq("user_email", user_email)
            .eq("partita_id", partita_id)
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception:
        return False


# ============================================================
# CORE: analisi e salvataggio
# ============================================================
def extract_partita_id(headers) -> str:
    return f"{headers.get('White','?')}_vs_{headers.get('Black','?')}_{headers.get('Date','Live')}"


def determine_user_color(headers, username: str) -> Optional[str]:
    white = headers.get("White", "").strip().lower()
    black = headers.get("Black", "").strip().lower()
    u = username.strip().lower()
    is_white = u in white
    is_black = u in black
    if is_white and not is_black:
        return "white"
    if is_black and not is_white:
        return "black"
    return None  # PGN ambiguo o utente non presente


def to_int(v) -> Optional[int]:
    try:
        return int(v) if v not in (None, "", "?") else None
    except Exception:
        return None


def save_partita_analizzata(
    user_email: str, headers, user_color: str, errors: list[dict]
) -> None:
    """Salva la riga in partite_analizzate (per rating trend)."""
    white = headers.get("White", "?")
    black = headers.get("Black", "?")
    w_elo = to_int(headers.get("WhiteElo"))
    b_elo = to_int(headers.get("BlackElo"))
    if user_color == "white":
        user_elo, opp_elo = w_elo, b_elo
    else:
        user_elo, opp_elo = b_elo, w_elo

    if user_elo is None or opp_elo is None:
        return  # senza rating non possiamo tracciare il trend

    date_raw = headers.get("Date", "")
    date_iso = date_raw.replace(".", "-") if date_raw and date_raw.count("-") == 2 and "?" not in date_raw else None

    blunders = sum(1 for e in errors if "Blunder" in e.get("tipo_problema", ""))
    mistakes = sum(1 for e in errors if "Mistake" in e.get("tipo_problema", ""))
    inaccuracies = sum(1 for e in errors if "Inaccuracy" in e.get("tipo_problema", ""))
    accuracy = 100.0
    if errors:
        avg_loss = sum(e.get("perdita_cp", 0) for e in errors) / len(errors)
        accuracy = round(max(0, min(100, 100 - avg_loss * 2)), 1)

    try:
        sb.table("partite_analizzate").upsert({
            "user_email": user_email,
            "partita_id": extract_partita_id(headers),
            "data_partita": date_iso,
            "white_player": white,
            "black_player": black,
            "user_color": user_color,
            "user_elo": user_elo,
            "opponent_elo": opp_elo,
            "user_rating_diff": user_elo - opp_elo,
            "result": headers.get("Result", "*"),
            "time_control": headers.get("TimeControl"),
            "termination": headers.get("Termination"),
            "accuracy": accuracy,
            "blunders": blunders,
            "mistakes": mistakes,
            "inaccuracies": inaccuracies,
        }, on_conflict="user_email,partita_id").execute()
    except Exception as e:
        log.warning("Salvataggio partita_analizzata fallito: %s", e)


def save_errors_and_reviews(
    user_email: str, partita_id: str, errors: list[dict]
) -> None:
    """Salva errori e crea review_items con la mossa migliore."""
    if not errors:
        return

    rows = [{
        "user_email": user_email,
        "partita_id": partita_id,
        "data": datetime.date.today().isoformat(),
        "categoria_errore": e["categoria"],
        "mossa_critica": e["label_mossa"],
        "spiegazione": f"Perdita {e['perdita_cp']} CP ({e['tipo_problema']})",
        "fen_prima": e["fen_prima"],
        "perdita_cp": e["perdita_cp"],
    } for e in errors]

    try:
        res = sb.table("errori_utenti").insert(rows).execute()
        inserted = res.data or []
    except Exception as e:
        log.warning("Insert errori fallito: %s", e)
        return

    # Crea review_items (best move per ogni errore)
    for row in inserted:
        fen = row.get("fen_prima")
        if not fen:
            continue
        uci, sol_san = fetch_best_move(fen)
        if not sol_san:
            continue
        label = row.get("mossa_critica", "")
        user_san = label.split()[-1] if " " in label else label
        try:
            sb.table("review_items").upsert({
                "user_email": user_email,
                "source_error_id": row["id"],
                "fen": fen,
                "solution_uci": uci,
                "solution_san": sol_san,
                "user_move_san": user_san,
                "category": row.get("categoria_errore"),
            }, on_conflict="user_email,source_error_id").execute()
        except Exception as e:
            log.warning("Insert review_item fallito: %s", e)


def analizza_e_salva_partita(
    user_email: str, pgn_text: str, target_username: str
) -> bool:
    """Ritorna True se ha effettivamente analizzato una nuova partita."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if not game:
        log.warning("PGN non valido per %s", user_email)
        return False

    headers = game.headers
    partita_id = extract_partita_id(headers)

    # Già analizzata?
    if game_exists(user_email, partita_id):
        log.info("[skip] %s · %s già analizzata", user_email, partita_id)
        return False

    user_color = determine_user_color(headers, target_username)
    if user_color is None:
        log.info("[skip] %s non compare in %s", target_username, partita_id)
        return False

    board = game.board()
    moves = list(game.mainline_moves())
    prev_eval = 0.0
    evals_cache: dict[str, float] = {}
    errors: list[dict] = []

    def get_eval(fen: str) -> float:
        if fen in evals_cache:
            return evals_cache[fen]
        e = fetch_stockfish_eval(fen)
        if e is None:
            e = prev_eval
        evals_cache[fen] = e
        return e

    for idx, move in enumerate(moves):
        fen_before = board.fen()
        try:
            san = board.san(move)
        except Exception:
            san = move.uci()

        eval_before = get_eval(fen_before)
        board.push(move)
        fen_after = board.fen()
        eval_after = get_eval(fen_after)

        num = (idx // 2) + 1
        is_white = (idx % 2 == 0)
        is_user = (is_white and user_color == "white") or (not is_white and user_color == "black")

        if is_user:
            delta = (eval_before - eval_after) if is_white else (eval_after - eval_before)
            tipo = None
            if delta >= BLUNDER_THRESHOLD:
                tipo = "Blunder"
            elif delta >= MISTAKE_THRESHOLD:
                tipo = "Mistake"
            if tipo:
                label = f"{num}. {san}" if is_white else f"{num}... {san}"
                categoria = classify_error(fen_before, san)
                errors.append({
                    "label_mossa": label,
                    "fen_prima": fen_before,
                    "perdita_cp": round(delta, 2),
                    "tipo_problema": tipo,
                    "categoria": categoria,
                })

        prev_eval = eval_after
        time.sleep(0.03)

    save_partita_analizzata(user_email, headers, user_color, errors)
    save_errors_and_reviews(user_email, partita_id, errors)
    record_analysis_usage(user_email, partita_id)
    log.info("[done] %s · %s · %d errori", user_email, partita_id, len(errors))
    return True


# ============================================================
# DOWNLOAD PARTITE
# ============================================================
def fetch_lichess_games(username: str, n: int) -> list[str]:
    try:
        r = httpx.get(
            f"https://lichess.org/api/games/user/{username.lower()}",
            params={"max": n},
            headers={"Accept": "application/x-chess-pgn", "User-Agent": USER_AGENT},
            timeout=25.0,
        )
        if r.status_code != 200:
            log.warning("Lichess %s HTTP %d", username, r.status_code)
            return []
        raw = r.text
        return ["[Event " + p if not p.startswith("[Event") else p
                for p in raw.split("\n[Event ") if p.strip()]
    except Exception as e:
        log.warning("Lichess fetch %s errore: %s", username, e)
        return []


def fetch_chesscom_games(username: str, n: int) -> list[str]:
    try:
        with httpx.Client(timeout=15.0, headers={"User-Agent": USER_AGENT}) as c:
            r = c.get(f"https://api.chess.com/pub/player/{username.lower()}/games/archives")
            if r.status_code != 200:
                return []
            archives = r.json().get("archives", [])
            if not archives:
                return []
            g = c.get(archives[-1])
            games = g.json().get("games", [])[-n:][::-1]
            return [x["pgn"] for x in games if x.get("pgn")]
    except Exception as e:
        log.warning("Chess.com fetch %s errore: %s", username, e)
        return []


# ============================================================
# MAIN
# ============================================================
def main():
    log.info("=== Sync worker start ===")
    started = datetime.datetime.now(datetime.timezone.utc)

    # Solo utenti Pro/Diamond con abbonamento attivo
    try:
        subs = (
            sb.table("config_utenti")
            .select("user_email, tier, data_scadenza")
            .in_("tier", ["Pro", "Diamond"])
            .execute()
        )
    except Exception as e:
        log.error("Lettura config_utenti fallita: %s", e)
        return

    if not subs.data:
        log.info("Nessun utente Pro/Diamond.")
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    total_games = 0
    total_users = 0

    for row in subs.data:
        email = row["user_email"]
        tier = row["tier"]
        scadenza = row.get("data_scadenza")

        # Salta abbonamenti scaduti
        if scadenza:
            try:
                exp = datetime.datetime.fromisoformat(scadenza.replace("Z", "+00:00"))
                if exp < now:
                    log.info("[skip] %s scaduto il %s", email, scadenza)
                    continue
            except Exception:
                pass

        # Limite mensile
        used = analyses_used_this_month(email)
        limit = MONTHLY_ANALYSES_LIMIT.get(tier, 5)
        if used >= limit:
            log.info("[skip] %s quota raggiunta (%d/%d)", email, used, limit)
            continue

        # Profili
        try:
            profs = (
                sb.table("profili_scacchi")
                .select("piattaforma, username")
                .eq("user_email", email)
                .execute()
            ).data or []
        except Exception as e:
            log.warning("Profili %s errore: %s", email, e)
            continue

        if not profs:
            continue

        user_games = 0
        for prof in profs:
            if user_games >= (limit - used):
                break

            platform = prof["piattaforma"]
            username = prof["username"]

            if platform == "Lichess":
                pgns = fetch_lichess_games(username, GAMES_PER_PROFILE)
            elif platform == "Chess.com":
                pgns = fetch_chesscom_games(username, GAMES_PER_PROFILE)
            else:
                continue

            for pgn in pgns:
                if user_games >= (limit - used):
                    break
                try:
                    if analizza_e_salva_partita(email, pgn, username):
                        user_games += 1
                        total_games += 1
                except Exception as e:
                    log.warning("Analisi %s/%s fallita: %s", email, username, e)

        if user_games > 0:
            total_users += 1
            log.info("[user] %s · %d partite sincronizzate", email, user_games)

    elapsed = (datetime.datetime.now(datetime.timezone.utc) - started).total_seconds()
    log.info(
        "=== Sync worker done · %d utenti · %d partite · %.1fs ===",
        total_users, total_games, elapsed,
    )


if __name__ == "__main__":
    main()
