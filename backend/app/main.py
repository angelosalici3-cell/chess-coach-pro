import datetime
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
from .sync import analyze_pending, run_cron, sync_user

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

app = FastAPI(title="Chess Coach API")
app.add_middleware(CORSMiddleware, allow_origins=[FRONTEND_URL], allow_methods=["*"], allow_headers=["*"])


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def current_user(authorization: str = Header(None)):
    """Verifica il token Supabase inviato dal browser. Ogni query è poi filtrata per email."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing_token")
    try:
        u = sb.auth.get_user(authorization[7:]).user
    except Exception:
        raise HTTPException(401, "invalid_token")
    if not u or not u.email:
        raise HTTPException(401, "invalid_token")
    return {"id": u.id, "email": u.email}


def tier_of(email: str) -> str:
    rows = sb.table("config_utenti").select("tier,data_scadenza").eq("user_email", email).limit(1).execute().data
    if not rows:
        return "Free"
    tier, exp = rows[0]["tier"], rows[0].get("data_scadenza")
    if tier != "Free" and exp and datetime.date.fromisoformat(exp) < datetime.date.today():
        return "Free"
    return tier


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/me")
def me(u=Depends(current_user)):
    tier = tier_of(u["email"])
    plan = get_plan(tier)
    month = datetime.date.today().strftime("%Y-%m")
    q = sb.table("quota_usage").select("ai_analyses_used").eq("user_email", u["email"]).eq("quota_month", month).execute().data
    n = sb.table("profili_scacchi").select("id", count="exact").eq("user_email", u["email"]).execute().count or 0
    return {
        "email": u["email"], "tier": tier,
        "profiles": {"used": n, "limit": plan.profiles},
        "lessons": {"used": q[0]["ai_analyses_used"] if q else 0, "limit": plan.gm_lessons_month},
        "auto_sync": plan.auto_sync,
    }


# ---------- Account scacchistici ----------
class ProfileIn(BaseModel):
    piattaforma: str
    username: str


@app.get("/profiles")
def list_profiles(u=Depends(current_user)):
    return sb.table("profili_scacchi").select("*").eq("user_email", u["email"]).execute().data


@app.post("/profiles")
def add_profile(body: ProfileIn, u=Depends(current_user)):
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
    return r.data[0]


@app.delete("/profiles/{profile_id}")
def delete_profile(profile_id: int, u=Depends(current_user)):
    sb.table("profili_scacchi").delete().eq("id", profile_id).eq("user_email", u["email"]).execute()
    return {"deleted": True}


# ---------- Partite: la lista e la riapertura leggono dal DB, senza rifare l'analisi ----------
@app.get("/games")
def list_games(u=Depends(current_user)):
    return (sb.table("games")
            .select("id,white,black,user_color,result,opening_name,played_at,accuracy_user,analyzed_at")
            .eq("user_email", u["email"]).order("played_at", desc=True).limit(100).execute().data)


@app.get("/games/{game_id}")
def get_game(game_id: str, u=Depends(current_user)):
    g = sb.table("games").select("*").eq("id", game_id).eq("user_email", u["email"]).limit(1).execute().data
    if not g:
        raise HTTPException(404, "not_found")
    moves = sb.table("moves").select("*").eq("game_id", game_id).order("ply").execute().data
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


def gm_lesson(err: dict, lang: str) -> str:
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = (f"Posizione (FEN) prima della mossa: {err['fen']}\n"
              f"Mossa giocata: {err['mossa_critica']}\nMossa migliore: {err.get('best_move') or 'sconosciuta'}")
    system = (f"Sei un Gran Maestro di scacchi e un ottimo insegnante. Rispondi solo in {LANG_NAMES.get(lang, 'italiano')}, "
              "in markdown semplice, con 3 punti: **Errore**, **Idea corretta**, **Regola pratica**. Max 120 parole.")
    r = client.models.generate_content(model=GEMINI_MODEL, contents=prompt, config={"system_instruction": system})
    if not r.text:
        raise RuntimeError("empty")
    return r.text.strip()


@app.post("/errors/{error_id}/lesson")
def lesson(error_id: int, body: LessonIn, u=Depends(current_user)):
    rows = sb.table("errori_utenti").select("*").eq("id", error_id).eq("user_email", u["email"]).limit(1).execute().data
    if not rows:
        raise HTTPException(404, "not_found")
    err = rows[0]
    if err.get("gm_lesson"):  # già generata: non consuma quota
        return {"lesson": err["gm_lesson"], "cached": True}
    if not sb.rpc("consume_gm_lesson", {"p_email": u["email"]}).execute().data:
        raise HTTPException(402, "quota_exhausted")
    try:
        text = gm_lesson(err, body.lang)
    except Exception:
        sb.rpc("refund_gm_lesson", {"p_email": u["email"]}).execute()  # se il GM non risponde, la lezione non conta
        raise HTTPException(502, "gm_failed")
    sb.table("errori_utenti").update({"gm_lesson": text, "gm_lesson_at": now_iso()}).eq("id", error_id).execute()
    return {"lesson": text, "cached": False}


# ---------- Stripe ----------
LEGAL_TEXT = {
    "it": "Abbonandoti accetti i [Termini]({url}/terms) e la [Privacy]({url}/privacy). Rinnovo mensile automatico, disdici quando vuoi dal portale.",
    "en": "By subscribing you accept the [Terms]({url}/terms) and the [Privacy Policy]({url}/privacy). Renews monthly, cancel any time from the portal.",
    "es": "Al suscribirte aceptas los [Términos]({url}/terms) y la [Privacidad]({url}/privacy). Renovación mensual automática, cancela cuando quieras desde el portal.",
}


class CheckoutIn(BaseModel):
    plan: str
    lang: str = "it"


@app.post("/billing/checkout")
def checkout(body: CheckoutIn, u=Depends(current_user)):
    if body.plan not in ("Plus", "Pro", "Elite"):
        raise HTTPException(400, "invalid_plan")
    row = sb.table("config_utenti").select("stripe_customer_id").eq("user_email", u["email"]).limit(1).execute().data
    cust = row[0].get("stripe_customer_id") if row else None
    args = dict(
        mode="subscription", line_items=[{"price": stripe_price_id(body.plan), "quantity": 1}],
        success_url=f"{FRONTEND_URL}/dashboard/plans?checkout=success", cancel_url=f"{FRONTEND_URL}/dashboard/plans?checkout=cancel",
        allow_promotion_codes=True, metadata={"email": u["email"], "plan": body.plan},
        locale=body.lang if body.lang in ("it", "en", "es") else "auto",
        custom_text={"submit": {"message": LEGAL_TEXT.get(body.lang, LEGAL_TEXT["en"]).format(url=FRONTEND_URL)}})
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
async def webhook(request: Request):
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
        sb.table("storico_abbonamenti").insert({
            "user_email": email, "tier_precedente": prev, "tier_nuovo": plan, "azione": "attivazione",
            "importo": (obj.get("amount_total") or 0) / 100, "stripe_session_id": obj["id"]}).execute()
    elif ev["type"] == "invoice.paid":
        end = obj["lines"]["data"][0]["period"]["end"]
        sb.table("config_utenti").update({
            "data_scadenza": datetime.date.fromtimestamp(end).isoformat(), "subscription_status": "active",
            "updated_at": now_iso()}).eq("stripe_customer_id", obj["customer"]).execute()
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
    for t in ("errori_utenti", "ai_usage_log", "games", "storico_rating", "profili_scacchi", "quota_usage", "storico_abbonamenti", "config_utenti"):
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
    rows = (sb.table("games").select("source,white,black,time_control,pgn,user_color,result,opening_name,played_at,accuracy_user")
            .eq("user_email", u["email"]).order("played_at", desc=True).limit(500).execute().data)[::-1]
    w = d = l = 0
    ops, rating, accs = {}, {}, []
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
            rating.setdefault((g["source"], uname, _speed(g["time_control"])), {})[g["played_at"][:10]] = elo  # un valore al giorno: l'ultimo
        if g["accuracy_user"] is not None:
            accs.append(float(g["accuracy_user"]))
    cats = Counter(r["categoria_errore"] for r in sb.table("errori_utenti").select("categoria_errore").eq("user_email", u["email"]).execute().data if r["categoria_errore"])
    # un grafico per account con una serie per ritmo, un punto al giorno (l'ultimo rating del giorno)
    order = ["bullet", "blitz", "rapid", "classical", "daily", "other"]
    accounts = {}
    for (src, uname, sp), days in rating.items():
        accounts.setdefault((src, uname), []).append((sp, days))
    rating_out = [{"source": src, "username": uname,
                   "series": [{"speed": sp, "points": [{"d": d_, "r": r_} for d_, r_ in sorted(days.items())]}
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


@app.post("/sync")
def sync(bg: BackgroundTasks, u=Depends(current_user)):
    tier = tier_of(u["email"])
    imported = sync_user(u["email"])
    limit = 3 if tier == "Free" else 8
    bg.add_task(analyze_pending, u["email"], limit)
    pending = sb.table("games").select("id", count="exact").eq("user_email", u["email"]).is_("analyzed_at", "null").not_.is_("user_color", "null").execute().count or 0
    return {"imported": imported, "analyzing": min(limit, pending), "pending": pending}


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
