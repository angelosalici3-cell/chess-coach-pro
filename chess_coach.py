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

GEMINI_MODEL_NAME = "gemini-3.8-flash"

@st.cache_resource
def init_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY or "INSERISCI" in SUPABASE_URL:
        return None
    try:
        from supabase import create_client
        return create_client(SUPABASE_URL.strip(), SUPABASE_KEY.strip())
    except Exception:
        return None

supabase = init_supabase()

st.set_page_config(page_title="Chess Coach Pro", layout="wide", page_icon="⚡", initial_sidebar_state="expanded")

# --- GESTIONE STATO INIZIALE ---
for key, default in {
    'user': None, 'lang': 'it', 'profile_setup_done': False,
    'nav_selection': "📊 Dashboard & Insights", 'theme_mode': 'Dark',
    'last_analyzed_pgn': None, 'current_board_ply': 0,
    'eval_history': None
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

if 'goto_tab' in st.session_state and st.session_state['goto_tab']:
    st.session_state['nav_selection'] = st.session_state['goto_tab']
    del st.session_state['goto_tab']

# --- KEEP-ALIVE MOBILE ---
st.components.v1.html("""
    <script>setInterval(function(){fetch(window.location.href);},25000);</script>
""", height=0)

# --- DATABASE & SUBSCRIPTION ENGINE ---
def get_user_tier(email):
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

                if now > data_scadenza:
                    supabase.table("config_utenti").update({
                        "tier": "Free", "data_scadenza": None, "updated_at": now.isoformat()
                    }).eq("user_email", email).execute()
                    supabase.table("storico_abbonamenti").update({"stato": "scaduto"})\
                        .eq("user_email", email).eq("stato", "attivo").execute()
                    return "Free"
            return current_tier
    except Exception:
        pass
    return "Free"

def registra_nuovo_abbonamento(email, new_tier, giorni_durata=30):
    if not supabase or not email:
        return
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        data_scadenza = now + datetime.timedelta(days=giorni_durata)
        now_iso = now.isoformat()
        scadenza_iso = data_scadenza.isoformat()

        supabase.table("storico_abbonamenti").update({"stato": "annullato"})\
            .eq("user_email", email).eq("stato", "attivo").execute()

        if new_tier != "Free":
            supabase.table("storico_abbonamenti").insert({
                "user_email": email, "tier": new_tier, "data_inizio": now_iso,
                "data_scadenza": scadenza_iso, "stato": "attivo"
            }).execute()

        res = supabase.table("config_utenti").select("user_email").eq("user_email", email).execute()
        if res.data and len(res.data) > 0:
            supabase.table("config_utenti").update({
                "tier": new_tier, "data_scadenza": scadenza_iso if new_tier != "Free" else None,
                "updated_at": now_iso
            }).eq("user_email", email).execute()
        else:
            supabase.table("config_utenti").insert({
                "user_email": email, "tier": new_tier,
                "data_scadenza": scadenza_iso if new_tier != "Free" else None,
                "updated_at": now_iso
            }).execute()
    except Exception as e:
        st.error(f"Errore durante l'aggiornamento dell'abbonamento: {e}")

query_params = st.query_params
if "success" in query_params and st.session_state.get('user'):
    sub_type = query_params.get("success")
    if sub_type in ["pro", "diamond"]:
        tier_name = "Pro" if sub_type == "pro" else "Diamond"
        registra_nuovo_abbonamento(st.session_state['user'], tier_name)
        st.success(f"🎉 Abbonamento {tier_name} attivato con successo!")
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
            border-color: rgba(255,215,0,0.6) !important; background: rgba(255,215,0,0.08) !important;
            transform: translateY(-1px);
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important;
            color: #0a0e1a !important; font-weight: 800 !important; border: none !important;
            box-shadow: 0 6px 18px rgba(255, 165, 0, 0.25) !important;
        }
        input, textarea { color: #e8eaf0 !important; background-color: rgba(10,14,26,0.7) !important;
            border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 10px !important; }
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
            border: 2px solid #d4af37; background: #ffffff;
            box-shadow: 0 10px 30px rgba(212,175,55,0.15);
        }
        .pricing-title { font-size: 1.5rem; font-weight: 800; color: #b8860b; margin-bottom: 0.5rem; }
        .pricing-price { font-size: 2.5rem; font-weight: 900; color: #1a202c; margin-bottom: 1rem; }
        .pricing-features { text-align: left; margin: 1.5rem 0; font-size: 0.9rem; color: #475569; list-style: none; padding: 0; }
        .pricing-features li { margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.5rem; }
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
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%) !important;
            color: #ffffff !important; font-weight: 800 !important; border: none !important;
            box-shadow: 0 6px 18px rgba(212,175,55,0.3) !important;
        }
        </style>"""

st.markdown(get_dynamic_css(st.session_state['theme_mode']), unsafe_allow_html=True)

TEXTS = {
    "it": {
        "title": "Chess Coach Pro", "subtitle": "Coaching Scacchistico AI ad Altissima Efficienza",
        "lang_select": "Lingua:", "theme_select": "Tema:",
        "login_header": "🔐 Accedi", "register_header": "📝 Registrati",
        "email_label": "Email:", "password_label": "Password:",
        "login_btn": "Accedi", "register_btn": "Crea Account", "logout_btn": "🚪 Disconnetti",
        "analyze_btn": "🔍 Avvia Analisi Affidabile",
        "critique_found": "criticità identificate sulle tue mosse!",
        "no_errors": "Partita eccellente! Nessun errore grave rilevato.",
        "gm_lesson_btn": "🎓 Spiegazione GM AI",
        "prompt_lang": "Rispondi in italiano.",
        "profile_setup_title": "Configura i tuoi Profili",
        "profile_setup_desc": "Collega i tuoi account Lichess o Chess.com per la sincronizzazione.",
        "continue_btn": "🚀 Entra nell'App",
        "already_analyzed": "⚠️ Questa partita è già stata analizzata in questa sessione."
    },
    "en": {
        "title": "Chess Coach Pro", "subtitle": "High-Efficiency AI Chess Coaching",
        "lang_select": "Language:", "theme_select": "Theme:",
        "login_header": "🔐 Login", "register_header": "📝 Register",
        "email_label": "Email:", "password_label": "Password:",
        "login_btn": "Login", "register_btn": "Create Account", "logout_btn": "🚪 Logout",
        "analyze_btn": "🔍 Start Reliable Analysis",
        "critique_found": "critical issues on your moves!",
        "no_errors": "Great game! No major blunders found.",
        "gm_lesson_btn": "🎓 Quick GM Insight",
        "prompt_lang": "Respond in English.",
        "profile_setup_title": "Setup your Chess Profiles",
        "profile_setup_desc": "Link your Lichess or Chess.com accounts for sync.",
        "continue_btn": "🚀 Enter App",
        "already_analyzed": "⚠️ This game has already been analyzed in this session."
    },
    "es": {
        "title": "Chess Coach Pro", "subtitle": "Entrenamiento de Ajedrez con IA de Alta Eficiencia",
        "lang_select": "Idioma:", "theme_select": "Tema:",
        "login_header": "🔐 Iniciar Sesión", "register_header": "📝 Registrarse",
        "email_label": "Correo:", "password_label": "Contraseña:",
        "login_btn": "Iniciar Sesión", "register_btn": "Crear Cuenta", "logout_btn": "🚪 Cerrar Sesión",
        "analyze_btn": "🔍 Iniciar Análisis Fiable",
        "critique_found": "¡críticas identificadas en tus jugadas!",
        "no_errors": "¡Excelente partida! Sin errores graves.",
        "gm_lesson_btn": "🎓 Análisis Rápido GM",
        "prompt_lang": "Responde en español.",
        "profile_setup_title": "Configura tus Perfiles",
        "profile_setup_desc": "Vincula tus cuentas para sincronizar.",
        "continue_btn": "🚀 Entrar a la App",
        "already_analyzed": "⚠️ Esta partida ya ha sido analizada."
    }
}

t = TEXTS[st.session_state['lang']]

# --- DATABASE HELPERS & AI CLUSTERS ---
def get_user_profiles(email):
    if supabase:
        try:
            res = supabase.table("profili_scacchi").select("*").eq("user_email", email).execute()
            if res.data: return res.data
        except Exception: pass
    return []

def add_user_profile(email, piattaforma, username):
    tier = get_user_tier(email)
    limit = 1 if tier == "Free" else (3 if tier == "Pro" else 5)
    current_profiles = get_user_profiles(email)
    if len(current_profiles) >= limit:
        return False, f"Limite raggiunto per il piano {tier} ({limit} profili)."
    if supabase:
        try:
            supabase.table("profili_scacchi").insert({"user_email": email, "piattaforma": piattaforma, "username": username.strip()}).execute()
            return True, "Profilo aggiunto!"
        except Exception as e: return False, f"Errore DB: {e}"
    return False, "Supabase non connesso."

def delete_user_profile(profile_id):
    if supabase:
        try:
            supabase.table("profili_scacchi").delete().eq("id", profile_id).execute()
            return True
        except Exception: pass
    return False

def classifica_errore_con_ai(fen_prima, mossa_giocata):
    prompt = f"""
    Sei un GM di scacchi ed un esperto di tattica. Analizza questa posizione e la mossa errata giocata.
    FEN prima della mossa: {fen_prima}
    Mossa errata: {mossa_giocata}
    
    Classifica l'errore scegliendo ESATTAMENTE UNA delle seguenti etichette tematiche:
    - Fork
    - Pin
    - Skewer
    - Hanging Piece
    - Discovered Attack
    - Double Check
    - Interference
    - Clearance
    - Zugzwang
    - Mate in 1
    - Mate in 2
    - Mate in 3+
    - Back Rank Mate
    - Smothered Mate
    - Endgame
    - Quiet Move
    - Defensive Move
    - Positional Weakness
    - Opening Mistake

    Rispondi SOLO con il nome esatto dell'etichetta in inglese tra quelle elencate, senza aggiungere altro testo.
    """
    try:
        client = genai.Client(api_key=MASTER_GEMINI_KEY) if "Client" in dir(genai) else None
        if client:
            resp = client.models.generate_content(model=GEMINI_MODEL_NAME, contents=prompt)
            tag = resp.text.strip()
        else:
            genai.configure(api_key=MASTER_GEMINI_KEY)
            model = genai.GenerativeModel(GEMINI_MODEL_NAME)
            resp = model.generate_content(prompt)
            tag = resp.text.strip()

        valid_tags = [
            "Fork", "Pin", "Skewer", "Hanging Piece", "Discovered Attack", 
            "Double Check", "Interference", "Clearance", "Zugzwang", 
            "Mate in 1", "Mate in 2", "Mate in 3+", "Back Rank Mate", 
            "Smothered Mate", "Endgame", "Quiet Move", "Defensive Move", 
            "Positional Weakness", "Opening Mistake"
        ]
        for vt in valid_tags:
            if vt.lower() in tag.lower():
                return vt
        return "Positional Weakness"
    except Exception:
        return "Positional Weakness"

def salva_errore_db(user_email, partita_id, categoria, mossa, spiegazione):
    if supabase:
        try:
            data_ora = datetime.datetime.now().strftime("%Y-%m-%d")
            supabase.table("errori_utenti").insert({
                "user_email": user_email, "partita_id": partita_id if partita_id else "Partita_Sconosciuta",
                "data": data_ora, "categoria_errore": categoria, "mossa_critica": mossa, "spiegazione": spiegazione
            }).execute()
        except Exception: pass

def carica_errori_db(user_email):
    if supabase:
        try:
            res = supabase.table("errori_utenti").select("*").eq("user_email", user_email).execute()
            if res.data: return pd.DataFrame(res.data)
        except Exception: pass
    return pd.DataFrame(columns=["data", "partita_id", "categoria_errore", "mossa_critica", "spiegazione"])

def tier_badge_html(tier):
    cls = "badge-free" if tier == "Free" else ("badge-pro" if tier == "Pro" else "badge-diamond")
    return f"<span class='tier-badge {cls}'>{tier}</span>"

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

        scelta_lingua_benvenuto = st.selectbox(t["lang_select"], options=["Italiano", "English", "Español"], index=0, key="lang_login_select")
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
                    except Exception as e: st.error(f"Errore: {e}")
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
                        st.success("Registrazione completata! Effettua il login.")
                    except Exception as e: st.error(f"Errore: {e}")
                else:
                    if email_reg:
                        st.session_state['user'] = email_reg
                        st.session_state['profile_setup_done'] = False
                        st.rerun()
    st.stop()

# ==========================================
# ONBOARDING PROFILES
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
                        st.success(msg)
                        time.sleep(0.4)
                        st.rerun()
                    else: st.error(msg)
                else: st.warning("Inserisci un username valido.")

        st.markdown("<div class='section-title'>📋 Account Collegati</div>", unsafe_allow_html=True)
        profiles_attuali = get_user_profiles(user_email)
        if profiles_attuali:
            for p in profiles_attuali:
                cols_pr = st.columns([3, 1])
                cols_pr[0].markdown(f"<div class='info-box'><b>{p['piattaforma']}</b>: <code>{p['username']}</code></div>", unsafe_allow_html=True)
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
# SIDEBAR / MENU STRUTTURATO PER ABBONAMENTO
# ==========================================
with st.sidebar:
    initials = (user_email[:2] if user_email else "U").upper()
    st.markdown(f"""
    <div class="user-card">
        <div class="avatar">{initials}</div>
        <div class="user-info">
            <div class="user-name">{user_email}</div>
            {tier_badge_html(user_tier)}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='font-size:0.95rem;margin-top:0.5rem;'>📊 1. CONTROL ROOM</div>", unsafe_allow_html=True)
    menu_c1 = ["📊 Dashboard & Insights"]

    st.markdown("<div class='section-title' style='font-size:0.95rem;margin-top:0.5rem;'>📖 2. PARTITE & ANALISI</div>", unsafe_allow_html=True)
    menu_c2 = ["🔍 Analizza Partita", "🌐 Importa & Sincronizza"]

    st.markdown("<div class='section-title' style='font-size:0.95rem;margin-top:0.5rem;'>🎯 3. PALESTRA ALLENAMENTO</div>", unsafe_allow_html=True)
    menu_c3 = ["🎯 Palestra sui Tuoi Errori"]

    st.markdown("<div class='section-title' style='font-size:0.95rem;margin-top:0.5rem;'>🛠️ 4. STUDIO & ACCOUNT</div>", unsafe_allow_html=True)
    menu_c4 = ["📚 Studio da Libri", "📝 Diario & PDF", "💎 Piani Abbonamento", "📞 Contatti & Supporto"]

    all_menu_options = menu_c1 + menu_c2 + menu_c3 + menu_c4

    if 'nav_selection' not in st.session_state or st.session_state['nav_selection'] not in all_menu_options:
        st.session_state['nav_selection'] = "📊 Dashboard & Insights"

    selected_nav = st.radio("Navigazione", all_menu_options, key="nav_selection", label_visibility="collapsed")

    st.markdown("<div class='section-title' style='font-size:0.95rem;margin-top:1rem;'>⚙️ Preferenze</div>", unsafe_allow_html=True)
    scelta_tema = st.selectbox(t["theme_select"], ["Dark", "Light"], index=0 if st.session_state['theme_mode'] == 'Dark' else 1)
    if scelta_tema != st.session_state['theme_mode']:
        st.session_state['theme_mode'] = scelta_tema
        st.rerun()

    scelta_lingua = st.selectbox(t["lang_select"], options=["Italiano", "English", "Español"], index=0 if st.session_state['lang'] == 'it' else 1)
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
# MOTORE STOCKFISH & HELPER DI ANALISI COMPLETI
# ==========================================
def fetch_stockfish_eval(session, fen, depth=10):
    for attempt in range(2):
        try:
            r = session.post("https://chess-api.com/v1", json={"fen": fen, "depth": depth}, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if data.get("eval") is not None: return float(data.get("eval"))
                elif data.get("centipawns") is not None: return float(data.get("centipawns")) / 100.0
                elif data.get("cp") is not None: return float(data.get("cp")) / 100.0
                elif data.get("value") is not None: return float(data.get("value")) / 100.0
                elif data.get("mate") is not None:
                    m = int(data.get("mate"))
                    return 100.0 if m > 0 else -100.0
        except Exception: time.sleep(0.3)
    return None

def analizza_partita_chess_api(pgn_text, target_usernames):
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if not game: return [], None, "Impossibile leggere il PGN fornito.", []

    headers = game.headers
    white_player = headers.get('White', 'Unknown').strip().lower()
    black_player = headers.get('Black', 'Unknown').strip().lower()
    user_is_white, user_is_black = True, True

    if target_usernames:
        user_list = [u.strip().lower() for u in target_usernames]
        found_match = False
        user_is_white, user_is_black = False, False
        for u in user_list:
            if u in white_player: user_is_white = True; found_match = True
            if u in black_player: user_is_black = True; found_match = True
        if not found_match: user_is_white, user_is_black = True, True

    partita_id = f"{headers.get('White', 'Unknown')}_vs_{headers.get('Black', 'Unknown')}_{headers.get('Date', 'Live')}"
    board = game.board()
    evaluations, eval_history = [], []
    headers_req = {"User-Agent": "ChessCoachPro/1.0", "Content-Type": "application/json"}
    main_moves = list(game.mainline_moves())
    total_ply_count = len(main_moves)
    total_full_moves = (total_ply_count + 1) // 2

    progress_bar = st.progress(0, text="♟️ Analisi Stockfish in corso...")
    session = requests.Session()
    session.headers.update(headers_req)
    prev_eval = 0.0

    for idx, move in enumerate(main_moves):
        fen_before = board.fen()
        try: move_san = board.san(move)
        except Exception: move_san = move.uci()

        eval_before = fetch_stockfish_eval(session, fen_before, depth=10)
        if eval_before is None: eval_before = prev_eval

        board.push(move)
        fen_after = board.fen()
        num_mossa = (idx // 2) + 1
        is_white_move = (idx % 2 == 0)
        progress_bar.progress((idx + 1) / max(total_ply_count, 1), text=f"♟️ Analisi mossa {num_mossa} di {total_full_moves}...")

        eval_after = fetch_stockfish_eval(session, fen_after, depth=10)
        if eval_after is None: eval_after = eval_before

        clamped = max(min(eval_after, 10.0), -10.0)
        eval_history.append({"ply": idx + 1, "num_move": num_mossa, "san": move_san, "eval_cp": eval_after, "eval_clamped": clamped, "is_white": is_white_move})

        is_user_move = (is_white_move and user_is_white) or (not is_white_move and user_is_black)
        if is_user_move:
            delta = (eval_before - eval_after) if is_white_move else (eval_after - eval_before)
            tipo_problema = "🔴 Blunder" if delta >= 2.0 else ("🟠 Mistake" if delta >= 1.0 else ("🟡 Inaccuracy" if delta >= 0.5 else None))
            if tipo_problema:
                label_mossa = f"{num_mossa}. {move_san}" if is_white_move else f"{num_mossa}... {move_san}"
                cat_mossa = classifica_errore_con_ai(fen_before, move.uci())
                evaluations.append({
                    "mossa_num": idx + 1, "label_mossa": label_mossa, "fen_prima": fen_before,
                    "fen_dopo": fen_after, "mossa_giocata": move.uci(), "perdita_cp": round(delta, 2),
                    "eval_dopo": eval_after, "tipo_problema": tipo_problema, "categoria": cat_mossa
                })
        prev_eval = eval_after
        time.sleep(0.02)

    progress_bar.empty()
    return evaluations, partita_id, None, eval_history

def salva_immagine_scacchiera_png(board, path_temp):
    svg_data = chess.svg.board(board=board, size=400)
    try:
        import cairosvg
        cairosvg.svg2png(bytestring=svg_data.encode('utf-8'), write_to=path_temp)
    except Exception:
        img = Image.new('RGB', (400, 400), color=(240, 217, 181))
        img.save(path_temp)

def genera_pdf_partita(board, mosse_lista, note_mosse, note_finali):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "Chess Coach Pro - Diario Partita", ln=True, align="C")
    pdf.ln(3)
    testo_mosse = ""
    for idx, m in enumerate(mosse_lista):
        num = (idx // 2) + 1
        testo_mosse += f"{num}. {m} " if idx % 2 == 0 else f"{m}  "
    pdf.set_font("helvetica", "", 9)
    pdf.multi_cell(0, 5, testo_mosse if testo_mosse else "Nessuna mossa registrata.")
    pdf.ln(4)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        tmp_img_path = tmp_file.name
    salva_immagine_scacchiera_png(board, tmp_img_path)
    y_inizio = pdf.get_y()
    if os.path.exists(tmp_img_path):
        pdf.image(tmp_img_path, x=10, y=y_inizio, w=85)
        os.remove(tmp_img_path)
    pdf.set_xy(100, y_inizio)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(95, 6, "Considerazioni per Mossa:", ln=True)
    for idx, m in enumerate(mosse_lista):
        num = (idx // 2) + 1
        etichetta = f"{num}. {m}" if idx % 2 == 0 else f"{num}... {m}"
        nota_utente = note_mosse.get(str(idx), "").strip()
        pdf.set_x(100)
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(95, 5, f"[{etichetta}]", ln=True)
        if nota_utente:
            pdf.set_x(100)
            pdf.set_font("helvetica", "", 8)
            pdf.multi_cell(95, 4, f"Note: {nota_utente}")
        pdf.set_x(100)
        pdf.cell(95, 4, "________________________________________", ln=True)
        pdf.ln(1)
    return bytes(pdf.output())

def render_eval_graph(eval_history, errors):
    if not HAS_PLOTLY or not eval_history: return
    x_vals = [e["ply"] for e in eval_history]
    y_vals = [e["eval_clamped"] for e in eval_history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode="lines", fill="tozeroy", line=dict(color="#FFD700", width=2), fillcolor="rgba(255,215,0,0.15)", name="Valutazione"))
    
    def get_y(ply):
        for e in eval_history:
            if e["ply"] == ply: return e["eval_clamped"]
        return 0

    blunders = [e["mossa_num"] for e in errors if "Blunder" in e["tipo_problema"]]
    mistakes = [e["mossa_num"] for e in errors if "Mistake" in e["tipo_problema"]]
    inaccuracies = [e["mossa_num"] for e in errors if "Inaccuracy" in e["tipo_problema"]]

    if inaccuracies:
        fig.add_trace(go.Scatter(x=inaccuracies, y=[get_y(n) for n in inaccuracies], mode="markers", marker=dict(color="#eab308", size=9), name="Inaccuracy"))
    if mistakes:
        fig.add_trace(go.Scatter(x=mistakes, y=[get_y(n) for n in mistakes], mode="markers", marker=dict(color="#f97316", size=10), name="Mistake"))
    if blunders:
        fig.add_trace(go.Scatter(x=blunders, y=[get_y(n) for n in blunders], mode="markers", marker=dict(color="#ef4444", size=12, symbol="x"), name="Blunder"))

    fig.update_layout(template='plotly_dark' if st.session_state['theme_mode'] == 'Dark' else 'plotly_white', height=320, margin=dict(l=10, r=10, t=30, b=10), showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# SEZIONE 1: CONTROL ROOM (DASHBOARD & INSIGHTS)
# ==========================================
if current_selection == "📊 Dashboard & Insights":
    st.markdown("<div class='section-title'>📊 Control Room & Insights Personali</div>", unsafe_allow_html=True)
    df_err = carica_errori_db(user_email)

    if user_tier in ["Pro", "Diamond"]:
        st.markdown(f"<div class='success-box'>🟢 Sincronizzazione automatica notturna attiva per il piano <b>{user_tier}</b>. Le tue partite vengono sincronizzate e censite in background.</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='info-box'>⚪ Piano Free attivo. <a href='#' target='_self'>Passa a Pro o Diamond</a> per attivare lo scaricamento automatico notturno delle partite.</div>", unsafe_allow_html=True)

    if not df_err.empty:
        n_errors = len(df_err)
        n_games = df_err['partita_id'].nunique() if 'partita_id' in df_err else 0
        avg_err_per_game = n_errors / max(n_games, 1)
        precision = max(0, min(100, int(100 - avg_err_per_game * 6)))

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.markdown(f"<div class='metric-card blue'><div class='metric-icon'>🎯</div><div class='metric-value'>{n_errors}</div><div class='metric-label'>Totale Errori Censiti</div></div>", unsafe_allow_html=True)
        kpi2.markdown(f"<div class='metric-card purple'><div class='metric-icon'>♟️</div><div class='metric-value'>{n_games}</div><div class='metric-label'>Partite Analizzate</div></div>", unsafe_allow_html=True)
        kpi3.markdown(f"<div class='metric-card green'><div class='metric-icon'>✨</div><div class='metric-value'>{precision}%</div><div class='metric-label'>Indice Precisione</div></div>", unsafe_allow_html=True)

        st.markdown("<div class='section-title'>🎯 Distribuzione Cluster di Errore</div>", unsafe_allow_html=True)
        if HAS_PLOTLY:
            counts_cat = df_err['categoria_errore'].value_counts()
            fig_pie = go.Figure(go.Pie(labels=counts_cat.index.tolist(), values=counts_cat.values.tolist(), hole=0.58))
            fig_pie.update_layout(template='plotly_dark' if st.session_state['theme_mode'] == 'Dark' else 'plotly_white', height=340, margin=dict(l=10, r=10, t=20, b=20))
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.markdown("<div class='info-box'>Nessun errore registrato nel cloud. Analizza qualche partita per popolare la tua Control Room!</div>", unsafe_allow_html=True)

# ==========================================
# SEZIONE 2: ANALIZZA PARTITA
# ==========================================
elif current_selection == "🔍 Analizza Partita":
    st.markdown("<div class='section-title'>📖 Analisi Dettagliata Partita</div>", unsafe_allow_html=True)

    pgn_val = st.session_state.get('pgn_manual_input', '')
    pgn_input = st.text_area("Incolla il PGN della partita:", value=pgn_val, height=140, key="pgn_area_input")

    if st.button(t["analyze_btn"], type="primary", use_container_width=True):
        if not pgn_input.strip(): st.warning("Inserisci un PGN valido.")
        else:
            current_pgn_text = pgn_input.strip()
            if st.session_state.get('last_analyzed_pgn') == current_pgn_text:
                st.warning(t['already_analyzed'])
            else:
                st.session_state['last_analyzed_pgn'] = current_pgn_text
                with st.spinner("🔍 Scansione Stockfish & Classificazione AI Cluster in corso..."):
                    user_profs = get_user_profiles(user_email)
                    user_usernames = [p['username'] for p in user_profs]
                    errori, p_id, err_msg, eval_hist = analizza_partita_chess_api(current_pgn_text, user_usernames)
                    st.session_state['stockfish_errors'] = errori
                    st.session_state['current_game_id'] = p_id
                    st.session_state['eval_history'] = eval_hist

                    game_obj = chess.pgn.read_game(io.StringIO(current_pgn_text))
                    if game_obj:
                        st.session_state['active_game_board'] = game_obj
                        st.session_state['active_game_moves'] = list(game_obj.mainline_moves())
                        st.session_state['current_board_ply'] = 0

                    if errori:
                        st.success(f"✅ Stockfish & AI: {len(errori)} {t['critique_found']}")
                        for item in errori:
                            salva_errore_db(user_email, p_id, item.get("categoria", "Positional Weakness"),
                                           item.get("label_mossa", "Mossa"), f"Perdita {item.get('perdita_cp')} CP")
                    else: st.success(f"✅ {t['no_errors']}")

    if st.session_state.get('eval_history'):
        st.markdown("<div class='section-title'>📈 Grafico di Valutazione</div>", unsafe_allow_html=True)
        render_eval_graph(st.session_state['eval_history'], st.session_state.get('stockfish_errors', []))

    if 'active_game_board' in st.session_state and st.session_state['active_game_board']:
        st.divider()
        game_moves = st.session_state['active_game_moves']
        max_ply = len(game_moves)
        current_ply = st.session_state['current_board_ply']

        c1, c2, c3, c4 = st.columns(4)
        if c1.button("⏪ Inizio", use_container_width=True): st.session_state['current_board_ply'] = 0; st.rerun()
        if c2.button("⬅️ Indietro", use_container_width=True) and current_ply > 0: st.session_state['current_board_ply'] -= 1; st.rerun()
        if c3.button("➡️ Avanti", use_container_width=True) and current_ply < max_ply: st.session_state['current_board_ply'] += 1; st.rerun()
        if c4.button("⏩ Fine", use_container_width=True): st.session_state['current_board_ply'] = max_ply; st.rerun()

        temp_board = st.session_state['active_game_board'].board()
        for i in range(st.session_state['current_board_ply']): temp_board.push(game_moves[i])

        svg_board = chess.svg.board(board=temp_board, size=430, colors={'square light': '#ebecd0', 'square dark': '#739552'})
        st.markdown(f'<div class="board-wrapper">{svg_board}</div>', unsafe_allow_html=True)

        st.markdown("<div class='section-title'>📋 Errori Rilevati e Cluster</div>", unsafe_allow_html=True)
        if st.session_state.get('stockfish_errors'):
            for idx, err in enumerate(st.session_state['stockfish_errors']):
                with st.expander(f"{err['tipo_problema']} · {err['label_mossa']} · Cluster: {err['categoria']} · -{err['perdita_cp']} CP", expanded=False):
                    st.markdown(f"**Mossa:** `{err['label_mossa']}` | **Cluster Tattico:** <span class='category-tag'>{err['categoria']}</span> | **Perdita:** -{err['perdita_cp']} CP", unsafe_allow_html=True)
                    
                    if st.button(t['gm_lesson_btn'], key=f"btn_lesson_{idx}", type="primary"):
                        with st.spinner("🎓 Il Grandemaster AI sta spiegando..."):
                            prompt_lesson = f"""
                            Sei un GM di scacchi. Spiega questo errore classificato come {err['categoria']}.
                            FEN: {err['fen_prima']}
                            Mossa errata: {err['mossa_giocata']}
                            {t['prompt_lang']}
                            Rispondi in massimo 3 righe con: 1. Errore; 2. Idea corretta; 3. Regola pratica.
                            """
                            client = genai.Client(api_key=MASTER_GEMINI_KEY) if "Client" in dir(genai) else None
                            if client:
                                resp = client.models.generate_content(model=GEMINI_MODEL_NAME, contents=prompt_lesson, config=types.GenerateContentConfig(max_output_tokens=100, temperature=0.2))
                                st.session_state[f"lesson_{idx}"] = resp.text
                            else:
                                genai.configure(api_key=MASTER_GEMINI_KEY)
                                resp = genai.GenerativeModel(GEMINI_MODEL_NAME).generate_content(prompt_lesson)
                                st.session_state[f"lesson_{idx}"] = resp.text

                    if f"lesson_{idx}" in st.session_state:
                        st.markdown(f"<div class='info-box'>💡 {st.session_state[f'lesson_{idx}']}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>Nessun errore registrato in questa partita.</div>", unsafe_allow_html=True)

# ==========================================
# SEZIONE 2B: IMPORTA & SINCRONIZZA
# ==========================================
elif current_selection == "🌐 Importa & Sincronizza":
    st.markdown("<div class='section-title'>🌐 Importa e Sincronizza Partite</div>", unsafe_allow_html=True)
    saved_profiles = get_user_profiles(user_email)

    col_i1, col_i2 = st.columns([2, 1])
    with col_i1:
        if saved_profiles:
            profile_options = [f"{p['piattaforma']}: {p['username']}" for p in saved_profiles]
            scelta_profilo = st.selectbox("Seleziona account:", profile_options)
            idx_sel = profile_options.index(scelta_profilo)
            plat, usr = saved_profiles[idx_sel]['piattaforma'], saved_profiles[idx_sel]['username']
        else:
            plat = st.radio("Piattaforma:", ["Lichess", "Chess.com"], horizontal=True)
            usr = st.text_input("Username:", value="")
    with col_i2:
        limite_partite = st.number_input("Partite da scaricare:", min_value=5, max_value=50, value=20)

    if st.button("📥 Scarica e Analizza", type="primary", use_container_width=True):
        if usr.strip():
            with st.spinner(f"Scaricamento partite per {usr}..."):
                try:
                    user_lower = usr.strip().lower()
                    if plat == "Lichess":
                        url_lic = f"https://lichess.org/api/games/user/{user_lower}"
                        r = requests.get(url_lic, params={"max": limite_partite}, headers={"Accept": "application/x-chess-pgn"}, timeout=20)
                        if r.status_code == 200: st.session_state['partite_importate'] = r.text; st.success("Scaricamento completato!")
                        else: st.error(f"Errore Lichess (HTTP {r.status_code})")
                    else:
                        r_arch = requests.get(f"https://api.chess.com/pub/player/{user_lower}/games/archives", headers={"User-Agent": "ChessCoachPro/1.0"}, timeout=10)
                        if r_arch.status_code == 200 and r_arch.json().get("archives"):
                            r_m = requests.get(r_arch.json()["archives"][-1], headers={"User-Agent": "ChessCoachPro/1.0"}, timeout=10)
                            games_j = r_m.json().get("games", [])[-limite_partite:][::-1]
                            st.session_state['partite_importate'] = "\n\n".join([g.get("pgn", "") for g in games_j if g.get("pgn")])
                            st.success("Scaricamento completato!")
                except Exception as e: st.error(f"Errore download: {e}")
        else: st.warning("Inserisci uno username valido.")

    if 'partite_importate' in st.session_state and st.session_state['partite_importate']:
        st.divider()
        raw_pgns = [p.strip() for p in st.session_state['partite_importate'].split("\n[Event ") if p.strip()]
        parsed_games = []
        for p in raw_pgns:
            full_p = "[Event " + p if not p.startswith("[Event") else p
            g_obj = chess.pgn.read_game(io.StringIO(full_p))
            if g_obj:
                parsed_games.append({"summary": f"{g_obj.headers.get('White','?')} vs {g_obj.headers.get('Black','?')}", "pgn": full_p})
        if parsed_games:
            sel_g = st.selectbox("Seleziona partita:", [g['summary'] for g in parsed_games])
            chosen_pgn = next(g['pgn'] for g in parsed_games if g['summary'] == sel_g)
            if st.button("🚀 Invia ad Analisi Stockfish", type="primary", use_container_width=True):
                st.session_state['pgn_manual_input'] = chosen_pgn
                st.session_state['goto_tab'] = "🔍 Analizza Partita"
                st.rerun()

# ==========================================
# SEZIONE 3: PALESTRA ALLENAMENTO (CON CLUSTER AVANZATI)
# ==========================================
elif current_selection == "🎯 Palestra sui Tuoi Errori":
    st.markdown("<div class='section-title'>🎯 Palestra di Allenamento Personalizzata</div>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8892a6;'>Allenati sui cluster tattici e di matto estratti dai tuoi errori reali.</p>", unsafe_allow_html=True)

    df_errori = carica_errori_db(user_email)

    if df_errori.empty:
        st.markdown("<div class='info-box'>Nessun errore registrato finora. Analizza qualche partita per sbloccare la tua palestra!</div>", unsafe_allow_html=True)
    else:
        cat_counts = df_errori['categoria_errore'].value_counts()
        punti_deboli = cat_counts.index.tolist()
        principale_debolezza = punti_deboli[0] if punti_deboli else "Fork"

        c_w1, c_w2 = st.columns([1, 2])
        c_w1.markdown(f"<div class='metric-card purple'><div class='metric-icon'>⚠️</div><div class='metric-value' style='font-size:1.3rem;'>{principale_debolezza}</div><div class='metric-label'>Punto Debole Principale</div></div>", unsafe_allow_html=True)
        c_w2.markdown(f"<div class='info-box'>💡 <b>Coach Tip:</b> Il cluster in cui commetti più errori è <b>{principale_debolezza}</b> ({cat_counts.iloc[0]} volte). Esercitati miratamente su questa tematica!</div>", unsafe_allow_html=True)

        st.divider()
        st.markdown("<div class='section-title'>🧩 Allenati sui Tuoi Errori per Cluster</div>", unsafe_allow_html=True)

        tema_scelto = st.selectbox("Filtra per Cluster Tematico:", ["Tutti i cluster"] + punti_deboli)
        df_es = df_errori.copy()
        if tema_scelto != "Tutti i cluster":
            df_es = df_es[df_es['categoria_errore'] == tema_scelto]

        if not df_es.empty:
            row_es = df_es.sample(1).iloc[0]
            st.markdown(f"**Partita:** `{row_es.get('partita_id')}` | **Cluster:** <span class='category-tag'>{row_es.get('categoria_errore')}</span>", unsafe_allow_html=True)
            st.markdown(f"<div class='warning-box'>In questa posizione hai sbagliato giocando <b>{row_es.get('mossa_critica')}</b>. Riconosci il tema tattico e trova la continuazione corretta!</div>", unsafe_allow_html=True)

            if st.button("💡 Mostra Aiuto GM", type="primary"):
                st.markdown(f"<div class='info-box'><b>Suggerimento sul tema {row_es.get('categoria_errore')}:</b> Fai attenzione alle diagonali aperte e alla protezione dei pezzi non difesi.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>Nessun esercizio disponibile per questo cluster.</div>", unsafe_allow_html=True)

# ==========================================
# SEZIONE 4A: STUDIO DA LIBRI
# ==========================================
elif current_selection == "📚 Studio da Libri":
    st.markdown("<div class='section-title'>📚 Studio da Libri con AI</div>", unsafe_allow_html=True)
    testo_libro_input = st.text_area("Incolla il testo del libro:", height=140)
    if st.button("🚀 Elabora Testo", type="primary"):
        if MASTER_GEMINI_KEY and testo_libro_input:
            try:
                genai.configure(api_key=MASTER_GEMINI_KEY)
                resp = genai.GenerativeModel(GEMINI_MODEL_NAME).generate_content(f"Estrai mosse e commenti in JSON: {{\"mosse_san\": [\"e4\"], \"commenti\": {{\"0\": \"Inizio\"}}}}. Testo: {testo_libro_input}")
                dati = json.loads(resp.text.replace("```json","").replace("```","").strip())
                board = chess.Board()
                steps = [{"ply": 0, "mossa_giocata": "Inizio", "fen": board.fen(), "commento": dati.get("commenti", {}).get("0", "")}]
                for idx, san in enumerate(dati.get("mosse_san", [])):
                    try:
                        move = board.parse_san(san)
                        board.push(move)
                        steps.append({"ply": idx+1, "mossa_giocata": san, "fen": board.fen(), "commento": dati.get("commenti", {}).get(str(idx+1), "")})
                    except Exception: break
                st.session_state['book_steps'] = steps
                st.session_state['book_ply'] = 0
                st.success("Studio pronto!")
            except Exception as e: st.error(f"Errore: {e}")

    if 'book_steps' in st.session_state and st.session_state['book_steps']:
        steps = st.session_state['book_steps']
        max_p = len(steps) - 1
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("⏪ Inizio", use_container_width=True): st.session_state['book_ply'] = 0; st.rerun()
        if c2.button("⬅️", use_container_width=True) and st.session_state['book_ply'] > 0: st.session_state['book_ply'] -= 1; st.rerun()
        if c3.button("➡️", use_container_width=True) and st.session_state['book_ply'] < max_p: st.session_state['book_ply'] += 1; st.rerun()
        if c4.button("⏩ Fine", use_container_width=True): st.session_state['book_ply'] = max_p; st.rerun()

        cur = steps[st.session_state['book_ply']]
        col_v1, col_v2 = st.columns([1, 1])
        with col_v1:
            svg = chess.svg.board(board=chess.Board(cur['fen']), size=340)
            st.markdown(f'<div class="board-wrapper">{svg}</div>', unsafe_allow_html=True)
        with col_v2:
            st.markdown(f"<div class='info-box'>💬 {cur.get('commento', '')}</div>", unsafe_allow_html=True)

# ==========================================
# SEZIONE 4B: DIARIO & PDF
# ==========================================
elif current_selection == "📝 Diario & PDF":
    st.markdown("<div class='section-title'>📝 Diario Partite & Report PDF</div>", unsafe_allow_html=True)
    input_d = st.text_area("Inserisci sequenza di mosse:", height=100)
    if st.button("🔄 Carica Scacchiera", type="primary"):
        if input_d.strip():
            try:
                b = chess.Board()
                l_m = []
                for m in input_d.split():
                    m_p = m.split(".")[-1]
                    if m_p and not m_p.isdigit():
                        b.push(b.parse_san(m_p)); l_m.append(m_p)
                st.session_state['diario_mosse'] = l_m
                st.session_state['diario_note_mosse'] = {}
                st.success("Caricato!")
            except Exception as e: st.error(f"Errore: {e}")

    if 'diario_mosse' in st.session_state and st.session_state['diario_mosse']:
        mosse_d = st.session_state['diario_mosse']
        b_d = chess.Board()
        for m in mosse_d: b_d.push(b_d.parse_san(m))
        col_d1, col_d2 = st.columns([1, 1])
        with col_d1:
            svg = chess.svg.board(board=b_d, size=340)
            st.markdown(f'<div class="board-wrapper">{svg}</div>', unsafe_allow_html=True)
        with col_d2:
            for idx, m in enumerate(mosse_d):
                st.session_state['diario_note_mosse'][str(idx)] = st.text_input(f"Nota {m}:", value=st.session_state['diario_note_mosse'].get(str(idx), ""), key=f"note_pdf_{idx}")
        if st.button("⚙️ Genera ed Esporta PDF", type="primary"):
            pdf_b = genera_pdf_partita(b_d, mosse_d, st.session_state['diario_note_mosse'], "")
            st.download_button("📥 Scarica Report PDF", data=pdf_b, file_name="diario_partita.pdf", mime="application/pdf")

# ==========================================
# SEZIONE 4C: PIANI ABBONAMENTO
# ==========================================
elif current_selection == "💎 Piani Abbonamento":
    st.markdown("<div class='section-title'>💎 Scegli il tuo Piano</div>", unsafe_allow_html=True)
    col_pr1, col_pr2, col_pr3 = st.columns(3)

    with col_pr1:
        st.markdown("<div class='pricing-card'><div class='pricing-title'>Free</div><div class='pricing-price'>€0</div><ul class='pricing-features'><li>✅ 1 Profilo</li><li>✅ Analisi Base</li></ul></div>", unsafe_allow_html=True)
        if user_tier == "Free": st.button("Attuale", disabled=True, use_container_width=True, key="b_f")
        else:
            if st.button("Passa a Free", use_container_width=True, key="b_tf"): registra_nuovo_abbonamento(user_email, "Free"); st.rerun()

    with col_pr2:
        st.markdown("<div class='pricing-card featured'><div class='tier-badge badge-pro'>Popolare</div><div class='pricing-title'>Pro</div><div class='pricing-price'>€4.99</div><ul class='pricing-features'><li>✅ 3 Profili</li><li>✅ Sincronizzazione Notturna</li><li>✅ Palestra Avanzata</li></ul></div>", unsafe_allow_html=True)
        if user_tier == "Pro": st.button("Attuale", disabled=True, use_container_width=True, key="b_p")
        else:
            if st.button("Sottoscrivi Pro 🚀", type="primary", use_container_width=True, key="b_tp"):
                if HAS_STRIPE and STRIPE_SECRET_KEY:
                    try:
                        host = st.context.headers.get("Host", "tuo-dominio.streamlit.app")
                        proto = "https" if "localhost" not in host else "http"
                        checkout_session = stripe.checkout.Session.create(
                            line_items=[{'price': STRIPE_PRO_PRICE_ID, 'quantity': 1}],
                            mode='subscription', success_url=f"{proto}://{host}/?success=pro", cancel_url=f"{proto}://{host}/?canceled=true", customer_email=user_email
                        )
                        st.components.v1.html(f"<script>window.top.location.href = '{checkout_session.url}';</script>", height=0)
                        st.link_button("👉 Clicca qui se non vieni reindirizzato", checkout_session.url, use_container_width=True)
                    except Exception as e: st.error(f"Errore Stripe: {e}")
                else:
                    registra_nuovo_abbonamento(user_email, "Pro")
                    st.success("Abbonamento Pro attivato (Test)!")
                    time.sleep(1)
                    st.rerun()

    with col_pr3:
        st.markdown("<div class='pricing-card'><div class='tier-badge badge-diamond'>Elite</div><div class='pricing-title'>Diamond</div><div class='pricing-price'>€9.99</div><ul class='pricing-features'><li>✅ 5 Profili</li><li>✅ Sync Prioritario</li><li>✅ Supporto 24/7</li></ul></div>", unsafe_allow_html=True)
        if user_tier == "Diamond": st.button("Attuale", disabled=True, use_container_width=True, key="b_d")
        else:
            if st.button("Sottoscrivi Diamond 💎", type="primary", use_container_width=True, key="b_td"):
                if HAS_STRIPE and STRIPE_SECRET_KEY:
                    try:
                        host = st.context.headers.get("Host", "tuo-dominio.streamlit.app")
                        proto = "https" if "localhost" not in host else "http"
                        checkout_session = stripe.checkout.Session.create(
                            line_items=[{'price': STRIPE_DIAMOND_PRICE_ID, 'quantity': 1}],
                            mode='subscription', success_url=f"{proto}://{host}/?success=diamond", cancel_url=f"{proto}://{host}/?canceled=true", customer_email=user_email
                        )
                        st.components.v1.html(f"<script>window.top.location.href = '{checkout_session.url}';</script>", height=0)
                        st.link_button("👉 Clicca qui se non vieni reindirizzato", checkout_session.url, use_container_width=True)
                    except Exception as e: st.error(f"Errore Stripe: {e}")
                else:
                    registra_nuovo_abbonamento(user_email, "Diamond")
                    st.success("Abbonamento Diamond attivato (Test)!")
                    time.sleep(1)
                    st.rerun()

# ==========================================
# SEZIONE 4D: CONTATTI & SUPPORTO
# ==========================================
elif current_selection == "📞 Contatti & Supporto":
    st.markdown("<div class='section-title'>📞 Contatti & Supporto</div>", unsafe_allow_html=True)
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("<div class='info-box'>Hai riscontrato un bug o hai suggerimenti? Scrivici a <b>support@chesscoachpro.com</b>.</div>", unsafe_allow_html=True)
        st.link_button("☕ Offrici un Caffè", "https://buymeacoffee.com", use_container_width=True)
    with col_c2:
        with st.form("contact_form"):
            c_name = st.text_input("Il tuo nome o username:")
            c_msg = st.text_area("Messaggio / Segnalazione:")
            if st.form_submit_button("Invia Messaggio", type="primary", use_container_width=True):
                if c_name.strip() and c_msg.strip(): st.success("Messaggio inviato con successo!")
                else: st.warning("Compila tutti i campi.")
