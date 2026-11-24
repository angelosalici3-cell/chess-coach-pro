"""Studio: area riservata a creator (solo numeri aggregati, mai email degli iscritti) e a chi gestisce l'app.
I compensi seguono il business plan: profili (nano/standard/partner/retention), conferma a 30 giorni, 12 mesi per abbonato,
tetto percentuale sul margine generato (con IVA indetraibile se il creator non è in forfettario o occasionale)."""
import datetime
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.plans import PLANS

from .auth import current_user
from .db import sb
from .promo import PromoIn, admin_create, get_code, is_admin, norm

router = APIRouter()

CONFIRM_DAYS = 30
ATTR_MONTHS = 12
VAT = 0.22
FEE_PCT, FEE_FIX, VAR_SUB = 0.0246, 0.25, 0.25          # stime del business plan
TAX_COEFF, TAX_SUBST, TAX_INPS = 0.67, 0.05, 0.2607     # forfettario: da confermare col commercialista
PROFILES = {   # cpa: × primo canone mensile; share: % incasso netto; ret: moltiplicatore premi a 3/6/12 mesi; perf: premio annuale
    "nano": dict(cpa=1.2, share=0.0, ret=0.0, perf=False),
    "standard": dict(cpa=0.6, share=0.10, ret=0.0, perf=False),
    "partner": dict(cpa=0.0, share=0.07, ret=0.7, perf=True),
    "retention": dict(cpa=0.0, share=0.0, ret=1.0, perf=False),
}
RET_STEPS = [(3, 90, 0.2), (6, 180, 0.4), (12, 360, 0.8)]   # (mesi coperti, giorni dal primo pagamento, quota del canone)
PERF_TIERS = [(8000, 0.03), (3000, 0.02)]
REGIMES = ("forfettario", "ordinario", "occasionale", "estero")


def creator_of(email: str) -> dict | None:
    try:
        r = sb.table("creators").select("*").eq("email", email.lower()).eq("active", True).limit(1).execute().data
        return r[0] if r else None
    except Exception:
        return None


def role_of(email: str) -> str | None:
    return "admin" if is_admin(email) else ("creator" if creator_of(email) else None)


def _d(s) -> datetime.datetime:
    return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00")).replace(tzinfo=None)


def vat_factor(regime: str | None) -> float:
    """Costo reale per EloRise di 1 € di compenso: l'IVA non si detrae in forfettario."""
    return 1 + VAT if regime in ("ordinario", "estero") else 1.0


def tax_complete(c: dict) -> bool:
    return bool(c.get("regime") in REGIMES and (c.get("tax_id") or "").strip() and (c.get("iban") or "").strip())


def settle(c: dict, events: list[dict], now: datetime.datetime | None = None) -> dict:
    """Calcola statistiche e compensi di un creator dagli eventi del suo codice."""
    now = now or datetime.datetime.now()
    rule = PROFILES.get(c.get("profile") or "nano", PROFILES["nano"])
    clicks = sum(e["kind"] == "click" for e in events)
    signups = sum(e["kind"] == "signup" for e in events)
    users: dict = {}
    for e in sorted(events, key=lambda e: e["created_at"]):
        if e["kind"] in ("paid", "renewal", "refund") and e.get("user_email"):
            users.setdefault(e["user_email"], []).append(e)
    cpa = share = ret = rev_all = refunds = 0.0
    confirmed = payers = 0
    pay_count = sub_months = 0.0
    window_rev = 0.0
    for ev in users.values():
        pos = [e for e in ev if e["kind"] in ("paid", "renewal") and float(e["amount"] or 0) > 0]
        if not pos:
            continue
        payers += 1
        t0 = _d(pos[0]["created_at"])
        plan = PLANS.get(pos[0].get("plan") or "Plus") or PLANS["Plus"]
        end = t0 + datetime.timedelta(days=30 * ATTR_MONTHS)
        net = covered = 0.0
        for e in ev:
            a, t = float(e["amount"] or 0), _d(e["created_at"])
            rev_all += a if a > 0 else 0
            refunds += -a if a < 0 else 0
            if t <= end:
                net += a
            if e["kind"] in ("paid", "renewal") and a > 0:
                pay_count += 1
                m = 12 if (plan.price_year_eur and a >= 0.6 * plan.price_year_eur) else 1
                covered += m; sub_months += m
        window_rev += max(0.0, net)
        age = (now - t0).days
        ok = age >= CONFIRM_DAYS and net > 0.5 * float(pos[0]["amount"])
        if not ok:
            continue
        confirmed += 1
        cpa += rule["cpa"] * plan.price_eur
        share += rule["share"] * max(0.0, net)
        for months, days, frac in RET_STEPS:
            if rule["ret"] and age >= days and covered >= months:
                ret += rule["ret"] * frac * plan.price_eur
    net_rev = rev_all - refunds
    perf_pct = next((p for th, p in PERF_TIERS if window_rev >= th), 0.0) if rule["perf"] else 0.0
    perf_amount = perf_pct * window_rev
    created = _d(c["created_at"]) if c.get("created_at") else now
    perf_due = perf_amount if (now - created).days >= 365 else 0.0     # il premio annuale matura dopo 12 mesi di collaborazione
    margin = net_rev * (1 - FEE_PCT) - FEE_FIX * pay_count - VAR_SUB * sub_months      # margine generato dai suoi abbonati
    factor = vat_factor(c.get("regime"))
    raw = cpa + share + ret + perf_due
    cap_net = max(0.0, (c.get("cap_pct") or 20) / 100 * margin / factor)
    earned = min(raw, cap_net)
    return {"clicks": clicks, "signups": signups, "payers": payers, "confirmed": confirmed, "revenue": round(net_rev, 2), "margin": round(margin, 2),
            "cpa": round(cpa, 2), "share": round(share, 2), "retention": round(ret, 2), "perf_pending": round(perf_amount - perf_due, 2), "perf": round(perf_due, 2),
            "raw": round(raw, 2), "cap": round(cap_net, 2), "capped": raw > cap_net, "earned": round(earned, 2), "cost_total": round(earned * factor, 2),
            "vat_extra": round(earned * (factor - 1), 2), "perf_pct": perf_pct, "window_rev": round(window_rev, 2), "vat_factor": factor}


def _events(code: str) -> list[dict]:
    return sb.table("promo_events").select("kind,user_email,plan,amount,created_at").eq("code", code).limit(100000).execute().data or []


def _series(events: list[dict], weeks: int = 12) -> list[dict]:
    today = datetime.date.today()
    mon = today - datetime.timedelta(days=today.weekday())
    start = [mon - datetime.timedelta(days=7 * i) for i in range(weeks - 1, -1, -1)]
    out = [{"w": d.isoformat(), "clicks": 0, "signups": 0} for d in start]
    for e in events:
        if e["kind"] in ("click", "signup"):
            idx = (_d(e["created_at"]).date() - start[0]).days // 7
            if 0 <= idx < weeks:
                out[idx]["clicks" if e["kind"] == "click" else "signups"] += 1
    return out


def _paid(code: str) -> tuple[float, float, list]:
    rows = sb.table("creator_payouts").select("amount,vat_amount,note,doc_ref,paid_at").eq("code", code).order("paid_at", desc=True).execute().data or []
    return sum(float(r["amount"]) for r in rows), sum(float(r["vat_amount"] or 0) for r in rows), rows


def _payload(c: dict) -> dict:
    code = c["code"]
    pc = get_code(code, only_active=False)
    if not pc:
        raise HTTPException(404, "code_not_found")
    ev = _events(code)
    s = settle(c, ev)
    paid, paid_vat, pays = _paid(code)
    return {"name": c["name"], "code": code, "profile": c.get("profile") or "nano", "cap_pct": c.get("cap_pct") or 20, "regime": c.get("regime"), "country": c.get("country"),
            "invoice_mode": c.get("invoice_mode"), "tax_ok": tax_complete(c), "discount_pct": pc["discount_pct"], "months": pc["months"], "active": pc["active"],
            **s, "paid": round(paid, 2), "due": round(s["earned"] - paid, 2), "payouts": pays[:20], "series": _series(ev),
            "confirm_days": CONFIRM_DAYS, "attr_months": ATTR_MONTHS}


def studio_user(u=Depends(current_user)):
    r = role_of(u["email"])
    if not r:
        raise HTTPException(403, "forbidden")
    return {**u, "role": r}


def admin_only(u=Depends(studio_user)):
    if u["role"] != "admin":
        raise HTTPException(403, "forbidden")
    return u


@router.get("/studio/me")
def me(u=Depends(studio_user)):
    c = creator_of(u["email"])
    return {"role": u["role"], "name": c["name"] if c else None, "code": c["code"] if c else None}


@router.get("/studio/creator")
def creator_view(code: str | None = None, u=Depends(studio_user)):
    if u["role"] == "admin" and code:
        rows = sb.table("creators").select("*").eq("code", norm(code)).limit(1).execute().data
        if not rows:
            raise HTTPException(404, "no_creator")
        return _payload(rows[0])
    c = creator_of(u["email"])
    if not c:
        raise HTTPException(404, "no_creator")
    return _payload(c)


class TaxIn(BaseModel):
    regime: str
    tax_id: str
    country: str = "IT"
    iban: str
    invoice_mode: str = ""


@router.post("/studio/creator/tax")
def save_tax(body: TaxIn, u=Depends(studio_user)):
    c = creator_of(u["email"])
    if not c:
        raise HTTPException(403, "forbidden")
    if body.regime not in REGIMES:
        raise HTTPException(400, "Scegli il regime fiscale")
    tid, iban = body.tax_id.strip().upper(), re.sub(r"\s+", "", body.iban).upper()
    if len(tid) < 11 or not re.match(r"^[A-Z0-9]+$", tid):
        raise HTTPException(400, "Codice fiscale o partita IVA non valido")
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$", iban):
        raise HTTPException(400, "IBAN non valido")
    sb.table("creators").update({"regime": body.regime, "tax_id": tid, "country": body.country.strip().upper()[:2] or "IT", "iban": iban,
                                 "invoice_mode": body.invoice_mode.strip()[:40] or None, "tax_updated_at": datetime.datetime.utcnow().isoformat()}).eq("email", c["email"]).execute()
    return {"ok": True}


class CreatorIn(BaseModel):
    email: str
    name: str
    code: str
    profile: str = "nano"
    cap_pct: int = 20
    discount_pct: int = 20
    months: int = 1


@router.post("/studio/admin/creators")
def add_creator(body: CreatorIn, u=Depends(admin_only)):
    """Abilita un'email e (se serve) crea il codice sconto. Il compenso è deciso dal profilo, non dal codice (commissione codice = 0)."""
    if body.profile not in PROFILES or not (0 <= body.cap_pct <= 60):
        raise HTTPException(400, "Profilo o tetto non validi")
    code = norm(body.code)
    if not get_code(code, only_active=False):
        admin_create(PromoIn(code=code, creator=body.name, discount_pct=body.discount_pct, months=body.months, commission_pct=0), u)
    sb.table("creators").upsert({"email": body.email.strip().lower(), "name": body.name.strip(), "code": code, "profile": body.profile, "cap_pct": body.cap_pct, "active": True}, on_conflict="email").execute()
    return {"ok": True}


class CreatorEdit(BaseModel):
    profile: str | None = None
    cap_pct: int | None = None
    active: bool | None = None


@router.post("/studio/admin/creators/{email}")
def edit_creator(email: str, body: CreatorEdit, u=Depends(admin_only)):
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if "profile" in upd and upd["profile"] not in PROFILES:
        raise HTTPException(400, "Profilo non valido")
    if "cap_pct" in upd and not (0 <= upd["cap_pct"] <= 60):
        raise HTTPException(400, "Tetto non valido")
    if upd:
        sb.table("creators").update(upd).eq("email", email.lower()).execute()
    return {"ok": True}


class PayoutIn(BaseModel):
    code: str
    amount: float          # compenso netto, senza IVA
    note: str = ""
    doc_ref: str = ""


@router.post("/studio/admin/payouts")
def add_payout(body: PayoutIn, u=Depends(admin_only)):
    rows = sb.table("creators").select("*").eq("code", norm(body.code)).limit(1).execute().data
    if not rows:
        raise HTTPException(404, "no_creator")
    c = rows[0]
    if not tax_complete(c):
        raise HTTPException(400, "Il creator non ha ancora inserito i dati fiscali")
    if body.amount <= 0:
        raise HTTPException(400, "Importo non valido")
    p = _payload(c)
    if body.amount > p["due"] + 0.01:
        raise HTTPException(400, f"Supera il maturato da pagare ({p['due']:.2f} €)")
    vat = round(body.amount * VAT, 2) if c["regime"] in ("ordinario", "estero") else 0.0
    sb.table("creator_payouts").insert({"code": c["code"], "amount": body.amount, "vat_amount": vat, "note": body.note.strip() or None, "doc_ref": body.doc_ref.strip() or None}).execute()
    return {"ok": True, "vat": vat}


class CostIn(BaseModel):
    label: str
    amount: float
    recurring: bool = True
    month: str            # YYYY-MM


@router.get("/studio/admin/costs")
def costs(u=Depends(admin_only)):
    return {"costs": sb.table("admin_costs").select("*").order("month", desc=True).execute().data or []}


@router.post("/studio/admin/costs")
def add_cost(body: CostIn, u=Depends(admin_only)):
    if body.amount < 0 or not re.match(r"^\d{4}-\d{2}$", body.month) or not body.label.strip():
        raise HTTPException(400, "Dati non validi")
    sb.table("admin_costs").insert({"label": body.label.strip(), "amount": body.amount, "recurring": body.recurring, "month": body.month + "-01"}).execute()
    return {"ok": True}


@router.post("/studio/admin/costs/{cid}/end")
def end_cost(cid: int, u=Depends(admin_only)):
    sb.table("admin_costs").update({"ended": datetime.date.today().replace(day=1).isoformat()}).eq("id", cid).execute()
    return {"ok": True}


@router.get("/studio/admin")
def admin_view(u=Depends(admin_only)):
    rows = sb.table("creators").select("*").order("created_at", desc=True).execute().data or []
    out = []
    for c in rows:
        p = _payload(c)
        out.append({"email": c["email"], "active": c["active"], **{k: p[k] for k in ("name", "code", "profile", "cap_pct", "regime", "tax_ok", "clicks", "signups", "payers", "confirmed", "revenue", "margin", "raw", "cap", "capped", "earned", "cost_total", "paid", "due")}})
    tot = {k: round(sum(x[k] for x in out), 2) for k in ("clicks", "signups", "payers", "revenue", "margin", "earned", "cost_total", "paid", "due")}
    return {"creators": out, "totals": tot, "profiles": list(PROFILES)}


def _month_keys(n: int = 12) -> list[str]:
    d = datetime.date.today().replace(day=1)
    out = []
    for _ in range(n):
        out.append(d.strftime("%Y-%m"))
        d = (d - datetime.timedelta(days=1)).replace(day=1)
    return out[::-1]


@router.get("/studio/admin/analytics")
def analytics(u=Depends(admin_only)):
    months = _month_keys(12)
    pay = sb.table("payments").select("kind,amount,plan,code,created_at").gte("created_at", months[0] + "-01").limit(100000).execute().data or []
    m = {k: dict(m=k, revenue=0.0, donations=0.0, refunds=0.0, disputes=0.0, payments=0, new_payers=0) for k in months}
    for p in pay:
        k = str(p["created_at"])[:7]
        if k not in m:
            continue
        a = float(p["amount"])
        if p["kind"] in ("payment", "renewal"):
            m[k]["revenue"] += a; m[k]["payments"] += 1; m[k]["new_payers"] += p["kind"] == "payment"
        elif p["kind"] == "donation":
            m[k]["donations"] += a; m[k]["payments"] += 1
        elif p["kind"] == "refund":
            m[k]["refunds"] += -a
        elif p["kind"] == "dispute":
            m[k]["disputes"] += -a
    costs_rows = sb.table("admin_costs").select("*").execute().data or []
    po = sb.table("creator_payouts").select("amount,vat_amount,paid_at").execute().data or []
    for k in months:
        first = datetime.date.fromisoformat(k + "-01")
        fixed = 0.0
        for c in costs_rows:
            start = datetime.date.fromisoformat(str(c["month"])[:10])
            end = datetime.date.fromisoformat(str(c["ended"])[:10]) if c.get("ended") else None
            if c["recurring"]:
                if start <= first and (not end or first < end):
                    fixed += float(c["amount"])
            elif start.strftime("%Y-%m") == k:
                fixed += float(c["amount"])
        r = m[k]
        gross = r["revenue"] + r["donations"]
        r["fees"] = round(gross * FEE_PCT + FEE_FIX * r["payments"], 2)
        r["variable"] = round(VAR_SUB * (r["payments"] - (1 if r["donations"] and not r["revenue"] else 0)), 2)
        r["fixed"] = round(fixed, 2)
        r["creators"] = round(sum(float(x["amount"]) + float(x["vat_amount"] or 0) for x in po if str(x["paid_at"])[:7] == k), 2)
        r["tax"] = round(max(0.0, gross - r["refunds"]) * TAX_COEFF * (TAX_SUBST + TAX_INPS), 2)
        r["profit"] = round(gross - r["refunds"] - r["disputes"] - r["fees"] - r["variable"] - r["fixed"] - r["creators"] - r["tax"], 2)
        for key in ("revenue", "donations", "refunds", "disputes"):
            r[key] = round(r[key], 2)
    cfg = sb.table("config_utenti").select("tier,subscription_status,updated_at").execute().data or []
    paying = [x for x in cfg if x["tier"] != "Free" and x.get("subscription_status") in ("active", "past_due", None)]
    by_tier = {t: sum(1 for x in paying if x["tier"] == t) for t in ("Plus", "Pro", "Elite")}
    mrr = sum(by_tier[t] * PLANS[t].price_eur for t in by_tier)
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat()
    canceled = sum(1 for x in cfg if x.get("subscription_status") == "canceled" and str(x.get("updated_at") or "") >= since)
    fixed_now = m[months[-1]]["fixed"]
    contrib = (mrr / len(paying) if paying else 7.19) * (1 - FEE_PCT) - FEE_FIX - VAR_SUB
    crows = sb.table("creators").select("*").execute().data or []
    cr_total = sum(settle(c, _events(c["code"]))["cost_total"] for c in crows)
    return {"months": [m[k] for k in months], "subs": {"by_tier": by_tier, "total": len(paying), "mrr": round(mrr, 2), "free": len(cfg) - len(paying), "canceled_30d": canceled,
            "churn_30d": round(100 * canceled / (len(paying) + canceled), 1) if (len(paying) + canceled) else 0, "arpu": round(mrr / len(paying), 2) if paying else 0},
            "breakeven": {"fixed": fixed_now, "contribution": round(contrib, 2), "subs_needed": round(fixed_now / contrib, 1) if contrib > 0 else None},
            "creators_cost_accrued": round(cr_total, 2)}
