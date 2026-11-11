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
    'eval_history': None, 'storico_errori_locale': [], 'storico_rating_locale': [],
    'lezioni_gm_salvate': {}
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

# --- DATABASE & LOCAL STORAGE HELPERS ---
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
                    return "Free"
            return current_tier
    except Exception:
        pass
    return "Free"

def check_and_consume_gm_quota(email, tier):
    if tier in ["Pro", "Diamond"]:
        return True, ""
    
    current_month = datetime.datetime.now().strftime("%Y-%m")
    key_quota = f"gm_quota_{email}_{current_month}"
    
    if key_quota not in st.session_state:
        st.session_state[key_quota] = 0
        
    if st.session_state[key_quota] >= 5:
        return False, "⚠️ Hai esaurito le 5 analisi GM gratuite di questo mese per il piano Free. Passa a Pro o Diamond per analisi illimitate!"
        
    st.session_state[key_quota] += 1
    return True, ""

def format_gm_lesson_html(raw_text):
    lines = raw_text.strip().split('\n')
    formatted_parts = []
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        if line_clean.startswith("1.") or "**Errore:**" in line_clean:
            text = line_clean.replace("1.", "").replace("**Errore:**", "").strip()
            formatted_parts.append(f"<div class='gm-section'><b>❌ Analisi Errore:</b> {text}</div>")
        elif line_clean.startswith("2.") or "**Idea corretta:**" in line_clean:
            text = line_clean.replace("2.", "").replace("**Idea corretta:**", "").strip()
            formatted_parts.append(f"<div class='gm-section'><b>💡 Idea Corretta:</b> {text}</div>")
        elif line_clean.startswith("3.") or "**Regola pratica:**" in line_clean:
            text = line_clean.replace("3.", "").replace("**Regola pratica:**", "").strip()
            formatted_parts.append(f"<div class='gm-section'><b>♟️ Regola Pratica:</b> {text}</div>")
        else:
            formatted_parts.append(f"<div class='gm-section'>{line_clean}</div>")
    
    if not formatted_parts:
        formatted_parts = [f"<div class='gm-section'>{raw_text}</div>"]

    content = "".join(formatted_parts)
    return f"""
    <div class='gm-card'>
        <div class='gm-header'>🎓 Lezione del Gran Maestro AI</div>
        {content}
    </div>
    """

def salva_errore_db(user_email, partita_id, categoria, mossa, spiegazione="", apertura=""):
    data_ora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    nuovo_errore = {
        "user_email": user_email,
        "partita_id": partita_id if partita_id else "Partita_Sconosciuta",
        "data": data_ora,
        "categoria_errore": categoria,
        "mossa_critica": mossa,
        "spiegazione": spiegazione,
        "apertura": apertura
    }
    if 'storico_errori_locale' not in st.session_state:
        st.session_state['storico_errori_locale'] = []
    
    esistente = next((e for e in st.session_state['storico_errori_locale'] if e['partita_id'] == partita_id and e['mossa_critica'] == mossa), None)
    if esistente:
        if spiegazione:
            esistente['spiegazione'] = spiegazione
        if apertura:
            esistente['apertura'] = apertura
    else:
        st.session_state['storico_errori_locale'].append(nuovo_errore)

    if supabase:
        try:
            supabase.table("errori_utenti").upsert(nuovo_errore, on_conflict="user_email,partita_id,mossa_critica").execute()
        except Exception: pass

def carica_errori_db(user_email):
    rows = []
    if supabase:
        try:
            res = supabase.table("errori_utenti").select("*").eq("user_email", user_email).execute()
            if res.data:
                rows = res.data
        except Exception: pass
    
    local_rows = st.session_state.get('storico_errori_locale', [])
    combined = rows + [r for r in local_rows if r not in rows]
    
    if combined:
        df = pd.DataFrame(combined)
        if 'apertura' not in df.columns:
            df['apertura'] = "Standard"
        return df
    return pd.DataFrame(columns=["data", "partita_id", "categoria_errore", "mossa_critica", "spiegazione", "apertura"])

def salva_rating_db(user_email, data_partita, rating, partita_id):
    record = {
        "user_email": user_email,
        "data": data_partita,
        "rating": int(rating),
        "partita_id": partita_id
    }
    if 'storico_rating_locale' not in st.session_state:
        st.session_state['storico_rating_locale'] = []
    st.session_state['storico_rating_locale'] = [r for r in st.session_state['storico_rating_locale'] if r['partita_id'] != partita_id]
    st.session_state['storico_rating_locale'].append(record)

    if supabase:
        try:
            supabase.table("storico_rating").upsert(record, on_conflict="user_email,partita_id").execute()
        except Exception: pass

def carica_rating_db(user_email):
    rows = []
    if supabase:
        try:
            res = supabase.table("storico_rating").select("*").eq("user_email", user_email).order("data").execute()
            if res.data:
                rows = res.data
        except Exception: pass
    
    local_rows = st.session_state.get('storico_rating_locale', [])
    combined = rows + [r for r in local_rows if r not in rows]
    
    if combined:
        df = pd.DataFrame(combined)
        df['data'] = pd.to_datetime(df['data'], errors='coerce')
        df = df.dropna(subset=['data']).sort_values('data').reset_index(drop=True)
        return df
    return pd.DataFrame(columns=["data", "rating", "partita_id"])

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
            <div class="brand-title">{t['title'] if 't' in globals() else 'Chess Coach Pro'}</div>
            <p class="brand-sub">Coaching Scacchistico AI ad Altissima Efficienza</p>
        </div>
        """, unsafe_allow_html=True)

        scelta_lingua_benvenuto = st.selectbox("Lingua:", options=["Italiano", "English", "Español"], index=0, key="lang_login_select")
        lang_c = 'it' if scelta_lingua_benvenuto == "Italiano" else ('en' if scelta_lingua_benvenuto == "English" else 'es')
        if lang_c != st.session_state['lang']:
            st.session_state['lang'] = lang_c
            st.rerun()

        TEXTS_MAP = {
            "it": {"login_header": "🔐 Accedi", "register_header": "📝 Registrati", "email_label": "Email:", "password_label": "Password:", "login_btn": "Accedi", "register_btn": "Crea Account"},
            "en": {"login_header": "🔐 Login", "register_header": "📝 Register", "email_label": "Email:", "password_label": "Password:", "login_btn": "Login", "register_btn": "Create Account"},
            "es": {"login_header": "🔐 Iniciar Sesión", "register_header": "📝 Registrarse", "email_label": "Correo:", "password_label": "Contraseña:", "login_btn": "Iniciar Sesión", "register_btn": "Crear Cuenta"}
        }
        lt = TEXTS_MAP[st.session_state['lang']]

        tab_log, tab_reg = st.tabs([lt["login_header"], lt["register_header"]])
        supabase_configurato = supabase is not None

        with tab_log:
            email_log = st.text_input(lt["email_label"], key="login_email")
            pass_log = st.text_input(lt["password_label"], type="password", key="login_pass")
            if st.button(lt["login_btn"], type="primary", use_container_width=True):
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
            email_reg = st.text_input(lt["email_label"], key="reg_email")
            pass_reg = st.text_input(lt["password_label"], type="password", key="reg_pass")
            if st.button(lt["register_btn"], type="primary", use_container_width=True):
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

TEXTS = {
    "it": {
        "title": "Chess Coach Pro", "subtitle": "Coaching Scacchistico AI ad Altissima Efficienza",
        "lang_select": "Lingua:", "theme_select": "Tema:",
        "login_header": "🔐 Accedi", "register_header": "📝 Registrati",
        "email_label": "Email:", "password_label": "Password:",
        "login_btn": "Accedi", "register_btn": "Crea Account", "logout_btn": "🚪 Disconnetti",
        "analyze_btn": "🔍 Avvia Analisi Motore",
        "critique_found": "errori tuoi individuati dal motore!",
        "no_errors": "Partita eccellente! Nessun errore rilevato per te.",
        "gm_lesson_btn": "🎓 Spiegazione GM AI",
        "prompt_lang": "Rispondi in italiano.",
        "profile_setup_title": "Configura i tuoi Profili",
        "profile_setup_desc": "Collega i tuoi account Lichess o Chess.com per la sincronizzazione.",
        "continue_btn": "🚀 Entra nell'App",
        "already_analyzed": "⚠️ Questa partita è già stata analizzata ed è presente nel tuo archivio."
    },
    "en": {
        "title": "Chess Coach Pro", "subtitle": "High-Efficiency AI Chess Coaching",
        "lang_select": "Language:", "theme_select": "Theme:",
        "login_header": "🔐 Login", "register_header": "📝 Register",
        "email_label": "Email:", "password_label": "Password:",
        "login_btn": "Login", "register_btn": "Create Account", "logout_btn": "🚪 Logout",
        "analyze_btn": "🔍 Start Engine Analysis",
        "critique_found": "errors of yours found by engine!",
        "no_errors": "Great game! No major errors found for you.",
        "gm_lesson_btn": "🎓 Quick GM Insight",
        "prompt_lang": "Respond in English.",
        "profile_setup_title": "Setup your Chess Profiles",
        "profile_setup_desc": "Link your Lichess or Chess.com accounts for sync.",
        "continue_btn": "🚀 Enter App",
        "already_analyzed": "⚠️ This game has already been analyzed and saved."
    },
    "es": {
        "title": "Chess Coach Pro", "subtitle": "Entrenamiento de Ajedrez con IA de Alta Eficiencia",
        "lang_select": "Idioma:", "theme_select": "Tema:",
        "login_header": "🔐 Iniciar Sesión", "register_header": "📝 Registrarse",
        "email_label": "Correo:", "password_label": "Contraseña:",
        "login_btn": "Iniciar Sesión", "register_btn": "Crear Cuenta", "logout_btn": "🚪 Cerrar Sesión",
        "analyze_btn": "🔍 Iniciar Análisis de Motor",
        "critique_found": "¡errores tuyos encontrados por el motor!",
        "no_errors": "¡Excelente partida! Sin errores graves para ti.",
        "gm_lesson_btn": "🎓 Análisis Rápido GM",
        "prompt_lang": "Responde en español.",
        "profile_setup_title": "Configura tus Perfiles",
        "profile_setup_desc": "Vincula tus cuentas para sincronizar.",
        "continue_btn": "🚀 Entrar a la App",
        "already_analyzed": "⚠️ Esta partida ya ha sido analizada."
    }
}

t = TEXTS[st.session_state['lang']]

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
# SIDEBAR / MENU STRUTTURATO
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

    st.markdown("### 🧭 Navigazione Principale")
    
    menu_options = [
        "📊 Dashboard & Insights",
        "🔍 Analizza Partita",
        "🌐 Importa & Sincronizza",
        "🎯 Palestra sui Tuoi Errori",
        "📚 Studio da Libri",
        "📝 Diario & PDF",
        "💎 Piani Abbonamento",
        "📞 Contatti & Supporto"
    ]

    if 'nav_selection' not in st.session_state or st.session_state['nav_selection'] not in menu_options:
        st.session_state['nav_selection'] = menu_options[0]

    selected_nav = st.radio("Sezioni App", menu_options, key="nav_selection", label_visibility="collapsed")

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
# MOTORE STOCKFISH & RILEVAMENTO APERTURA REALE
# ==========================================
def detect_opening(game_moves_san):
    if not game_moves_san:
        return "Apertura Standard"
    
    m1 = game_moves_san[0] if len(game_moves_san) > 0 else ""
    m2 = game_moves_san[1] if len(game_moves_san) > 1 else ""
    m3 = game_moves_san[2] if len(game_moves_san) > 2 else ""
    m4 = game_moves_san[3] if len(game_moves_san) > 3 else ""

    if m1 == "e4":
        if m2 == "e5":
            if m3 == "Nf3":
                if m4 == "Nc6": return "Partita Italiana / Spagnola (Ruy Lopez)"
                elif m4 == "Nf6": return "Difesa Petroff"
                return "Partita Aperta (1.e4 e5)"
            return "Gioco Aperto (1.e4 e5)"
        elif m2 == "c5": return "Difesa Siciliana"
        elif m2 == "e6": return "Difesa Francese"
        elif m2 == "c6": return "Difesa Caro-Kann"
        elif m2 == "Nf6": return "Difesa Alekhine"
        return "Gioco di Re (1.e4)"
    elif m1 == "d4":
        if m2 == "Nf6":
            if m3 == "c4":
                if m4 == "e6": return "Difesa Nimzo-Indiana / Regina"
                elif m4 == "g6": return "Difesa Indiana di Re / Grünfeld"
                return "Difesa Indiana"
            return "Difesa Indiana di Donna / Reti"
        elif m2 == "d5":
            if m3 == "c4": return "Gambetto di Donna"
            return "Partita di Donna (1.d4 d5)"
        return "Gioco di Donna (1.d4)"
    elif m1 == "Nf3": return "Apertura Reti / Zukertort"
    elif m1 == "c4": return "Partita Inglese"
    
    return f"Apertura ({m1} {m2})"

def fetch_stockfish_eval(session, fen, depth=10):
    try:
        r = session.post("https://chess-api.com/v1", json={"fen": fen, "depth": depth}, timeout=2.5)
        if r.status_code == 200:
            data = r.json()
            if data.get("eval") is not None: return float(data.get("eval"))
            elif data.get("centipawns") is not None: return float(data.get("centipawns")) / 100.0
            elif data.get("cp") is not None: return float(data.get("cp")) / 100.0
            elif data.get("value") is not None: return float(data.get("value")) / 100.0
            elif data.get("mate") is not None:
                m = int(data.get("mate"))
                return 100.0 if m > 0 else -100.0
    except Exception:
        pass
    return None

def analizza_partita_stockfish(pgn_text, target_usernames):
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if not game: return [], None, "Impossibile leggere il PGN fornito.", [], 1500, datetime.datetime.now().strftime("%Y-%m-%d"), "Apertura Standard"

    headers = game.headers
    white_player = headers.get('White', 'Unknown').strip().lower()
    black_player = headers.get('Black', 'Unknown').strip().lower()
    white_elo = headers.get('WhiteElo', '1500')
    black_elo = headers.get('BlackElo', '1500')
    date_str = headers.get('Date', datetime.datetime.now().strftime("%Y-%m-%d")).replace('.', '-')
    
    # Rilevamento apertura PGN headers o euristico
    opening_name = headers.get('Opening', '')
    eco_code = headers.get('ECO', '')
    
    main_moves_list = list(game.mainline_moves())
    temp_b = game.board()
    san_moves = []
    for mv in main_moves_list:
        try: san_moves.append(temp_b.san(mv))
        except: san_moves.append(mv.uci())
        temp_b.push(mv)

    if opening_name:
        opening_display = f"{opening_name} ({eco_code})" if eco_code else opening_name
    else:
        opening_display = detect_opening(san_moves)

    user_is_white, user_is_black = False, False
    user_rating = 1500

    if target_usernames:
        user_list = [u.strip().lower() for u in target_usernames]
        found_match = False
        for u in user_list:
            if u in white_player: 
                user_is_white = True; found_match = True
                if white_elo.isdigit(): user_rating = int(white_elo)
            if u in black_player: 
                user_is_black = True; found_match = True
                if black_elo.isdigit(): user_rating = int(black_elo)
        if not found_match: 
            user_is_white, user_is_black = True, False
            if white_elo.isdigit(): user_rating = int(white_elo)
    else:
        user_is_white, user_is_black = True, False
        if white_elo.isdigit(): user_rating = int(white_elo)

    partita_id = f"{headers.get('White', 'Unknown')}_vs_{headers.get('Black', 'Unknown')}_{date_str}"
    
    board = game.board()
    detected_errors, eval_history = [], []
    headers_req = {"User-Agent": "ChessCoachPro/1.0 (support@chesscoachpro.com)", "Content-Type": "application/json"}
    total_ply_count = len(main_moves_list)
    total_full_moves = (total_ply_count + 1) // 2

    progress_bar = st.progress(0, text="♟️ Analisi rapida Stockfish in corso...")
    session = requests.Session()
    session.headers.update(headers_req)
    prev_eval = 0.0

    for idx, move in enumerate(main_moves_list):
        fen_before = board.fen()
        move_san = san_moves[idx]

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
                detected_errors.append({
                    "mossa_num": idx + 1, "label_mossa": label_mossa, "fen_prima": fen_before,
                    "fen_dopo": fen_after, "mossa_giocata": move.uci(), "perdita_cp": round(delta, 2),
                    "eval_dopo": eval_after, "tipo_problema": tipo_problema, "categoria": "Errore Tattico"
                })
        prev_eval = eval_after

    progress_bar.empty()
    return detected_errors, partita_id, None, eval_history, user_rating, date_str, opening_display

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
# SEZIONE 1: DASHBOARD & INSIGHTS
# ==========================================
if current_selection == "📊 Dashboard & Insights":
    st.markdown("<div class='section-title'>📊 Control Room & Rating in Tempo Reale</div>", unsafe_allow_html=True)
    df_err = carica_errori_db(user_email)
    df_rating = carica_rating_db(user_email)

    if user_tier in ["Pro", "Diamond"]:
        st.markdown(f"<div class='success-box'>🟢 Sincronizzazione automatica notturna attiva per il piano <b>{user_tier}</b>. Le tue partite vengono sincronizzate e censite in background.</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='info-box'>⚪ Piano Free attivo. Passa a Pro o Diamond per attivare lo scaricamento automatico notturno delle partite.</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'>📈 Andamento Rating e Variazione Giornaliera</div>", unsafe_allow_html=True)
    if not df_rating.empty and HAS_PLOTLY:
        df_rating['diff'] = df_rating['rating'].diff().fillna(0)

        col_r1, col_r2 = st.columns(2)
        
        with col_r1:
            st.markdown("##### 📉 Trend Rating in Tempo Reale")
            fig_rating = go.Figure()
            fig_rating.add_trace(go.Scatter(
                x=df_rating['data'], y=df_rating['rating'],
                mode='lines+markers', line=dict(color='#3b82f6', width=3),
                marker=dict(size=8), name="Rating"
            ))
            fig_rating.update_layout(
                template='plotly_dark' if st.session_state['theme_mode'] == 'Dark' else 'plotly_white',
                height=280, margin=dict(l=10, r=10, t=20, b=10),
                xaxis_title="Data", yaxis_title="Rating Elo"
            )
            st.plotly_chart(fig_rating, use_container_width=True)

        with col_r2:
            st.markdown("##### 📊 Differenza Rating (Day-over-Day)")
            colors = ['#10b981' if val >= 0 else '#ef4444' for val in df_rating['diff']]
            fig_diff = go.Figure()
            fig_diff.add_trace(go.Bar(
                x=df_rating['data'], y=df_rating['diff'],
                marker_color=colors, name="Variazione Elo"
            ))
            fig_diff.update_layout(
                template='plotly_dark' if st.session_state['theme_mode'] == 'Dark' else 'plotly_white',
                height=280, margin=dict(l=10, r=10, t=20, b=10),
                xaxis_title="Data", yaxis_title="Delta Elo"
            )
            st.plotly_chart(fig_diff, use_container_width=True)
    else:
        st.markdown("<div class='info-box'>Analizza almeno una partita con Elo valido per visualizzare i grafici del rating in tempo reale.</div>", unsafe_allow_html=True)

    st.divider()

    if not df_err.empty:
        n_errors = len(df_err)
        n_games = df_err['partita_id'].nunique() if 'partita_id' in df_err else 0
        avg_err_per_game = n_errors / max(n_games, 1)
        precision = max(0, min(100, int(100 - avg_err_per_game * 6)))

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.markdown(f"<div class='metric-card blue'><div class='metric-icon'>🎯</div><div class='metric-value'>{n_errors}</div><div class='metric-label'>Totale Errori Censiti</div></div>", unsafe_allow_html=True)
        kpi2.markdown(f"<div class='metric-card purple'><div class='metric-icon'>♟️</div><div class='metric-value'>{n_games}</div><div class='metric-label'>Partite Analizzate</div></div>", unsafe_allow_html=True)
        kpi3.markdown(f"<div class='metric-card green'><div class='metric-icon'>✨</div><div class='metric-value'>{precision}%</div><div class='metric-label'>Indice Precisione</div></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='info-box'>Nessun errore registrato nel cloud o in memoria. Analizza qualche partita per popolare la tua Control Room!</div>", unsafe_allow_html=True)

# ==========================================
# SEZIONE 2: ANALIZZA PARTITA (CON SLIDER + FRECCE & APERTURA REALE)
# ==========================================
elif current_selection == "🔍 Analizza Partita":
    st.markdown("<div class='section-title'>📖 Analisi Dettagliata Partita</div>", unsafe_allow_html=True)

    pgn_val = st.session_state.get('pgn_manual_input', '')
    pgn_input = st.text_area("Incolla il PGN della partita:", value=pgn_val, height=140, key="pgn_area_input")

    if st.button(t["analyze_btn"], type="primary", use_container_width=True):
        if not pgn_input.strip(): st.warning("Inserisci un PGN valido.")
        else:
            current_pgn_text = pgn_input.strip()
            
            game_check = chess.pgn.read_game(io.StringIO(current_pgn_text))
            already_exists = False
            if game_check:
                h_check = game_check.headers
                p_id_check = f"{h_check.get('White', 'Unknown')}_vs_{h_check.get('Black', 'Unknown')}_vs_{h_check.get('Date', 'Live')}"
                df_check = carica_errori_db(user_email)
                if not df_check.empty and 'partita_id' in df_check.columns:
                    if p_id_check in df_check['partita_id'].values:
                        already_exists = True

            if already_exists:
                st.warning(t['already_analyzed'])
            else:
                with st.spinner("🔍 Analisi rapida Stockfish in corso..."):
                    user_profs = get_user_profiles(user_email)
                    user_usernames = [p['username'] for p in user_profs]
                    errori, p_id, err_msg, eval_hist, rating_partita, data_partita, opening_used = analizza_partita_stockfish(current_pgn_text, user_usernames)
                    
                    st.session_state['stockfish_errors'] = errori
                    st.session_state['current_game_id'] = p_id
                    st.session_state['eval_history'] = eval_hist
                    st.session_state['current_opening'] = opening_used

                    salva_rating_db(user_email, data_partita, rating_partita, p_id)

                    game_obj = chess.pgn.read_game(io.StringIO(current_pgn_text))
                    if game_obj:
                        st.session_state['active_game_board'] = game_obj
                        st.session_state['active_game_moves'] = list(game_obj.mainline_moves())
                        st.session_state['current_board_ply'] = 0

                    if errori:
                        st.success(f"✅ Stockfish: {len(errori)} {t['critique_found']}")
                        for item in errori:
                            salva_errore_db(user_email, p_id, item.get("categoria", "Errore Tattico"),
                                           item.get("label_mossa", "Mossa"), "", opening_used)
                    else: st.success(f"✅ {t['no_errors']}")

    if 'current_opening' in st.session_state and st.session_state['current_opening']:
        st.markdown(f"<div class='success-box'>📖 <b>Apertura Rilevata:</b> {st.session_state['current_opening']}</div>", unsafe_allow_html=True)

    if st.session_state.get('eval_history'):
        st.markdown("<div class='section-title'>📈 Grafico di Valutazione</div>", unsafe_allow_html=True)
        render_eval_graph(st.session_state['eval_history'], st.session_state.get('stockfish_errors', []))

    if 'active_game_board' in st.session_state and st.session_state['active_game_board']:
        st.divider()
        game_moves = st.session_state['active_game_moves']
        max_ply = len(game_moves)
        
        # --- SLIDER E FRECCE SINCRONIZZATE ---
        if 'current_board_ply' not in st.session_state:
            st.session_state['current_board_ply'] = 0

        c1, c2, c3, c4 = st.columns(4)
        if c1.button("⏪ Inizio", use_container_width=True): 
            st.session_state['current_board_ply'] = 0
            st.rerun()
        if c2.button("⬅️ Indietro", use_container_width=True) and st.session_state['current_board_ply'] > 0: 
            st.session_state['current_board_ply'] -= 1
            st.rerun()
        if c3.button("➡️ Avanti", use_container_width=True) and st.session_state['current_board_ply'] < max_ply: 
            st.session_state['current_board_ply'] += 1
            st.rerun()
        if c4.button("⏩ Fine", use_container_width=True): 
            st.session_state['current_board_ply'] = max_ply
            st.rerun()

        current_ply = st.slider(
            "🧭 Navigazione Rapida Mosse", 
            min_value=0, 
            max_value=max_ply, 
            value=st.session_state['current_board_ply'],
            key="board_slider_position"
        )
        if current_ply != st.session_state['current_board_ply']:
            st.session_state['current_board_ply'] = current_ply
            st.rerun()

        temp_board = st.session_state['active_game_board'].board()
        for i in range(st.session_state['current_board_ply']): temp_board.push(game_moves[i])

        svg_board = chess.svg.board(board=temp_board, size=430, colors={'square light': '#ebecd0', 'square dark': '#739552'})
        st.markdown(f'<div class="board-wrapper">{svg_board}</div>', unsafe_allow_html=True)

        st.markdown("<div class='section-title'>📋 Errori Rilevati dal Motore</div>", unsafe_allow_html=True)
        if st.session_state.get('stockfish_errors'):
            df_storico_DB = carica_errori_db(user_email)

            for idx, err in enumerate(st.session_state['stockfish_errors']):
                p_id_curr = st.session_state.get('current_game_id', 'Partita_Sconosciuta')
                
                lezione_esistente = ""
                if not df_storico_DB.empty and 'partita_id' in df_storico_DB.columns:
                    match_db = df_storico_DB[(df_storico_DB['partita_id'] == p_id_curr) & (df_storico_DB['mossa_critica'] == err['label_mossa'])]
                    if not match_db.empty:
                        spiegazione_db = match_db.iloc[0].get('spiegazione', '')
                        if spiegazione_db:
                            lezione_esistente = spiegazione_db

                with st.expander(f"{err['tipo_problema']} · {err['label_mossa']} · -{err['perdita_cp']} CP", expanded=False):
                    st.markdown(f"**Mossa:** `{err['label_mossa']}` | **Perdita:** -{err['perdita_cp']} CP", unsafe_allow_html=True)
                    
                    if st.button(t['gm_lesson_btn'], key=f"btn_lesson_{idx}", type="primary"):
                        # Verifica quota mensile piano free
                        allowed, limit_msg = check_and_consume_gm_quota(user_email, user_tier)
                        if not allowed:
                            st.error(limit_msg)
                        else:
                            with st.spinner("🎓 Il Gran Maestro AI sta preparando la lezione..."):
                                prompt_lesson = f"""
                                Sei un GM di scacchi. Spiega questo errore tattico.
                                FEN: {err['fen_prima']}
                                Mossa errata: {err['mossa_giocata']}
                                {t['prompt_lang']}
                                Rispondi rigorosamente con:
                                1. [Spiegazione dell'errore commesso]
                                2. [Idea corretta da giocare]
                                3. [Regola pratica generale]
                                """
                                try:
                                    client = genai.Client(api_key=MASTER_GEMINI_KEY) if "Client" in dir(genai) else None
                                    if client:
                                        resp = client.models.generate_content(model=GEMINI_MODEL_NAME, contents=prompt_lesson)
                                        testo_gm = resp.text
                                    else:
                                        genai.configure(api_key=MASTER_GEMINI_KEY)
                                        resp = genai.GenerativeModel(GEMINI_MODEL_NAME).generate_content(prompt_lesson)
                                        testo_gm = resp.text
                                    
                                    formatted_lesson = format_gm_lesson_html(testo_gm)
                                    st.session_state[f"lesson_{idx}"] = formatted_lesson
                                    
                                    # Salvataggio persistente nel DB
                                    current_op = st.session_state.get('current_opening', 'Standard')
                                    salva_errore_db(user_email, p_id_curr, err.get('categoria', 'Errore Tattico'), err['label_mossa'], formatted_lesson, current_op)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"⚠️ Errore API Gemini: {e}")

                    if lezione_esistente:
                        st.markdown(lezione_esistente, unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>Nessun errore registrato in questa partita.</div>", unsafe_allow_html=True)

# ==========================================
# SEZIONE 3: IMPORTA & SINCRONIZZA
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
                        headers_lic = {
                            "Accept": "application/x-chess-pgn",
                            "User-Agent": "ChessCoachPro/1.0 (support@chesscoachpro.com)"
                        }
                        r = requests.get(url_lic, params={"max": limite_partite}, headers=headers_lic, timeout=25)
                        if r.status_code == 200 and r.text.strip():
                            st.session_state['partite_importate'] = r.text
                            st.success("Scaricamento completato con successo!")
                        elif r.status_code == 404:
                            st.error(f"Errore 404: Utente Lichess '{user_lower}' non trovato. Verifica lo username.")
                        else:
                            st.error(f"Errore Lichess (HTTP {r.status_code})")
                    else:
                        headers_cc = {"User-Agent": "ChessCoachPro/1.0 (support@chesscoachpro.com)"}
                        r_arch = requests.get(f"https://api.chess.com/pub/player/{user_lower}/games/archives", headers=headers_cc, timeout=10)
                        if r_arch.status_code == 200 and r_arch.json().get("archives"):
                            r_m = requests.get(r_arch.json()["archives"][-1], headers=headers_cc, timeout=10)
                            games_j = r_m.json().get("games", [])[-limite_partite:][::-1]
                            st.session_state['partite_importate'] = "\n\n".join([g.get("pgn", "") for g in games_j if g.get("pgn")])
                            st.success("Scaricamento completato con successo!")
                        else:
                            st.error("Impossibile recuperare gli archivi da Chess.com. Verifica lo username.")
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
            if st.button("🚀 Invia ad Analisi Motore", type="primary", use_container_width=True):
                st.session_state['pgn_manual_input'] = chosen_pgn
                st.session_state['goto_tab'] = "🔍 Analizza Partita"
                st.rerun()

# ==========================================
# SEZIONE 4: PALESTRA ALLENAMENTO (CON FILTRI MULTIPLI - Sviluppo 3)
# ==========================================
elif current_selection == "🎯 Palestra sui Tuoi Errori":
    st.markdown("<div class='section-title'>🎯 Palestra di Allenamento & Lezioni GM</div>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8892a6;'>Filtra e riconsulta tutte le lezioni e gli errori salvati dalle tue partite.</p>", unsafe_allow_html=True)

    df_errori = carica_errori_db(user_email)

    if df_errori.empty:
        st.markdown("<div class='info-box'>Nessun errore registrato finora. Analizza qualche partita per sbloccare la tua palestra!</div>", unsafe_allow_html=True)
    else:
        # --- FILTRI MULTIPLI (Richiesta Sviluppo 3) ---
        st.markdown("##### 🔎 Filtri di Ricerca Avanzata")
        col_f1, col_f2, col_f3 = st.columns(3)
        
        partite_list = ["Tutte"] + list(df_errori['partita_id'].unique())
        aperture_list = ["Tutte"] + list(df_errori['apertura'].unique()) if 'apertura' in df_errori.columns else ["Tutte"]
        categorie_list = ["Tutte"] + list(df_errori['categoria_errore'].unique())

        filtro_partita = col_f1.selectbox("Filtra per Partita:", partite_list)
        filtro_apertura = col_f2.selectbox("Filtra per Apertura:", aperture_list)
        filtro_categoria = col_f3.selectbox("Filtra per Categoria:", categorie_list)

        df_filtrato = df_errori.copy()
        if filtro_partita != "Tutte":
            df_filtrato = df_filtrato[df_filtrato['partita_id'] == filtro_partita]
        if filtro_apertura != "Tutte":
            df_filtrato = df_filtrato[df_filtrato['apertura'] == filtro_apertura]
        if filtro_categoria != "Tutte":
            df_filtrato = df_filtrato[df_filtrato['categoria_errore'] == filtro_categoria]

        st.divider()

        lezioni_salvate = df_filtrato[df_filtrato['spiegazione'].str.len() > 0]
        if not lezioni_salvate.empty:
            st.markdown(f"<div class='section-title'>📚 Lezioni GM Trovate ({len(lezioni_salvate)})</div>", unsafe_allow_html=True)
            for _, row in lezioni_salvate.iterrows():
                with st.expander(f"Partita: {row['partita_id']} · Mossa: {row['mossa_critica']} · Apertura: {row.get('apertura', 'Standard')} ({row['data']})"):
                    st.markdown(row['spiegazione'], unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>Nessuna lezione GM corrisponde ai filtri selezionati. Clicca su 'Spiegazione GM AI' durante l'analisi delle partite per popolarla!</div>", unsafe_allow_html=True)

# ==========================================
# SEZIONE 5: STUDIO DA LIBRI
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
# SEZIONE 6: DIARIO & PDF
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
# SEZIONE 7: PIANI ABBONAMENTO
# ==========================================
elif current_selection == "💎 Piani Abbonamento":
    st.markdown("<div class='section-title'>💎 Scegli il tuo Piano</div>", unsafe_allow_html=True)
    col_pr1, col_pr2, col_pr3 = st.columns(3)

    with col_pr1:
        st.markdown("<div class='pricing-card'><div class='pricing-title'>Free</div><div class='pricing-price'>€0</div><ul class='pricing-features'><li>✅ 1 Profilo</li><li>✅ 5 Analisi GM al mese</li><li>✅ Analisi Motore Base</li></ul></div>", unsafe_allow_html=True)
        if user_tier == "Free":
            st.button("Piano Attuale", disabled=True, use_container_width=True, key="b_f")
        else:
            if st.button("Passa a Free", use_container_width=True, key="b_tf"):
                registra_nuovo_abbonamento(user_email, "Free")
                st.rerun()

    with col_pr2:
        is_pro = (user_tier == "Pro")
        st.markdown(f"<div class='pricing-card {'featured' if is_pro else ''}'><div class='tier-badge badge-pro'>Popolare</div><div class='pricing-title'>Pro</div><div class='pricing-price'>€4.99</div><ul class='pricing-features'><li>✅ 3 Profili</li><li>✅ Analisi GM Illimitate</li><li>✅ Sincronizzazione Notturna</li></ul></div>", unsafe_allow_html=True)
        
        if is_pro:
            st.markdown("<div class='success-box' style='text-align:center;'>✨ Piano Attivo</div>", unsafe_allow_html=True)
        elif user_tier == "Diamond":
            st.markdown("<div class='info-box' style='text-align:center;'>🔒 Incluso in Diamond</div>", unsafe_allow_html=True)
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
        is_diamond = (user_tier == "Diamond")
        st.markdown(f"<div class='pricing-card {'featured' if is_diamond else ''}'><div class='tier-badge badge-diamond'>Elite</div><div class='pricing-title'>Diamond</div><div class='pricing-price'>€9.99</div><ul class='pricing-features'><li>✅ 5 Profili</li><li>✅ Analisi GM Illimitate</li><li>✅ Sync Prioritario 24/7</li></ul></div>", unsafe_allow_html=True)
        
        if is_diamond:
            st.markdown("<div class='success-box' style='text-align:center;'>✨ Piano Attivo</div>", unsafe_allow_html=True)
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

    st.divider()
    st.markdown("""
    <div style="text-align: center; padding: 1rem;">
        <p style="color: #8892a6; margin-bottom: 0.5rem;">Vuoi sostenere ulteriormente lo sviluppo di Chess Coach Pro?</p>
        <a href="https://buymeacoffee.com" target="_blank" style="text-decoration: none; font-weight: 700; background: #FFDD00; color: #000; padding: 8px 16px; border-radius: 8px; display: inline-block;">
            ☕ Offrici un Caffè
        </a>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# SEZIONE 8: CONTATTI & SUPPORTO
# ==========================================
elif current_selection == "📞 Contatti & Supporto":
    st.markdown("<div class='section-title'>📞 Contatti & Supporto</div>", unsafe_allow_html=True)
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("<div class='info-box'>Hai riscontrato un bug o hai suggerimenti? Scrivici a <b>support@chesscoachpro.com</b>.</div>", unsafe_allow_html=True)
    with col_c2:
        with st.form("contact_form"):
            c_name = st.text_input("Il tuo nome o username:")
            c_msg = st.text_area("Messaggio / Segnalazione:")
            if st.form_submit_button("Invia Messaggio", type="primary", use_container_width=True):
                if c_name.strip() and c_msg.strip(): st.success("Messaggio inviato con successo!")
                else: st.warning("Compila tutti i campi.")
