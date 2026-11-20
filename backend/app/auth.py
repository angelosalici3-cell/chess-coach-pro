"""Autenticazione e piano dell'utente (condivisi da main e dai moduli)."""
import datetime

from fastapi import Header, HTTPException

from . import cache
from .db import sb


def current_user(authorization: str = Header(None)):
    """Verifica il token Supabase inviato dal browser. Ogni query è poi filtrata per email."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing_token")
    token = authorization[7:]
    hit = cache.get(("tok", token))  # stesso token già verificato da pochi secondi: niente nuova chiamata a Supabase
    if hit:
        return hit
    try:
        u = sb.auth.get_user(token).user
    except Exception:
        raise HTTPException(401, "invalid_token")
    if not u or not u.email:
        raise HTTPException(401, "invalid_token")
    out = {"id": u.id, "email": u.email, "created_at": str(getattr(u, "created_at", "") or ""),
           "confirmed": bool(getattr(u, "email_confirmed_at", None))}
    cache.put(("tok", token), out, 120)
    return out


def tier_from(cfg: dict | None) -> str:
    """Piano effettivo dalla riga config_utenti (Free se manca o è scaduto)."""
    if not cfg:
        return "Free"
    tier, exp = cfg["tier"], cfg.get("data_scadenza")
    if tier != "Free" and exp and datetime.date.fromisoformat(exp) < datetime.date.today():
        return "Free"
    return tier


def tier_of(email: str) -> str:
    rows = sb.table("config_utenti").select("tier,data_scadenza").eq("user_email", email).limit(1).execute().data
    return tier_from(rows[0] if rows else None)
