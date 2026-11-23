import datetime
import logging
import time
from concurrent.futures import ThreadPoolExecutor
import os

import stripe
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import re
from collections import Counter

from fastapi import BackgroundTasks

from core.plans import get_plan, stripe_price_id
from .db import sb
from .engine import analyze_game
from . import cache, mailer
from .auth import current_user, tier_from, tier_of
from .sync import _fetch_err, SECONDS_PER_GAME, analyze_initial, analyze_pending, failed_ids, import_history, initial_rows, is_running, job_status, last_error, onboard, run_cron, start_job, run_job, sync_user
from .promo import attribute_checkout, attribute_renewal, checkout_discount, is_admin, promo_for, router as promo_router
from .train import router as train_router

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
# Free usa il modello più economico; se non esiste o fallisce si ripiega su GEMINI_MODEL
GEMINI_MODEL_FREE = os.environ.get("GEMINI_MODEL_FREE", "gemini-3.5-flash-lite")

log = logging.getLogger("main")

app = FastAPI(title="EloRise API")
app.include_router(train_router)
app.include_router(promo_router)
app.add_middleware(CORSMiddleware, allow_origins=[FRONTEND_URL], allow_methods=["*"], allow_headers=["*"])


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@app.get("/health")
def health():
    return {"ok": True}


def _new_cards(email: str) -> int:
    try:
        return sb.table("cards").select("id", count="exact").eq("user_email", email).eq("seen", False).limit(1).execute().count or 0
    except Exception:  # tabella non ancora creata (006 non eseguito)
        return 0


_pool = ThreadPoolExecutor(max_workers=8)


@app.get("/me")
def me(bg: BackgroundTasks, lang: str = "it", u=Depends(current_user)):
    email = u["email"]
    hit = cache.get(("me", email))
    if hit:
        return hit
    if u.get("confirmed"):   # account attivo: una sola volta, mail di benvenuto con piani e video
        bg.add_task(mailer.send_once, email, "welcome", "welcome", lang)
    month = datetime.date.today().strftime("%Y-%m")
    # le query sono indipendenti: partono insieme invece di una dopo l'altra
    f_cfg = _pool.submit(lambda: (sb.table("config_utenti").select("tier,data_scadenza,bonus_lessons").eq("user_email", email).limit(1).execute().data or [None])[0])
    f_q = _pool.submit(lambda: sb.table("quota_usage").select("ai_analyses_used").eq("user_email", email).eq("quota_month", month).execute().data)
    f_n = _pool.submit(lambda: sb.table("profili_scacchi").select("id", count="exact").eq("user_email", email).execute().count or 0)
    f_c = _pool.submit(_new_cards, email)
    f_p = _pool.submit(promo_for, email)
    cfg, q, n = f_cfg.result(), f_q.result(), f_n.result()
    tier = tier_from(cfg)
    plan = get_plan(tier)
    out = {
        "email": email, "tier": tier,
        "profiles": {"used": n, "limit": plan.profiles},
        "lessons": {"used": q[0]["ai_analyses_used"] if q else 0, "limit": plan.gm_lessons_month},
        "auto_sync": plan.auto_sync, "history_games": plan.history_games,
        "new_cards": f_c.result(),
        "is_admin": is_admin(email), "promo": f_p.result(),
        "bonus_lessons": (cfg or {}).get("bonus_lessons") or 0,
        "renews": (cfg or {}).get("data_scadenza") if tier != "Free" else None,
        "member_since": u.get("created_at"),
    }
    cache.put(("me", email), out, 15)
    return out


# ---------- Account scacchistici ----------
class ProfileIn(BaseModel):
    piattaforma: str
    username: str


def _mine(u):
    """Account attualmente collegati: le partite di un profilo rimosso non devono più comparire in elenco e grafici."""
    pr = sb.table("profili_scacchi").select("piattaforma,username").eq("user_email", u["email"]).execute().data
    return {(p["piattaforma"], (p["username"] or "").lower()) for p in pr}


def _is_mine(g, mine):
    c = g.get("user_color")
    uname = g.get("white") if c == "white" else g.get("black") if c == "black" else None
    return not mine or uname is None or (g["source"], uname.lower()) in mine


@app.get("/profiles")
def list_profiles(u=Depends(current_user)):
    return sb.table("profili_scacchi").select("*").eq("user_email", u["email"]).execute().data


@app.post("/profiles")
def add_profile(body: ProfileIn, bg: BackgroundTasks, u=Depends(current_user)):
    if body.piattaforma not in ("lichess", "chesscom") or not body.username.strip():
        raise HTTPException(400, "invalid_profile")
    plan = get_plan(tier_of(u["email"]))
    n = sb.table("profili_scacchi").select("id", count="exact").eq("user_email", u["email"]).execute().count or 0
    if n >= plan.profiles:
        raise HTTPException(402, "profile_limit")
    try:
        r = sb.table("profili_scacchi").insert(
            {"user_email": u["email"], "piattaforma": body.piattaforma, "username": body.username.strip()}).execute()
    except Exception:
        raise HTTPException(409, "profile_exists")
    bg.add_task(onboard, u["email"], tier_of(u["email"]))  # storico e analisi iniziale, in background
    cache.bust(u["email"])
    return r.data[0]


@app.delete("/profiles/{profile_id}")
def delete_profile(profile_id: int, u=Depends(current_user)):
    sb.table("profili_scacchi").delete().eq("id", profile_id).eq("user_email", u["email"]).execute()
    cache.bust(u["email"])
    return {"deleted": True}


# ---------- Partite: la lista e la riapertura leggono dal DB, senza rifare l'analisi ----------
@app.get("/games")
def list_games(u=Depends(current_user)):
    """Elenco per la pagina Partite: esito, ritmo, errori per partita, già calcolati qui così il telefono non deve fare altre richieste."""
    rows = (sb.table("games")
            .select("id,white,black,user_color,result,opening_name,played_at,accuracy_user,analyzed_at,source,time_control")
            .eq("user_email", u["email"]).order("played_at", desc=True).limit(300).execute().data)
    mine = _mine(u)
    rows = [g for g in rows if _is_mine(g, mine)]
    errs: dict = {}
    for e in sb.table("errori_utenti").select("game_id,classification").eq("user_email", u["email"]).in_("classification", ["mistake", "blunder"]).limit(5000).execute().data:
        c = errs.setdefault(e["game_id"], {"blunder": 0, "mistake": 0})
        c[e["classification"]] += 1
    out = []
    for g in rows:
        c, res = g["user_color"], g["result"]
        outcome = None
        if c and res in ("1-0", "0-1", "1/2-1/2"):
            outcome = "d" if res == "1/2-1/2" else "w" if (res == "1-0") == (c == "white") else "l"
        e = errs.get(g["id"], {"blunder": 0, "mistake": 0})
        out.append({**g, "outcome": outcome, "me": (g["white"] if c == "white" else g["black"]) if c else None,
                    "opp": (g["black"] if c == "white" else g["white"]) if c else None,
                    "speed": _speed(g["time_control"]), "blunders": e["blunder"], "mistakes": e["mistake"]})
    return out


def _moves_from_pgn(g: dict) -> list:
    """Mosse dal PGN (senza valutazioni): per le partite scaricate e non ancora analizzate."""
    import chess, chess.pgn, io as _io
    out = []
    try:
        pg = chess.pgn.read_game(_io.StringIO(g["pgn"]))
        board, white = pg.board(), (g.get("user_color") == "white")
        for i, mv in enumerate(pg.mainline_moves()):
            san = board.san(mv); board.push(mv)
            out.append({"game_id": g["id"], "ply": i + 1, "san": san, "uci": mv.uci(), "fen_after": board.fen(), "eval_cp": None,
                        "best_move_san": None, "classification": None, "is_user_move": ((i % 2 == 0) == white) if g.get("user_color") else False})
    except Exception:
        return []
    return out


@app.get("/games/{game_id}")
def get_game(game_id: str, u=Depends(current_user)):
    g = sb.table("games").select("*").eq("id", game_id).eq("user_email", u["email"]).limit(1).execute().data
    if not g:
        raise HTTPException(404, "not_found")
    moves = sb.table("moves").select("*").eq("game_id", game_id).order("ply").execute().data
    if not moves and g[0].get("pgn"):
        moves = _moves_from_pgn(g[0])   # partita non ancora analizzata: le mosse si vedono comunque, leggendo il PGN
    errors = sb.table("errori_utenti").select("*").eq("game_id", game_id).eq("user_email", u["email"]).order("ply").execute().data
    prev = 0
    for m in moves:  # perdita di valutazione (centesimi di pedone) di chi ha mosso, 0 se la mossa migliora la posizione
        cur = m.get("eval_cp")
        if cur is None:
            m["loss_cp"] = None
            continue
        m["loss_cp"] = max(0, min(500, (prev - cur) if m["ply"] % 2 else (cur - prev)))
        prev = cur
    return {"game": g[0], "moves": moves, "errors": errors}


# ---------- Lezione del Gran Maestro AI ----------
class LessonIn(BaseModel):
    lang: str = "it"


LANG_NAMES = {"it": "italiano", "en": "English", "es": "español"}


class GmBusy(Exception):
    """Gemini sovraccarico o limite gratuito raggiunto: riprovare tra poco."""


def _is_busy(e: Exception) -> bool:
    t = (str(e) + type(e).__name__).lower()
    return any(k in t for k in ("429", "503", "resource_exhausted", "unavailable", "overloaded", "quota", "rate"))


def gm_lesson(err: dict, lang: str, tier: str = "Free") -> str:
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options={"timeout": 45000})
    prompt = (f"Posizione (FEN) prima della mossa: {err['fen']}\n"
              f"Mossa giocata: {err['mossa_critica']}\nMossa migliore: {err.get('best_move') or 'sconosciuta'}")
    system = (f"Sei un Gran Maestro di scacchi e un ottimo insegnante. Rispondi solo in {LANG_NAMES.get(lang, 'italiano')}, "
              "in markdown semplice, con 3 punti: **Errore**, **Idea corretta**, **Regola pratica**. Max 120 parole.")
    cfg = {"system_instruction": system}
    models = [GEMINI_MODEL_FREE, GEMINI_MODEL] if tier == "Free" else [GEMINI_MODEL, GEMINI_MODEL_FREE]
    models = list(dict.fromkeys(m for m in models if m))
    busy, last = False, None
    for model in models:
        for attempt in range(2):  # un secondo tentativo dopo una breve pausa, poi si passa al modello successivo
            try:
                r = client.models.generate_content(model=model, contents=prompt, config=cfg)
                if r.text and r.text.strip():
                    return r.text.strip()
                last = RuntimeError("risposta vuota")
                log.warning("GM %s: risposta vuota", model)
                break
            except Exception as e:
                last = e
                log.warning("GM %s tentativo %s fallito: %s: %s", model, attempt + 1, type(e).__name__, str(e)[:300])
                if _is_busy(e):
                    busy = True
                    time.sleep(1.5 * (attempt + 1))
                    continue
                break
    if busy:
        raise GmBusy(str(last))
    raise RuntimeError(str(last))


def _quota_left(email: str, tier: str) -> bool:
    """Controllo veloce senza consumare nulla: la quota si scala solo a lezione generata."""
    plan = get_plan(tier)
    if plan.gm_lessons_month is None:
        return True
    month = datetime.date.today().strftime("%Y-%m")
    q = sb.table("quota_usage").select("ai_analyses_used").eq("user_email", email).eq("quota_month", month).execute().data
    if (q[0]["ai_analyses_used"] if q else 0) < plan.gm_lessons_month:
        return True
    b = sb.table("config_utenti").select("bonus_lessons").eq("user_email", email).limit(1).execute().data
    return bool(b and (b[0].get("bonus_lessons") or 0) > 0)


def _lesson_for(err: dict, lang: str, email: str) -> dict:
    if err.get("gm_lesson"):  # già generata: non consuma quota
        return {"lesson": err["gm_lesson"], "cached": True, "error_id": err["id"]}
    tier = tier_of(email)
    if not _quota_left(email, tier):
        raise HTTPException(402, "quota_exhausted")
    # prima si genera la lezione, poi si scala la quota: se il GM non risponde, il contatore non si muove mai
    try:
        text = gm_lesson(err, lang, tier)
    except GmBusy:
        raise HTTPException(503, "gm_busy")
    except Exception as e:
        log.exception("GM fallito: %s", e)
        raise HTTPException(502, "gm_failed")
    sb.table("errori_utenti").update({"gm_lesson": text, "gm_lesson_at": now_iso()}).eq("id", err["id"]).execute()  # la lezione si salva sempre
    if not sb.rpc("consume_gm_lesson", {"p_email": email}).execute().data:
        log.warning("quota esaurita durante la generazione per %s: lezione salvata comunque", email)
    cache.bust(email)
    return {"lesson": text, "cached": False, "error_id": err["id"]}


@app.post("/errors/{error_id}/lesson")
def lesson(error_id: int, body: LessonIn, u=Depends(current_user)):
    rows = sb.table("errori_utenti").select("*").eq("id", error_id).eq("user_email", u["email"]).limit(1).execute().data
    if not rows:
        raise HTTPException(404, "not_found")
    return _lesson_for(rows[0], body.lang, u["email"])


START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


@app.post("/games/{game_id}/moves/{ply}/lesson")
def move_lesson(game_id: str, ply: int, body: LessonIn, u=Depends(current_user)):
    """Lezione su una mossa che non è un errore salvato (le imprecisioni): crea la riga al momento della richiesta."""
    g = sb.table("games").select("id,opening_name").eq("id", game_id).eq("user_email", u["email"]).limit(1).execute().data
    if not g:
        raise HTTPException(404, "not_found")
    ex = sb.table("errori_utenti").select("*").eq("game_id", game_id).eq("user_email", u["email"]).eq("ply", ply).limit(1).execute().data
    if ex:
        return _lesson_for(ex[0], body.lang, u["email"])
    ms = sb.table("moves").select("*").eq("game_id", game_id).in_("ply", [ply - 1, ply]).execute().data
    cur = next((m for m in ms if m["ply"] == ply), None)
    if not cur or not cur.get("is_user_move") or cur.get("classification") != "inaccuracy":
        raise HTTPException(404, "not_found")
    prev = next((m for m in ms if m["ply"] == ply - 1), None)
    fen = prev["fen_after"] if prev else START_FEN
    white = ply % 2 == 1
    loss = 0
    if prev and prev.get("eval_cp") is not None and cur.get("eval_cp") is not None:
        loss = max(0, (prev["eval_cp"] - cur["eval_cp"]) if white else (cur["eval_cp"] - prev["eval_cp"]))
    pieces = sum(1 for ch in fen.split(" ")[0] if ch.isalpha())
    cat = "endgame" if pieces <= 10 else "opening" if ply <= 20 else "positional"
    row = {"user_email": u["email"], "game_id": game_id, "ply": ply, "fen": fen,
           "mossa_critica": f"{(ply + 1) // 2}{'.' if white else '...'} {cur['san']}", "best_move": cur.get("best_move_san"),
           "categoria_errore": cat, "classification": "inaccuracy", "eval_loss_cp": int(loss),
           "apertura": g[0].get("opening_name"), "data": now_iso()}
    ins = sb.table("errori_utenti").upsert(row, on_conflict="user_email,game_id,ply").execute().data
    if not ins:
        raise HTTPException(500, "db_error")
    return _lesson_for(ins[0], body.lang, u["email"])


# ---------- Stripe ----------
LEGAL_TEXT = {
    "it": "Abbonandoti accetti i [Termini]({url}/terms) e la [Privacy]({url}/privacy). Rinnovo mensile automatico, disdici quando vuoi dal portale.",
    "en": "By subscribing you accept the [Terms]({url}/terms) and the [Privacy Policy]({url}/privacy). Renews monthly, cancel any time from the portal.",
    "es": "Al suscribirte aceptas los [Términos]({url}/terms) y la [Privacidad]({url}/privacy). Renovación mensual automática, cancela cuando quieras desde el portal.",
}


class CheckoutIn(BaseModel):
    plan: str
    lang: str = "it"
    interval: str = "month"   # "month" | "year"


@app.post("/billing/checkout")
def checkout(body: CheckoutIn, u=Depends(current_user)):
    if body.plan not in ("Plus", "Pro", "Elite"):
        raise HTTPException(400, "invalid_plan")
    row = sb.table("config_utenti").select("stripe_customer_id").eq("user_email", u["email"]).limit(1).execute().data
    cust = row[0].get("stripe_customer_id") if row else None
    args = dict(
        mode="subscription", line_items=[{"price": stripe_price_id(body.plan, "year" if body.interval == "year" else "month"), "quantity": 1}],
        success_url=f"{FRONTEND_URL}/dashboard/plans?checkout=success", cancel_url=f"{FRONTEND_URL}/dashboard/plans?checkout=cancel",
        metadata={"email": u["email"], "plan": body.plan, "lang": body.lang if body.lang in ("it", "en", "es") else "it", "interval": "year" if body.interval == "year" else "month"},
        locale=body.lang if body.lang in ("it", "en", "es") else "auto",
        custom_text={"submit": {"message": LEGAL_TEXT.get(body.lang, LEGAL_TEXT["en"]).format(url=FRONTEND_URL)}})
    disc = checkout_discount(u["email"])      # codice arrivato dal link del creatore: sconto già applicato
    if disc:
        args["discounts"] = [{"promotion_code": disc["pid"]}]
        args["metadata"]["promo"] = disc["code"]
    else:
        args["allow_promotion_codes"] = True
    if os.environ.get("STRIPE_TERMS_CHECKBOX") == "1":
        args["consent_collection"] = {"terms_of_service": "required"}
    if cust:
        args["customer"] = cust
    else:
        args["customer_email"] = u["email"]
    return {"url": stripe.checkout.Session.create(**args).url}


@app.post("/billing/portal")
def portal(u=Depends(current_user)):
    row = sb.table("config_utenti").select("stripe_customer_id").eq("user_email", u["email"]).limit(1).execute().data
    if not row or not row[0].get("stripe_customer_id"):
        raise HTTPException(404, "no_customer")
    return {"url": stripe.billing_portal.Session.create(customer=row[0]["stripe_customer_id"], return_url=f"{FRONTEND_URL}/dashboard/plans").url}


@app.post("/billing/webhook")
async def webhook(request: Request, bg: BackgroundTasks):
    try:
        ev = stripe.Webhook.construct_event(
            await request.body(), request.headers.get("stripe-signature", ""), os.environ["STRIPE_WEBHOOK_SECRET"])
    except Exception:
        raise HTTPException(400, "bad_signature")
    obj = ev["data"]["object"]
    if ev["type"] == "checkout.session.completed":
        email, plan = obj["metadata"]["email"], obj["metadata"]["plan"]
        prev = tier_of(email)
        sb.table("config_utenti").upsert({
            "user_email": email, "tier": plan, "subscription_status": "active",
            "stripe_customer_id": obj["customer"], "stripe_subscription_id": obj["subscription"],
            "updated_at": now_iso()}, on_conflict="user_email").execute()
        cache.bust(email)
        sb.table("storico_abbonamenti").insert({
            "user_email": email, "tier_precedente": prev, "tier_nuovo": plan, "azione": "attivazione",
            "importo": (obj.get("amount_total") or 0) / 100, "stripe_session_id": obj["id"]}).execute()
        attribute_checkout(obj, email, plan)
        bg.add_task(mailer.send_once, email, f"sub:{obj['id']}", "subscribed", obj["metadata"].get("lang", "it"), plan=plan, interval=obj["metadata"].get("interval", "month"))
        bg.add_task(onboard, email, plan)  # più storico e più partite analizzate col nuovo piano
    elif ev["type"] == "invoice.paid":
        end = obj["lines"]["data"][0]["period"]["end"]
        sb.table("config_utenti").update({
            "data_scadenza": datetime.date.fromtimestamp(end).isoformat(), "subscription_status": "active",
            "updated_at": now_iso()}).eq("stripe_customer_id", obj["customer"]).execute()
        attribute_renewal(obj)
    elif ev["type"] == "customer.subscription.deleted":
        sb.table("config_utenti").update({
            "tier": "Free", "subscription_status": "canceled", "data_scadenza": None,
            "updated_at": now_iso()}).eq("stripe_subscription_id", obj["id"]).execute()
    return {"received": True}


# ---------- Cancellazione account (GDPR) ----------
@app.delete("/me")
def delete_me(u=Depends(current_user)):
    email = u["email"]
    row = sb.table("config_utenti").select("stripe_subscription_id").eq("user_email", email).limit(1).execute().data
    if row and row[0].get("stripe_subscription_id"):
        try:
            stripe.Subscription.cancel(row[0]["stripe_subscription_id"])
        except Exception:
            pass
    ids = [g["id"] for g in sb.table("games").select("id").eq("user_email", email).execute().data]
    if ids:
        sb.table("moves").delete().in_("game_id", ids).execute()
    try:
        sb.table("cards").delete().eq("user_email", email).execute()
    except Exception:
        pass  # tabella assente se 006 non è stato eseguito
    try:
        sb.table("promo_events").update({"user_email": None}).eq("user_email", email).execute()   # i conteggi restano, l'email no
    except Exception:
        pass
    for t in ("mistake_cards", "puzzle_attempts", "training_stats", "rewards", "errori_utenti", "ai_usage_log", "games", "storico_rating", "profili_scacchi", "quota_usage", "storico_abbonamenti", "config_utenti"):
        sb.table(t).delete().eq("user_email", email).execute()
    sb.table("user_profiles").delete().eq("user_id", u["id"]).execute()
    sb.auth.admin.delete_user(u["id"])
    return {"deleted": True}


# ---------- Statistiche, lezioni, sincronizzazione ----------
def _elo(pgn: str, color: str):
    m = re.search(rf'\[{"White" if color == "white" else "Black"}Elo "(\d+)"\]', pgn or "")
    return int(m.group(1)) if m else None


def _speed(tc: str | None):
    """Categoria di ritmo come Lichess: durata stimata = base + 40 * incremento."""
    m = re.match(r"^(\d+)(?:\+(\d+))?$", tc or "")
    if not m:
        return "daily" if tc and "/" in tc else "other"
    est = int(m.group(1)) + 40 * int(m.group(2) or 0)
    return "bullet" if est < 180 else "blitz" if est < 480 else "rapid" if est < 1500 else "classical"


@app.get("/stats")
def stats(u=Depends(current_user)):
    hit = cache.get(("stats", u["email"]))
    if hit:
        return hit
    out = _stats(u)
    cache.put(("stats", u["email"]), out, 60)
    return out


def _stats(u):
    rows = (sb.table("games").select("source,white,black,time_control,pgn,user_color,result,opening_name,played_at,accuracy_user")
            .eq("user_email", u["email"]).order("played_at", desc=True).limit(1000).execute().data)[::-1]
    mine = _mine(u)
    rows = [g for g in rows if _is_mine(g, mine)]
    w = d = l = 0
    ops, rating, accs, disp, cnt = {}, {}, [], {}, {}
    for g in rows:
        c, res = g["user_color"], g["result"]
        if c and res in ("1-0", "0-1", "1/2-1/2"):
            o = "d" if res == "1/2-1/2" else "w" if (res == "1-0") == (c == "white") else "l"
            w, d, l = w + (o == "w"), d + (o == "d"), l + (o == "l")
            name = (g["opening_name"] or "?").split(":")[0].split(",")[0].strip()
            e = ops.setdefault(name, {"name": name, "games": 0, "w": 0, "d": 0, "l": 0})
            e["games"] += 1
            e[o] += 1
        if c and g["played_at"] and (elo := _elo(g["pgn"], c)):
            uname = g["white"] if c == "white" else g["black"]
            disp.setdefault((g["source"], (uname or "").lower()), uname)
            k3 = (g["source"], (uname or "").lower(), _speed(g["time_control"]))
            rating.setdefault(k3, {})[g["played_at"][:10]] = elo  # un valore al giorno: l'ultimo
            cnt[k3] = cnt.get(k3, 0) + 1                          # partite per ritmo: serve a scegliere il grafico predefinito
        if g["accuracy_user"] is not None:
            accs.append(float(g["accuracy_user"]))
    cats = Counter(r["categoria_errore"] for r in sb.table("errori_utenti").select("categoria_errore").eq("user_email", u["email"]).in_("classification", ["mistake", "blunder"]).execute().data if r["categoria_errore"])
    # un grafico per account con una serie per ritmo, un punto al giorno (l'ultimo rating del giorno)
    order = ["bullet", "blitz", "rapid", "classical", "daily", "other"]
    accounts = {}
    for (src, uname, sp), days in rating.items():
        accounts.setdefault((src, uname), []).append((sp, days))
    rating_out = [{"source": src, "username": disp.get((src, uname), uname),
                   "series": [{"speed": sp, "n": cnt.get((src, uname, sp), 0), "points": [{"d": d_, "r": r_} for d_, r_ in sorted(days.items())]}
                              for sp, days in sorted(ser, key=lambda x: order.index(x[0]))]}
                  for (src, uname), ser in accounts.items()]
    n = w + d + l
    top = sorted(ops.values(), key=lambda x: -x["games"])[:10]
    return {"games": len(rows), "w": w, "d": d, "l": l, "win_rate": round(100 * w / n) if n else None,
            "accuracy": round(sum(accs) / len(accs)) if accs else None, "rating": rating_out,
            "openings": [{**o, "win_rate": round(100 * o["w"] / o["games"])} for o in top],
            "categories": [{"cat": k, "count": v} for k, v in cats.most_common()]}


@app.get("/lessons")
def all_lessons(u=Depends(current_user)):
    return (sb.table("errori_utenti")
            .select("id,game_id,ply,mossa_critica,best_move,categoria_errore,gm_lesson,gm_lesson_at,apertura,games(white,black)")
            .eq("user_email", u["email"]).not_.is_("gm_lesson", "null").order("gm_lesson_at", desc=True).limit(300).execute().data)


@app.get("/onboarding/status")
def onboarding_status(bg: BackgroundTasks, u=Depends(current_user)):
    """Avanzamento dell'analisi iniziale: quante delle partite garantite dal piano sono già analizzate."""
    email = u["email"]
    tier = tier_of(email)
    profs = sb.table("profili_scacchi").select("id,last_sync_at").eq("user_email", email).execute().data
    if not profs:
        return {"state": "no_profile"}
    rows = initial_rows(email, tier)
    target = get_plan(tier).initial_games
    bad = failed_ids(email)
    pending = sum(1 for r in rows if not r["analyzed_at"] and r["id"] not in bad)
    failed = sum(1 for r in rows if not r["analyzed_at"] and r["id"] in bad)
    importing = any(not p.get("last_sync_at") for p in profs)
    if not importing and pending and not is_running(email):
        bg.add_task(analyze_initial, email, tier)  # se il server era stato riavviato, riprende da dove era rimasto
    state = "working" if (importing or pending) else "done"
    return {"state": state, "target": target, "total": len(rows), "analyzed": len(rows) - pending - failed, "pending": pending,
            "failed": failed, "error": last_error(email) if failed else None,
            "importing": importing, "eta_min": max(1, round(pending * SECONDS_PER_GAME / 60)) if pending else 0}


@app.post("/sync/history")
def sync_history(bg: BackgroundTasks, u=Depends(current_user)):
    """Importa (o amplia dopo un upgrade) lo storico previsto dal piano."""
    tier = tier_of(u["email"])
    bg.add_task(onboard, u["email"], tier)
    return {"started": True, "games": get_plan(tier).history_games}


FREE_PER_CLICK = 5     # Free: partite scaricate e analizzate a ogni clic
FREE_PER_DAY = 10      # Free: tetto giornaliero di analisi (limita il costo del server)


@app.post("/sync")
def sync(bg: BackgroundTasks, n: int = 15, u=Depends(current_user)):
    """Scarica le partite e le analizza subito, nei limiti del piano. Il contatore si segue con GET /sync/status.
    - Piani a pagamento: si scarica lo storico del piano e si analizzano TUTTE le partite da analizzare.
    - Free: poche partite a clic (FREE_PER_CLICK) e un tetto giornaliero (FREE_PER_DAY)."""
    email = u["email"]
    tier = tier_of(email)
    plan = get_plan(tier)
    if tier == "Free":
        today = datetime.date.today().isoformat()
        done_today = len(sb.table("games").select("id").eq("user_email", email).gte("analyzed_at", today).execute().data or [])
        left = max(0, FREE_PER_DAY - done_today)
        imported = sync_user(email, FREE_PER_CLICK)
        cache.bust(email)
        if left == 0:
            return {"imported": imported, "fetch_error": _fetch_err.get(email),
                    "job": {"state": "limit", "daily": FREE_PER_DAY, "done_today": done_today, "total": 0, "done": 0, "failed": 0, "imported": imported}}
        limit = min(FREE_PER_CLICK, left)
    else:
        try:
            import_history(email, tier)          # completa lo storico del piano (non rifà ciò che c'è già)
        except Exception as e:
            log.warning("storico %s: %s", email, e)
        imported = sync_user(email, 200)
        cache.bust(email)
        limit = plan.history_games               # tutte le partite del piano
    job = start_job(email, limit, imported)
    if job["ids"]:
        bg.add_task(run_job, email, job["ids"])
    return {"imported": imported, "job": job["status"], "fetch_error": _fetch_err.get(email)}


@app.get("/sync/status")
def sync_status(u=Depends(current_user)):
    return job_status(u["email"])


@app.post("/games/{game_id}/analyze")
def analyze_one(game_id: str, bg: BackgroundTasks, u=Depends(current_user)):
    g = sb.table("games").select("*").eq("id", game_id).eq("user_email", u["email"]).limit(1).execute().data
    if not g:
        raise HTTPException(404, "not_found")
    bg.add_task(analyze_game, g[0])
    return {"queued": True}


@app.post("/cron/sync")
def cron_sync(bg: BackgroundTasks, x_cron_secret: str = Header(None)):
    secret = os.environ.get("CRON_SECRET")
    if not secret or x_cron_secret != secret:
        raise HTTPException(403, "forbidden")
    bg.add_task(run_cron)
    return {"started": True}


@app.get("/diag")
def diag(u=Depends(current_user)):
    """Controlli rapidi per capire perché un'analisi non parte: database, colonne, motore, servizi esterni."""
    import httpx as _hx
    from . import engine as E
    out = []
    def add(name, ok, detail=""): out.append({"name": name, "ok": bool(ok), "detail": str(detail)[:200]})
    for col in ("analysis_depth", "highlights", "accuracy_user", "analyzed_at"):
        try:
            sb.table("games").select(col).limit(1).execute(); add(f"colonna games.{col}", True)
        except Exception as e:
            add(f"colonna games.{col}", False, str(e) + "  -> esegui supabase/012_analysis_depth.sql")
    try:
        sb.table("eval_cache").select("fen").limit(1).execute(); add("tabella eval_cache", True)
    except Exception as e:
        add("tabella eval_cache", False, str(e) + "  -> esegui supabase/011_eval_cache.sql")
    add("Stockfish sul server", bool(E.STOCKFISH), E.STOCKFISH or "assente: si usa il servizio online (può rifiutare le richieste)")
    if E.STOCKFISH:
        ev, san = E.eval_local("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"); add("Stockfish risponde", ev is not None, f"{ev} {san}")
    with _hx.Client(headers={"User-Agent": "EloRise/1.0"}) as c:
        ce, cs, cd = E.eval_cloud(c, "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"); add("memoria pubblica Lichess", ce is not None, f"{ce} {cs} profondità {cd}")
        ev, san = E.eval_fen(c, "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"); add("servizio online chess-api.com", ev is not None, E._api_err or f"{ev} {san}")
        try:
            r = c.get("https://lichess.org/api/user/lichess", timeout=8.0); add("Lichess raggiungibile", r.status_code == 200, f"HTTP {r.status_code}")
        except Exception as e:
            add("Lichess raggiungibile", False, e)
    return out
