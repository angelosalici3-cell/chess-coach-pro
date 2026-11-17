"""Autenticazione e piano dell'utente (condivisi da main e dai moduli)."""
import datetime

from fastapi import Header, HTTPException

from .db import sb


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
