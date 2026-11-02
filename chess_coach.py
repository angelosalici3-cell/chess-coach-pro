import streamlit as st
import google.generativeai as genai
import chess
import chess.svg
import chess.pgn
import pandas as pd
import json
import datetime
import io
import os
import tempfile
import time
import requests
from fpdf import FPDF
from PIL import Image
import base64
from supabase import create_client, Client

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
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

# Configurazione Stripe
STRIPE_SECRET_KEY = st.secrets.get("STRIPE_SECRET_KEY", "")
STRIPE_PRO_PRICE_ID = st.secrets.get("STRIPE_PRO_PRICE_ID", "")
STRIPE_DIAMOND_PRICE_ID = st.secrets.get("STRIPE_DIAMOND_PRICE_ID", "")

if HAS_STRIPE and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

GEMINI_MODEL_NAME = "gemini-2.5-flash"

@st.cache_resource
def init_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY or "INSERISCI" in SUPABASE_URL:
        return None
    try:
        return create_client(SUPABASE_URL.strip(), SUPABASE_KEY.strip())
    except Exception:
        return None

supabase = init_supabase()

st.set_page_config(page_title="Chess Coach Pro", layout="wide", page_icon="⚡", initial_sidebar_state="expanded")

# --- GESTIONE STATO INIZIALE ---
for key, default in {
    'user': None, 'lang': 'it', 'profile_setup_done': False,
    'nav_selection': "📖 Analizza", 'theme_mode': 'Dark',
    'last_analyzed_pgn': None, 'current_board_ply': 0,
    'eval_history': None
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Gestione sicura del reindirizzamento di pagina
if 'goto_tab' in st.session_state and st.session_state['goto_tab']:
    st.session_state['nav_selection'] = st.session_state['goto_tab']
    del st.session_state['goto_tab']

# --- KEEP-ALIVE MOBILE ---
st.components.v1.html("""
    <script>setInterval(function(){fetch(window.location.href);},25000);</script>
""", height=0)

# --- DATABASE & SUBSCRIPTION ENGINE ---
def get_user_tier(email):
    """
    Ottiene il tier dell'utente verificando contemporaneamente l'eventuale scadenza.
    Se l'abbonamento è scaduto, viene automaticamente retrocesso a 'Free'.
    """
    if not supabase or not email:
        return "Free"
    
    try:
        res = supabase.table("config_utenti").select("tier, data_scadenza").eq("user_email", email).execute()
        if res.data and len(res.data) > 0:
            user_data = res.data[0]
            current_tier = user_data.get("tier", "Free")
            data_scadenza_str = user_data.get("data_scadenza")

            if current_tier in ["Pro", "Diamond"] and data_scadenza_str:
                data_scadenza = datetime.datetime.fromisoformat(data_scadenza_str.replace("Z", "+00:00"))
                now = datetime.datetime.now(datetime.timezone.utc)

                # Se l'abbonamento è scaduto -> Downgrade automatico a Free
                if now > data_scadenza:
                    supabase.table("config_utenti").update({
                        "tier": "Free",
                        "data_scadenza": None,
                        "updated_at": now.isoformat()
                    }).eq("user_email", email).execute()

                    # Segna nello storico che l'abbonamento precedente è scaduto
                    supabase.table("storico_abbonamenti").update({"stato": "scaduto"})\
                        .eq("user_email", email).eq("stato", "attivo").execute()

                    return "Free"

            return current_tier
    except Exception:
        pass
    return "Free"

def registra_nuovo_abbonamento(email, new_tier, giorni_durata=30):
    """
    Registra il nuovo abbonamento aggiornando sia lo stato corrente che lo storico transazioni.
    """
    if not supabase or not email:
        return

    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        data_scadenza = now + datetime.timedelta(days=giorni_durata)

        now_iso = now.isoformat()
        scadenza_iso = data_scadenza.isoformat()

        # 1. Disattiva eventuali vecchi abbonamenti attivi nello storico
        supabase.table("storico_abbonamenti").update({"stato": "annullato"})\
            .eq("user_email", email).eq("stato", "attivo").execute()

        # 2. Inserisci il nuovo record nello storico abbonamenti per campagne commerciali/marketing
        if new_tier != "Free":
            supabase.table("storico_abbonamenti").insert({
                "user_email": email,
                "tier": new_tier,
                "data_inizio": now_iso,
                "data_scadenza": scadenza_iso,
                "stato": "attivo"
            }).execute()

        # 3. Aggiorna lo stato attuale dell'utente in config_utenti
        res = supabase.table("config_utenti").select("user_email").eq("user_email", email).execute()
        if res.data and len(res.data) > 0:
            supabase.table("config_utenti").update({
                "tier": new_tier,
                "data_scadenza": scadenza_iso if new_tier != "Free" else None,
                "updated_at": now_iso
            }).eq("user_email", email).execute()
        else:
            supabase.table("config_utenti").insert({
                "user_email": email,
                "tier": new_tier,
                "data_scadenza": scadenza_iso if new_tier != "Free" else None,
                "updated_at": now_iso
            }).execute()

    except Exception as e:
        st.error(f"Errore durante l'aggiornamento dell'abbonamento: {e}")

# Gestione del ritorno da Stripe tramite query params
query_params = st.query_params
if "success" in query_params and st.session_state.get('user'):
    sub_type = query_params.get("success")
    if sub_type in ["pro", "diamond"]:
        tier_name = "Pro" if sub_type == "pro" else "Diamond"
        registra_nuovo_abbonamento(st.session_state['user'], tier_name)
        st.success(f"🎉 Abbonamento {tier_name} attivato con successo e registrato nel tuo profilo!")
        st.query_params.clear()

# --- CSS DINAMICO PULITO ---
def get_dynamic_css(theme):
    common_fix = """
        #MainMenu { visibility: hidden !important; }
        footer { visibility: hidden !important; }
        [data-testid="stDecoration"] { visibility: hidden !important; }
    """

    if theme == 'Dark':
        return "<style>" + common_fix + """
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=Inter:wght@300;400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        h1, h2, h3, h4, h5, h6, .brand-title { font-family: 'Outfit', sans-serif; }

        .stApp {
            background:
                radial-gradient(1200px 800px at 10% -10%, rgba(255, 215, 0, 0.08), transparent 50%),
                radial-gradient(1000px 600px at 90% 110%, rgba(124, 58, 237, 0.10), transparent 50%),
                linear-gradient(135deg, #070b14 0%, #0d1220 50%, #0a0e1a 100%);
            color: #e8eaf0;
        }
        .main .block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1200px; }
        h1, h2, h3, h4, h5, h6, p, span, label, div { color: #e8eaf0; }

        .hero { text-align: center; padding: 1rem 0 0.5rem 0; animation: fadeIn 0.6s ease-in; }
        .brand-title {
            background: linear-gradient(90deg, #FFD700 0%, #FFA500 50%, #FFB347 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-size: 2.6rem; font-weight: 900; text-align: center; letter-spacing: -0.5px; margin-bottom: 0;
        }
        .brand-sub {
            text-align: center; color: #8892a6 !important;
            font-size: 0.95rem; margin: 0.2rem 0 1rem 0; letter-spacing: 1.5px; text-transform: uppercase; font-weight: 500;
        }
        .hero-logo { font-size: 3.5rem; display: block; text-align: center; margin-bottom: -0.4rem; }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b101c 0%, #080c15 100%) !important;
            border-right: 1px solid rgba(255, 215, 0, 0.08);
        }
        section[data-testid="stSidebar"] > div { padding-top: 1rem; }

        .user-card {
            display: flex; align-items: center; gap: 0.9rem;
            padding: 0.9rem; border-radius: 14px;
            background: linear-gradient(135deg, rgba(255,215,0,0.10), rgba(255,165,0,0.03));
            border: 1px solid rgba(255, 215, 0, 0.18); margin-bottom: 1rem;
        }
        .avatar {
            width: 46px; height: 46px; border-radius: 50%;
            background: linear-gradient(135deg, #FFD700, #FFA500);
            display: flex; align-items: center; justify-content: center;
            color: #0a0e1a; font-weight: 800; font-size: 1.05rem;
            box-shadow: 0 4px 14px rgba(255, 215, 0, 0.35); flex-shrink: 0;
        }
        .user-info { flex: 1; min-width: 0; }
        .user-name { font-size: 0.82rem; font-weight: 600; color: #e8eaf0;
                     overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

        .tier-badge {
            display: inline-block; padding: 3px 10px; border-radius: 20px;
            font-weight: 700; font-size: 0.68rem; text-transform: uppercase;
            letter-spacing: 0.5px; margin-top: 2px;
        }
        .badge-free    { background: rgba(136,146,166,0.15); color: #8892a6; border: 1px solid rgba(136,146,166,0.3); }
        .badge-pro     { background: rgba(255,215,0,0.15); color: #FFD700; border: 1px solid rgba(255,215,0,0.4); }
        .badge-diamond { background: rgba(0,210,255,0.15); color: #00d2ff; border: 1px solid rgba(0,210,255,0.4); }

        .category-tag {
            background: rgba(255, 215, 0, 0.1); color: #FFD700;
            padding: 2px 8px; border-radius: 6px; font-weight: 600; font-size: 0.75rem;
            border: 1px solid rgba(255,215,0,0.2);
        }

        div[data-testid="stExpander"] {
            background: linear-gradient(135deg, rgba(20,26,42,0.75) 0%, rgba(15,20,32,0.75) 100%) !important;
            border: 1px solid rgba(255, 215, 0, 0.12) !important;
            border-radius: 14px !important; color: #e8eaf0 !important;
            margin-bottom: 0.6rem; overflow: hidden; backdrop-filter: blur(6px);
        }
        div[data-testid="stExpander"]:hover { border-color: rgba(255, 215, 0, 0.3) !important; }
        div[data-testid="stExpander"] summary p { color: #e8eaf0 !important; font-weight: 600; }

        .metric-card {
            background: linear-gradient(135deg, rgba(20,26,42,0.9), rgba(15,20,32,0.9));
            border-radius: 16px; padding: 1.2rem 1.1rem;
            border: 1px solid rgba(255,255,255,0.06);
            position: relative; overflow: hidden; transition: transform 0.25s ease, border-color 0.25s ease;
        }
        .metric-card:hover { transform: translateY(-3px); border-color: rgba(255,215,0,0.35); }
        .metric-card::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
            background: linear-gradient(90deg, #FFD700, #FFA500);
        }
        .metric-card.blue::before   { background: linear-gradient(90deg, #3b82f6, #6366f1); }
        .metric-card.purple::before { background: linear-gradient(90deg, #a855f7, #ec4899); }
        .metric-card.green::before  { background: linear-gradient(90deg, #10b981, #34d399); }
        .metric-icon { font-size: 1.6rem; margin-bottom: 0.3rem; }
        .metric-value { font-size: 2rem; font-weight: 800; font-family: 'Outfit', sans-serif;
                        color: #fff; line-height: 1.1; margin-bottom: 0.2rem; }
        .metric-label { font-size: 0.8rem; color: #8892a6; text-transform: uppercase;
                        letter-spacing: 0.8px; font-weight: 500; }

        .board-wrapper {
            display: flex; justify-content: center; align-items: center;
            padding: 1.2rem; border-radius: 20px;
            background: linear-gradient(135deg, rgba(255,215,0,0.05), rgba(255,165,0,0.02));
            border: 1px solid rgba(255,215,0,0.12); box-shadow: 0 20px 50px rgba(0,0,0,0.35);
            max-width: fit-content; margin: 0 auto;
        }
        .board-wrapper svg { border-radius: 12px; }

        .pricing-card {
            background: linear-gradient(135deg, rgba(20,26,42,0.9), rgba(15,20,32,0.9));
            border: 1px solid rgba(255,215,0,0.2); border-radius: 20px;
            padding: 2rem 1.5rem; text-align: center; position: relative;
            box-shadow: 0 10px 30px rgba(0,0,0,0.4); height: 100%;
        }
        .pricing-card.featured {
            border: 2px solid #FFD700;
            background: linear-gradient(135deg, rgba(30,38,60,0.95), rgba(20,26,42,0.95));
            box-shadow: 0 15px 40px rgba(255,215,0,0.2);
        }
        .pricing-title { font-size: 1.5rem; font-weight: 800; color: #FFD700; margin-bottom: 0.5rem; }
        .pricing-price { font-size: 2.5rem; font-weight: 900; color: #fff; margin-bottom: 1rem; }
        .pricing-features { text-align: left; margin: 1.5rem 0; font-size: 0.9rem; color: #cbd5e1; list-style: none; padding: 0; }
        .pricing-features li { margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.5rem; }

        .info-box, .success-box, .warning-box, .error-box {
            border-radius: 12px; padding: 0.9rem 1.1rem; margin: 0.5rem 0;
            border-left: 3px solid; font-size: 0.92rem;
        }
        .info-box    { background: rgba(59,130,246,0.08); border-color: #3b82f6; color: #93c5fd; }
        .success-box { background: rgba(16,185,129,0.08); border-color: #10b981; color: #6ee7b7; }
        .warning-box { background: rgba(234,179,8,0.08);  border-color: #eab308; color: #fde047; }
        .error-box   { background: rgba(239,68,68,0.08);  border-color: #ef4444; color: #fca5a5; }

        .section-title {
            font-family: 'Outfit', sans-serif; font-size: 1.4rem; font-weight: 700;
            margin: 1.4rem 0 0.8rem 0; display: flex; align-items: center; gap: 0.5rem; color: #fff;
        }
        .section-title::after {
            content: ''; flex: 1; height: 1px;
            background: linear-gradient(90deg, rgba(255,215,0,0.35), transparent);
            margin-left: 0.6rem;
        }

        .stButton > button {
            border-radius: 10px !important; transition: all 0.22s ease !important;
            font-weight: 600 !important; border: 1px solid rgba(255,215,0,0.25) !important;
            background: rgba(20,26,42,0.6) !important; color: #e8eaf0 !important;
        }
        .stButton > button:hover {
            border-color: rgba(255,215,0,0.6) !important;
            background: rgba(255,215,0,0.08) !important;
            transform: translateY(-1px);
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important;
            color: #0a0e1a !important; font-weight: 800 !important; border: none !important;
            box-shadow: 0 6px 18px rgba(255, 165, 0, 0.25) !important;
        }
        .stButton > button[kind="primary"]:hover {
            box-shadow: 0 8px 24px rgba(255, 165, 0, 0.4) !important; transform: translateY(-2px);
        }

        input, textarea, .stTextInput input, .stTextArea textarea {
            color: #e8eaf0 !important; background-color: rgba(10,14,26,0.7) !important;
            border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 10px !important;
        }
        input:focus, textarea:focus { border-color: rgba(255,215,0,0.5) !important; }

        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #FFD700, #FFA500) !important;
        }
        div[data-testid="stMetricValue"] { color: #FFD700 !important; font-family: 'Outfit', sans-serif; }
        div[data-testid="stMetricLabel"] { color: #8892a6 !important; }
        hr { border-color: rgba(255,255,255,0.06) !important; }
        @keyframes fadeIn { from {opacity: 0; transform: translateY(6px);} to {opacity: 1; transform: translateY(0);} }
        </style>"""
    else:
        return "<style>" + common_fix + """
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=Inter:wght@300;400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        h1, h2, h3, h4, h5, h6, .brand-title { font-family: 'Outfit', sans-serif; }

        .stApp {
            background:
                radial-gradient(1200px 800px at 10% -10%, rgba(212,175,55,0.12), transparent 50%),
                radial-gradient(1000px 600px at 90% 110%, rgba(59,130,246,0.10), transparent 50%),
                linear-gradient(135deg, #f8fafc 0%, #eef2f7 50%, #e2e8f0 100%);
            color: #1a202c;
        }
        .main .block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1200px; }
        h1, h2, h3, h4, h5, h6, p, span, label, div { color: #1a202c; }

        .hero { text-align: center; padding: 1rem 0 0.5rem 0; }
        .brand-title {
            background: linear-gradient(90deg, #b8860b 0%, #d4af37 50%, #c9a227 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-size: 2.6rem; font-weight: 900; text-align: center; letter-spacing: -0.5px; margin-bottom: 0;
        }
        .brand-sub {
            text-align: center; color: #64748b !important;
            font-size: 0.95rem; margin: 0.2rem 0 1rem 0; letter-spacing: 1.5px; text-transform: uppercase; font-weight: 500;
        }
        .hero-logo { font-size: 3.5rem; display: block; text-align: center; margin-bottom: -0.4rem; }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%) !important;
            border-right: 1px solid rgba(0,0,0,0.06);
        }

        .user-card {
            display: flex; align-items: center; gap: 0.9rem;
            padding: 0.9rem; border-radius: 14px;
            background: linear-gradient(135deg, rgba(212,175,55,0.10), rgba(212,175,55,0.02));
            border: 1px solid rgba(212,175,55,0.25); margin-bottom: 1rem;
        }
        .avatar {
            width: 46px; height: 46px; border-radius: 50%;
            background: linear-gradient(135deg, #d4af37, #b8860b);
            display: flex; align-items: center; justify-content: center;
            color: #ffffff; font-weight: 800; font-size: 1.05rem;
            box-shadow: 0 4px 14px rgba(212,175,55,0.35); flex-shrink: 0;
        }
        .user-info { flex: 1; min-width: 0; }
        .user-name { font-size: 0.82rem; font-weight: 600; color: #1a202c;
                     overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

        .tier-badge {
            display: inline-block; padding: 3px 10px; border-radius: 20px;
            font-weight: 700; font-size: 0.68rem; text-transform: uppercase;
            letter-spacing: 0.5px; margin-top: 2px;
        }
        .badge-free    { background: #e2e8f0; color: #64748b; border: 1px solid #cbd5e1; }
        .badge-pro     { background: rgba(212,175,55,0.15); color: #b8860b; border: 1px solid #d4af37; }
        .badge-diamond { background: rgba(59,130,246,0.15); color: #2563eb; border: 1px solid #3b82f6; }

        .category-tag {
            background: rgba(212,175,55,0.15); color: #b8860b;
            padding: 2px 8px; border-radius: 6px; font-weight: 600; font-size: 0.75rem;
            border: 1px solid rgba(212,175,55,0.3);
        }

        div[data-testid="stExpander"] {
            background: #ffffff !important; border: 1px solid #e2e8f0 !important;
            border-radius: 14px !important; color: #1a202c !important;
            margin-bottom: 0.6rem; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        div[data-testid="stExpander"]:hover { border-color: #d4af37 !important; }
        div[data-testid="stExpander"] summary p { color: #1a202c !important; font-weight: 600; }

        .metric-card {
            background: #ffffff; border-radius: 16px; padding: 1.2rem 1.1rem;
            border: 1px solid #e2e8f0; position: relative; overflow: hidden;
            box-shadow: 0 2px 12px rgba(0,0,0,0.05);
            transition: transform 0.25s ease, border-color 0.25s ease;
        }
        .metric-card:hover { transform: translateY(-3px); border-color: rgba(212,175,55,0.5); }
        .metric-card::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
            background: linear-gradient(90deg, #d4af37, #b8860b);
        }
        .metric-card.blue::before   { background: linear-gradient(90deg, #3b82f6, #6366f1); }
        .metric-card.purple::before { background: linear-gradient(90deg, #a855f7, #ec4899); }
        .metric-card.green::before  { background: linear-gradient(90deg, #10b981, #34d399); }
        .metric-icon { font-size: 1.6rem; margin-bottom: 0.3rem; }
        .metric-value { font-size: 2rem; font-weight: 800; font-family: 'Outfit', sans-serif;
                        color: #1a202c; line-height: 1.1; margin-bottom: 0.2rem; }
        .metric-label { font-size: 0.8rem; color: #64748b; text-transform: uppercase;
                        letter-spacing: 0.8px; font-weight: 500; }

        .board-wrapper {
            display: flex; justify-content: center; align-items: center;
            padding: 1.2rem; border-radius: 20px; background: #ffffff;
            border: 1px solid #e2e8f0; box-shadow: 0 8px 30px rgba(0,0,0,0.08);
            max-width: fit-content; margin: 0 auto;
        }
        .board-wrapper svg { border-radius: 12px; }

        .pricing-card {
            background: #ffffff; border: 1px solid #cbd5e1; border-radius: 20px;
            padding: 2rem 1.5rem; text-align: center; position: relative;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05); height: 100%;
        }
        .pricing-card.featured {
            border: 2px solid #d4af37;
            background: #ffffff;
            box-shadow: 0 10px 30px rgba(212,175,55,0.15);
        }
        .pricing-title { font-size: 1.5rem; font-weight: 800; color: #b8860b; margin-bottom: 0.5rem; }
        .pricing-price { font-size: 2.5rem; font-weight: 900; color: #1a202c; margin-bottom: 1rem; }
        .pricing-features { text-align: left; margin: 1.5rem 0; font-size: 0.9rem; color: #475569; list-style: none; padding: 0; }
        .pricing-features li { margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.5rem; }

        .error-card {
            background: #ffffff; border-left: 3px solid #ef4444;
            padding: 1rem 1.1rem; border-radius: 12px; margin-bottom: 0.7rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        .error-card.mistake  { border-left-color: #f97316; }
        .error-card.inaccuracy { border-left-color: #eab308; }
        .error-header { display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: center; }
        .error-move  { font-family: monospace; font-weight: 700;
                       color: #b8860b; background: rgba(212,175,55,0.12);
                       padding: 3px 10px; border-radius: 8px; font-size: 0.9rem; }
        .error-loss  { color: #dc2626; font-weight: 700; font-size: 0.85rem; }

        .info-box, .success-box, .warning-box, .error-box {
            border-radius: 12px; padding: 0.9rem 1.1rem; margin: 0.5rem 0;
            border-left: 3px solid; font-size: 0.92rem;
        }
        .info-box    { background: rgba(59,130,246,0.08); border-color: #3b82f6; color: #1e40af; }
        .success-box { background: rgba(16,185,129,0.08); border-color: #10b981; color: #047857; }
        .warning-box { background: rgba(234,179,8,0.10);  border-color: #eab308; color: #854d0e; }
        .error-box   { background: rgba(239,68,68,0.08);  border-color: #ef4444; color: #b91c1c; }

        .section-title {
            font-family: 'Outfit', sans-serif; font-size: 1.4rem; font-weight: 700;
            margin: 1.4rem 0 0.8rem 0; display: flex; align-items: center; gap: 0.5rem; color: #1a202c;
        }
        .section-title::after {
            content: ''; flex: 1; height: 1px;
            background: linear-gradient(90deg, rgba(212,175,55,0.4), transparent);
            margin-left: 0.6rem;
        }

        .stButton > button {
            border-radius: 10px !important; transition: all 0.22s ease !important;
            font-weight: 600 !important; border: 1px solid #e2e8f0 !important;
            background: #ffffff !important; color: #1a202c !important;
        }
        .stButton > button:hover {
            border-color: rgba(212,175,55,0.7) !important;
            background: rgba(212,175,55,0.05) !important; transform: translateY(-1px);
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%) !important;
            color: #ffffff !important; font-weight: 800 !important; border: none !important;
            box-shadow: 0 6px 18px rgba(212,175,55,0.3) !important;
        }
        .stButton > button[kind="primary"]:hover {
            box-shadow: 0 8px 24px rgba(212,175,55,0.45) !important; transform: translateY(-2px);
        }

        input, textarea { color: #1a202c !important; background-color: #ffffff !important;
            border: 1px solid #e2e8f0 !important; border-radius: 10px !important; }
        input:focus, textarea:focus { border-color: #d4af37 !important; }

        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #d4af37, #b8860b) !important;
        }
        div[data-testid="stMetricValue"] { color: #b8860b !important; font-family: 'Outfit', sans-serif; }
        hr { border-color: #e2e8f0 !important; }
        </style>"""

st.markdown(get_dynamic_css(st.session_state['theme_mode']), unsafe_allow_html=True)

def plotly_template():
    return 'plotly_dark' if st.session_state['theme_mode'] == 'Dark' else 'plotly_white'

TEXTS = {
    "it": {
        "title": "Chess Coach Pro", "subtitle": "Coaching Scacchistico AI ad Altissima Efficienza",
        "tab1": "📖 Analizza", "tab2": "📊 Dashboard", "tab3": "📚 Libri", "tab4": "📝 Diario", "tab5": "🌐 Importa",
        "tab6": "💎 Piani Abbonamento", "tab7": "📞 Contatti & Donazioni",
        "settings": "Account & Tema", "lang_select": "Lingua:", "theme_select": "Tema:",
        "login_header": "🔐 Accedi", "register_header": "📝 Registrati",
        "email_label": "Email:", "password_label": "Password:",
        "login_btn": "Accedi", "register_btn": "Crea Account", "logout_btn": "🚪 Disconnetti",
        "analyze_btn": "🔍 Avvia Analisi Affidabile",
        "critique_found": "criticità identificate sulle tue mosse!",
        "no_errors": "Partita eccellente! Nessun errore grave rilevato sulle tue mosse.",
        "gm_lesson_btn": "🎓 Spiegazione GM AI",
        "prompt_lang": "Rispondi in italiano.",
        "profile_setup_title": "Configura i tuoi Profili",
        "profile_setup_desc": "Collega i tuoi account Lichess o Chess.com per importare le tue partite al volo.",
        "continue_btn": "🚀 Entra nell'App",
        "already_analyzed": "⚠️ Questa partita è già stata analizzata in questa sessione per evitare duplicazioni."
    },
    "en": {
        "title": "Chess Coach Pro", "subtitle": "High-Efficiency AI Chess Coaching",
        "tab1": "📖 Analyze", "tab2": "📊 Dashboard", "tab3": "📚 Books", "tab4": "📝 Diary", "tab5": "🌐 Import",
        "tab6": "💎 Subscription Plans", "tab7": "📞 Contacts & Donations",
        "settings": "Account & Theme", "lang_select": "Language:", "theme_select": "Theme:",
        "login_header": "🔐 Login", "register_header": "📝 Register",
        "email_label": "Email:", "password_label": "Password:",
        "login_btn": "Login", "register_btn": "Create Account", "logout_btn": "🚪 Logout",
        "analyze_btn": "🔍 Start Reliable Analysis",
        "critique_found": "critical issues on your moves!",
        "no_errors": "Great game! No major blunders found on your moves.",
        "gm_lesson_btn": "🎓 Quick GM Insight",
        "prompt_lang": "Respond in English.",
        "profile_setup_title": "Setup your Chess Profiles",
        "profile_setup_desc": "Link your Lichess or Chess.com accounts to sync your games.",
        "continue_btn": "🚀 Enter App",
        "already_analyzed": "⚠️ This game has already been analyzed in this session."
    },
    "es": {
        "title": "Chess Coach Pro", "subtitle": "Entrenamiento de Ajedrez con IA de Alta Eficiencia",
        "tab1": "📖 Analizar", "tab2": "📊 Dashboard", "tab3": "📚 Libros", "tab4": "📝 Diario", "tab5": "🌐 Importar",
        "tab6": "💎 Planes de Suscripción", "tab7": "📞 Contacto y Donaciones",
        "settings": "Cuenta y Tema", "lang_select": "Idioma:", "theme_select": "Tema:",
        "login_header": "🔐 Iniciar Sesión", "register_header": "📝 Registrarse",
        "email_label": "Correo:", "password_label": "Contraseña:",
        "login_btn": "Iniciar Sesión", "register_btn": "Crear Cuenta", "logout_btn": "🚪 Cerrar Sesión",
        "analyze_btn": "🔍 Iniciar Análisis Fiable",
        "critique_found": "¡críticas identificadas en tus jugadas!",
        "no_errors": "¡Excelente partida! Sin errores graves en tus jugadas.",
        "gm_lesson_btn": "🎓 Análisis Rápido GM",
        "prompt_lang": "Responde en español.",
        "profile_setup_title": "Configura tus Perfiles",
        "profile_setup_desc": "Vincula tus cuentas para sincronizar tus partidas.",
        "continue_btn": "🚀 Entrar a la App",
        "already_analyzed": "⚠️ Esta partida ya ha sido analizada en esta sesión."
    }
}

t = TEXTS[st.session_state['lang']]

def get_user_profiles(email):
    if supabase:
        try:
            res = supabase.table("profili_scacchi").select("*").eq("user_email", email).execute()
            if res.data:
                return res.data
        except Exception:
            pass
    return []

def add_user_profile(email, piattaforma, username):
    tier = get_user_tier(email)
    limit = 1 if tier == "Free" else (3 if tier == "Pro" else 5)
    current_profiles = get_user_profiles(email)
    if len(current_profiles) >= limit:
        return False, f"Limite raggiunto per il piano {tier} ({limit} profil{'io' if limit==1 else 'i'})."
    if supabase:
        try:
            supabase.table("profili_scacchi").insert({
                "user_email": email, "piattaforma": piattaforma, "username": username.strip()
            }).execute()
            return True, "Profilo aggiunto!"
        except Exception as e:
            return False, f"Errore DB: {e}"
    return False, "Supabase non connesso."

def delete_user_profile(profile_id):
    if supabase:
        try:
            supabase.table("profili_scacchi").delete().eq("id", profile_id).execute()
            return True
        except Exception:
            pass
    return False

def salva_errore_db(user_email, partita_id, categoria, mossa, spiegazione):
    if supabase:
        try:
            data_ora = datetime.datetime.now().strftime("%Y-%m-%d")
            supabase.table("errori_utenti").insert({
                "user_email": user_email,
                "partita_id": partita_id if partita_id else "Partita_Sconosciuta",
                "data": data_ora, "categoria_errore": categoria,
                "mossa_critica": mossa, "spiegazione": spiegazione
            }).execute()
        except Exception:
            pass

def carica_errori_db(user_email):
    if supabase:
        try:
            res = supabase.table("errori_utenti").select("*").eq("user_email", user_email).execute()
            if res.data:
                return pd.DataFrame(res.data)
        except Exception:
            pass
    return pd.DataFrame(columns=["data", "partita_id", "categoria_errore", "mossa_critica", "spiegazione"])

def tier_badge_html(tier):
    cls = "badge-free" if tier == "Free" else ("badge-pro" if tier == "Pro" else "badge-diamond")
    return f"<span class='tier-badge {cls}'>{tier}</span>"

# ==========================================
# LOGIN
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

        scelta_lingua_benvenuto = st.selectbox(
            t["lang_select"], options=["Italiano", "English", "Español"],
            index=0 if st.session_state['lang'] == 'it' else (1 if st.session_state['lang'] == 'en' else 2),
            key="lang_login_select"
        )
        lang_c = 'it' if scelta_lingua_benvenuto == "Italiano" else ('en' if scelta_lingua_benvenuto == "English" else 'es')
        if lang_c != st.session_state['lang']:
            st.session_state['lang'] = lang_c
            st.rerun()

        tab_log, tab_reg = st.tabs([t["login_header"], t["register_header"]])
        supabase_configurato = supabase is not None

        with tab_log:
            email_log = st.text_input(t["email_label"], key="login_email")
            pass_log = st.text_input(t["password_label"], type="password", key="login_pass")
            if st.button(t["login_btn"], type="primary", use_container_width=True):
                if supabase_configurato and email_log and pass_log:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email_log, "password": pass_log})
                        st.session_state['user'] = res.user.email
                        st.session_state['profile_setup_done'] = False
                        st.rerun()
                    except Exception as e:
                        st.markdown(f"<div class='error-box'>Errore: {e}</div>", unsafe_allow_html=True)
                else:
                    st.session_state['user'] = email_log if email_log else "beta_tester@chess.com"
                    st.session_state['profile_setup_done'] = False
                    st.rerun()

        with tab_reg:
            email_reg = st.text_input(t["email_label"], key="reg_email")
            pass_reg = st.text_input(t["password_label"], type="password", key="reg_pass")
            if st.button(t["register_btn"], type="primary", use_container_width=True):
                if supabase_configurato and email_reg and pass_reg:
                    try:
                        supabase.auth.sign_up({"email": email_reg, "password": pass_reg})
                        st.markdown("<div class='success-box'>Registrazione completata! Effettua il login.</div>", unsafe_allow_html=True)
                    except Exception as e:
                        st.markdown(f"<div class='error-box'>Errore: {e}</div>", unsafe_allow_html=True)
                else:
                    if email_reg:
                        st.session_state['user'] = email_reg
                        st.session_state['profile_setup_done'] = False
                        st.rerun()
    st.stop()

# ==========================================
# ONBOARDING
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
            piattaforma_in = st.selectbox("Piattaforma:", ["Lichess", "Chess.com"])
            username_in = st.text_input("Username:", placeholder="es. Chene91")
            submit_prof = st.form_submit_button("Salva Profilo", type="primary", use_container_width=True)
            if submit_prof:
                if username_in.strip():
                    success, msg = add_user_profile(user_email, piattaforma_in, username_in.strip())
                    if success:
                        st.markdown(f"<div class='success-box'>{msg}</div>", unsafe_allow_html=True)
                        time.sleep(0.4)
                        st.rerun()
                    else:
                        st.markdown(f"<div class='error-box'>{msg}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='warning-box'>Inserisci un username valido.</div>", unsafe_allow_html=True)

        st.markdown("<div class='section-title'>📋 Account Collegati</div>", unsafe_allow_html=True)
        profiles_attuali = get_user_profiles(user_email)
        if profiles_attuali:
            for p in profiles_attuali:
                cols_pr = st.columns([3, 1])
                with cols_pr[0]:
                    st.markdown(f"<div class='info-box'><b>{p['piattaforma']}</b>: <code>{p['username']}</code></div>", unsafe_allow_html=True)
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
# SIDEBAR & NAVIGAZIONE (DINAMICA CON TIER AGGIORNATO)
# ==========================================
with st.sidebar:
    initials = (user_email[:2] if user_email else "U").upper()
    # Mostra dinamicamente l'etichetta aggiornata sotto l'email dell'utente
    st.markdown(f"""
    <div class="user-card">
        <div class="avatar">{initials}</div>
        <div class="user-info">
            <div class="user-name">{user_email}</div>
            {tier_badge_html(user_tier)}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='font-size:1.05rem;margin-top:0.5rem;'>🧭 Menu Principale</div>", unsafe_allow_html=True)

    menu_options = [
        t["tab1"], t["tab2"], t["tab3"], t["tab4"], t["tab5"],
        t["tab6"], t["tab7"]
    ]
    
    if 'nav_selection' not in st.session_state:
        st.session_state['nav_selection'] = t["tab1"]

    selected_nav = st.radio("Navigazione", menu_options, key="nav_selection", label_visibility="collapsed")

    st.markdown("<div class='section-title' style='font-size:1.05rem;margin-top:1rem;'>⚙️ Preferenze</div>", unsafe_allow_html=True)

    scelta_tema = st.selectbox(t["theme_select"], ["Dark", "Light"],
                               index=0 if st.session_state['theme_mode'] == 'Dark' else 1)
    if scelta_tema != st.session_state['theme_mode']:
        st.session_state['theme_mode'] = scelta_tema
        st.rerun()

    scelta_lingua = st.selectbox(
        t["lang_select"], options=["Italiano", "English", "Español"],
        index=0 if st.session_state['lang'] == 'it' else (1 if st.session_state['lang'] == 'en' else 2)
    )
    lang_code = 'it' if scelta_lingua == "Italiano" else ('en' if scelta_lingua == "English" else 'es')
    if lang_code != st.session_state['lang']:
        st.session_state['lang'] = lang_code
        st.rerun()

    st.divider()
    if st.button("⚙️ Gestisci Profili", use_container_width=True):
        st.session_state['profile_setup_done'] = False
        st.rerun()

    if st.button(t["logout_btn"], use_container_width=True):
        if supabase:
            try: supabase.auth.sign_out()
            except Exception: pass
        st.session_state['user'] = None
        st.session_state['profile_setup_done'] = False
        st.rerun()

# --- HEADER PRINCIPALE ---
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
# GESTIONE SEZIONE PIANI DI ABBONAMENTO (TAB6)
# ==========================================
if current_selection == t["tab6"]:
    st.markdown("<div class='section-title'>💎 Scegli il tuo Piano</div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#8892a6;margin-bottom:2rem;'>Sblocca tutta la potenza di Chess Coach Pro con i nostri abbonamenti dedicati.</p>", unsafe_allow_html=True)

    col_pr1, col_pr2, col_pr3 = st.columns(3)

    with col_pr1:
        st.markdown("""
        <div class="pricing-card">
            <div class="pricing-title">Free</div>
            <div class="pricing-price">€0<span style="font-size:1rem;color:#8892a6">/mese</span></div>
            <ul class="pricing-features">
                <li>✅ 1 Profilo scacchistico</li>
                <li>✅ Analisi base Stockfish</li>
                <li>✅ Dashboard standard</li>
                <li>❌ Spiegazioni GM illimitate</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        if user_tier == "Free":
            st.button("Piano Attuale", disabled=True, use_container_width=True, key="btn_free")
        else:
            if st.button("Passa a Free", use_container_width=True, key="btn_to_free"):
                registra_nuovo_abbonamento(user_email, "Free")
                st.rerun()

    with col_pr2:
        st.markdown("""
        <div class="pricing-card featured">
            <div class="tier-badge badge-pro" style="margin-bottom:0.5rem;">Più Popolare</div>
            <div class="pricing-title">Pro</div>
            <div class="pricing-price">€4.99<span style="font-size:1rem;color:#8892a6">/mese</span></div>
            <ul class="pricing-features">
                <li>✅ Fino a 3 Profili collegati</li>
                <li>✅ Analisi Stockfish prioritaria</li>
                <li>✅ Esportazione PDF illimitata</li>
                <li>✅ Insights GM AI avanzati</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        if user_tier == "Pro":
            st.button("Piano Attuale", disabled=True, use_container_width=True, key="btn_pro_current")
        else:
            if st.button("Sottoscrivi Pro 🚀", type="primary", use_container_width=True, key="btn_sub_pro"):
                if HAS_STRIPE and STRIPE_SECRET_KEY:
                    try:
                        host = st.context.headers.get("Host", "tuo-dominio.streamlit.app")
                        proto = "https" if "localhost" not in host else "http"
                        success_url = f"{proto}://{host}/?success=pro"
                        cancel_url = f"{proto}://{host}/?canceled=true"

                        checkout_session = stripe.checkout.Session.create(
                            line_items=[{
                                'price': STRIPE_PRO_PRICE_ID,
                                'quantity': 1,
                            }],
                            mode='subscription',
                            success_url=success_url,
                            cancel_url=cancel_url,
                            customer_email=user_email
                        )

                        st.components.v1.html(f"""
                            <script>
                                window.top.location.href = "{checkout_session.url}";
                            </script>
                        """, height=0)
                        
                        st.success("Reindirizzamento a Stripe in corso...")
                        st.link_button("👉 Clicca qui se non vieni reindirizzato automaticamente", checkout_session.url, use_container_width=True)
                    except Exception as e:
                        st.markdown(f"<div class='error-box'>Errore Stripe: {e}</div>", unsafe_allow_html=True)
                else:
                    registra_nuovo_abbonamento(user_email, "Pro")
                    st.success("Abbonamento Pro attivato (Simulazione Test)!")
                    time.sleep(1)
                    st.rerun()

    with col_pr3:
        st.markdown("""
        <div class="pricing-card">
            <div class="tier-badge badge-diamond" style="margin-bottom:0.5rem;">Elite</div>
            <div class="pricing-title">Diamond</div>
            <div class="pricing-price">€9.99<span style="font-size:1rem;color:#8892a6">/mese</span></div>
            <ul class="pricing-features">
                <li>✅ Fino a 5 Profili collegati</li>
                <li>✅ Analisi Stockfish Profondità Massima</li>
                <li>✅ Cloud Storage illimitato</li>
                <li>✅ Supporto prioritario 24/7</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        if user_tier == "Diamond":
            st.button("Piano Attuale", disabled=True, use_container_width=True, key="btn_diamond_current")
        else:
            if st.button("Sottoscrivi Diamond 💎", type="primary", use_container_width=True, key="btn_sub_diamond"):
                if HAS_STRIPE and STRIPE_SECRET_KEY:
                    try:
                        host = st.context.headers.get("Host", "tuo-dominio.streamlit.app")
                        proto = "https" if "localhost" not in host else "http"
                        success_url = f"{proto}://{host}/?success=diamond"
                        cancel_url = f"{proto}://{host}/?canceled=true"

                        checkout_session = stripe.checkout.Session.create(
                            line_items=[{
                                'price': STRIPE_DIAMOND_PRICE_ID,
                                'quantity': 1,
                            }],
                            mode='subscription',
                            success_url=success_url,
                            cancel_url=cancel_url,
                            customer_email=user_email
                        )

                        st.components.v1.html(f"""
                            <script>
                                window.top.location.href = "{checkout_session.url}";
                            </script>
                        """, height=0)
                        
                        st.success("Reindirizzamento a Stripe in corso...")
                        st.link_button("👉 Clicca qui se non vieni reindirizzato automaticamente", checkout_session.url, use_container_width=True)
                    except Exception as e:
                        st.markdown(f"<div class='error-box'>Errore Stripe: {e}</div>", unsafe_allow_html=True)
                else:
                    registra_nuovo_abbonamento(user_email, "Diamond")
                    st.success("Abbonamento Diamond attivato (Simulazione Test)!")
                    time.sleep(1)
                    st.rerun()