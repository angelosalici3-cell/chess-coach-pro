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

# --- CONFIGURAZIONE CENTRALIZZATA ---
MASTER_GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

GEMINI_MODEL_NAME = "gemini-3.8-flash"

@st.cache_resource
def init_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY or "INSERISCI" in SUPABASE_URL:
        return None
    try:
        return create_client(SUPABASE_URL.strip(), SUPABASE_KEY.strip())
    except Exception:
        return None

supabase = init_supabase()

st.set_page_config(page_title="Chess Coach Pro", layout="wide", page_icon="⚡")

# --- GESTIONE STATO E SESSIONE PERSISTENTE ---
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'lang' not in st.session_state:
    st.session_state['lang'] = 'it'
if 'profile_setup_done' not in st.session_state:
    st.session_state['profile_setup_done'] = False
if 'active_nav_tab' not in st.session_state:
    st.session_state['active_nav_tab'] = 0
if 'theme_mode' not in st.session_state:
    st.session_state['theme_mode'] = 'Dark'
if 'last_analyzed_pgn' not in st.session_state:
    st.session_state['last_analyzed_pgn'] = None
if 'current_board_ply' not in st.session_state:
    st.session_state['current_board_ply'] = 0

# --- KEEP-ALIVE JAVASCRIPT PER MOBILE (PUNTO 4: Evita disconnessioni in standby) ---
st.components.v1.html("""
    <script>
    setInterval(function() {
        fetch(window.location.href);
    }, 25000);
    </script>
""", height=0)

# --- STILE CSS DINAMICO (DARK / LIGHT MODE) ---
def get_dynamic_css(theme):
    if theme == 'Dark':
        return """
        <style>
            .stApp { background: linear-gradient(135deg, #0e1117 0%, #161b22 100%); color: #f0f6fc; }
            h1, h2, h3, p, span, label { color: #f0f6fc !important; }
            .brand-title { background: linear-gradient(90deg, #FFD700, #FFA500); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.2rem; font-weight: 900; text-align: center; }
            .brand-sub { text-align: center; color: #8b949e !important; font-size: 0.95rem; margin-bottom: 1.5rem; }
            div[data-testid="stExpander"] { background: #161b22; border: 1px solid #30363d; border-radius: 12px; }
            .tier-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 0.85rem; text-transform: uppercase; }
            .badge-free { background: #21262d; color: #8b949e; border: 1px solid #30363d; }
            .badge-pro { background: rgba(255, 215, 0, 0.15); color: #FFD700; border: 1px solid #FFD700; }
            .badge-diamond { background: rgba(0, 210, 255, 0.15); color: #00d2ff; border: 1px solid #00d2ff; }
            .category-tag { background: rgba(255, 215, 0, 0.1); color: #FFD700; padding: 2px 8px; border-radius: 6px; font-weight: 600; font-size: 0.8rem; }
            button[kind="primary"] { border-radius: 10px !important; background: linear-gradient(90deg, #FFD700 0%, #FFA500 100%) !important; color: #0e1117 !important; font-weight: 800 !important; border: none !important; }
        </style>
        """
    else:
        return """
        <style>
            .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); color: #1f2428; }
            h1, h2, h3, p, span, label { color: #1f2428 !important; }
            .brand-title { background: linear-gradient(90deg, #d4af37, #b8860b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.2rem; font-weight: 900; text-align: center; }
            .brand-sub { text-align: center; color: #57606a !important; font-size: 0.95rem; margin-bottom: 1.5rem; }
            div[data-testid="stExpander"] { background: #ffffff; border: 1px solid #d0d7de; border-radius: 12px; color: #1f2428; }
            .tier-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 0.85rem; text-transform: uppercase; }
            .badge-free { background: #eaeef2; color: #57606a; border: 1px solid #d0d7de; }
            .badge-pro { background: rgba(212, 175, 55, 0.15); color: #b8860b; border: 1px solid #d4af37; }
            .badge-diamond { background: rgba(0, 120, 215, 0.15); color: #005fb8; border: 1px solid #0078d7; }
            .category-tag { background: rgba(212, 175, 55, 0.15); color: #b8860b; padding: 2px 8px; border-radius: 6px; font-weight: 600; font-size: 0.8rem; }
            button[kind="primary"] { border-radius: 10px !important; background: linear-gradient(90deg, #d4af37 0%, #b8860b 100%) !important; color: #ffffff !important; font-weight: 800 !important; border: none !important; }
        </style>
        """

st.markdown(get_dynamic_css(st.session_state['theme_mode']), unsafe_allow_html=True)

TEXTS = {
    "it": {
        "title": "⚡ Chess Coach Pro",
        "subtitle": "Coaching Scacchistico AI ad Altissima Efficienza",
        "tab1": "📖 Analizza",
        "tab2": "📊 Dashboard",
        "tab3": "📚 Libri",
        "tab4": "📝 Diario",
        "tab5": "🌐 Importa",
        "settings": "⚙️ Account & Tema",
        "lang_select": "🌐 Lingua:",
        "theme_select": "🎨 Tema:",
        "login_header": "🔐 Accedi",
        "register_header": "📝 Registrati",
        "email_label": "Email:",
        "password_label": "Password:",
        "login_btn": "Accedi alla Piattaforma",
        "register_btn": "Crea Account",
        "logout_btn": "🚪 Disconnetti",
        "analyze_btn": "🔍 Avvia Analisi Personale",
        "critique_found": "criticità identificate sulle tue mosse!",
        "no_errors": "Partita eccellente! Nessun errore grave rilevato sulle tue mosse.",
        "gm_lesson_btn": "🎓 Spiegazione GM AI",
        "prompt_lang": "Rispondi in italiano.",
        "profile_setup_title": "🎯 Configura i tuoi Profili",
        "profile_setup_desc": "Collega i tuoi account Lichess o Chess.com per importare le tue partite al volo.",
        "continue_btn": "🚀 Entra nell'App",
        "already_analyzed": "⚠️ Questa partita è già stata analizzata in questa sessione per evitare duplicazioni nel database."
    },
    "en": {
        "title": "⚡ Chess Coach Pro",
        "subtitle": "High-Efficiency AI Chess Coaching",
        "tab1": "📖 Analyze",
        "tab2": "📊 Dashboard",
        "tab3": "📚 Books",
        "tab4": "📝 Diary",
        "tab5": "🌐 Import",
        "settings": "⚙️ Account & Theme",
        "lang_select": "🌐 Language:",
        "theme_select": "🎨 Theme:",
        "login_header": "🔐 Login",
        "register_header": "📝 Register",
        "email_label": "Email:",
        "password_label": "Password:",
        "login_btn": "Login to Platform",
        "register_btn": "Create Account",
        "logout_btn": "🚪 Logout",
        "analyze_btn": "🔍 Start Personal Analysis",
        "critique_found": "critical issues identified on your moves!",
        "no_errors": "Great game! No major blunders found on your moves.",
        "gm_lesson_btn": "🎓 Quick GM Insight",
        "prompt_lang": "Respond in English.",
        "profile_setup_title": "🎯 Setup your Chess Profiles",
        "profile_setup_desc": "Link your Lichess or Chess.com accounts to sync your games.",
        "continue_btn": "🚀 Enter App",
        "already_analyzed": "⚠️ This game has already been analyzed in this session to prevent duplicate database records."
    },
    "es": {
        "title": "⚡ Chess Coach Pro",
        "subtitle": "Entrenamiento de Ajedrez con IA de Alta Eficiencia",
        "tab1": "📖 Analizar",
        "tab2": "📊 Dashboard",
        "tab3": "📚 Libros",
        "tab4": "📝 Diario",
        "tab5": "🌐 Importar",
        "settings": "⚙️ Cuenta y Tema",
        "lang_select": "🌐 Idioma:",
        "theme_select": "🎨 Tema:",
        "login_header": "🔐 Iniciar Sesión",
        "register_header": "📝 Registrarse",
        "email_label": "Correo electrónico:",
        "password_label": "Contraseña:",
        "login_btn": "Iniciar Sesión",
        "register_btn": "Crear Cuenta",
        "logout_btn": "🚪 Cerrar Sesión",
        "analyze_btn": "🔍 Iniciar Análisis Personal",
        "critique_found": "¡críticas identificadas en tus jugadas!",
        "no_errors": "¡Excelente partida! Sin errores graves en tus jugadas.",
        "gm_lesson_btn": "🎓 Análisis Rápido GM",
        "prompt_lang": "Responde en español.",
        "profile_setup_title": "🎯 Configura tus Perfiles",
        "profile_setup_desc": "Vincula tus cuentas para sincronizar tus partidas.",
        "continue_btn": "🚀 Entrar a la App",
        "already_analyzed": "⚠️ Esta partida ya ha sido analizada en esta sesión para evitar duplicar registros."
    }
}

t = TEXTS[st.session_state['lang']]

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
                "user_email": email,
                "piattaforma": piattaforma,
                "username": username.strip()
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
                "partita_id": partita_id,
                "data": data_ora,
                "categoria_errore": categoria,
                "mossa_critica": mossa,
                "spiegazione": spiegazione
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

# ==========================================
# 1. LOGIN
# ==========================================
if not st.session_state['user']:
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.markdown(f"<div class='brand-title'>{t['title']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='brand-sub'>{t['subtitle']}</div>", unsafe_allow_html=True)
        
        scelta_lingua_benvenuto = st.selectbox(
            t["lang_select"],
            options=["Italiano", "English", "Español"],
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
                        st.success("Accesso effettuato!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore di accesso: {e}")
                else:
                    st.session_state['user'] = email_log if email_log else "beta_tester@chess.com"
                    st.session_state['profile_setup_done'] = False
                    st.success("Accesso in modalità Beta Demo!")
                    st.rerun()
                    
        with tab_reg:
            email_reg = st.text_input(t["email_label"], key="reg_email")
            pass_reg = st.text_input(t["password_label"], type="password", key="reg_pass")
            
            if st.button(t["register_btn"], type="primary", use_container_width=True):
                if supabase_configurato and email_reg and pass_reg:
                    try:
                        supabase.auth.sign_up({"email": email_reg, "password": pass_reg})
                        st.success("Registrazione completata! Effettua il login.")
                    except Exception as e:
                        st.error(f"Errore: {e}")
                else:
                    if email_reg:
                        st.session_state['user'] = email_reg
                        st.session_state['profile_setup_done'] = False
                        st.rerun()
    st.stop()

# ==========================================
# 2. ONBOARDING PROFILI
# ==========================================
user_email = st.session_state['user']
user_tier = get_user_tier(user_email)

if not st.session_state.get('profile_setup_done', False):
    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
    with col_p2:
        st.markdown(f"<h2>{t['profile_setup_title']}</h2>", unsafe_allow_html=True)
        st.write(t['profile_setup_desc'])
        
        badge_class = "badge-free" if user_tier == "Free" else ("badge-pro" if user_tier == "Pro" else "badge-diamond")
        st.markdown(f"Piano: <span class='tier-badge {badge_class}'>{user_tier}</span>", unsafe_allow_html=True)
        st.divider()
        
        st.markdown("### ➕ Aggiungi Account")
        with st.form("form_add_profile"):
            piattaforma_in = st.selectbox("Piattaforma:", ["Lichess", "Chess.com"])
            username_in = st.text_input("Username:", placeholder="es. Chene91")
            submit_prof = st.form_submit_button("Salva Profilo", type="primary")
            
            if submit_prof:
                if username_in.strip():
                    success, msg = add_user_profile(user_email, piattaforma_in, username_in.strip())
                    if success:
                        st.success(msg)
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Inserisci un username valido.")
                    
        st.markdown("### 📋 Account Collegati")
        profiles_attuali = get_user_profiles(user_email)
        if profiles_attuali:
            for p in profiles_attuali:
                cols_pr = st.columns([2, 1])
                cols_pr[0].write(f"**{p['piattaforma']}**: `{p['username']}`")
                if cols_pr[1].button("🗑️ Rimuovi", key=f"del_prof_{p['id']}"):
                    delete_user_profile(p['id'])
                    st.rerun()
        else:
            st.info("Nessun profilo salvato finora.")
            
        st.divider()
        if st.button(t['continue_btn'], type="primary", use_container_width=True):
            st.session_state['profile_setup_done'] = True
            st.rerun()
    st.stop()

# ==========================================
# 3. ENGINE CON ANALISI ESCLUSIVA GIOCATORE (PUNTO 2) & FIX CONTEGGIO MOSSE (PUNTO 1)
# ==========================================
def determina_categoria_mossa(num_mossa, delta_cp, total_moves):
    if num_mossa <= 12:
        return "Apertura"
    elif num_mossa >= total_moves - 10 or (total_moves > 40 and num_mossa > 30):
        return "Finale"
    elif delta_cp >= 2.0:
        return "Tattica"
    else:
        return "Posizionale"

def analizza_partita_chess_api(pgn_text, target_usernames):
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if not game:
        return [], None, "Impossibile leggere il PGN fornito."

    headers = game.headers
    white_player = headers.get('White', 'Unknown').strip().lower()
    black_player = headers.get('Black', 'Unknown').strip().lower()
    
    # PUNTO 2: Determina se l'utente gioca col Bianco o col Nero
    user_is_white = True
    user_is_black = True
    
    if target_usernames:
        user_list = [u.strip().lower() for u in target_usernames]
        user_is_white = white_player in user_list
        user_is_black = black_player in user_list
        # Se non trova corrispondenze dirette, analizza il bianco come fallback
        if not user_is_white and not user_is_black:
            user_is_white = True

    partita_id = f"{headers.get('White', 'Unknown')}_vs_{headers.get('Black', 'Unknown')}_{headers.get('Date', 'Live')}"

    board = game.board()
    evaluations = []
    headers_req = {"User-Agent": "ChessCoachPro/1.0", "Content-Type": "application/json"}
    prev_eval = 0.0
    
    main_moves = list(game.mainline_moves())
    total_ply_count = len(main_moves)
    total_full_moves = (total_ply_count + 1) // 2  # PUNTO 1: Conteggio esatto mosse complete
    
    progress_bar = st.progress(0, text="Scansione Stockfish lampo in corso...")
    session = requests.Session()
    session.headers.update(headers_req)
    
    for idx, move in enumerate(main_moves):
        fen_before = board.fen()
        board.push(move)
        fen_after = board.fen()
        
        num_mossa = (idx // 2) + 1
        is_white_move = (idx % 2 == 0)
        
        # PUNTO 2: FILTRO ESCLUSIVO - Salta le mosse dell'avversario
        if is_white_move and not user_is_white:
            continue
        if not is_white_move and not user_is_black:
            continue

        label_mossa = f"{num_mossa}. {move.uci()}" if is_white_move else f"{num_mossa}... {move.uci()}"
        
        # PUNTO 1: Avanzamento visivo coerente
        progress_bar.progress((idx + 1) / total_ply_count, text=f"Scansione mossa {num_mossa} di {total_full_moves} (Ply {idx+1}/{total_ply_count})...")
        
        curr_eval = prev_eval
        valid_eval_found = False
        
        try:
            payload = {"fen": fen_after, "depth": 12}
            r = session.post("https://chess-api.com/v1", json=payload, timeout=3)
            if r.status_code == 200:
                data = r.json()
                eval_val = data.get("eval")
                mate_val = data.get("mate")
                
                if eval_val is not None:
                    curr_eval = float(eval_val)
                    valid_eval_found = True
                elif mate_val is not None:
                    curr_eval = 100.0 if mate_val > 0 else -100.0
                    valid_eval_found = True
        except Exception:
            pass

        if not valid_eval_found and idx > 0:
            curr_eval = prev_eval

        delta = (prev_eval - curr_eval) if is_white_move else (curr_eval - prev_eval)
        
        if delta >= 2.0:
            tipo_problema = "🔴 Blunder"
        elif delta >= 1.0:
            tipo_problema = "🟠 Mistake"
        elif delta >= 0.5:
            tipo_problema = "🟡 Inaccuracy"
        else:
            tipo_problema = None

        if tipo_problema:
            cat_mossa = determina_categoria_mossa(num_mossa, round(delta, 2), total_full_moves)
            evaluations.append({
                "mossa_num": idx + 1,
                "label_mossa": label_mossa,
                "fen_prima": fen_before,
                "fen_dopo": fen_after,
                "mossa_giocata": move.uci(),
                "perdita_cp": round(delta, 2),
                "eval_dopo": curr_eval,
                "tipo_problema": tipo_problema,
                "categoria": cat_mossa
            })
            
        prev_eval = curr_eval
        
    progress_bar.empty()
    return evaluations, partita_id, None

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

# --- SIDEBAR ---
with st.sidebar:
    st.header(t["settings"])
    badge_class = "badge-free" if user_tier == "Free" else ("badge-pro" if user_tier == "Pro" else "badge-diamond")
    st.markdown(f"👤 **{user_email}**<br>Piano: <span class='tier-badge {badge_class}'>{user_tier}</span>", unsafe_allow_html=True)
    st.divider()
    
    scelta_tema = st.selectbox(t["theme_select"], ["Dark", "Light"], index=0 if st.session_state['theme_mode']=='Dark' else 1)
    if scelta_tema != st.session_state['theme_mode']:
        st.session_state['theme_mode'] = scelta_tema
        st.rerun()

    if st.button("⚙️ Gestisci Profili", use_container_width=True):
        st.session_state['profile_setup_done'] = False
        st.rerun()

    scelta_lingua = st.selectbox(
        t["lang_select"],
        options=["Italiano", "English", "Español"],
        index=0 if st.session_state['lang'] == 'it' else (1 if st.session_state['lang'] == 'en' else 2)
    )
    lang_code = 'it' if scelta_lingua == "Italiano" else ('en' if scelta_lingua == "English" else 'es')
    if lang_code != st.session_state['lang']:
        st.session_state['lang'] = lang_code
        st.rerun()

    st.divider()
    if st.button(t["logout_btn"], use_container_width=True):
        if supabase:
            try: supabase.auth.sign_out()
            except Exception: pass
        st.session_state['user'] = None
        st.session_state['profile_setup_done'] = False
        st.rerun()

# --- HEADER APP & NAVIGAZIONE MOBILE CUSTOM ---
st.markdown(f"<div class='brand-title'>{t['title']}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='brand-sub'>{t['subtitle']}</div>", unsafe_allow_html=True)

nav_labels = [t["tab1"], t["tab2"], t["tab3"], t["tab4"], t["tab5"]]
cols_nav = st.columns(len(nav_labels))

for idx, label in enumerate(nav_labels):
    is_active = (st.session_state['active_nav_tab'] == idx)
    btn_type = "primary" if is_active else "secondary"
    if cols_nav[idx].button(label, key=f"nav_btn_{idx}", type=btn_type, use_container_width=True):
        st.session_state['active_nav_tab'] = idx
        st.rerun()

st.divider()

current_tab = st.session_state['active_nav_tab']

# ==========================================
# TAB 0: ANALIZZA PGN (PUNTO 3: UNICA SCACCHIERA E LISTA ERRORI SOTTO)
# ==========================================
if current_tab == 0:
    st.subheader(t["tab1"])
    
    pgn_val = st.session_state.get('pgn_manual_input', '')
    pgn_input = st.text_area("Incolla PGN della partita:", value=pgn_val, height=140, key="pgn_area_input")
    
    if st.button(t["analyze_btn"], type="primary", use_container_width=True):
        if not pgn_input.strip():
            st.warning("Inserisci un PGN valido.")
        else:
            pgn_hash = hash(pgn_input.strip())
            if st.session_state.get('last_analyzed_pgn') == pgn_hash:
                st.warning(t["already_analyzed"])
            else:
                st.session_state['last_analyzed_pgn'] = pgn_hash
                with st.spinner("Scansione personale in corso..."):
                    user_profs = get_user_profiles(user_email)
                    user_usernames = [p['username'] for p in user_profs]
                    
                    errori, p_id, err_msg = analizza_partita_chess_api(pgn_input.strip(), user_usernames)
                    st.session_state['stockfish_errors'] = errori
                    st.session_state['current_game_id'] = p_id
                    
                    game_obj = chess.pgn.read_game(io.StringIO(pgn_input.strip()))
                    if game_obj:
                        st.session_state['active_game_board'] = game_obj
                        st.session_state['active_game_moves'] = list(game_obj.mainline_moves())
                        st.session_state['current_board_ply'] = 0

                    if errori:
                        st.success(f"Stockfish: {len(errori)} {t['critique_found']}")
                        for item in errori:
                            salva_errore_db(user_email, p_id, item.get("categoria", "Tattica"), item.get("label_mossa", "Mossa"), f"Perdita {item.get('perdita_cp')} CP")
                    else:
                        st.info(t["no_errors"])

    # PUNTO 3: REPLAYER INTERATTIVO AD UNICA SCACCHIERA E LISTA ERRORI SOTTO
    if 'active_game_board' in st.session_state and st.session_state['active_game_board']:
        st.divider()
        game_moves = st.session_state['active_game_moves']
        max_ply = len(game_moves)
        total_full_moves = (max_ply + 1) // 2
        
        current_ply = st.session_state['current_board_ply']
        current_full_move = (current_ply + 1) // 2
        
        st.markdown(f"### ♟️ Scacchiera Interattiva — Mossa {current_full_move} di {total_full_moves} (Ply {current_ply}/{max_ply})")
        
        # Pulsanti di navigazione orizzontali
        c_b1, c_b2, c_b3, c_b4 = st.columns(4)
        if c_b1.button("⏪ Inizio"):
            st.session_state['current_board_ply'] = 0
            st.rerun()
        if c_b2.button("⬅️ Indietro") and current_ply > 0:
            st.session_state['current_board_ply'] -= 1
            st.rerun()
        if c_b3.button("➡️ Avanti") and current_ply < max_ply:
            st.session_state['current_board_ply'] += 1
            st.rerun()
        if c_b4.button("⏩ Fine"):
            st.session_state['current_board_ply'] = max_ply
            st.rerun()

        # Generazione UNICA della scacchiera principale
        temp_board = st.session_state['active_game_board'].board()
        for i in range(st.session_state['current_board_ply']):
            temp_board.push(game_moves[i])

        st.write(chess.svg.board(board=temp_board, size=360), unsafe_allow_html=True)
        
        # ELENCO TESTUALE DEGLI ERRORI SOTTO LA SCACCHIERA (NO GRAFICI/NO SCACCHIERI RIPETUTI)
        st.divider()
        st.markdown("### 📋 Lista Errori Rilevati sulle Tue Mosse")
        if 'stockfish_errors' in st.session_state and st.session_state['stockfish_errors']:
            for idx, err in enumerate(st.session_state['stockfish_errors']):
                cat_label = err.get('categoria', 'Tattica')
                with st.expander(f"{err['tipo_problema']} su `{err['label_mossa']}` — Categoria: [{cat_label}] (Perdita: -{err['perdita_cp']} CP)"):
                    btn_key = f"btn_lesson_{idx}"
                    if st.button(f"{t['gm_lesson_btn']} {err['label_mossa']}", key=btn_key, type="primary"):
                        if not MASTER_GEMINI_KEY:
                            st.error("Chiave Master Gemini non configurata.")
                        else:
                            with st.spinner("Analisi GM in generazione..."):
                                try:
                                    genai.configure(api_key=MASTER_GEMINI_KEY)
                                    generation_config = {"max_output_tokens": 150, "temperature": 0.3}
                                    model_gm = genai.GenerativeModel(GEMINI_MODEL_NAME, generation_config=generation_config)
                                    prompt_lesson = f"""
                                    Sei un GM. FEN: {err['fen_prima']} | Mossa errata: {err['mossa_giocata']}.
                                    {t['prompt_lang']}
                                    In max 30 parole spieghi: 1. L'errore. 2. La mossa migliore. 3. Regola d'oro.
                                    """
                                    resp = model_gm.generate_content(prompt_lesson)
                                    st.session_state[f"lesson_{idx}"] = resp.text
                                except Exception as e:
                                    st.error(f"Errore AI: {e}")
                    if f"lesson_{idx}" in st.session_state:
                        st.info(st.session_state[f"lesson_{idx}"])
        else:
            st.info("Nessun errore grave registrato sulle tue mosse in questa partita.")

# ==========================================
# TAB 1: DASHBOARD AVANZATA & FILTRATA
# ==========================================
elif current_tab == 1:
    st.subheader(t["tab2"])
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

        st.markdown("---")
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Totale Errori Personali", len(df_filtered))
        kpi2.metric("Partite Analizzate", df_filtered['partita_id'].nunique() if 'partita_id' in df_filtered else 0)
        kpi3.metric("Indice di Precisione Personale", f"{max(0, 100 - len(df_filtered)*3)}%")

        st.markdown("---")

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("### 📊 Errori per Categoria")
            if not df_filtered.empty:
                counts_cat = df_filtered['categoria_errore'].value_counts()
                st.bar_chart(counts_cat)
            else:
                st.info("Nessun dato per i filtri selezionati.")
                
        with col_g2:
            st.markdown("### 📈 Trend Errori nel Tempo")
            if not df_filtered.empty and 'data' in df_filtered.columns:
                counts_date = df_filtered.groupby('data').size()
                st.line_chart(counts_date)
            else:
                st.info("Dati temporali non sufficienti.")

        st.markdown("### 🗂️ Registro Dettagliato Errori")
        st.dataframe(df_filtered[['data', 'partita_id', 'categoria_errore', 'mossa_critica', 'spiegazione']], hide_index=True, use_container_width=True)
    else:
        st.info("Nessun errore salvato nel cloud. Analizza qualche partita per popolare la tua Dashboard di crescita!")

# ==========================================
# TAB 2: STUDIO LIBRI
# ==========================================
elif current_tab == 2:
    st.subheader(t["tab3"])
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
                        steps.append({"ply": idx+1, "mossa_giocata": san, "fen": board.fen(), "commento": dati_libro.get("commenti", {}).get(str(idx+1), "")})
                    except Exception: break
                st.session_state['book_steps'] = steps
                st.session_state['current_ply'] = 0
                st.success("Studio pronto!")
            except Exception as e: st.error(f"Errore: {e}")

    if 'book_steps' in st.session_state and st.session_state['book_steps']:
        steps = st.session_state['book_steps']
        max_p = len(steps) - 1
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("⏪"): st.session_state['current_ply'] = 0; st.rerun()
        if c2.button("⬅️") and st.session_state['current_ply'] > 0: st.session_state['current_ply'] -= 1; st.rerun()
        if c3.button("➡️") and st.session_state['current_ply'] < max_p: st.session_state['current_ply'] += 1; st.rerun()
        if c4.button("⏩"): st.session_state['current_ply'] = max_p; st.rerun()
        
        cur = steps[st.session_state['current_ply']]
        col_v1, col_v2 = st.columns([1, 1])
        with col_v1: st.write(chess.svg.board(board=chess.Board(cur['fen']), size=280), unsafe_allow_html=True)
        with col_v2: st.info(cur['commento'])

# ==========================================
# TAB 3: DIARIO & PDF
# ==========================================
elif current_tab == 3:
    st.subheader(t["tab4"])
    input_diario = st.text_area("Inserisci la sequenza di mosse:", height=100)
    if st.button("🔄 Carica Scacchiera"):
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
                st.success("Partita caricata!")
            except Exception as e: st.error(f"Errore: {e}")

    if 'diario_mosse' in st.session_state and st.session_state['diario_mosse']:
        mosse_d = st.session_state['diario_mosse']
        b_d = chess.Board()
        for m in mosse_d: b_d.push(b_d.parse_san(m))
        col_d1, col_d2 = st.columns([1, 1])
        with col_d1: st.write(chess.svg.board(board=b_d, size=280), unsafe_allow_html=True)
        with col_d2:
            for idx, m in enumerate(mosse_d):
                st.session_state['diario_note_mosse'][str(idx)] = st.text_input(f"Nota {m}:", value=st.session_state['diario_note_mosse'].get(str(idx), ""), key=f"note_pdf_{idx}")
        if st.button("⚙️ Genera ed Esporta PDF", type="primary"):
            pdf_b = genera_pdf_partita(b_d, mosse_d, st.session_state['diario_note_mosse'], "")
            st.download_button("📥 Scarica Report PDF", data=pdf_b, file_name="diario_partita.pdf", mime="application/pdf")

# ==========================================
# TAB 4: IMPORTA PARTITE
# ==========================================
elif current_tab == 4:
    st.subheader(t["tab5"])
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
            st.info("Nessun profilo salvato. Inseriscine uno al volo:")
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
                        params_lic = {"max": limite_partite}
                        r = requests.get(url_lic, params=params_lic, headers=headers_lic, timeout=20)
                        if r.status_code == 200:
                            st.session_state['partite_importate'] = r.text
                            st.success(f"Scaricamento completato per {usr}!")
                        else:
                            st.error(f"Errore Lichess (HTTP {r.status_code}).")
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
                                    st.success(f"Scaricamento completato per {usr}!")
                                else:
                                    st.error("Errore archivio Chess.com.")
                            else:
                                st.warning("Nessun archivio trovato.")
                        else:
                            st.error(f"Utente non trovato (HTTP {r_arch.status_code}).")
                except Exception as e: 
                    st.error(f"Errore download: {e}")
        else:
            st.warning("Username non valido.")

    if 'partite_importate' in st.session_state and st.session_state['partite_importate']:
        st.divider()
        st.markdown("### 🔍 Filtra Partite Scaricate")
        
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
                    "pgn": pgn_str,
                    "tc": tc,
                    "result": result
                })

        if parsed_games:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_tc = st.selectbox("Filtra Tempo:", ["Tutti", "Blitz", "Rapid", "Bullet", "Classical", "Altro/Custom"])
            with col_f2:
                filtro_res = st.selectbox("Filtra Risultato:", ["Tutti", "Vittorie Bianco (1-0)", "Vittorie Nero (0-1)", "Patte (1/2-1/2)"])

            filtered_games = parsed_games
            if filtro_tc != "Tutti":
                filtered_games = [g for g in filtered_games if g['tc'] == filtro_tc]
            if filtro_res == "Vittorie Bianco (1-0)":
                filtered_games = [g for g in filtered_games if g['result'] == "1-0"]
            elif filtro_res == "Vittorie Nero (0-1)":
                filtered_games = [g for g in filtered_games if g['result'] == "0-1"]
            elif filtro_res == "Patte (1/2-1/2)":
                filtered_games = [g for g in filtered_games if g['result'] == "1/2-1/2"]

            st.write(f"Trovate **{len(filtered_games)}** partite.")

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
                st.warning("Nessuna partita corrisponde ai filtri.")