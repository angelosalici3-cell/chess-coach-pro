"""Codici promo per creatori e community: link ?ref=CODICE, sconto su Stripe e tracciamento
di clic, iscrizioni, primi pagamenti e rinnovi. Tutto tollera le tabelle mancanti (008 non eseguito)."""
import os
import re

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import current_user
from .db import sb

router = APIRouter()
CODE_RE = re.compile(r"^[A-Z0-9_-]{3,24}$")


def norm(code: str | None) -> str:
    return (code or "").strip().upper()


def is_admin(email: str) -> bool:
    return email.lower() in {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}


def admin_user(u=Depends(current_user)):
    if not is_admin(u["email"]):
        raise HTTPException(403, "forbidden")
    return u


def get_code(code: str, only_active: bool = True) -> dict | None:
    q = sb.table("promo_codes").select("*").eq("code", norm(code))
    if only_active:
        q = q.eq("active", True)
    rows = q.limit(1).execute().data
    return rows[0] if rows else None


def record(code: str, kind: str, email: str | None = None, plan: str | None = None, amount: float = 0, ref_id: str | None = None) -> None:
    try:
        sb.table("promo_events").insert({"code": code, "kind": kind, "user_email": email, "plan": plan, "amount": amount, "ref_id": ref_id}).execute()
    except Exception:  # duplicato (webhook ripetuto) o tabella assente
        pass


def attribution(email: str) -> str | None:
    """Codice con cui l'utente è arrivato (prima iscrizione), se c'è."""
    try:
        rows = sb.table("promo_events").select("code").eq("user_email", email).eq("kind", "signup").order("created_at").limit(1).execute().data
        return rows[0]["code"] if rows else None
    except Exception:
        return None


def promo_for(email: str) -> dict | None:
    """Per /me: codice attivo dell'utente e sconto previsto al checkout."""
    try:
        code = attribution(email)
        pc = get_code(code) if code else None
        if not pc:
            return None
        return {"code": pc["code"], "discount_pct": pc["discount_pct"], "months": pc["months"]}
    except Exception:
        return None


def checkout_discount(email: str) -> dict | None:
    try:
        code = attribution(email)
        pc = get_code(code) if code else None
        if pc and pc.get("stripe_promotion_id"):
            return {"code": pc["code"], "pid": pc["stripe_promotion_id"]}
    except Exception:
        pass
    return None


def _code_from_session(session_id: str) -> str | None:
    """Codice digitato nella pagina di pagamento Stripe (anche senza link)."""
    try:
        s = stripe.checkout.Session.retrieve(session_id, expand=["total_details.breakdown"])
        for d in s["total_details"]["breakdown"]["discounts"]:
            pc = d["discount"].get("promotion_code")
            if pc:
                code = norm(pc if isinstance(pc, str) and not pc.startswith("promo_") else stripe.PromotionCode.retrieve(pc)["code"])
                if get_code(code, only_active=False):
                    return code
    except Exception:
        pass
    return None


def attribute_checkout(obj: dict, email: str, plan: str) -> None:
    try:
        code = norm((obj.get("metadata") or {}).get("promo")) or _code_from_session(obj["id"]) or attribution(email)
        if not code or not get_code(code, only_active=False):
            return
        if not attribution(email):
            record(code, "signup", email)
        record(code, "paid", email, plan, (obj.get("amount_total") or 0) / 100, obj["id"])
    except Exception:
        pass


def attribute_renewal(invoice: dict) -> None:
    try:
        if invoice.get("billing_reason") != "subscription_cycle":
            return
        rows = sb.table("config_utenti").select("user_email,tier").eq("stripe_customer_id", invoice["customer"]).limit(1).execute().data
        if not rows:
            return
        email = rows[0]["user_email"]
        code = attribution(email)
        if code:
            record(code, "renewal", email, rows[0].get("tier"), (invoice.get("amount_paid") or 0) / 100, invoice["id"])
    except Exception:
        pass


# ---------- Pubblici / utente ----------
class CodeIn(BaseModel):
    code: str


@router.post("/promo/click")
def click(body: CodeIn):
    if get_code(body.code):
        record(norm(body.code), "click")
    return {"ok": True}


@router.post("/promo/claim")
def claim(body: CodeIn, u=Depends(current_user)):
    code = norm(body.code)
    pc = get_code(code)
    if not pc:
        return {"ok": False}
    if not attribution(u["email"]):
        record(code, "signup", u["email"])
    return {"ok": True, **(promo_for(u["email"]) or {})}


# ---------- Amministrazione ----------
class PromoIn(BaseModel):
    code: str
    creator: str
    channel: str = ""
    discount_pct: int = 0
    months: int = 1
    commission_pct: int = 0
    note: str = ""


class ActiveIn(BaseModel):
    active: bool


def _stripe_promo(code: str, pct: int, months: int):
    kw = {"duration": "repeating", "duration_in_months": months} if months > 1 else {"duration": "once"}
    c = stripe.Coupon.create(percent_off=pct, name=f"Promo {code}", **kw)
    try:
        p = stripe.PromotionCode.create(coupon=c.id, code=code)
    except Exception:  # versioni recenti dell'API Stripe
        p = stripe.PromotionCode.create(promotion={"type": "coupon", "coupon": c.id}, code=code)
    return c.id, p.id


@router.get("/admin/promo")
def admin_list(u=Depends(admin_user)):
    codes = sb.table("promo_codes").select("*").order("created_at", desc=True).execute().data or []
    ev = sb.table("promo_events").select("code,kind,user_email,amount").limit(100000).execute().data or []
    agg: dict[str, dict] = {}
    for e in ev:
        a = agg.setdefault(e["code"], {"clicks": 0, "signups": 0, "paid": set(), "revenue": 0.0})
        if e["kind"] == "click":
            a["clicks"] += 1
        elif e["kind"] == "signup":
            a["signups"] += 1
        elif e["kind"] in ("paid", "renewal"):
            a["revenue"] += float(e["amount"] or 0)
            if e.get("user_email"):
                a["paid"].add(e["user_email"])
    out = []
    for c in codes:
        a = agg.get(c["code"], {"clicks": 0, "signups": 0, "paid": set(), "revenue": 0.0})
        out.append({**c, "clicks": a["clicks"], "signups": a["signups"], "payers": len(a["paid"]),
                    "revenue": round(a["revenue"], 2), "commission": round(a["revenue"] * c["commission_pct"] / 100, 2)})
    return {"codes": out}


@router.post("/admin/promo")
def admin_create(body: PromoIn, u=Depends(admin_user)):
    code = norm(body.code)
    if not CODE_RE.match(code):
        raise HTTPException(400, "Codice: 3-24 caratteri, solo lettere, numeri, - e _")
    if not (0 <= body.discount_pct <= 100 and 1 <= body.months <= 12 and 0 <= body.commission_pct <= 100):
        raise HTTPException(400, "Valori non validi")
    if get_code(code, only_active=False):
        raise HTTPException(409, "Codice già esistente")
    coupon_id = promo_id = None
    if body.discount_pct > 0:
        try:
            coupon_id, promo_id = _stripe_promo(code, body.discount_pct, body.months)
        except Exception as e:
            raise HTTPException(502, f"Stripe: {e}")
    sb.table("promo_codes").insert({
        "code": code, "creator": body.creator.strip(), "channel": body.channel.strip() or None,
        "discount_pct": body.discount_pct, "months": body.months, "commission_pct": body.commission_pct,
        "stripe_coupon_id": coupon_id, "stripe_promotion_id": promo_id, "note": body.note.strip() or None}).execute()
    return {"ok": True, "code": code}


@router.post("/admin/promo/{code}/active")
def admin_active(code: str, body: ActiveIn, u=Depends(admin_user)):
    pc = get_code(code, only_active=False)
    if not pc:
        raise HTTPException(404, "not_found")
    sb.table("promo_codes").update({"active": body.active}).eq("code", pc["code"]).execute()
    if pc.get("stripe_promotion_id"):
        try:
            stripe.PromotionCode.modify(pc["stripe_promotion_id"], active=body.active)
        except Exception:
            pass
    return {"ok": True}
