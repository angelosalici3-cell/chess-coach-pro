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
from supabase import create_client, Client

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# --- CONFIGURAZIONE CENTRALIZZATA ---
MASTER_GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

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

# --- GESTIONE STATO ---
for key, default in {
    'user': None, 'lang': 'it', 'profile_setup_done': False,
    'active_nav_tab': 0, 'theme_mode': 'Dark',
    'last_analyzed_pgn': None, 'current_board_ply': 0,
    'eval_history': None
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- KEEP-ALIVE MOBILE ---
st.components.v1.html("""
    <script>setInterval(function(){fetch(window.location.href);},25000);</script>
""", height=0)

# --- CSS DINAMICO PREMIUM ---
def get_dynamic_css(theme):
    # FIX: header visibile + hamburger menu ben evidente e cliccabile.
    common_fix = """
        #MainMenu { visibility: hidden !important; }
        footer { visibility: hidden !important; }
        [data-testid="stToolbar"] { visibility: hidden !important; }
        [data-testid="stDecoration"] { visibility: hidden !important; }
        [data-testid="stStatusWidget"] { visibility: hidden !important; }

        /* Header trasparente ma sopra tutto per garantire il click */
        header[data-testid="stHeader"] {
            background: transparent !important;
            backdrop-filter: none !important;
            z-index: 999990 !important;
            pointer-events: auto !important;
        }

        /* ===== HAMBURGER MENU FORZATO VISIBILE ===== */
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"],
        button[kind="header"] {
            display: inline-flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            align-items: center !important;
            justify-content: center !important;
            background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important;
            border-radius: 10px !important;
            padding: 8px !important;
            margin: 8px !important;
            width: 42px !important;
            height: 42px !important;
            box-shadow: 0 4px 14px rgba(255, 165, 0, 0.45) !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease !important;
            z-index: 999999 !important;
            border: none !important;
        }
        [data-testid="collapsedControl"]:hover,
        [data-testid="stSidebarCollapsedControl"]:hover,
        button[kind="header"]:hover {
            transform: scale(1.08) !important;
            box-shadow: 0 6px 20px rgba(255, 165, 0, 0.7) !important;
        }
        [data-testid="collapsedControl"] svg,
        [data-testid="stSidebarCollapsedControl"] svg,
        button[kind="header"] svg {
            fill: #0a0e1a !important;
            color: #0a0e1a !important;
            stroke: #0a0e1a !important;
            width: 22px !important;
            height: 22px !important;
        }

        /* Quando la sidebar è APERTA, il bottone di chiusura nella sidebar */
        [data-testid="stSidebar"] [data-testid="baseButton-header"] {
            color: #FFD700 !important;
        }
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

        .error-card {
            background: linear-gradient(135deg, rgba(20,26,42,0.85), rgba(15,20,32,0.85));
            border-left: 3px solid #ef4444;
            padding: 1rem 1.1rem; border-radius: 12px; margin-bottom: 0.7rem;
        }
        .error-card.mistake  { border-left-color: #f97316; }
        .error-card.inaccuracy { border-left-color: #eab308; }
        .error-header { display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: center; }
        .error-move  { font-family: 'JetBrains Mono', monospace; font-weight: 700;
                       color: #FFD700; background: rgba(255,215,0,0.08);
                       padding: 3px 10px; border-radius: 8px; font-size: 0.9rem; }
        .error-loss  { color: #f87171; font-weight: 700; font-size: 0.85rem; }

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

        .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.06); }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px 10px 0 0; padding: 0.6rem 1.2rem;
            background: transparent; color: #8892a6;
        }
        .stTabs [aria-selected="true"] {
            background: rgba(255,215,0,0.08) !important;
            color: #FFD700 !important; font-weight: 700;
        }

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

        .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; border-bottom: 1px solid #e2e8f0; }
        .stTabs [data-baseweb="tab"] { border-radius: 10px 10px 0 0; padding: 0.6rem 1.2rem;
            background: transparent; color: #64748b; }
        .stTabs [aria-selected="true"] {
            background: rgba(212,175,55,0.1) !important; color: #b8860b !important; font-weight: 700;
        }
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #d4af37, #b8860b) !important;
        }
        div[data-testid="stMetricValue"] { color: #b8860b !important; font-family: 'Outfit', sans-serif; }
        hr { border-color: #e2e8f0 !important; }
        </style>"""

st.markdown(get_dynamic_css(st.session_state['theme_mode']), unsafe_allow_html=True)

# --- Plotly theme helper ---
def plotly_template():
    return 'plotly_dark' if st.session_state['theme_mode'] == 'Dark' else 'plotly_white'

TEXTS = {
    "it": {
        "title": "Chess Coach Pro", "subtitle": "Coaching Scacchistico AI ad Altissima Efficienza",
        "tab1": "📖 Analizza", "tab2": "📊 Dashboard", "tab3": "📚 Libri", "tab4": "📝 Diario", "tab5": "🌐 Importa",
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

# --- DATABASE HELPERS ---
def get_user_tier(email):
    if supabase:
        try:
            res = supabase.table("config_utenti").select("tier").eq("user_email", email).execute()
            if res.data and res.data[0].get("tier"):
                return res.data[0].get("tier")
        except Exception:
            pass
    return "Free"

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
# ENGINE
# ==========================================
def determina_categoria_mossa(num_mossa, delta_cp, total_moves):
    if num_mossa <= 12: return "Apertura"
    elif num_mossa >= total_moves - 10 or (total_moves > 40 and num_mossa > 30): return "Finale"
    elif delta_cp >= 2.0: return "Tattica"
    else: return "Posizionale"

def analizza_partita_chess_api(pgn_text, target_usernames):
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if not game:
        return [], None, "Impossibile leggere il PGN fornito.", []

    headers = game.headers
    white_player = headers.get('White', 'Unknown').strip().lower()
    black_player = headers.get('Black', 'Unknown').strip().lower()
    user_is_white = True
    user_is_black = True

    if target_usernames:
        user_list = [u.strip().lower() for u in target_usernames]
        found_match = False
        user_is_white = False
        user_is_black = False
        for u in user_list:
            if u in white_player: user_is_white = True; found_match = True
            if u in black_player: user_is_black = True; found_match = True
        if not found_match:
            user_is_white = True; user_is_black = True

    partita_id = f"{headers.get('White', 'Unknown')}_vs_{headers.get('Black', 'Unknown')}_{headers.get('Date', 'Live')}"
    board = game.board()
    evaluations = []
    eval_history = []
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
        try:
            move_san = board.san(move)
        except Exception:
            move_san = move.uci()

        eval_before = prev_eval
        try:
            r = session.post("https://chess-api.com/v1", json={"fen": fen_before, "depth": 10}, timeout=4)
            if r.status_code == 200:
                data = r.json()
                if data.get("eval") is not None:
                    eval_before = float(data.get("eval"))
                elif data.get("mate") is not None:
                    eval_before = 100.0 if data.get("mate") > 0 else -100.0
        except Exception:
            pass

        board.push(move)
        fen_after = board.fen()
        num_mossa = (idx // 2) + 1
        is_white_move = (idx % 2 == 0)
        progress_bar.progress((idx + 1) / max(total_ply_count, 1),
                              text=f"♟️ Analisi mossa {num_mossa} di {total_full_moves}...")

        eval_after = eval_before
        try:
            r = session.post("https://chess-api.com/v1", json={"fen": fen_after, "depth": 10}, timeout=4)
            if r.status_code == 200:
                data = r.json()
                if data.get("eval") is not None:
                    eval_after = float(data.get("eval"))
                elif data.get("mate") is not None:
                    eval_after = 100.0 if data.get("mate") > 0 else -100.0
        except Exception:
            pass

        clamped = max(min(eval_after, 10.0), -10.0)
        eval_history.append({
            "ply": idx + 1, "num_move": num_mossa, "san": move_san,
            "eval_cp": eval_after, "eval_clamped": clamped, "is_white": is_white_move
        })

        is_user_move = (is_white_move and user_is_white) or (not is_white_move and user_is_black)
        if is_user_move:
            delta = (eval_before - eval_after) if is_white_move else (eval_after - eval_before)
            if delta >= 2.0: tipo_problema = "🔴 Blunder"
            elif delta >= 1.0: tipo_problema = "🟠 Mistake"
            elif delta >= 0.5: tipo_problema = "🟡 Inaccuracy"
            else: tipo_problema = None
            if tipo_problema:
                label_mossa = f"{num_mossa}. {move_san}" if is_white_move else f"{num_mossa}... {move_san}"
                cat_mossa = determina_categoria_mossa(num_mossa, round(delta, 2), total_full_moves)
                evaluations.append({
                    "mossa_num": idx + 1, "label_mossa": label_mossa,
                    "fen_prima": fen_before, "fen_dopo": fen_after,
                    "mossa_giocata": move.uci(), "perdita_cp": round(delta, 2),
                    "eval_dopo": eval_after, "tipo_problema": tipo_problema, "categoria": cat_mossa
                })
        prev_eval = eval_after
        time.sleep(0.03)

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
    """Grafico di valutazione stile chess.com con marker sugli errori."""
    if not HAS_PLOTLY or not eval_history:
        return
    x_vals = [e["ply"] for e in eval_history]
    y_vals = [e["eval_clamped"] for e in eval_history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals, mode="lines", fill="tozeroy",
        line=dict(color="#FFD700", width=2),
        fillcolor="rgba(255,215,0,0.15)",
        name="Valutazione",
        hovertemplate="Mossa %{x}<br>Eval: %{y:.2f}<extra></extra>",
    ))

    def get_y(ply):
        for e in eval_history:
            if e["ply"] == ply:
                return e["eval_clamped"]
        return 0

    blunders = [e["mossa_num"] for e in errors if "Blunder" in e["tipo_problema"]]
    mistakes = [e["mossa_num"] for e in errors if "Mistake" in e["tipo_problema"]]
    inaccuracies = [e["mossa_num"] for e in errors if "Inaccuracy" in e["tipo_problema"]]

    if inaccuracies:
        fig.add_trace(go.Scatter(
            x=inaccuracies, y=[get_y(n) for n in inaccuracies], mode="markers",
            marker=dict(color="#eab308", size=9, line=dict(width=1, color="#fff")),
            name="Inaccuracy"))
    if mistakes:
        fig.add_trace(go.Scatter(
            x=mistakes, y=[get_y(n) for n in mistakes], mode="markers",
            marker=dict(color="#f97316", size=10, line=dict(width=1, color="#fff")),
            name="Mistake"))
    if blunders:
        fig.add_trace(go.Scatter(
            x=blunders, y=[get_y(n) for n in blunders], mode="markers",
            marker=dict(color="#ef4444", size=12, symbol="x", line=dict(width=2, color="#fff")),
            name="Blunder"))

    fig.update_layout(
        template=plotly_template(),
        margin=dict(l=10, r=10, t=30, b=10),
        height=320, showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="Mossa", showgrid=False),
        yaxis=dict(title="Valutazione (pedoni)", range=[-10, 10],
                   showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

# --- SIDEBAR ---
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

    st.markdown("<div class='section-title' style='font-size:1.05rem;margin-top:0.5rem;'>⚙️ Preferenze</div>", unsafe_allow_html=True)

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
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
        st.session_state['user'] = None
        st.session_state['profile_setup_done'] = False
        st.rerun()

# --- HEADER ---
st.markdown(f"""
<div class="hero">
    <span class="hero-logo">♟️</span>
    <div class="brand-title">{t['title']}</div>
    <p class="brand-sub">{t['subtitle']}</p>
</div>
""", unsafe_allow_html=True)

# --- NAVIGAZIONE ---
nav_labels = [t["tab1"], t["tab2"], t["tab3"], t["tab4"], t["tab5"]]
cols_nav = st.columns(len(nav_labels))
for idx, label in enumerate(nav_labels):
    is_active = (st.session_state['active_nav_tab'] == idx)
    btn_type = "primary" if is_active else "secondary"
    if cols_nav[idx].button(label, key=f"nav_btn_{idx}", type=btn_type, use_container_width=True):
        st.session_state['active_nav_tab'] = idx
        st.rerun()

st.write("")
current_tab = st.session_state['active_nav_tab']

# ==========================================
# TAB 0: ANALIZZA
# ==========================================
if current_tab == 0:
    st.markdown("<div class='section-title'>📖 Analizza una Partita</div>", unsafe_allow_html=True)

    pgn_val = st.session_state.get('pgn_manual_input', '')
    pgn_input = st.text_area("Incolla il PGN della partita:", value=pgn_val, height=140, key="pgn_area_input")

    if st.button(t["analyze_btn"], type="primary", use_container_width=True):
        if not pgn_input.strip():
            st.markdown("<div class='warning-box'>Inserisci un PGN valido.</div>", unsafe_allow_html=True)
        else:
            pgn_hash = hash(pgn_input.strip())
            if st.session_state.get('last_analyzed_pgn') == pgn_hash:
                st.markdown(f"<div class='warning-box'>{t['already_analyzed']}</div>", unsafe_allow_html=True)
            else:
                st.session_state['last_analyzed_pgn'] = pgn_hash
                with st.spinner("🔍 Scansione affidabile Stockfish in corso..."):
                    user_profs = get_user_profiles(user_email)
                    user_usernames = [p['username'] for p in user_profs]
                    errori, p_id, err_msg, eval_hist = analizza_partita_chess_api(pgn_input.strip(), user_usernames)
                    st.session_state['stockfish_errors'] = errori
                    st.session_state['current_game_id'] = p_id
                    st.session_state['eval_history'] = eval_hist

                    game_obj = chess.pgn.read_game(io.StringIO(pgn_input.strip()))
                    if game_obj:
                        st.session_state['active_game_board'] = game_obj
                        st.session_state['active_game_moves'] = list(game_obj.mainline_moves())
                        st.session_state['current_board_ply'] = 0

                    if errori:
                        st.markdown(f"<div class='success-box'>✅ Stockfish: <b>{len(errori)}</b> {t['critique_found']}</div>", unsafe_allow_html=True)
                        for item in errori:
                            salva_errore_db(user_email, p_id, item.get("categoria", "Tattica"),
                                           item.get("label_mossa", "Mossa"), f"Perdita {item.get('perdita_cp')} CP")
                    else:
                        st.markdown(f"<div class='success-box'>✅ {t['no_errors']}</div>", unsafe_allow_html=True)

    # Grafico di valutazione (chess.com style)
    if st.session_state.get('eval_history'):
        st.markdown("<div class='section-title'>📈 Grafico di Valutazione</div>", unsafe_allow_html=True)
        render_eval_graph(st.session_state['eval_history'], st.session_state.get('stockfish_errors', []))

    if 'active_game_board' in st.session_state and st.session_state['active_game_board']:
        st.divider()
        game_moves = st.session_state['active_game_moves']
        max_ply = len(game_moves)
        total_full_moves = (max_ply + 1) // 2
        current_ply = st.session_state['current_board_ply']
        current_full_move = (current_ply + 1) // 2

        st.markdown(f"<div class='section-title'>♟️ Scacchiera — Mossa {current_full_move} di {total_full_moves}</div>", unsafe_allow_html=True)

        c_b1, c_b2, c_b3, c_b4 = st.columns(4)
        if c_b1.button("⏪ Inizio", use_container_width=True):
            st.session_state['current_board_ply'] = 0; st.rerun()
        if c_b2.button("⬅️ Indietro", use_container_width=True) and current_ply > 0:
            st.session_state['current_board_ply'] -= 1; st.rerun()
        if c_b3.button("➡️ Avanti", use_container_width=True) and current_ply < max_ply:
            st.session_state['current_board_ply'] += 1; st.rerun()
        if c_b4.button("⏩ Fine", use_container_width=True):
            st.session_state['current_board_ply'] = max_ply; st.rerun()

        temp_board = st.session_state['active_game_board'].board()
        for i in range(st.session_state['current_board_ply']):
            temp_board.push(game_moves[i])

        svg_board = chess.svg.board(
            board=temp_board, size=430,
            colors={'square light': '#ebecd0', 'square dark': '#739552'}
        )
        st.markdown(f'<div class="board-wrapper">{svg_board}</div>', unsafe_allow_html=True)

        st.markdown("<div class='section-title'>📋 Errori Rilevati sulle Tue Mosse</div>", unsafe_allow_html=True)
        if st.session_state.get('stockfish_errors'):
            for idx, err in enumerate(st.session_state['stockfish_errors']):
                cat_label = err.get('categoria', 'Tattica')
                severity = "Blunder" if "Blunder" in err['tipo_problema'] else ("Mistake" if "Mistake" in err['tipo_problema'] else "Inaccuracy")
                sev_class = "blunder" if severity == "Blunder" else ("mistake" if severity == "Mistake" else "inaccuracy")

                with st.expander(f"{err['tipo_problema']} · {err['label_mossa']} · Categoria: {cat_label} · -{err['perdita_cp']} CP", expanded=False):
                    st.markdown(f"""
                    <div class="error-card {sev_class}">
                        <div class="error-header">
                            <span class="error-move">{err['label_mossa']}</span>
                            <span class="error-loss">Perdita: -{err['perdita_cp']} CP</span>
                            <span class="category-tag">{cat_label}</span>
                            <span class="category-tag">{severity}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    btn_key = f"btn_lesson_{idx}"
                    if st.button(f"{t['gm_lesson_btn']}", key=btn_key, type="primary", use_container_width=True):
                        if not MASTER_GEMINI_KEY or "INSERISCI" in MASTER_GEMINI_KEY:
                            st.markdown("<div class='error-box'>⚠️ Chiave GEMINI_API_KEY non configurata nei Secrets!</div>", unsafe_allow_html=True)
                        else:
                            with st.spinner("🎓 Il Grandemaster AI sta analizzando..."):
                                try:
                                    prompt_lesson = f"""
                                    Sei un Grandemaster di scacchi.
                                    Posizione FEN prima della mossa: {err['fen_prima']}
                                    Mossa errata giocata: {err['mossa_giocata']}
                                    {t['prompt_lang']}
                                    Spiega in massimo 35 parole:
                                    1. Perché la mossa è un errore.
                                    2. Qual era l'idea migliore.
                                    3. Una regola/principio pratico.
                                    """
                                    try:
                                        from google import genai as new_genai
                                        client = new_genai.Client(api_key=MASTER_GEMINI_KEY)
                                        response = client.models.generate_content(
                                            model=GEMINI_MODEL_NAME, contents=prompt_lesson
                                        )
                                        st.session_state[f"lesson_{idx}"] = response.text
                                    except Exception:
                                        genai.configure(api_key=MASTER_GEMINI_KEY)
                                        model_gm = genai.GenerativeModel(GEMINI_MODEL_NAME)
                                        resp = model_gm.generate_content(prompt_lesson)
                                        st.session_state[f"lesson_{idx}"] = resp.text
                                except Exception as e:
                                    st.markdown(f"<div class='error-box'>❌ Errore: {e}</div>", unsafe_allow_html=True)

                    if f"lesson_{idx}" in st.session_state:
                        st.markdown(f"<div class='info-box'>💡 {st.session_state[f'lesson_{idx}']}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>Nessun errore grave registrato sulle tue mosse in questa partita.</div>", unsafe_allow_html=True)

# ==========================================
# TAB 1: DASHBOARD (senza tabella dettagliata)
# ==========================================
elif current_tab == 1:
    st.markdown("<div class='section-title'>📊 La Tua Dashboard</div>", unsafe_allow_html=True)
    df_err = carica_errori_db(user_email)

    if not df_err.empty:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            partite_disponibili = ["Tutte le partite"] + list(df_err['partita_id'].dropna().unique())
            filtro_partita = st.selectbox("Filtra per Partita:", partite_disponibili)
        with col_f2:
            tipi_disponibili = ["Tutti i tipi"] + list(df_err['categoria_errore'].dropna().unique())
            filtro_tipo = st.selectbox("Filtra per Tipo di Errore:", tipi_disponibili)

        df_filtered = df_err.copy()
        if filtro_partita != "Tutte le partite":
            df_filtered = df_filtered[df_filtered['partita_id'] == filtro_partita]
        if filtro_tipo != "Tutti i tipi":
            df_filtered = df_filtered[df_filtered['categoria_errore'] == filtro_tipo]

        st.write("")
        n_errors = len(df_filtered)
        n_games = df_filtered['partita_id'].nunique() if 'partita_id' in df_filtered else 0
        avg_err_per_game = n_errors / max(n_games, 1)
        precision = max(0, min(100, int(100 - avg_err_per_game * 6)))

        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.markdown(f"""
            <div class="metric-card blue">
                <div class="metric-icon">🎯</div>
                <div class="metric-value">{n_errors}</div>
                <div class="metric-label">Totale Errori</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi2:
            st.markdown(f"""
            <div class="metric-card purple">
                <div class="metric-icon">♟️</div>
                <div class="metric-value">{n_games}</div>
                <div class="metric-label">Partite Analizzate</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi3:
            st.markdown(f"""
            <div class="metric-card green">
                <div class="metric-icon">✨</div>
                <div class="metric-value">{precision}%</div>
                <div class="metric-label">Indice Precisione</div>
            </div>
            """, unsafe_allow_html=True)

        st.write("")
        col_g1, col_g2 = st.columns([1, 1])

        with col_g1:
            st.markdown("<div class='section-title'>🎯 Distribuzione Errori</div>", unsafe_allow_html=True)
            if not df_filtered.empty:
                if HAS_PLOTLY:
                    counts_cat = df_filtered['categoria_errore'].value_counts()
                    palette = ['#FFD700', '#FFA500', '#7c3aed', '#3b82f6', '#10b981', '#ef4444']
                    fig_pie = go.Figure(go.Pie(
                        labels=counts_cat.index.tolist(),
                        values=counts_cat.values.tolist(),
                        hole=0.58,
                        marker=dict(colors=palette[:len(counts_cat)],
                                    line=dict(color='rgba(255,255,255,0.1)', width=1)),
                        textinfo='label+percent',
                        textfont=dict(size=12, color='#e8eaf0' if st.session_state['theme_mode'] == 'Dark' else '#1a202c')
                    ))
                    fig_pie.update_layout(
                        template=plotly_template(), height=340,
                        margin=dict(l=10, r=10, t=20, b=20),
                        showlegend=True,
                        legend=dict(orientation='v', yanchor='middle', y=0.5, x=1.0)
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.bar_chart(df_filtered['categoria_errore'].value_counts(), use_container_width=True)
            else:
                st.markdown("<div class='info-box'>Nessun dato per i filtri selezionati.</div>", unsafe_allow_html=True)

        with col_g2:
            st.markdown("<div class='section-title'>🎚️ Indice di Precisione</div>", unsafe_allow_html=True)
            if HAS_PLOTLY:
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=precision,
                    number={'suffix': '%', 'font': {'color': '#FFD700' if st.session_state['theme_mode'] == 'Dark' else '#b8860b', 'size': 42}},
                    gauge={
                        'axis': {'range': [0, 100], 'tickcolor': '#8892a6'},
                        'bar': {'color': '#FFD700' if st.session_state['theme_mode'] == 'Dark' else '#d4af37', 'thickness': 0.3},
                        'bgcolor': 'rgba(0,0,0,0)',
                        'steps': [
                            {'range': [0, 40],  'color': 'rgba(239,68,68,0.18)'},
                            {'range': [40, 70], 'color': 'rgba(234,179,8,0.18)'},
                            {'range': [70, 100],'color': 'rgba(16,185,129,0.18)'}
                        ],
                        'threshold': {
                            'line': {'color': '#10b981', 'width': 4},
                            'thickness': 0.75, 'value': 80
                        }
                    }
                ))
                fig_gauge.update_layout(
                    template=plotly_template(), height=340,
                    margin=dict(l=10, r=10, t=30, b=10)
                )
                st.plotly_chart(fig_gauge, use_container_width=True)
            else:
                st.metric("Precisione", f"{precision}%")

        st.markdown("<div class='section-title'>📈 Trend Errori nel Tempo</div>", unsafe_allow_html=True)
        if not df_filtered.empty and 'data' in df_filtered.columns:
            if HAS_PLOTLY:
                counts_date = df_filtered.groupby('data').size().reset_index(name='count')
                counts_date = counts_date.sort_values('data')
                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(
                    x=counts_date['data'].tolist(),
                    y=counts_date['count'].tolist(),
                    mode='lines+markers',
                    line=dict(color='#FFD700' if st.session_state['theme_mode'] == 'Dark' else '#d4af37', width=2.5),
                    fill='tozeroy',
                    fillcolor='rgba(255,215,0,0.15)' if st.session_state['theme_mode'] == 'Dark' else 'rgba(212,175,55,0.15)',
                    marker=dict(size=9, color='#FFD700' if st.session_state['theme_mode'] == 'Dark' else '#d4af37',
                                line=dict(width=2, color='#0a0e1a' if st.session_state['theme_mode'] == 'Dark' else '#ffffff')),
                    hovertemplate='Data: %{x}<br>Errori: %{y}<extra></extra>'
                ))
                fig_line.update_layout(
                    template=plotly_template(), height=320,
                    margin=dict(l=10, r=10, t=20, b=10),
                    xaxis=dict(showgrid=False, title=""),
                    yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.15)', title="Numero Errori"),
                    hovermode='x unified'
                )
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.line_chart(df_filtered.groupby('data').size(), use_container_width=True)
        else:
            st.markdown("<div class='info-box'>Dati temporali non sufficienti.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='info-box'>Nessun errore salvato nel cloud. Analizza qualche partita per popolare la tua Dashboard di crescita!</div>", unsafe_allow_html=True)

# ==========================================
# TAB 2: LIBRI
# ==========================================
elif current_tab == 2:
    st.markdown("<div class='section-title'>📚 Studio da Libri</div>", unsafe_allow_html=True)
    testo_libro_input = st.text_area("Incolla il testo del libro:", height=140)
    if st.button("🚀 Elabora Testo con AI", type="primary"):
        if MASTER_GEMINI_KEY and testo_libro_input:
            try:
                genai.configure(api_key=MASTER_GEMINI_KEY)
                model = genai.GenerativeModel(GEMINI_MODEL_NAME)
                prompt_libro = f"Estrai mosse e commenti in JSON: {{\"mosse_san\": [\"e4\"], \"commenti\": {{\"0\": \"Inizio\"}}}}. {t['prompt_lang']} Testo: {testo_libro_input}"
                risposta = model.generate_content(prompt_libro)
                dati_libro = json.loads(risposta.text.replace("```json", "").replace("```", "").strip())

                board = chess.Board()
                steps = [{"ply": 0, "mossa_giocata": "Inizio", "fen": board.fen(), "commento": dati_libro.get("commenti", {}).get("0", "")}]
                for idx, san in enumerate(dati_libro.get("mosse_san", [])):
                    try:
                        move = board.parse_san(san)
                        board.push(move)
                        steps.append({"ply": idx+1, "mossa_giocata": san, "fen": board.fen(),
                                      "commento": dati_libro.get("commenti", {}).get(str(idx+1), "")})
                    except Exception:
                        break
                st.session_state['book_steps'] = steps
                st.session_state['current_ply'] = 0
                st.markdown("<div class='success-box'>Studio pronto!</div>", unsafe_allow_html=True)
            except Exception as e:
                st.markdown(f"<div class='error-box'>Errore: {e}</div>", unsafe_allow_html=True)

    if 'book_steps' in st.session_state and st.session_state['book_steps']:
        steps = st.session_state['book_steps']
        max_p = len(steps) - 1
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("⏪ Inizio", use_container_width=True): st.session_state['current_ply'] = 0; st.rerun()
        if c2.button("⬅️", use_container_width=True) and st.session_state['current_ply'] > 0: st.session_state['current_ply'] -= 1; st.rerun()
        if c3.button("➡️", use_container_width=True) and st.session_state['current_ply'] < max_p: st.session_state['current_ply'] += 1; st.rerun()
        if c4.button("⏩ Fine", use_container_width=True): st.session_state['current_ply'] = max_p; st.rerun()

        cur = steps[st.session_state['current_ply']]
        col_v1, col_v2 = st.columns([1, 1])
        with col_v1:
            svg = chess.svg.board(board=chess.Board(cur['fen']), size=340,
                                  colors={'square light': '#ebecd0', 'square dark': '#739552'})
            st.markdown(f'<div class="board-wrapper">{svg}</div>', unsafe_allow_html=True)
        with col_v2:
            st.markdown(f"<div class='info-box'>💬 {cur['commento']}</div>", unsafe_allow_html=True)

# ==========================================
# TAB 3: DIARIO
# ==========================================
elif current_tab == 3:
    st.markdown("<div class='section-title'>📝 Diario & PDF</div>", unsafe_allow_html=True)
    input_diario = st.text_area("Inserisci la sequenza di mosse:", height=100)
    if st.button("🔄 Carica Scacchiera", type="primary"):
        if input_diario.strip():
            try:
                board_t = chess.Board()
                l_v = []
                for m in input_diario.split():
                    m_p = m.split(".")[-1]
                    if m_p and not m_p.isdigit():
                        board_t.push(board_t.parse_san(m_p))
                        l_v.append(m_p)
                st.session_state['diario_mosse'] = l_v
                st.session_state['diario_note_mosse'] = {}
                st.markdown("<div class='success-box'>Partita caricata!</div>", unsafe_allow_html=True)
            except Exception as e:
                st.markdown(f"<div class='error-box'>Errore: {e}</div>", unsafe_allow_html=True)

    if 'diario_mosse' in st.session_state and st.session_state['diario_mosse']:
        mosse_d = st.session_state['diario_mosse']
        b_d = chess.Board()
        for m in mosse_d:
            b_d.push(b_d.parse_san(m))
        col_d1, col_d2 = st.columns([1, 1])
        with col_d1:
            svg = chess.svg.board(board=b_d, size=340,
                                  colors={'square light': '#ebecd0', 'square dark': '#739552'})
            st.markdown(f'<div class="board-wrapper">{svg}</div>', unsafe_allow_html=True)
        with col_d2:
            for idx, m in enumerate(mosse_d):
                st.session_state['diario_note_mosse'][str(idx)] = st.text_input(
                    f"Nota {m}:",
                    value=st.session_state['diario_note_mosse'].get(str(idx), ""),
                    key=f"note_pdf_{idx}"
                )
        if st.button("⚙️ Genera ed Esporta PDF", type="primary"):
            pdf_b = genera_pdf_partita(b_d, mosse_d, st.session_state['diario_note_mosse'], "")
            st.download_button("📥 Scarica Report PDF", data=pdf_b,
                              file_name="diario_partita.pdf", mime="application/pdf")

# ==========================================
# TAB 4: IMPORTA
# ==========================================
elif current_tab == 4:
    st.markdown("<div class='section-title'>🌐 Importa Partite</div>", unsafe_allow_html=True)
    saved_profiles = get_user_profiles(user_email)

    col_i1, col_i2 = st.columns([2, 1])
    with col_i1:
        if saved_profiles:
            profile_options = [f"{p['piattaforma']}: {p['username']}" for p in saved_profiles]
            scelta_profilo = st.selectbox("Seleziona account salvato:", profile_options)
            idx_sel = profile_options.index(scelta_profilo)
            plat = saved_profiles[idx_sel]['piattaforma']
            usr = saved_profiles[idx_sel]['username']
        else:
            st.markdown("<div class='info-box'>Nessun profilo salvato. Inseriscine uno al volo:</div>", unsafe_allow_html=True)
            plat = st.radio("Piattaforma:", ["Lichess", "Chess.com"], horizontal=True)
            usr = st.text_input("Username:", value="")
    with col_i2:
        limite_partite = st.number_input("Partite da scaricare:", min_value=5, max_value=50, value=20)

    if st.button("📥 Scarica Ultime Partite", type="primary", use_container_width=True):
        if usr.strip():
            with st.spinner(f"Scaricamento partite per {usr}..."):
                try:
                    user_lower = usr.strip().lower()
                    if plat == "Lichess":
                        url_lic = f"https://lichess.org/api/games/user/{user_lower}"
                        headers_lic = {"Accept": "application/x-chess-pgn", "User-Agent": "ChessCoachPro/1.0"}
                        r = requests.get(url_lic, params={"max": limite_partite}, headers=headers_lic, timeout=20)
                        if r.status_code == 200:
                            st.session_state['partite_importate'] = r.text
                            st.markdown(f"<div class='success-box'>Scaricamento completato per {usr}!</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div class='error-box'>Errore Lichess (HTTP {r.status_code}).</div>", unsafe_allow_html=True)
                    else:
                        headers_c = {"User-Agent": "ChessCoachPro/1.0 (Contact: support@chesscoachpro.com)"}
                        arch_url = f"https://api.chess.com/pub/player/{user_lower}/games/archives"
                        r_arch = requests.get(arch_url, headers=headers_c, timeout=10)
                        if r_arch.status_code == 200:
                            archives = r_arch.json().get("archives", [])
                            if archives:
                                r_m = requests.get(archives[-1], headers=headers_c, timeout=10)
                                if r_m.status_code == 200:
                                    games_j = r_m.json().get("games", [])[-limite_partite:][::-1]
                                    pgn_all = "\n\n".join([g.get("pgn", "") for g in games_j if g.get("pgn")])
                                    st.session_state['partite_importate'] = pgn_all
                                    st.markdown(f"<div class='success-box'>Scaricamento completato per {usr}!</div>", unsafe_allow_html=True)
                                else:
                                    st.markdown("<div class='error-box'>Errore archivio Chess.com.</div>", unsafe_allow_html=True)
                            else:
                                st.markdown("<div class='warning-box'>Nessun archivio trovato.</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div class='error-box'>Utente non trovato (HTTP {r_arch.status_code}).</div>", unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f"<div class='error-box'>Errore download: {e}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='warning-box'>Username non valido.</div>", unsafe_allow_html=True)

    if 'partite_importate' in st.session_state and st.session_state['partite_importate']:
        st.divider()
        st.markdown("<div class='section-title'>🔍 Filtra Partite Scaricate</div>", unsafe_allow_html=True)

        raw_pgns = [p.strip() for p in st.session_state['partite_importate'].split("\n\n\n") if p.strip()]
        if len(raw_pgns) <= 1:
            raw_pgns = [p.strip() for p in st.session_state['partite_importate'].split("\n[Event ") if p.strip()]
            raw_pgns = ["[Event " + p if not p.startswith("[Event") else p for p in raw_pgns]

        parsed_games = []
        for pgn_str in raw_pgns:
            g_io = io.StringIO(pgn_str)
            game_obj = chess.pgn.read_game(g_io)
            if game_obj:
                headers = game_obj.headers
                white = headers.get("White", "Unknown")
                black = headers.get("Black", "Unknown")
                result = headers.get("Result", "*")
                eco = headers.get("ECO", "?")
                date = headers.get("Date", "????.??.??")
                event = headers.get("Event", "Casual Game")
                event_lower = event.lower()
                if "bullet" in event_lower: tc = "Bullet"
                elif "blitz" in event_lower: tc = "Blitz"
                elif "rapid" in event_lower: tc = "Rapid"
                elif "classical" in event_lower or "class" in event_lower: tc = "Classical"
                else: tc = "Altro/Custom"
                parsed_games.append({
                    "summary": f"{date} | {white} vs {black} [{result}] ({tc}, ECO: {eco})",
                    "pgn": pgn_str, "tc": tc, "result": result
                })

        if parsed_games:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_tc = st.selectbox("Filtra Tempo:", ["Tutti", "Blitz", "Rapid", "Bullet", "Classical", "Altro/Custom"])
            with col_f2:
                filtro_res = st.selectbox("Filtra Risultato:", ["Tutti", "Vittorie Bianco (1-0)", "Vittorie Nero (0-1)", "Patte (1/2-1/2)"])

            filtered_games = parsed_games
            if filtro_tc != "Tutti": filtered_games = [g for g in filtered_games if g['tc'] == filtro_tc]
            if filtro_res == "Vittorie Bianco (1-0)": filtered_games = [g for g in filtered_games if g['result'] == "1-0"]
            elif filtro_res == "Vittorie Nero (0-1)": filtered_games = [g for g in filtered_games if g['result'] == "0-1"]
            elif filtro_res == "Patte (1/2-1/2)": filtered_games = [g for g in filtered_games if g['result'] == "1/2-1/2"]

            st.markdown(f"<div class='info-box'>Trovate <b>{len(filtered_games)}</b> partite.</div>", unsafe_allow_html=True)

            if filtered_games:
                game_options = [g['summary'] for g in filtered_games]
                scelta_partita = st.selectbox("Seleziona la partita da analizzare:", game_options)
                selected_idx = game_options.index(scelta_partita)
                chosen_pgn = filtered_games[selected_idx]['pgn']

                if st.button("🚀 Invia ad Analisi Stockfish", type="primary", use_container_width=True):
                    st.session_state['pgn_manual_input'] = chosen_pgn
                    st.session_state['active_nav_tab'] = 0
                    st.rerun()
            else:
                st.markdown("<div class='warning-box'>Nessuna partita corrisponde ai filtri.</div>", unsafe_allow_html=True)