"""Studio: area riservata ai creator (vedono SOLO i propri numeri aggregati, mai email o nomi degli iscritti) e a chi gestisce l'app.
Guadagno del creator = commissione % sugli incassi del suo codice + bonus a soglie di abbonati paganti confermati."""
import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import current_user
from .db import sb
from .promo import PromoIn, admin_create, get_code, is_admin, norm

router = APIRouter()
CONFIRM_DAYS = 30   # un pagante conta per i bonus dopo 30 giorni: protegge da rimborsi e abusi
MILESTONES = [(5, 25), (15, 100), (40, 300), (100, 1000)]   # abbonati confermati -> bonus in euro, una tantum


def creator_of(email: str) -> dict | None:
    try:
        r = sb.table("creators").select("*").eq("email", email.lower()).eq("active", True).limit(1).execute().data
        return r[0] if r else None
    except Exception:
        return None


def role_of(email: str) -> str | None:
    return "admin" if is_admin(email) else ("creator" if creator_of(email) else None)


def _stats(code: str, weeks: int = 12) -> dict:
    ev = sb.table("promo_events").select("kind,user_email,amount,created_at").eq("code", code).limit(100000).execute().data or []
    today = datetime.date.today()
    mon = today - datetime.timedelta(days=today.weekday())
    start = [mon - datetime.timedelta(days=7 * i) for i in range(weeks - 1, -1, -1)]
    series = [{"w": d.isoformat(), "clicks": 0, "signups": 0} for d in start]
    clicks = signups = 0
    revenue = 0.0
    first_paid: dict = {}
    for e in ev:
        d = datetime.datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")).replace(tzinfo=None)
        k = e["kind"]
        if k in ("click", "signup"):
            clicks += k == "click"; signups += k == "signup"
            idx = (d.date() - start[0]).days // 7
            if 0 <= idx < weeks:
                series[idx]["clicks" if k == "click" else "signups"] += 1
        elif k in ("paid", "renewal"):
            revenue += float(e["amount"] or 0)
            if e.get("user_email") and (e["user_email"] not in first_paid or d < first_paid[e["user_email"]]):
                first_paid[e["user_email"]] = d
    limit = datetime.datetime.now() - datetime.timedelta(days=CONFIRM_DAYS)
    confirmed = sum(1 for d in first_paid.values() if d <= limit)
    return {"clicks": clicks, "signups": signups, "payers": len(first_paid), "confirmed": confirmed, "revenue": round(revenue, 2), "series": series}


def _money(code_row: dict, st: dict) -> dict:
    commission = round(st["revenue"] * code_row["commission_pct"] / 100, 2)
    bonus = sum(b for n, b in MILESTONES if st["confirmed"] >= n)
    paid = sum(float(p["amount"]) for p in (sb.table("creator_payouts").select("amount").eq("code", code_row["code"]).execute().data or []))
    return {"commission": commission, "bonus": bonus, "earned": round(commission + bonus, 2), "paid": round(paid, 2), "due": round(commission + bonus - paid, 2)}


def _payload(code: str, name: str) -> dict:
    pc = get_code(code, only_active=False)
    if not pc:
        raise HTTPException(404, "code_not_found")
    st = _stats(code)
    mo = _money(pc, st)
    nxt = next(((n, b) for n, b in MILESTONES if st["confirmed"] < n), None)
    pays = sb.table("creator_payouts").select("amount,note,paid_at").eq("code", code).order("paid_at", desc=True).limit(20).execute().data or []
    return {"name": name, "code": code, "discount_pct": pc["discount_pct"], "months": pc["months"], "commission_pct": pc["commission_pct"], "active": pc["active"],
            **st, **mo, "milestones": [{"n": n, "bonus": b, "reached": st["confirmed"] >= n} for n, b in MILESTONES], "next": {"n": nxt[0], "bonus": nxt[1]} if nxt else None,
            "payouts": pays, "confirm_days": CONFIRM_DAYS}


def studio_user(u=Depends(current_user)):
    r = role_of(u["email"])
    if not r:
        raise HTTPException(403, "forbidden")
    return {**u, "role": r}


@router.get("/studio/me")
def me(u=Depends(studio_user)):
    c = creator_of(u["email"])
    return {"role": u["role"], "name": c["name"] if c else None, "code": c["code"] if c else None}


@router.get("/studio/creator")
def creator_view(code: str | None = None, u=Depends(studio_user)):
    if u["role"] == "admin" and code:
        row = sb.table("creators").select("name").eq("code", norm(code)).limit(1).execute().data
        return _payload(norm(code), row[0]["name"] if row else norm(code))
    c = creator_of(u["email"])
    if not c:
        raise HTTPException(404, "no_creator")
    return _payload(c["code"], c["name"])


@router.get("/studio/admin")
def admin_view(u=Depends(studio_user)):
    if u["role"] != "admin":
        raise HTTPException(403, "forbidden")
    rows = sb.table("creators").select("*").order("created_at", desc=True).execute().data or []
    out = []
    for c in rows:
        p = _payload(c["code"], c["name"])
        out.append({"email": c["email"], "active": c["active"], **{k: p[k] for k in ("name", "code", "clicks", "signups", "payers", "confirmed", "revenue", "commission", "bonus", "earned", "paid", "due")}})
    tot = {k: round(sum(x[k] for x in out), 2) for k in ("clicks", "signups", "payers", "revenue", "earned", "paid", "due")}
    return {"creators": out, "totals": tot}


class CreatorIn(BaseModel):
    email: str
    name: str
    code: str
    discount_pct: int = 20
    months: int = 1
    commission_pct: int = 20


@router.post("/studio/admin/creators")
def add_creator(body: CreatorIn, u=Depends(studio_user)):
    """Crea (se serve) il codice sconto e abilita l'email del creator allo Studio."""
    if u["role"] != "admin":
        raise HTTPException(403, "forbidden")
    code = norm(body.code)
    if not get_code(code, only_active=False):
        admin_create(PromoIn(code=code, creator=body.name, discount_pct=body.discount_pct, months=body.months, commission_pct=body.commission_pct), u)
    sb.table("creators").upsert({"email": body.email.strip().lower(), "name": body.name.strip(), "code": code, "active": True}, on_conflict="email").execute()
    return {"ok": True}


class PayoutIn(BaseModel):
    code: str
    amount: float
    note: str = ""


@router.post("/studio/admin/payouts")
def add_payout(body: PayoutIn, u=Depends(studio_user)):
    if u["role"] != "admin":
        raise HTTPException(403, "forbidden")
    if body.amount <= 0:
        raise HTTPException(400, "invalid_amount")
    sb.table("creator_payouts").insert({"code": norm(body.code), "amount": body.amount, "note": body.note.strip() or None}).execute()
    return {"ok": True}
