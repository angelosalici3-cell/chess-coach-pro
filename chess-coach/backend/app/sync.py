"""Download partite da Lichess / Chess.com, import in `games`, analisi in coda."""
import datetime
import io
import logging
import re

import chess.pgn
import httpx

from core.plans import PLANS, get_plan
from .db import sb
from .engine import analyze_game

log = logging.getLogger("sync")
UA = {"User-Agent": "ChessCoachPro/1.0 (support@chesscoachpro.com)"}


def fetch_lichess(username: str, n: int) -> list[str]:
    r = httpx.get(f"https://lichess.org/api/games/user/{username.lower()}", params={"max": n, "opening": "true"},
                  headers={**UA, "Accept": "application/x-chess-pgn"}, timeout=25.0)
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
        for url in reversed(r.json().get("archives", [])[-2:]):
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
            "opening_eco": h.get("ECO"), "opening_name": opening, "played_at": played}


def sync_user(email: str, n: int = 15) -> int:
    imported = 0
    profs = sb.table("profili_scacchi").select("*").eq("user_email", email).execute().data
    for p in profs:
        src = p["piattaforma"]
        if src not in ("lichess", "chesscom"):
            continue
        try:
            pgns = fetch_lichess(p["username"], n) if src == "lichess" else fetch_chesscom(p["username"], n)
        except Exception as e:
            log.warning("fetch %s/%s: %s", src, p["username"], e)
            continue
        rows = [r for r in (to_row(email, src, x, p["username"]) for x in pgns) if r]
        if rows:
            res = sb.table("games").upsert(rows, on_conflict="user_email,source,source_game_id", ignore_duplicates=True).execute()
            imported += len(res.data or [])
        sb.table("profili_scacchi").update({"last_sync_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}).eq("id", p["id"]).execute()
    return imported


def analyze_pending(email: str, limit: int) -> None:
    rows = (sb.table("games").select("*").eq("user_email", email).is_("analyzed_at", "null")
            .not_.is_("user_color", "null").order("played_at", desc=True).limit(limit).execute().data)
    for g in rows:
        try:
            analyze_game(g)
        except Exception as e:
            log.warning("analisi %s fallita: %s", g["id"], e)


def run_cron() -> None:
    """Sync notturna per tutti gli abbonati (Plus/Pro/Elite) con abbonamento non scaduto."""
    today = datetime.date.today()
    users = sb.table("config_utenti").select("user_email,tier,data_scadenza").in_("tier", [k for k, p in PLANS.items() if p.auto_sync]).execute().data
    for u in users:
        if u.get("data_scadenza") and datetime.date.fromisoformat(u["data_scadenza"]) < today:
            continue
        try:
            sync_user(u["user_email"])
            analyze_pending(u["user_email"], 5)
        except Exception as e:
            log.warning("cron %s: %s", u["user_email"], e)
