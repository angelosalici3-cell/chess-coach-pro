import streamlit as st
from google import genai
from google.genai import types
import chess
import chess.svg
import chess.pgn
import pandas as pd
import json
import datetime
import io
import os
import time
import requests

try:
    import stripe
    HAS_STRIPE = True
except ImportError:
    HAS_STRIPE = False

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# --- CONFIGURAZIONE CENTRALIZZATA ---
MASTER_GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", "") # Usa anon per il client
STRIPE_SECRET_KEY = st.secrets.get("STRIPE_SECRET_KEY", "")
STRIPE_PRO_PRICE_ID = st.secrets.get("STRIPE_PRO_PRICE_ID", "")
STRIPE_DIAMOND_PRICE_ID = st.secrets.get("STRIPE_DIAMOND_PRICE_ID", "")
APP_BASE_URL = st.secrets.get("APP_BASE_URL", "http://localhost:8501")

if HAS_STRIPE and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

GEMINI_MODEL_NAME = "gemini-2.5-flash"

# ==========================================
# HELPERS: NORMALIZZAZIONE & UTILS
# ==========================================
def _canonical_platform(p):
    if not p: return None
    s = str(p).strip().lower().replace(".", "").replace("_", "").replace("-", "").replace(" ", "")
    return {"lichess": "lichess", "chesscom": "chesscom", "chess": "chesscom", "fide": "fide"}.get(s)

def _canonical_source(s):
    if not s: return "manual"
    v = str(s).strip().lower()
    return v if v in ("lichess", "chesscom", "manual", "pgn_upload") else "manual"

def _canonical_categoria(c):
    if not c: return "tactical"
    v = str(c).strip().lower()
    return v if v in ("tactical", "positional", "opening", "endgame", "time_trouble") else "tactical"

def _safe_date_str(raw):
    today = datetime.date.today().isoformat()
    if not raw: return today
    s = str(raw).strip().replace(".", "-").replace("/", "-")[:10]
    if "?" in s or "Live" in s or not s: return today
    try:
        datetime.date.fromisoformat(s)
        return s
    except Exception:
        return today

def _utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def _normalize_pgn_date(raw_date):
    if not raw_date or "?" in str(raw_date): return "Live"
    return str(raw_date).replace(".", "-")

def build_partita_id(headers):
    white = (headers.get("White", "Unknown") or "Unknown").strip()
    black = (headers.get("Black", "Unknown") or "Unknown").strip()
    date = _normalize_pgn_date(headers.get("Date", ""))
    return f"{white}_vs_{black}_{date}"

# ==========================================
# SUPABASE CLIENT
# ==========================================
def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY or "INSERISCI" in SUPABASE_URL:
        return None
    try:
        from supabase import create_client
        client = create_client(SUPABASE_URL.strip(), SUPABASE_KEY.strip())
        if "sb_access_token" in st.session_state and "sb_refresh_token" in st.session_state:
            client.auth.set_session(
                st.session_state["sb_access_token"],
                st.session_state["sb_refresh_token"],
            )
        return client
    except Exception:
        return None

st.set_page_config(page_title="Chess Coach Pro", layout="wide", page_icon="⚡", initial_sidebar_state="expanded")

# ==========================================
# PERSISTENZA UTENTE E CHECKOUT RETURN
# ==========================================
query_params = st.query_params

# Gestione del ritorno da Stripe
if "checkout" in query_params:
    status = query_params.get("checkout")
    if status == "success":
        st.toast("🎉 Pagamento completato! Attendi qualche secondo per l'attivazione del piano.")
    elif status == "cancel":
        st.toast("❌ Pagamento annullato.")
    # Rimuove il parametro dall'URL per non mostrarlo ad ogni refresh
    st.query_params.clear()
    time.sleep(1)
    st.rerun()

persisted_user = query_params.get("user_email", None)

for key, default in {
    'user': persisted_user, 'lang': 'it', 'profile_setup_done': bool(persisted_user),
    'nav_selection': "📊 Dashboard & Insights", 'theme_mode': 'Dark',
    'last_analyzed_pgn': None, 'current_board_ply': 0,
    'eval_history': None, 'storico_errori_locale': [], 'storico_rating_locale': [],
    'lezioni_gm_salvate': {}
}.items():
    if key not in st.session_state or st.session_state[key] is None:
        st.session_state[key] = default

if st.session_state.get('user') and query_params.get("user_email") != st.session_state['user']:
    st.query_params["user_email"] = st.session_state['user']

if 'goto_tab' in st.session_state and st.session_state['goto_tab']:
    st.session_state['nav_selection'] = st.session_state['goto_tab']
    del st.session_state['goto_tab']

st.components.v1.html("<script>setInterval(function(){fetch(window.location.href);},25000);</script>", height=0)

# ==========================================
# DB HELPERS
# ==========================================
def get_user_profiles(email):
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("profili_scacchi").select("*").eq("user_email", email).execute()
            if res.data: return res.data
        except Exception: pass
    return []

def add_user_profile(email, piattaforma, username):
    plat = _canonical_platform(piattaforma)
    if not plat: return False, f"Piattaforma non riconosciuta."
    if not username or not username.strip(): return False, "Username obbligatorio."
    tier = get_user_tier(email)
    limit = 1 if tier == "Free" else (2 if tier == "Plus" else (3 if tier == "Pro" else 5))
    if len(get_user_profiles(email)) >= limit: return False, f"Limite raggiunto per il piano {tier}."
    sb = get_supabase()
    if not sb: return False, "Supabase non connesso."
    try:
        sb.table("profili_scacchi").insert({"user_email": email, "piattaforma": plat, "username": username.strip()}).execute()
        return True, f"Profilo aggiunto!"
    except Exception as e:
        if "duplicate" in str(e).lower(): return False, f"Account già collegato."
        return False, f"Errore DB: {e}"

def delete_user_profile(profile_id):
    sb = get_supabase()
    if sb:
        try:
            sb.table("profili_scacchi").delete().eq("id", profile_id).execute()
            return True
        except Exception: pass
    return False

def get_user_tier(email):
    sb = get_supabase()
    if not sb or not email: return "Free"
    try:
        res = sb.table("config_utenti").select("tier, data_scadenza, subscription_status").eq("user_email", email).execute()
        if res.data:
            u = res.data[0]
            tier = u.get("tier", "Free") or "Free"
            scad = u.get("data_scadenza")
            if tier in ["Plus", "Pro", "Elite"] and scad:
                try: scad_date = datetime.date.fromisoformat(str(scad)[:10])
                except Exception: scad_date = None
                if scad_date and datetime.date.today() > scad_date:
                    sb.table("config_utenti").update({"tier": "Free", "data_scadenza": None, "subscription_status": "inactive", "updated_at": _utc_now_iso()}).eq("user_email", email).execute()
                    return "Free"
            return tier
    except Exception: pass
    return "Free"

def get_current_gm_usage(email, tier):
    if tier in ["Pro", "Elite"]: return "Illimitate"
    current_month = datetime.datetime.now().strftime("%Y-%m")
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("quota_usage").select("ai_analyses_used").eq("user_email", email).eq("quota_month", current_month).execute()
            if res.data:
                used = res.data[0].get("ai_analyses_used", 0)
                limit = 5 if tier == "Free" else 20
                return f"{used} / {limit} usate"
        except Exception: pass
    limit = 5 if tier == "Free" else 20
    return f"0 / {limit} usate"

def check_and_consume_gm_quota(email, tier):
    if tier in ["Pro", "Elite"]: return True, ""
    current_month = datetime.datetime.now().strftime("%Y-%m")
    limit = 5 if tier == "Free" else 20
    used = 0
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("quota_usage").select("ai_analyses_used").eq("user_email", email).eq("quota_month", current_month).execute()
            if res.data: used = res.data[0].get("ai_analyses_used", 0)
        except Exception: pass
    if used >= limit: return False, f"⚠️ Hai esaurito le {limit} analisi GM questo mese. Passa a un piano superiore!"
    if sb:
        try:
            existing = sb.table("quota_usage").select("*").eq("user_email", email).eq("quota_month", current_month).execute()
            if existing.data:
                sb.table("quota_usage").update({"ai_analyses_used": int(existing.data[0].get("ai_analyses_used", 0)) + 1}).eq("user_email", email).eq("quota_month", current_month).execute()
            else:
                sb.table("quota_usage").insert({"user_email": email, "quota_month": current_month, "ai_analyses_used": 1}).execute()
        except Exception: pass
    return True, ""

def registra_movimento_abbonamento(user_email, tier_precedente, tier_nuovo, azione, importo=0.0, stripe_id=None):
    sb = get_supabase()
    if not sb: return
    try:
        sb.table("storico_abbonamenti").insert({
            "user_email": user_email, "tier_precedente": tier_precedente, "tier_nuovo": tier_nuovo,
            "azione": azione, "importo": importo, "stripe_session_id": stripe_id,
        }).execute()
    except Exception: pass

def format_gm_lesson_html(raw_text):
    lines = raw_text.strip().split('\n')
    parts = []
    for line in lines:
        line_clean = line.strip()
        if not line_clean: continue
        low = line_clean.lower()
        if line_clean.startswith("1.") or "**analisi dell'errore:**" in low:
            parts.append(f"<div class='gm-section'><b>❌ Analisi Errore:</b> {line_clean.replace('1.', '').replace('**Analisi dell\'errore:**', '').strip()}</div>")
        elif line_clean.startswith("2.") or "**idea corretta:**" in low:
            parts.append(f"<div class='gm-section'><b>💡 Idea Corretta:</b> {line_clean.replace('2.', '').replace('**Idea corretta:**', '').strip()}</div>")
        elif line_clean.startswith("3.") or "**regola pratica:**" in low:
            parts.append(f"<div class='gm-section'><b>♟️ Regola Pratica:</b> {line_clean.replace('3.', '').replace('**Regola pratica:**', '').strip()}</div>")
        else:
            parts.append(f"<div class='gm-section'>{line_clean}</div>")
    return f"<div class='gm-card'><div class='gm-header'>🎓 Lezione del Gran Maestro AI</div>{''.join(parts)}</div>"

def salva_partita_e_errori_db(user_email, pgn_text, source, source_game_id, headers, errori, eval_history, rating_partita, data_partita, opening_name, opening_eco, user_color, result, time_control):
    sb = get_supabase()
    if not sb: return None
    try:
        src = _canonical_source(source)
        game_data = {
            "user_email": user_email, "source": src, "source_game_id": source_game_id, "pgn": pgn_text,
            "white": headers.get("White", "Unknown"), "black": headers.get("Black", "Unknown"),
            "user_color": user_color, "result": result, "time_control": time_control,
            "opening_eco": opening_eco or None, "opening_name": opening_name,
            "played_at": _utc_now_iso(), "analyzed_at": _utc_now_iso(), "analysis_depth": 12,
        }
        res_game = sb.table("games").upsert(game_data, on_conflict="user_email,source,source_game_id").execute()
        game_id = res_game.data[0]["id"] if res_game.data else None
        if not game_id:
            r = sb.table("games").select("id").eq("user_email", user_email).eq("source", src).eq("source_game_id", source_game_id).execute()
            game_id = r.data[0]["id"] if r.data else None
        if not game_id: return None

        if rating_partita:
            try: sb.table("storico_rating").upsert({"user_email": user_email, "data": _safe_date_str(data_partita), "rating": int(rating_partita), "partita_id": source_game_id}, on_conflict="user_email,partita_id").execute()
            except Exception: pass

        errori_payload = errori if errori else [{"categoria": "tactical", "label_mossa": "Partita Perfetta", "perdita_cp": 0, "mossa_num": 0}]
        for err in errori_payload:
            err_record = {
                "user_email": user_email, "game_id": game_id, "ply": int(err.get("mossa_num", 0)),
                "fen": err.get("fen_prima", "") or "", "mossa_critica": err.get("label_mossa", "N/A"),
                "best_move": err.get("best_move", "") or "", "categoria_errore": _canonical_categoria(err.get("categoria")),
                "eval_loss_cp": int(float(err.get("perdita_cp", 0)) * 100), "spiegazione": err.get("spiegazione", "") or "",
                "apertura": opening_name, "data": _utc_now_iso(),
            }
            try: sb.table("errori_utenti").upsert(err_record, on_conflict="user_email,game_id,ply").execute()
            except Exception: pass
        return game_id
    except Exception as e:
        st.error(f"Errore DB: {e}")
        return None

def aggiorna_spiegazione_errore_db(user_email, game_id, mossa_critica, spiegazione_html):
    sb = get_supabase()
    if sb and game_id:
        try: sb.table("errori_utenti").update({"spiegazione": spiegazione_html}).eq("user_email", user_email).eq("game_id", game_id).eq("mossa_critica", mossa_critica).execute()
        except Exception: pass

def carica_errori_db(user_email):
    rows = []
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("errori_utenti").select("*, games(source_game_id, opening_name)").eq("user_email", user_email).execute()
            if res.data:
                for r in res.data:
                    g = r.get("games") or {}
                    r["partita_id"] = g.get("source_game_id") or "Partita_Sconosciuta"
                    r["apertura"] = r.get("apertura") or g.get("opening_name") or "Standard"
                    r.pop("games", None)
                    rows.append(r)
        except Exception: pass
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["data", "partita_id", "categoria_errore", "mossa_critica", "spiegazione", "apertura", "game_id"])

def carica_rating_db(user_email):
    rows = []
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("storico_rating").select("*").eq("user_email", user_email).order("data").execute()
            if res.data: rows = res.data
        except Exception: pass
    if rows:
        df = pd.DataFrame(rows)
        df['data'] = pd.to_datetime(df['data'], errors='coerce')
        df = df.dropna(subset=['data']).sort_values('data').reset_index(drop=True)
        return df
    return pd.DataFrame(columns=["data", "rating", "partita_id"])

def game_already_analyzed(user_email, p_id_check):
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("games").select("id").eq("user_email", user_email).eq("source_game_id", p_id_check).execute()
            if res.data: return True
        except Exception: pass
    return False

def tier_badge_html(tier):
    return f"<span class='tier-badge badge-{tier.lower()}'>{tier}</span>"

# ==========================================
# FUNZIONI STRIPE
# ==========================================
def create_stripe_checkout_session(user_email, plan_key):
    if not HAS_STRIPE or not STRIPE_SECRET_KEY:
        st.error("Stripe non configurato correttamente.")
        return None
        
    price_id = STRIPE_PRO_PRICE_ID if plan_key == "Pro" else STRIPE_DIAMOND_PRICE_ID
    if not price_id:
        st.error(f"Prezzo Stripe per il piano {plan_key} mancante nei secret.")
        return None

    sb = get_supabase()
    customer_id = None
    if sb:
        try:
            res = sb.table("config_utenti").select("stripe_customer_id").eq("user_email", user_email).execute()
            if res.data and res.data[0].get("stripe_customer_id"):
                customer_id = res.data[0]["stripe_customer_id"]
        except Exception: pass

    try:
        session_args = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": f"{APP_BASE_URL}/?checkout=success",
            "cancel_url": f"{APP_BASE_URL}/?checkout=cancel",
            "customer_email": user_email if not customer_id else None,
            "customer": customer_id,
            "metadata": {"user_email": user_email, "plan": plan_key}
        }
        # Rimuove chiavi None
        session_args = {k: v for k, v in session_args.items() if v is not None}
        
        session = stripe.checkout.Session.create(**session_args)
        
        # Salva il customer_id per i prossimi acquisti
        if not customer_id and session.customer and sb:
            sb.table("config_utenti").upsert({
                "user_email": user_email,
                "stripe_customer_id": session.customer
            }, on_conflict="user_email").execute()
            
        return session.url
    except Exception as e:
        st.error(f"Errore Stripe Checkout: {e}")
        return None

def create_stripe_billing_portal(user_email):
    if not HAS_STRIPE or not STRIPE_SECRET_KEY: return None
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("config_utenti").select("stripe_customer_id").eq("user_email", user_email).execute()
            if res.data and res.data[0].get("stripe_customer_id"):
                portal = stripe.billing_portal.Session.create(
                    customer=res.data[0]["stripe_customer_id"],
                    return_url=APP_BASE_URL,
                )
                return portal.url
        except Exception as e:
            st.error(f"Errore portale Stripe: {e}")
    return None

# ==========================================
# CSS DINAMICO
# ==========================================
def get_dynamic_css(theme):
    common_fix = "#MainMenu { visibility: hidden !important; } footer { visibility: hidden !important; } [data-testid='stDecoration'] { visibility: hidden !important; }"
    if theme == 'Dark':
        return "<style>" + common_fix + """
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800;900&family=Inter:wght@300;400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        h1, h2, h3, h4, h5, h6, .brand-title { font-family: 'Outfit', sans-serif; }
        .stApp { background: radial-gradient(1200px 800px at 10% -10%, rgba(255,215,0,0.08), transparent 50%), radial-gradient(1000px 600px at 90% 110%, rgba(124,58,237,0.10), transparent 50%), linear-gradient(135deg, #070b14 0%, #0d1220 50%, #0a0e1a 100%); color: #e8eaf0; }
        .main .block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1200px; }
        h1, h2, h3, h4, h5, h6, p, span, label, div { color: #e8eaf0; }
        .hero { text-align: center; padding: 1rem 0 0.5rem 0; }
        .brand-title { background: linear-gradient(90deg, #FFD700 0%, #FFA500 50%, #FFB347 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.6rem; font-weight: 900; text-align: center; }
        .brand-sub { text-align: center; color: #8892a6 !important; font-size: 0.95rem; text-transform: uppercase; }
        section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0b101c 0%, #080c15 100%) !important; border-right: 1px solid rgba(255,215,0,0.08); }
        .user-card { display: flex; align-items: center; gap: 0.9rem; padding: 0.9rem; border-radius: 14px; background: linear-gradient(135deg, rgba(255,215,0,0.10), rgba(255,165,0,0.03)); border: 1px solid rgba(255,215,0,0.18); margin-bottom: 1rem; }
        .avatar { width: 46px; height: 46px; border-radius: 50%; background: linear-gradient(135deg, #FFD700, #FFA500); display: flex; align-items: center; justify-content: center; color: #0a0e1a; font-weight: 800; }
        .user-name { font-size: 0.82rem; font-weight: 600; }
        .tier-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-weight: 700; font-size: 0.68rem; text-transform: uppercase; }
        .badge-free { background: rgba(136,146,166,0.15); color: #8892a6; }
        .badge-plus { background: rgba(59,130,246,0.15); color: #3b82f6; }
        .badge-pro { background: rgba(255,215,0,0.15); color: #FFD700; }
        .badge-elite { background: rgba(0,210,255,0.15); color: #00d2ff; }
        .metric-card { background: rgba(20,26,42,0.9); border-radius: 16px; padding: 1.2rem; border: 1px solid rgba(255,255,255,0.06); }
        .metric-value { font-size: 2rem; font-weight: 800; color: #fff; }
        .metric-label { font-size: 0.8rem; color: #8892a6; text-transform: uppercase; }
        .board-wrapper { display: flex; justify-content: center; padding: 1.2rem; border-radius: 20px; background: rgba(255,215,0,0.05); border: 1px solid rgba(255,215,0,0.12); max-width: fit-content; margin: 0 auto; }
        .gm-card { background: linear-gradient(135deg, rgba(30,41,59,0.85), rgba(15,23,42,0.95)); border: 1px solid rgba(255,215,0,0.25); border-radius: 16px; padding: 1.2rem 1.4rem; margin-top: 0.8rem; }
        .gm-header { color: #FFD700; font-weight: 700; margin-bottom: 0.8rem; border-bottom: 1px solid rgba(255,215,0,0.15); padding-bottom: 0.5rem; }
        .gm-section { margin-bottom: 0.7rem; color: #cbd5e1; }
        .gm-section b { color: #FFD700; }
        .pricing-card { background: rgba(20,26,42,0.9); border: 1px solid rgba(255,215,0,0.2); border-radius: 20px; padding: 2rem; text-align: center; height: 100%; }
        .pricing-card.featured { border: 2px solid #FFD700; }
        .pricing-title { font-size: 1.5rem; font-weight: 800; color: #FFD700; }
        .pricing-price { font-size: 2.5rem; font-weight: 900; color: #fff; margin-bottom: 1rem; }
        .pricing-features { text-align: left; margin: 1.5rem 0; font-size: 0.9rem; color: #cbd5e1; list-style: none; padding: 0; }
        .info-box, .success-box, .warning-box { border-radius: 12px; padding: 0.9rem; margin: 0.5rem 0; border-left: 3px solid; font-size: 0.92rem; }
        .info-box { background: rgba(59,130,246,0.08); border-color: #3b82f6; color: #93c5fd; }
        .success-box { background: rgba(16,185,129,0.08); border-color: #10b981; color: #6ee7b7; }
        .warning-box { background: rgba(234,179,8,0.08); border-color: #eab308; color: #fde047; }
        .section-title { font-size: 1.4rem; font-weight: 700; margin: 1.4rem 0 0.8rem 0; color: #fff; border-bottom: 1px solid rgba(255,215,0,0.2); padding-bottom: 0.5rem; }
        .stButton > button { border-radius: 10px !important; font-weight: 600 !important; border: 1px solid rgba(255,215,0,0.25) !important; background: rgba(20,26,42,0.6) !important; color: #e8eaf0 !important; }
        .stButton > button[kind="primary"] { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important; color: #0a0e1a !important; font-weight: 800 !important; border: none !important; }
        </style>"""
    else:
        return "<style>" + common_fix + """
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800;900&family=Inter:wght@300;400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        h1, h2, h3, h4, h5, h6, .brand-title { font-family: 'Outfit', sans-serif; }
        .stApp { background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); color: #1a202c; }
        .main .block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1200px; }
        h1, h2, h3, h4, h5, h6, p, span, label, div { color: #1a202c; }
        .hero { text-align: center; padding: 1rem 0 0.5rem 0; }
        .brand-title { background: linear-gradient(90deg, #b8860b 0%, #d4af37 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.6rem; font-weight: 900; }
        .brand-sub { text-align: center; color: #64748b !important; font-size: 0.95rem; text-transform: uppercase; }
        section[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid rgba(0,0,0,0.06); }
        .user-card { display: flex; align-items: center; gap: 0.9rem; padding: 0.9rem; border-radius: 14px; background: rgba(212,175,55,0.10); border: 1px solid rgba(212,175,55,0.25); margin-bottom: 1rem; }
        .avatar { width: 46px; height: 46px; border-radius: 50%; background: linear-gradient(135deg, #d4af37, #b8860b); display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 800; }
        .tier-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-weight: 700; font-size: 0.68rem; text-transform: uppercase; }
        .badge-free { background: #e2e8f0; color: #64748b; }
        .badge-plus { background: rgba(59,130,246,0.15); color: #2563eb; }
        .badge-pro { background: rgba(212,175,55,0.15); color: #b8860b; }
        .badge-elite { background: rgba(0,210,255,0.15); color: #00d2ff; }
        .metric-card { background: #ffffff; border-radius: 16px; padding: 1.2rem; border: 1px solid #e2e8f0; }
        .metric-value { font-size: 2rem; font-weight: 800; color: #1a202c; }
        .metric-label { font-size: 0.8rem; color: #64748b; text-transform: uppercase; }
        .board-wrapper { display: flex; justify-content: center; padding: 1.2rem; border-radius: 20px; background: #ffffff; border: 1px solid #e2e8f0; max-width: fit-content; margin: 0 auto; }
        .gm-card { background: #ffffff; border: 1px solid rgba(212,175,55,0.3); border-radius: 16px; padding: 1.2rem 1.4rem; margin-top: 0.8rem; }
        .gm-header { color: #b8860b; font-weight: 700; margin-bottom: 0.8rem; border-bottom: 1px solid rgba(212,175,55,0.15); padding-bottom: 0.5rem; }
        .gm-section { margin-bottom: 0.7rem; color: #334155; }
        .gm-section b { color: #b8860b; }
        .pricing-card { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 20px; padding: 2rem; text-align: center; height: 100%; }
        .pricing-card.featured { border: 2px solid #d4af37; }
        .pricing-title { font-size: 1.5rem; font-weight: 800; color: #b8860b; }
        .pricing-price { font-size: 2.5rem; font-weight: 900; color: #1a202c; margin-bottom: 1rem; }
        .pricing-features { text-align: left; margin: 1.5rem 0; font-size: 0.9rem; color: #475569; list-style: none; padding: 0; }
        .info-box, .success-box, .warning-box { border-radius: 12px; padding: 0.9rem; margin: 0.5rem 0; border-left: 3px solid; font-size: 0.92rem; }
        .info-box { background: rgba(59,130,246,0.08); border-color: #3b82f6; color: #1e40af; }
        .success-box { background: rgba(16,185,129,0.08); border-color: #10b981; color: #047857; }
        .warning-box { background: rgba(234,179,8,0.10); border-color: #eab308; color: #854d0e; }
        .section-title { font-size: 1.4rem; font-weight: 700; margin: 1.4rem 0 0.8rem 0; color: #1a202c; border-bottom: 1px solid rgba(212,175,55,0.2); padding-bottom: 0.5rem; }
        .stButton > button { border-radius: 10px !important; font-weight: 600 !important; border: 1px solid #e2e8f0 !important; background: #ffffff !important; color: #1a202c !important; }
        .stButton > button[kind="primary"] { background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%) !important; color: #ffffff !important; font-weight: 800 !important; border: none !important; }
        </style>"""

st.markdown(get_dynamic_css(st.session_state['theme_mode']), unsafe_allow_html=True)

TEXTS = {
    "it": {
        "title": "Chess Coach Pro", "subtitle": "Coaching Scacchistico AI",
        "login_header": "🔐 Accedi", "register_header": "📝 Registrati",
        "logout_btn": "🚪 Disconnetti",
        "analyze_btn": "🔍 Avvia Analisi Motore",
        "critique_found": "errori tuoi individuati dal motore!",
        "no_errors": "Partita eccellente! Nessun errore rilevato.",
        "gm_lesson_btn": "🎓 Spiegazione GM AI",
        "profile_setup_title": "Configura i tuoi Profili",
        "profile_setup_desc": "Collega i tuoi account Lichess o Chess.com.",
        "continue_btn": "🚀 Entra nell'App",
        "already_analyzed": "⚠️ Questa partita è già stata analizzata.",
    }
}
t = TEXTS['it']

# ==========================================
# LOGIN SCREEN
# ==========================================
if not st.session_state['user']:
    col_l1, col_l2, col_l3 = st.columns([1, 1.4, 1])
    with col_l2:
        st.markdown(f"""
        <div class="hero" style="padding-top: 2.5rem;">
            <span class="hero-logo">♟️</span>
            <div class="brand-title">{t['title']}</div>
            <p class="brand-sub">{t['subtitle']}</p>
        </div>
        """, unsafe_allow_html=True)

        tab_log, tab_reg = st.tabs([t["login_header"], t["register_header"]])

        with tab_log:
            email_log = st.text_input("Email:", key="login_email")
            pass_log = st.text_input("Password:", type="password", key="login_pass")
            if st.button("Accedi", type="primary", use_container_width=True):
                if email_log and pass_log:
                    sb = get_supabase()
                    if sb:
                        try:
                            res = sb.auth.sign_in_with_password({"email": email_log.strip(), "password": pass_log})
                            st.session_state['sb_access_token'] = res.session.access_token
                            st.session_state['sb_refresh_token'] = res.session.refresh_token
                            st.session_state['user'] = email_log.strip()
                            st.query_params["user_email"] = email_log.strip()
                            st.session_state['profile_setup_done'] = False
                            st.success("Login effettuato!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception:
                            st.error("Credenziali non valide o utente inesistente.")
                    else:
                        st.session_state['user'] = email_log.strip()
                        st.query_params["user_email"] = email_log.strip()
                        st.rerun()
                else:
                    st.warning("Inserisci email e password.")

        with tab_reg:
            email_reg = st.text_input("Email:", key="reg_email")
            pass_reg = st.text_input("Password:", type="password", key="reg_pass")
            if st.button("Crea Account", type="primary", use_container_width=True):
                if email_reg and pass_reg:
                    sb = get_supabase()
                    if sb:
                        try:
                            res = sb.auth.sign_up({"email": email_reg.strip(), "password": pass_reg})
                            if res.session:
                                st.session_state['sb_access_token'] = res.session.access_token
                                st.session_state['sb_refresh_token'] = res.session.refresh_token
                            st.session_state['user'] = email_reg.strip()
                            st.query_params["user_email"] = email_reg.strip()
                            st.session_state['profile_setup_done'] = False

                            try:
                                sb.table("config_utenti").upsert({
                                    "user_email": email_reg.strip(), "tier": "Free", "subscription_status": "inactive",
                                }, on_conflict="user_email").execute()
                                registra_movimento_abbonamento(email_reg.strip(), None, "Free", "attivazione", 0.0)
                            except Exception as e:
                                st.warning(f"Config utente: {e}")

                            st.success("Registrazione completata!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Errore di registrazione: {e}")
                    else:
                        st.session_state['user'] = email_reg.strip()
                        st.query_params["user_email"] = email_reg.strip()
                        st.rerun()
                else:
                    st.warning("Inserisci email e password.")
    st.stop()

# ==========================================
# ONBOARDING PROFILI
# ==========================================
user_email = st.session_state['user']
user_tier = get_user_tier(user_email)

if not st.session_state.get('profile_setup_done', False):
    col_p1, col_p2, col_p3 = st.columns([1, 1.6, 1])
    with col_p2:
        st.markdown(f"""
        <div class="hero" style="padding-top: 1.5rem;">
            <span class="hero-logo">🎯</span>
            <div class="brand-title" style="font-size: 2rem;">{t['profile_setup_title']}</div>
            <p class="brand-sub">{t['profile_setup_desc']}</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center;margin-bottom:1.2rem;'>Piano: {tier_badge_html(user_tier)}</div>", unsafe_allow_html=True)

        st.markdown("<div class='section-title'>➕ Aggiungi Account</div>", unsafe_allow_html=True)
        with st.form("form_add_profile"):
            piattaforma_in = st.selectbox("Piattaforma:", ["lichess", "chesscom", "fide"])
            username_in = st.text_input("Username:", placeholder="es. Chene91")
            submit_prof = st.form_submit_button("Salva Profilo", type="primary", use_container_width=True)
            if submit_prof:
                if username_in.strip():
                    success, msg = add_user_profile(user_email, piattaforma_in, username_in.strip())
                    if success:
                        st.success(msg)
                        time.sleep(0.4)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Inserisci un username valido.")

        st.markdown("<div class='section-title'>📋 Account Collegati</div>", unsafe_allow_html=True)
        profiles_attuali = get_user_profiles(user_email)
        if profiles_attuali:
            for p in profiles_attuali:
                cols_pr = st.columns([3, 1])
                cols_pr[0].markdown(f"<div class='info-box'><b>{p['piattaforma'].upper()}</b>: <code>{p['username']}</code></div>", unsafe_allow_html=True)
                if cols_pr[1].button("🗑️", key=f"del_prof_{p['id']}", use_container_width=True):
                    delete_user_profile(p['id'])
                    st.rerun()
        else:
            st.markdown("<div class='warning-box'>Nessun profilo salvato finora.</div>", unsafe_allow_html=True)

        st.write("")
        if st.button(t['continue_btn'], type="primary", use_container_width=True):
            st.session_state['profile_setup_done'] = True
            st.rerun()
    st.stop()

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    initials = (user_email[:2] if user_email else "U").upper()
    gm_usage_str = get_current_gm_usage(user_email, user_tier)

    st.markdown(f"""
    <div class="user-card">
        <div class="avatar">{initials}</div>
        <div class="user-info">
            <div class="user-name">{user_email}</div>
            {tier_badge_html(user_tier)}
            <div style="font-size:0.75rem; color:#FFD700; margin-top:4px;">🎯 Quota GM: {gm_usage_str}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🧭 Navigazione Principale")
    menu_options = [
        "📊 Dashboard & Insights",
        "🔍 Analizza Partita",
        "🌐 Importa & Sincronizza",
        "🎯 Palestra sui Tuoi Errori",
        "📚 Studio da Libri",
        "📝 Diario & PDF",
        "💎 Piani Abbonamento",
        "📞 Contatti & Supporto",
    ]

    if 'nav_selection' not in st.session_state or st.session_state['nav_selection'] not in menu_options:
        st.session_state['nav_selection'] = menu_options[0]

    selected_nav = st.radio("Sezioni App", menu_options, key="nav_selection", label_visibility="collapsed")

    st.markdown("<div class='section-title' style='font-size:0.95rem;margin-top:1rem;'>⚙️ Preferenze</div>", unsafe_allow_html=True)
    scelta_tema = st.selectbox("Tema:", ["Dark", "Light"], index=0 if st.session_state['theme_mode'] == 'Dark' else 1)
    if scelta_tema != st.session_state['theme_mode']:
        st.session_state['theme_mode'] = scelta_tema
        st.rerun()

    st.divider()
    if st.button("⚙️ Gestisci Profili", use_container_width=True):
        st.session_state['profile_setup_done'] = False
        st.rerun()

    if st.button(t["logout_btn"], use_container_width=True):
        sb = get_supabase()
        if sb:
            try: sb.auth.sign_out()
            except Exception: pass
        st.session_state['user'] = None
        if "user_email" in st.query_params: del st.query_params["user_email"]
        for k in ("sb_access_token", "sb_refresh_token"):
            if k in st.session_state: del st.session_state[k]
        st.session_state['profile_setup_done'] = False
        st.rerun()

st.markdown(f"""
<div class="hero">
    <span class="hero-logo">♟️</span>
    <div class="brand-title">{t['title']}</div>
    <p class="brand-sub">{t['subtitle']}</p>
</div>
""", unsafe_allow_html=True)
st.divider()

current_selection = st.session_state['nav_selection']

# ==========================================
# ANALISI & MOTORE (Semplificato)
# ==========================================
def fetch_stockfish_eval(session, fen, depth=12):
    try:
        r = session.post("https://chess-api.com/v1", json={"fen": fen, "depth": depth}, timeout=3.0)
        if r.status_code == 200:
            data = r.json()
            if data.get("eval") is not None: return float(data.get("eval"))
            if data.get("centipawns") is not None: return float(data.get("centipawns")) / 100.0
            if data.get("cp") is not None: return float(data.get("cp")) / 100.0
            if data.get("value") is not None: return float(data.get("value")) / 100.0
            if data.get("mate") is not None: return 100.0 if int(data.get("mate")) > 0 else -100.0
    except Exception: pass
    return None

def analizza_partita_stockfish(pgn_text, target_usernames):
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if not game: return [], None, "PGN non valido.", [], 1500, datetime.datetime.now().strftime("%Y-%m-%d"), "Apertura Standard", "", "white", "1/2-1/2", "unknown"
    headers = game.headers
    white_player = headers.get('White', 'Unknown').strip().lower()
    black_player = headers.get('Black', 'Unknown').strip().lower()
    white_elo, black_elo = headers.get('WhiteElo', '1500'), headers.get('BlackElo', '1500')
    partita_id = build_partita_id(headers)
    
    user_is_white, user_is_black = False, False
    user_rating = 1500
    if target_usernames:
        users = [u.strip().lower() for u in target_usernames]
        for u in users:
            if u and u in white_player: user_is_white = True; user_rating = int(white_elo) if white_elo.isdigit() else 1500
            if u and u in black_player: user_is_black = True; user_rating = int(black_elo) if black_elo.isdigit() else 1500
    if not user_is_white and not user_is_black: user_is_white = True

    user_color = "white" if (user_is_white and not user_is_black) else ("black" if (user_is_black and not user_is_white) else "white")
    board = game.board()
    errors, eval_history = [], []
    session = requests.Session()
    prev_eval = 0.0
    total_ply = len(list(game.mainline_moves()))

    for idx, move in enumerate(game.mainline_moves()):
        fen_before = board.fen()
        try: move_san = board.san(move)
        except Exception: move_san = move.uci()

        eval_before = fetch_stockfish_eval(session, fen_before, depth=12) or prev_eval
        board.push(move)
        fen_after = board.fen()
        eval_after = fetch_stockfish_eval(session, fen_after, depth=12) or eval_before

        num_mossa, is_white_move = (idx // 2) + 1, (idx % 2 == 0)
        eval_history.append({"ply": idx + 1, "eval_clamped": max(min(eval_after, 10.0), -10.0)})

        is_user_move = (is_white_move and user_is_white) or (not is_white_move and user_is_black)
        if is_user_move:
            delta = (eval_before - eval_after) if is_white_move else (eval_after - eval_before)
            if delta >= 0.5:
                tipo = "🔴 Blunder" if delta >= 2.0 else ("🟠 Mistake" if delta >= 1.0 else "🟡 Inaccuracy")
                label = f"{num_mossa}. {move_san}" if is_white_move else f"{num_mossa}... {move_san}"
                errors.append({"mossa_num": idx + 1, "label_mossa": label, "fen_prima": fen_before, "perdita_cp": round(delta, 2), "tipo_problema": tipo, "categoria": "tactical" if delta >= 1.5 else "positional"})
        prev_eval = eval_after
    return errors, partita_id, None, eval_history, user_rating, _normalize_pgn_date(headers.get('Date', '')), headers.get('Opening', 'Standard'), headers.get('ECO', ''), user_color, headers.get('Result', '*'), headers.get('TimeControl', 'unknown')

def render_eval_graph(eval_history, errors):
    if not HAS_PLOTLY or not eval_history: return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[e["ply"] for e in eval_history], y=[e["eval_clamped"] for e in eval_history], mode="lines", fill="tozeroy", line=dict(color="#FFD700", width=2)))
    fig.update_layout(template='plotly_dark' if st.session_state['theme_mode'] == 'Dark' else 'plotly_white', height=320, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# SEZIONI UI
# ==========================================
if current_selection == "📊 Dashboard & Insights":
    st.markdown("<div class='section-title'>📊 Control Room</div>", unsafe_allow_html=True)
    df_err = carica_errori_db(user_email)
    df_rating = carica_rating_db(user_email)

    if not df_rating.empty and HAS_PLOTLY:
        fig_r = go.Figure()
        fig_r.add_trace(go.Scatter(x=df_rating['data'], y=df_rating['rating'], mode='lines+markers', line=dict(color='#3b82f6', width=3)))
        fig_r.update_layout(template='plotly_dark' if st.session_state['theme_mode'] == 'Dark' else 'plotly_white', height=280)
        st.plotly_chart(fig_r, use_container_width=True)
    
    if not df_err.empty:
        df_real = df_err[df_err['mossa_critica'] != 'Partita Perfetta']
        k1, k2 = st.columns(2)
        k1.markdown(f"<div class='metric-card blue'><div class='metric-value'>{len(df_real)}</div><div class='metric-label'>Errori Censiti</div></div>", unsafe_allow_html=True)
        k2.markdown(f"<div class='metric-card purple'><div class='metric-value'>{df_err['partita_id'].nunique()}</div><div class='metric-label'>Partite</div></div>", unsafe_allow_html=True)

elif current_selection == "🔍 Analizza Partita":
    st.markdown("<div class='section-title'>📖 Analisi Partita</div>", unsafe_allow_html=True)
    pgn_input = st.text_area("PGN:", value=st.session_state.get('pgn_manual_input', ''), height=140)
    if st.button(t["analyze_btn"], type="primary", use_container_width=True):
        if pgn_input.strip():
            with st.spinner("Analisi..."):
                usernames = [p['username'] for p in get_user_profiles(user_email)]
                (errori, p_id, _, eval_hist, rating, data_p, opening, eco, color, result, tc) = analizza_partita_stockfish(pgn_input.strip(), usernames)
                st.session_state['stockfish_errors'] = errori
                st.session_state['eval_history'] = eval_hist
                game_obj = chess.pgn.read_game(io.StringIO(pgn_input.strip()))
                salva_partita_e_errori_db(user_email, pgn_input.strip(), "manual", p_id, game_obj.headers if game_obj else {}, errori, eval_hist, rating, data_p, opening, eco, color, result, tc)
                if game_obj:
                    st.session_state['active_game_board'] = game_obj
                    st.session_state['active_game_moves'] = list(game_obj.mainline_moves())
                    st.session_state['current_board_ply'] = 0
                st.success(f"Trovati {len(errori)} errori.")
    
    if st.session_state.get('eval_history'):
        render_eval_graph(st.session_state['eval_history'], st.session_state.get('stockfish_errors', []))
        
    if st.session_state.get('active_game_board'):
        game_moves = st.session_state['active_game_moves']
        ply = st.slider("Mosse", 0, len(game_moves), value=st.session_state.get('current_board_ply', 0))
        st.session_state['current_board_ply'] = ply
        tb = st.session_state['active_game_board'].board()
        for i in range(ply): tb.push(game_moves[i])
        st.markdown(f'<div class="board-wrapper">{chess.svg.board(board=tb, size=430)}</div>', unsafe_allow_html=True)

elif current_selection == "💎 Piani Abbonamento":
    st.markdown("<div class='section-title'>💎 Scegli il tuo Piano</div>", unsafe_allow_html=True)
    col_pr1, col_pr2, col_pr3, col_pr4 = st.columns(4)

    with col_pr1:
        st.markdown("<div class='pricing-card'><div class='pricing-title'>Free</div><div class='pricing-price'>€0</div></div>", unsafe_allow_html=True)
        if user_tier == "Free":
            st.button("Piano Attuale", disabled=True, use_container_width=True, key="b_f")
        else:
            if st.button("Gestisci Abbonamento", use_container_width=True, key="b_tf"):
                portal_url = create_stripe_billing_portal(user_email)
                if portal_url:
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={portal_url}">', unsafe_allow_html=True)

    with col_pr2:
        st.markdown("<div class='pricing-card'><div class='pricing-title'>Plus</div><div class='pricing-price'>€2.99</div></div>", unsafe_allow_html=True)
        if user_tier == "Plus":
            st.button("Piano Attuale", disabled=True, use_container_width=True, key="b_plus")
        else:
            if st.button("Sottoscrivi Plus 🚀", type="primary", use_container_width=True, key="b_tplus"):
                url = create_stripe_checkout_session(user_email, "Plus")
                if url:
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={url}">', unsafe_allow_html=True)

    with col_pr3:
        st.markdown("<div class='pricing-card'><div class='pricing-title'>Pro</div><div class='pricing-price'>€4.99</div></div>", unsafe_allow_html=True)
        if user_tier == "Pro":
            st.button("Piano Attuale", disabled=True, use_container_width=True, key="b_pro")
        else:
            if st.button("Sottoscrivi Pro 🚀", type="primary", use_container_width=True, key="b_tp"):
                url = create_stripe_checkout_session(user_email, "Pro")
                if url:
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={url}">', unsafe_allow_html=True)

    with col_pr4:
        st.markdown("<div class='pricing-card'><div class='pricing-title'>Elite</div><div class='pricing-price'>€9.99</div></div>", unsafe_allow_html=True)
        if user_tier == "Elite":
            st.button("Piano Attuale", disabled=True, use_container_width=True, key="b_elite")
        else:
            if st.button("Sottoscrivi Elite 💎", type="primary", use_container_width=True, key="b_telite"):
                url = create_stripe_checkout_session(user_email, "Elite")
                if url:
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={url}">', unsafe_allow_html=True)

# (Il resto delle sezioni UI, come Importa, Palestra, etc., rimane invariato)
