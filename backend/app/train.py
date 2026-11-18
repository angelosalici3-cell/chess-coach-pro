"""Endpoint: allenamento (errori e puzzle), traguardi e ricompense, analisi del tempo, aperture personali."""
import datetime
import random
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import pgnlite
from . import cardlogic as CL
from . import trainlogic as T
from .auth import current_user, tier_of
from .db import sb

router = APIRouter()


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _count(q) -> int:
    return q.execute().count or 0


# ---------------------------------------------------------------- statistiche di allenamento
DEFAULT_STATS = {"puzzle_rating": 1200, "puzzles_solved": 0, "puzzles_failed": 0, "mistakes_fixed": 0,
                 "current_streak": 0, "best_streak": 0, "training_days": 0, "last_train_date": None}


def get_stats(email: str) -> dict:
    rows = sb.table("training_stats").select("*").eq("user_email", email).limit(1).execute().data
    return rows[0] if rows else {"user_email": email, **DEFAULT_STATS}


def save_stats(email: str, patch: dict) -> dict:
    st = {**get_stats(email), **patch, "user_email": email}
    sb.table("training_stats").upsert(st, on_conflict="user_email").execute()
    return st


def _live_streak(st: dict) -> int:
    """La serie è viva se l'ultimo allenamento è oggi o ieri."""
    last = st.get("last_train_date")
    if not last:
        return 0
    gap = (datetime.date.today() - datetime.date.fromisoformat(last)).days
    return st.get("current_streak") or 0 if gap <= 1 else 0


def _errors(email: str, cols: str = "id,fen,best_move,mossa_critica,eval_loss_cp,game_id,ply,categoria_errore,apertura", limit: int = 400):
    return (sb.table("errori_utenti").select(cols).eq("user_email", email).in_("classification", ["mistake", "blunder"])
            .not_.is_("best_move", "null").not_.is_("fen", "null").order("data", desc=True).limit(limit).execute().data)


@router.get("/train/overview")
def overview(u=Depends(current_user)):
    email = u["email"]
    st = get_stats(email)
    errs = _errors(email, "id")
    cards = sb.table("mistake_cards").select("error_id,due_at").eq("user_email", email).execute().data
    carded = {c["error_id"] for c in cards}
    due = sum(1 for c in cards if c["due_at"] <= _now().isoformat())
    return {"stats": {**st, "current_streak": _live_streak(st)}, "mistakes_total": len(errs),
            "mistakes_new": sum(1 for e in errs if str(e["id"]) not in carded), "mistakes_due": due,
            "done_today": st.get("last_train_date") == datetime.date.today().isoformat(),
            "puzzles_available": _count(sb.table("puzzles").select("id", count="exact").limit(1)) > 0}


# ---------------------------------------------------------------- ripasso dei propri errori
@router.get("/train/mistakes/next")
def mistakes_next(u=Depends(current_user)):
    email, now = u["email"], _now().isoformat()
    for _ in range(3):
        due = sb.table("mistake_cards").select("error_id").eq("user_email", email).lte("due_at", now).order("due_at").limit(1).execute().data
        if not due:
            break
        e = sb.table("errori_utenti").select("id,fen,best_move,mossa_critica,eval_loss_cp,game_id,ply,categoria_errore,apertura").eq("id", due[0]["error_id"]).eq("user_email", email).limit(1).execute().data
        if e:
            return {"error": e[0], "new": False}
        sb.table("mistake_cards").delete().eq("user_email", email).eq("error_id", due[0]["error_id"]).execute()  # errore cancellato
    carded = {c["error_id"] for c in sb.table("mistake_cards").select("error_id").eq("user_email", email).execute().data}
    errs = _errors(email)
    for e in errs:
        if str(e["id"]) not in carded:
            return {"error": e, "new": True}
    nxt = sb.table("mistake_cards").select("due_at").eq("user_email", email).order("due_at").limit(1).execute().data
    return {"error": None, "reason": "no_errors" if not errs else "all_done", "next_due": nxt[0]["due_at"] if nxt else None}


class MistakeAns(BaseModel):
    error_id: str
    correct: bool


@router.post("/train/mistakes/answer")
def mistakes_answer(body: MistakeAns, u=Depends(current_user)):
    email = u["email"]
    ok = sb.table("errori_utenti").select("id").eq("id", body.error_id).eq("user_email", email).limit(1).execute().data
    if not ok:
        raise HTTPException(404, "not_found")
    row = sb.table("mistake_cards").select("*").eq("user_email", email).eq("error_id", body.error_id).limit(1).execute().data
    card = row[0] if row else {"user_email": email, "error_id": body.error_id, "box": 1, "attempts": 0, "correct": 0}
    box, due = T.leitner_next(card["box"], body.correct, _now())
    sb.table("mistake_cards").upsert({**card, "box": box, "due_at": due.isoformat(), "attempts": card["attempts"] + 1,
                                      "correct": card["correct"] + (1 if body.correct else 0), "last_at": _now().isoformat()},
                                     on_conflict="user_email,error_id").execute()
    st = get_stats(email)
    patch = T.touch_streak(st, datetime.date.today())
    if body.correct:
        patch["mistakes_fixed"] = (st.get("mistakes_fixed") or 0) + 1
    st = save_stats(email, patch)
    return {"box": box, "due_at": due.isoformat(), "stats": {**st, "current_streak": _live_streak(st)}}


# ---------------------------------------------------------------- puzzle Lichess
@router.get("/train/puzzle/next")
def puzzle_next(theme: str | None = None, u=Depends(current_user)):
    email = u["email"]
    if theme and not re.fullmatch(r"[A-Za-z0-9]{2,30}", theme):
        raise HTTPException(400, "bad_theme")
    st = get_stats(email)
    r = st["puzzle_rating"]
    recent = {a["puzzle_id"] for a in sb.table("puzzle_attempts").select("puzzle_id").eq("user_email", email).order("created_at", desc=True).limit(80).execute().data}
    for spread in (100, 250, 500, 3000):
        lo, hi = max(0, r - spread), r + spread

        def q(cols):
            base = sb.table("puzzles").select(cols, count="exact").gte("rating", lo).lte("rating", hi)
            return base.contains("themes", [theme]) if theme else base
        total = q("id").limit(1).execute().count or 0
        if not total:
            continue
        off = random.randint(0, max(0, total - 40))
        rows = [p for p in q("id,fen,moves,rating,themes").range(off, off + 39).execute().data if p["id"] not in recent]
        if rows:
            return {"puzzle": random.choice(rows), "rating": r}
    if not sb.table("puzzles").select("id").limit(1).execute().data:
        raise HTTPException(404, "no_puzzles")
    raise HTTPException(404, "no_match")


class PuzzleRes(BaseModel):
    puzzle_id: str
    solved: bool


@router.post("/train/puzzle/result")
def puzzle_result(body: PuzzleRes, u=Depends(current_user)):
    email = u["email"]
    p = sb.table("puzzles").select("rating").eq("id", body.puzzle_id).limit(1).execute().data
    if not p:
        raise HTTPException(404, "not_found")
    st = get_stats(email)
    since = (_now() - datetime.timedelta(minutes=10)).isoformat()
    dup = sb.table("puzzle_attempts").select("id").eq("user_email", email).eq("puzzle_id", body.puzzle_id).gte("created_at", since).limit(1).execute().data
    if dup:  # già registrato: niente doppio conteggio
        return {"rating": st["puzzle_rating"], "delta": 0, "stats": {**st, "current_streak": _live_streak(st)}}
    new = T.elo_update(st["puzzle_rating"], p[0]["rating"], body.solved)
    sb.table("puzzle_attempts").insert({"user_email": email, "puzzle_id": body.puzzle_id, "solved": body.solved,
                                        "rating_before": st["puzzle_rating"], "rating_after": new}).execute()
    patch = T.touch_streak(st, datetime.date.today())
    patch.update({"puzzle_rating": new, "puzzles_solved": st["puzzles_solved"] + (1 if body.solved else 0),
                  "puzzles_failed": st["puzzles_failed"] + (0 if body.solved else 1)})
    out = save_stats(email, patch)
    return {"rating": new, "delta": new - st["puzzle_rating"], "stats": {**out, "current_streak": _live_streak(out)}}


# ---------------------------------------------------------------- traguardi, livelli, ricompense
def _metrics(email: str, st: dict) -> dict:
    games = _count(sb.table("games").select("id", count="exact").eq("user_email", email).limit(1))
    analyzed_rows = sb.table("games").select("id,accuracy_user,opening_name").eq("user_email", email).not_.is_("analyzed_at", "null").limit(1000).execute().data
    all_open = sb.table("games").select("opening_name").eq("user_email", email).limit(1000).execute().data
    openings = {(g["opening_name"] or "").split(":")[0].split(",")[0].strip() for g in all_open if g.get("opening_name")}
    with_err = {e["game_id"] for e in sb.table("errori_utenti").select("game_id").eq("user_email", email).limit(5000).execute().data}
    accs = [float(g["accuracy_user"]) for g in analyzed_rows if g.get("accuracy_user") is not None]
    return {"games": games, "analyzed": len(analyzed_rows), "puzzles": st["puzzles_solved"], "streak": st["best_streak"],
            "fixed": st["mistakes_fixed"], "lessons": _count(sb.table("errori_utenti").select("id", count="exact").eq("user_email", email).not_.is_("gm_lesson", "null").limit(1)),
            "accuracy": round(max(accs)) if accs else 0, "openings": len(openings), "puzzle_rating": st["puzzle_rating"],
            "clean": sum(1 for g in analyzed_rows if g["id"] not in with_err)}


def _game_rows(email: str) -> list[dict]:
    cols = "id,played_at,user_color,result,white,black,pgn,accuracy_user,opening_name,source,time_control"
    def q(c):
        return (sb.table("games").select(c).eq("user_email", email).not_.is_("user_color", "null")
                .order("played_at", desc=True).limit(1000).execute().data)
    try:
        rows = q(cols + ",highlights")
    except Exception:  # colonna non ancora creata (007 non eseguito)
        rows = q(cols)
    for g in rows:
        pl = pgnlite.plies(g["pgn"])
        g["sans"], g["clks"], g["tc"] = [p["san"] for p in pl], [p["clk"] for p in pl], g.get("time_control")
    return rows


def ensure_highlights(email: str, limit: int = 15) -> int:
    """Calcola rimonta e mosse brillanti per le partite analizzate prima dell'introduzione della funzione (poche alla volta)."""
    try:
        todo = (sb.table("games").select("id,user_color").eq("user_email", email).not_.is_("analyzed_at", "null").is_("highlights", "null")
                .not_.is_("user_color", "null").order("played_at", desc=True).limit(limit).execute().data)
    except Exception:
        return 0
    for g in todo:
        rows = sb.table("moves").select("ply,eval_cp,fen_after,is_user_move").eq("game_id", g["id"]).order("ply").limit(1000).execute().data
        sb.table("games").update({"highlights": CL.highlights_from_moves(rows, g["user_color"]) if rows else {"v": 1, "low_cp": None, "brilliant": []}}).eq("id", g["id"]).execute()
    return len(todo)


def _open_wins(email: str) -> dict:
    """Vittorie per ogni apertura (solo le prime 10 semimosse contano)."""
    wins = {o["id"]: 0 for o in CL.OPENINGS}
    for g in _game_rows(email):
        if CL.outcome(g) != "w":
            continue
        for o in CL.OPENINGS:
            if CL.opening_match(g["sans"], g["user_color"], o):
                wins[o["id"]] += 1
    return wins


def _ach(email: str) -> dict:
    st = get_stats(email)
    m = _metrics(email, st)
    xp = T.xp_total(m, st)
    lvl = T.level_of(xp)
    claimed = {r["code"] for r in sb.table("rewards").select("code").eq("user_email", email).execute().data}
    bonus = (sb.table("config_utenti").select("bonus_lessons").eq("user_email", email).limit(1).execute().data or [{}])[0].get("bonus_lessons") or 0
    return {"xp": xp, "level": lvl, "level_xp": T.xp_for_level(lvl), "next_xp": T.xp_for_level(lvl + 1), "bonus_lessons": bonus,
            "shields": [{"id": sid, "value": m[sid], "tiers": tiers, "tier": T.shield_tier(m[sid], tiers)} for sid, tiers in T.SHIELDS]
                       + [{"id": "op_" + oid, "value": n, "tiers": CL.OPEN_TIERS, "tier": CL.tier_of(n), "kind": "opening", "color": next(o["color"] for o in CL.OPENINGS if o["id"] == oid)}
                          for oid, n in _open_wins(email).items()],
            "rewards": [{**r, "claimed": f"lvl{r['lvl']}" in claimed, "claimable": lvl >= r["lvl"] and f"lvl{r['lvl']}" not in claimed} for r in T.REWARDS],
            "streak": _live_streak(st), "stats": st}


@router.get("/achievements")
def achievements(u=Depends(current_user)):
    return _ach(u["email"])


class ClaimIn(BaseModel):
    lvl: int


@router.post("/rewards/claim")
def claim(body: ClaimIn, u=Depends(current_user)):
    email = u["email"]
    reward = next((r for r in T.REWARDS if r["lvl"] == body.lvl), None)
    if not reward:
        raise HTTPException(404, "not_found")
    if _ach(email)["level"] < reward["lvl"]:
        raise HTTPException(400, "level_too_low")
    try:  # il vincolo unique (utente, codice) impedisce il doppio riscatto anche con richieste simultanee
        sb.table("rewards").insert({"user_email": email, "code": f"lvl{reward['lvl']}", "kind": reward["kind"], "detail": reward}).execute()
    except Exception:
        raise HTTPException(409, "already_claimed")
    cfg = sb.table("config_utenti").select("*").eq("user_email", email).limit(1).execute().data
    bonus = (cfg[0].get("bonus_lessons") or 0) if cfg else 0
    granted = {}
    if reward["kind"] == "bonus_lessons":
        granted = {"kind": "bonus_lessons", "amount": reward["amount"]}
    elif tier_of(email) == "Free":  # prova gratuita solo a chi non ha già un piano a pagamento
        exp = (datetime.date.today() + datetime.timedelta(days=reward["days"])).isoformat()
        granted = {"kind": "trial", "tier": reward["tier"], "days": reward["days"], "until": exp}
        if cfg:
            sb.table("config_utenti").update({"tier": reward["tier"], "data_scadenza": exp}).eq("user_email", email).execute()
        else:
            sb.table("config_utenti").insert({"user_email": email, "tier": reward["tier"], "data_scadenza": exp, "bonus_lessons": 0}).execute()
    else:  # già abbonato: la prova diventa lezioni bonus (2 per ogni giorno)
        granted = {"kind": "bonus_lessons", "amount": reward["days"] * 2, "converted": True}
    if granted["kind"] == "bonus_lessons":
        if cfg:
            sb.table("config_utenti").update({"bonus_lessons": bonus + granted["amount"]}).eq("user_email", email).execute()
        else:
            sb.table("config_utenti").insert({"user_email": email, "tier": "Free", "bonus_lessons": granted["amount"]}).execute()
    return {"granted": granted, "tier": tier_of(email)}


# ---------------------------------------------------------------- analisi del tempo
def _losses(rows: list[dict]) -> dict:
    """ply -> centesimi di pedone persi da chi ha mosso (0..500)."""
    out, prev = {}, 0
    for m in sorted(rows, key=lambda r: r["ply"]):
        cur = m.get("eval_cp")
        if cur is None:
            continue
        out[m["ply"]] = max(0, min(500, (prev - cur) if m["ply"] % 2 else (cur - prev)))
        prev = cur
    return out


def _fetch_moves(ids: list[str]) -> dict:
    by: dict[str, list] = {}
    for i in range(0, len(ids), 10):
        start = 0
        while True:
            rows = sb.table("moves").select("game_id,ply,eval_cp").in_("game_id", ids[i:i + 10]).range(start, start + 999).execute().data
            for r in rows:
                by.setdefault(r["game_id"], []).append(r)
            if len(rows) < 1000:
                break
            start += 1000
    return by


@router.get("/games/{game_id}/time")
def game_time(game_id: str, u=Depends(current_user)):
    g = sb.table("games").select("pgn,time_control,user_color").eq("id", game_id).eq("user_email", u["email"]).limit(1).execute().data
    if not g:
        raise HTTPException(404, "not_found")
    g = g[0]
    mt = pgnlite.move_times(g["pgn"], g["time_control"])
    if mt is None:
        return {"available": False}
    loss = _losses(sb.table("moves").select("ply,eval_cp").eq("game_id", game_id).execute().data)
    white = g["user_color"] == "white"
    for m in mt:
        m["you"] = (m["ply"] % 2 == 1) == white
        m["loss_cp"] = loss.get(m["ply"])
    tc = pgnlite.parse_tc(g["time_control"])
    return {"available": True, "moves": mt, "base": tc[0] if tc else None, "threshold": pgnlite.trouble_threshold(g["time_control"])}


@router.get("/stats/time")
def stats_time(u=Depends(current_user)):
    email = u["email"]
    games = (sb.table("games").select("id,pgn,time_control,user_color,result").eq("user_email", email).eq("has_clock", True)
             .not_.is_("analyzed_at", "null").not_.is_("user_color", "null").order("played_at", desc=True).limit(80).execute().data)
    if not games:
        return {"games": 0}
    by = _fetch_moves([g["id"] for g in games])
    n_games = n_moves = trouble = fast_err = fast_all = lost_time = 0
    spent_sum = 0.0
    loss_t, cnt_t, loss_n, cnt_n = 0, 0, 0, 0
    for g in games:
        mt = pgnlite.move_times(g["pgn"], g["time_control"])
        if not mt:
            continue
        n_games += 1
        loss = _losses(by.get(g["id"], []))
        white = g["user_color"] == "white"
        thr = pgnlite.trouble_threshold(g["time_control"])
        for m in mt:
            if (m["ply"] % 2 == 1) != white or m["spent"] is None or m["ply"] <= 2:
                continue
            n_moves += 1
            spent_sum += m["spent"]
            lc = loss.get(m["ply"])
            in_trouble = m["clock"] is not None and m["clock"] < thr
            if in_trouble:
                trouble += 1
            if lc is not None:
                if in_trouble:
                    loss_t, cnt_t = loss_t + lc, cnt_t + 1
                else:
                    loss_n, cnt_n = loss_n + lc, cnt_n + 1
                if m["spent"] <= 3:
                    fast_all += 1
                    if lc >= 100:
                        fast_err += 1
        res = g["result"]
        lost = (res == "0-1" and white) or (res == "1-0" and not white)
        term = pgnlite.headers(g["pgn"]).get("Termination", "").lower()
        if lost and ("time" in term):
            lost_time += 1
    if not n_moves:
        return {"games": 0}
    return {"games": n_games, "moves": n_moves, "avg_spent": round(spent_sum / n_moves, 1),
            "trouble_share": round(100 * trouble / n_moves), "loss_trouble": round(loss_t / cnt_t) if cnt_t else None,
            "loss_normal": round(loss_n / cnt_n) if cnt_n else None, "fast_errors": fast_err, "fast_moves": fast_all, "lost_on_time": lost_time}


# ---------------------------------------------------------------- le tue aperture (per l'Atlante)
@router.get("/openings/mine")
def openings_mine(u=Depends(current_user)):
    rows = (sb.table("games").select("id,user_color,result,played_at,white,black,pgn").eq("user_email", u["email"])
            .not_.is_("user_color", "null").order("played_at", desc=True).limit(400).execute().data)
    out = []
    for g in rows:
        w = g["user_color"] == "white"
        res = g["result"]
        r = "d" if res == "1/2-1/2" else "w" if (res == "1-0") == w and res in ("1-0", "0-1") else "l" if res in ("1-0", "0-1") else None
        if r is None:
            continue
        out.append({"id": g["id"], "c": "w" if w else "b", "r": r, "d": (g["played_at"] or "")[:10],
                    "o": g["black"] if w else g["white"], "m": [p["san"] for p in pgnlite.plies(g["pgn"])[:30]]})
    return out


# ---------------------------------------------------------------- carte collezionabili
def assign_cards(email: str, rows: list[dict] | None = None, with_progress: bool = False):
    """Valuta gli obiettivi sulle partite dell'utente e salva le carte nuove. Chiamata subito dopo ogni analisi: la carta è pronta prima che l'utente apra l'app."""
    if rows is None:
        if ensure_highlights(email):
            pass
        rows = _game_rows(email)
    with_err = {str(e["game_id"]) for e in sb.table("errori_utenti").select("game_id").eq("user_email", email).limit(5000).execute().data}
    clean = {g["id"] for g in rows if g.get("accuracy_user") is not None and str(g["id"]) not in with_err}
    ev = CL.evaluate(rows, clean)
    have = {(c["goal"], c["game_id"]) for c in sb.table("cards").select("goal,game_id").eq("user_email", email).execute().data}
    new = [{"user_email": email, **c} for c in ev["cards"] if (c["goal"], c["game_id"]) not in have]
    if new:
        sb.table("cards").upsert(new, on_conflict="user_email,goal,game_id", ignore_duplicates=True).execute()
    return (len(new), ev["progress"]) if with_progress else len(new)


@router.get("/cards")
def cards(u=Depends(current_user)):
    """Restituisce l'album completo (assegnando prima eventuali carte nuove) con i dati per rigiocare la partita."""
    email = u["email"]
    ensure_highlights(email)
    rows = _game_rows(email)
    n_new, progress = assign_cards(email, rows, with_progress=True)
    owned = sb.table("cards").select("*").eq("user_email", email).order("created_at", desc=True).limit(300).execute().data
    by_id = {str(g["id"]): g for g in rows}
    missing = [c["game_id"] for c in owned if c["game_id"] not in by_id]
    if missing:  # partita fuori dalle ultime 1000: la recupero a parte
        for g in sb.table("games").select("id,played_at,user_color,result,white,black,pgn,accuracy_user,opening_name,source").eq("user_email", email).in_("id", missing[:100]).execute().data:
            g["sans"] = [p["san"] for p in pgnlite.plies(g["pgn"])]
            by_id[str(g["id"])] = g
    out = []
    for c in owned:
        g = by_id.get(c["game_id"])
        if not g:
            continue
        w = g["user_color"] == "white"
        out.append({"id": c["id"], "goal": c["goal"], "rarity": c["rarity"], "new": not c["seen"], "data": c["data"],
                    "game": {"id": g["id"], "me": g["white"] if w else g["black"], "opp": g["black"] if w else g["white"], "color": g["user_color"],
                             "result": g["result"], "opening": g.get("opening_name"), "date": (g.get("played_at") or "")[:10], "acc": g.get("accuracy_user"),
                             "elo": CL.elo(g["pgn"], g["user_color"]), "opp_elo": CL.elo(g["pgn"], "black" if w else "white"), "sans": g["sans"][:160],
                             "hi": (c["data"] or {}).get("hi")}})
    have_goals = {c["goal"] for c in owned}
    have = {}
    for c in owned:
        have[c["goal"]] = have.get(c["goal"], 0) + 1
    goals = [{"goal": k, "rarity": v["rarity"], "max": v["max"], "owned": have.get(k, 0), "group": "single"} for k, v in CL.GOALS.items()]
    for k, steps in CL.STREAK_STEPS.items():
        goals += [{"goal": f"streak_{k}_{n}", "rarity": CL.TIER_RARITY[i], "max": 3, "owned": have.get(f"streak_{k}_{n}", 0), "group": f"streak_{k}"} for i, n in enumerate(steps, 1)]
    for sp in CL.SPEEDS:
        goals += [{"goal": f"hours_{sp}_{i}", "rarity": CL.TIER_RARITY[i], "max": 1, "owned": have.get(f"hours_{sp}_{i}", 0), "group": "hours"} for i in (1, 2, 3)]
    return {"cards": out, "goals": goals, "new": n_new, "progress": progress, "hour_steps": CL.HOUR_STEPS}


@router.post("/cards/seen")
def cards_seen(u=Depends(current_user)):
    sb.table("cards").update({"seen": True}).eq("user_email", u["email"]).eq("seen", False).execute()
    return {"ok": True}
