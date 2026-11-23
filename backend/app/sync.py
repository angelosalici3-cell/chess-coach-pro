"""Download partite da Lichess / Chess.com, import in `games`, analisi in coda."""
import datetime
import threading
import io
import logging
import re

import chess.pgn
import httpx

from core.plans import PLANS, get_plan
from .db import sb
from .engine import analyze_game

log = logging.getLogger("sync")
UA = {"User-Agent": "EloRise/1.0 (support@elorise.app)"}


def fetch_lichess(username: str, n: int) -> list[str]:
    r = httpx.get(f"https://lichess.org/api/games/user/{username.lower()}", params={"max": n, "opening": "true", "clocks": "true"},
                  headers={**UA, "Accept": "application/x-chess-pgn"}, timeout=25.0 if n <= 100 else 180.0)
    if r.status_code != 200:
        return []
    out, buf = [], io.StringIO(r.text)
    while (g := chess.pgn.read_game(buf)):
        out.append(str(g))
    return out


def fetch_chesscom(username: str, n: int) -> list[str]:
    out = []
    with httpx.Client(headers=UA, timeout=15.0) as c:
        r = c.get(f"https://api.chess.com/pub/player/{username.lower()}/games/archives")
        if r.status_code != 200:
            return []
        for url in reversed(r.json().get("archives", [])[-36:]):  # fino a 3 anni di archivi mensili
            games = c.get(url).json().get("games", [])[::-1]
            out += [g["pgn"] for g in games if g.get("pgn")]
            if len(out) >= n:
                break
    return out[:n]


def to_row(email: str, source: str, pgn_text: str, username: str):
    g = chess.pgn.read_game(io.StringIO(pgn_text))
    if not g:
        return None
    h = g.headers
    u = username.lower()
    color = "white" if h.get("White", "").lower() == u else "black" if h.get("Black", "").lower() == u else None
    gid = ((h.get("Site") if source == "lichess" else h.get("Link")) or "").rstrip("/").split("/")[-1]
    if not gid:
        return None
    try:
        played = datetime.datetime.strptime(
            f"{h.get('UTCDate') or h.get('Date')} {h.get('UTCTime', '00:00:00')}", "%Y.%m.%d %H:%M:%S"
        ).replace(tzinfo=datetime.timezone.utc).isoformat()
    except Exception:
        played = None
    opening = h.get("Opening")
    if not opening and h.get("ECOUrl"):
        opening = re.split(r"-\d", h["ECOUrl"].rstrip("/").split("/")[-1])[0].replace("-", " ")
    return {"user_email": email, "source": source, "source_game_id": gid, "pgn": str(g), "white": h.get("White"),
            "black": h.get("Black"), "user_color": color, "result": h.get("Result"), "time_control": h.get("TimeControl"),
            "opening_eco": h.get("ECO"), "opening_name": opening, "played_at": played,
            "has_clock": "[%clk" in pgn_text}


def _sync_profile(email: str, p: dict, n: int) -> int:
    """Scarica le ultime n partite di un profilo e inserisce solo quelle nuove."""
    src = p["piattaforma"]
    imported = 0
    try:
        pgns = fetch_lichess(p["username"], n) if src == "lichess" else fetch_chesscom(p["username"], n)
    except Exception as e:
        log.warning("fetch %s/%s: %s", src, p["username"], e)
        sb.table("profili_scacchi").update({"last_sync_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}).eq("id", p["id"]).execute()
        return 0
    rows = [r for r in (to_row(email, src, x, p["username"]) for x in pgns) if r]
    if rows:
        ids = [r["source_game_id"] for r in rows]
        have = {}
        for i in range(0, len(ids), 200):  # a blocchi: la query non deve diventare enorme
            for e in sb.table("games").select("source_game_id,has_clock").eq("user_email", email).eq("source", src).in_("source_game_id", ids[i:i + 200]).execute().data:
                have[e["source_game_id"]] = e.get("has_clock")
        new = [r for r in rows if r["source_game_id"] not in have]
        for i in range(0, len(new), 200):
            res = sb.table("games").upsert(new[i:i + 200], on_conflict="user_email,source,source_game_id", ignore_duplicates=True).execute()
            imported += len(res.data or [])
        for r in rows:  # partite già presenti senza orologio: recupera il PGN con i tempi
            if have.get(r["source_game_id"]) is False and r["has_clock"]:
                sb.table("games").update({"pgn": r["pgn"], "has_clock": True}).eq("user_email", email).eq("source", src).eq("source_game_id", r["source_game_id"]).execute()
    sb.table("profili_scacchi").update({"last_sync_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}).eq("id", p["id"]).execute()
    return imported


def sync_user(email: str, n: int = 15) -> int:
    imported = 0
    for p in sb.table("profili_scacchi").select("*").eq("user_email", email).execute().data:
        if p["piattaforma"] in ("lichess", "chesscom"):
            imported += _sync_profile(email, p, n)
    return imported


def import_history(email: str, tier: str) -> int:
    """Importa lo storico in base al piano. Si rifà solo se il piano permette più partite di quelle già importate."""
    cap = get_plan(tier).history_games
    imported = 0
    for p in sb.table("profili_scacchi").select("*").eq("user_email", email).execute().data:
        if p["piattaforma"] not in ("lichess", "chesscom") or (p.get("history_n") or 0) >= cap:
            continue
        imported += _sync_profile(email, p, cap)
        sb.table("profili_scacchi").update({"history_n": cap}).eq("id", p["id"]).execute()
    return imported


def analyze_pending(email: str, limit: int) -> None:
    rows = (sb.table("games").select("*").eq("user_email", email).is_("analyzed_at", "null")
            .not_.is_("user_color", "null").order("played_at", desc=True).limit(limit).execute().data)
    for g in rows:
        try:
            analyze_game(g)
        except Exception as e:
            log.warning("analisi %s fallita: %s", g["id"], e)
    try:  # le carte si assegnano subito: la preview è pronta quando l'utente apre l'app
        from .train import assign_cards
        assign_cards(email)
    except Exception as e:
        log.warning("carte %s: %s", email, e)


_running: set = set()
_lock = threading.Lock()
SECONDS_PER_GAME = 35      # stima per il tempo mostrato all'utente


def initial_rows(email: str, tier: str) -> list[dict]:
    """Le partite più recenti che il piano garantisce di analizzare subito."""
    n = get_plan(tier).initial_games
    return (sb.table("games").select("id,analyzed_at").eq("user_email", email).not_.is_("user_color", "null")
            .order("played_at", desc=True).limit(n).execute().data)


def is_running(email: str) -> bool:
    return email in _running


def analyze_initial(email: str, tier: str) -> None:
    """Analizza TUTTE le partite iniziali del piano, dalla più recente, a piccoli gruppi. Una sola esecuzione per utente."""
    with _lock:
        if email in _running:
            return
        _running.add(email)
    tried: set = set()
    try:
        while True:
            todo = [r["id"] for r in initial_rows(email, tier) if not r["analyzed_at"] and r["id"] not in tried][:4]
            if not todo:
                break
            tried.update(todo)
            for g in sorted(sb.table("games").select("*").in_("id", todo).execute().data, key=lambda x: x.get("played_at") or "", reverse=True):
                try:
                    analyze_game(g)
                except Exception as e:
                    log.warning("analisi iniziale %s fallita: %s", g["id"], e)
            try:  # le carte si assegnano man mano
                from .train import assign_cards
                assign_cards(email)
            except Exception as e:
                log.warning("carte %s: %s", email, e)
    finally:
        with _lock:
            _running.discard(email)


def onboard(email: str, tier: str) -> None:
    """Dopo il collegamento di un account (o un upgrade): scarica lo storico e analizza le partite garantite dal piano."""
    try:
        import_history(email, tier)
    except Exception as e:
        log.warning("storico %s: %s", email, e)
    analyze_initial(email, tier)


def _paid_users() -> list[dict]:
    """Abbonati con sincronizzazione automatica e abbonamento non scaduto (Elite, Pro, Plus in questo ordine)."""
    today = datetime.date.today()
    rank = {"Elite": 0, "Pro": 1, "Plus": 2}
    users = sb.table("config_utenti").select("user_email,tier,data_scadenza").in_("tier", [k for k, p in PLANS.items() if p.auto_sync]).execute().data
    users = [u for u in users if not (u.get("data_scadenza") and datetime.date.fromisoformat(u["data_scadenza"]) < today)]
    return sorted(users, key=lambda u: rank.get(u["tier"], 9))


def run_cron() -> None:
    """FASE 1, notturna: solo DOWNLOAD delle partite nuove (veloce). L'analisi è una fase separata: analyze_queue."""
    for u in _paid_users():
        try:
            sync_user(u["user_email"], 200)   # tutte le partite giocate dall'ultima volta, con un massimo di sicurezza
        except Exception as e:
            log.warning("cron download %s: %s", u["user_email"], e)


def analyze_queue(budget_s: int = 18000, workers: int = 3) -> dict:
    """FASE 2: analizza tutte le partite in attesa degli abbonati, fuori dal download.
    Equa: a giro un gruppo di partite per utente (le più recenti prima), Elite e Pro per primi.
    Si ferma allo scadere del tempo; ciò che resta si riprende alla corsa successiva."""
    from concurrent.futures import ThreadPoolExecutor
    import time
    t0, done, failed = time.time(), 0, 0
    users = _paid_users()
    tried: set = set()
    with ThreadPoolExecutor(workers) as pool:
        while time.time() - t0 < budget_s:
            batch = []
            for u in users:
                rows = (sb.table("games").select("*").eq("user_email", u["user_email"]).is_("analyzed_at", "null")
                        .not_.is_("user_color", "null").order("played_at", desc=True).limit(12).execute().data)
                batch += [g for g in rows if g["id"] not in tried][:6]
            if not batch:
                break
            def one(g):
                try:
                    analyze_game(g); return True
                except Exception as e:
                    log.warning("analisi %s fallita: %s", g["id"], e); return False
            for g, ok in zip(batch, pool.map(one, batch)):
                tried.add(g["id"]); done += ok; failed += (not ok)
            for u in users:
                try:
                    from .train import assign_cards
                    assign_cards(u["user_email"])   # le carte si assegnano man mano
                except Exception as e:
                    log.warning("carte %s: %s", u["user_email"], e)
    left = 0
    for u in users:
        left += sb.table("games").select("id", count="exact").eq("user_email", u["user_email"]).is_("analyzed_at", "null").not_.is_("user_color", "null").execute().count or 0
    return {"analyzed": done, "failed": failed, "left": left, "minutes": round((time.time() - t0) / 60, 1)}
