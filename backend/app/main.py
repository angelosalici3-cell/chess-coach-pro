import datetime
import os

import stripe
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client

from core.plans import get_plan, stripe_price_id

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

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
    if err.get("spiegazione"):  # già generata: non consuma quota
        return {"lesson": err["spiegazione"], "cached": True}
    if not sb.rpc("consume_gm_lesson", {"p_email": u["email"]}).execute().data:
        raise HTTPException(402, "quota_exhausted")
    try:
        text = gm_lesson(err, body.lang)
    except Exception:
        sb.rpc("refund_gm_lesson", {"p_email": u["email"]}).execute()  # se il GM non risponde, la lezione non conta
        raise HTTPException(502, "gm_failed")
    sb.table("errori_utenti").update({"spiegazione": text}).eq("id", error_id).execute()
    return {"lesson": text, "cached": False}


# ---------- Stripe ----------
class CheckoutIn(BaseModel):
    plan: str


@app.post("/billing/checkout")
def checkout(body: CheckoutIn, u=Depends(current_user)):
    if body.plan not in ("Plus", "Pro", "Elite"):
        raise HTTPException(400, "invalid_plan")
    row = sb.table("config_utenti").select("stripe_customer_id").eq("user_email", u["email"]).limit(1).execute().data
    cust = row[0].get("stripe_customer_id") if row else None
    args = dict(
        mode="subscription", line_items=[{"price": stripe_price_id(body.plan), "quantity": 1}],
        success_url=f"{FRONTEND_URL}/?checkout=success", cancel_url=f"{FRONTEND_URL}/?checkout=cancel",
        allow_promotion_codes=True, metadata={"email": u["email"], "plan": body.plan})
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
    return {"url": stripe.billing_portal.Session.create(customer=row[0]["stripe_customer_id"], return_url=FRONTEND_URL).url}


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
