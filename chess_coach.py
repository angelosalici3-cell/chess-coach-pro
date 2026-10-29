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
import berserk
from fpdf import FPDF
from PIL import Image
from supabase import create_client, Client

# --- CONFIGURAZIONE CENTRALIZZATA ---
MASTER_GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def init_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY or "INSERISCI" in SUPABASE_URL:
        return None
    try:
        return create_client(SUPABASE_URL.strip(), SUPABASE_KEY.strip())
    except Exception:
        return None

supabase = init_supabase()

# --- STILE CSS MODERN, MOBILE-FIRST & ACCATTIVANTE ---
CUSTOM_CSS = """
<style>
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #161b22 100%);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    h1, h2, h3 {
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }
    .brand-title {
        background: linear-gradient(90deg, #FFD700, #FFA500);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        font-weight: 900;
        text-align: center;
        margin-bottom: 0px;
    }
    .brand-sub {
        text-align: center;
        color: #8b949e;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    div[data-testid="stExpander"], div.stMarkdown > div {
        border-radius: 12px;
    }
    .tier-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        text-transform: uppercase;
    }
    .badge-free { background: #21262d; color: #8b949e; border: 1px solid #30363d; }
    .badge-pro { background: rgba(255, 215, 0, 0.15); color: #FFD700; border: 1px solid #FFD700; }
    .badge-diamond { background: rgba(0, 210, 255, 0.15); color: #00d2ff; border: 1px solid #00d2ff; }
    
    .stTextInput input, .stTextArea textarea, .stSelectbox div {
        border-radius: 10px !important;
    }
    button[kind="primary"] {
        border-radius: 10px !important;
        background: linear-gradient(90deg, #FFD700 0%, #FFA500 100%) !important;
        color: #0e1117 !important;
        font-weight: 800 !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(255, 215, 0, 0.2);
        transition: all 0.2s ease;
    }
    button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 215, 0, 0.35);
    }
</style>
"""

# --- DIZIONARIO MULTILINGUE (i18n) ---
TEXTS = {
    "it": {
        "title": "⚡ Chess Coach Pro",
        "subtitle": "Coaching Scacchistico AI ad Altissima Efficienza",
        "tab1": "📖 Analizza",
        "tab2": "📊 Dashboard",
        "tab3": "📚 Libri",
        "tab4": "📝 Diario",
        "tab5": "🌐 Importa",
        "settings": "⚙️ Account",
        "lang_select": "🌐 Lingua / Language:",
        "login_header": "🔐 Accedi",
        "register_header": "📝 Registrati",
        "email_label": "Email:",
        "password_label": "Password:",
        "login_btn": "Accedi alla Piattaforma",
        "register_btn": "Crea Account",
        "logout_btn": "🚪 Disconnetti",
        "analyze_btn": "🔍 Avvia Analisi Cloud",
        "critique_found": "criticità identificate!",
        "no_errors": "Partita eccellente! Nessun errore grave rilevato.",
        "gm_lesson_btn": "🎓 Analisi Rapida GM",
        "prompt_lang": "Rispondi in italiano.",
        "profile_setup_title": "🎯 Configura i tuoi Profili",
        "profile_setup_desc": "Collega i tuoi account Lichess o Chess.com per importare le tue partite al volo.",
        "continue_btn": "🚀 Entra nell'App"
    },
    "en": {
        "title": "⚡ Chess Coach Pro",
        "subtitle": "High-Efficiency AI Chess Coaching",
        "tab1": "📖 Analyze",
        "tab2": "📊 Dashboard",
        "tab3": "📚 Books",
        "tab4": "📝 Diary",
        "tab5": "🌐 Import",
        "settings": "⚙️ Account",
        "lang_select": "🌐 Language:",
        "login_header": "🔐 Login",
        "register_header": "📝 Register",
        "email_label": "Email:",
        "password_label": "Password:",
        "login_btn": "Login to Platform",
        "register_btn": "Create Account",
        "logout_btn": "🚪 Logout",
        "analyze_btn": "🔍 Start Cloud Analysis",
        "critique_found": "critical issues identified!",
        "no_errors": "Great game! Stockfish found no major blunders.",
        "gm_lesson_btn": "🎓 Quick GM Insight",
        "prompt_lang": "Respond in English.",
        "profile_setup_title": "🎯 Setup your Chess Profiles",
        "profile_setup_desc": "Link your Lichess or Chess.com accounts to sync your games.",
        "continue_btn": "🚀 Enter App"
    },
    "es": {
        "title": "⚡ Chess Coach Pro",
        "subtitle": "Entrenamiento de Ajedrez con IA de Alta Eficiencia",
        "tab1": "📖 Analizar",
        "tab2": "📊 Dashboard",
        "tab3": "📚 Libros",
        "tab4": "📝 Diario",
        "tab5": "🌐 Importar",
        "settings": "⚙️ Cuenta",
        "lang_select": "🌐 Idioma:",
        "login_header": "🔐 Iniciar Sesión",
        "register_header": "📝 Registrarse",
        "email_label": "Correo electrónico:",
        "password_label": "Contraseña:",
        "login_btn": "Iniciar Sesión",
        "register_btn": "Crear Cuenta",
        "logout_btn": "🚪 Cerrar Sesión",
        "analyze_btn": "🔍 Iniciar Análisis Cloud",
        "critique_found": "¡críticas identificadas!",
        "no_errors": "¡Excelente partida! Sin errores graves.",
        "gm_lesson_btn": "🎓 Análisis Rápido GM",
        "prompt_lang": "Responde en español.",
        "profile_setup_title": "🎯 Configura tus Perfiles",
        "profile_setup_desc": "Vincula tus cuentas para sincronizar tus partidas.",
        "continue_btn": "🚀 Entrar a la App"
    }
}

st.set_page_config(page_title="Chess Coach Pro", layout="wide", page_icon="⚡")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'lang' not in st.session_state:
    st.session_state['lang'] = 'it'
if 'profile_setup_done' not in st.session_state:
    st.session_state['profile_setup_done'] = False
if 'active_nav_tab' not in st.session_state:
    st.session_state['active_nav_tab'] = 0

t = TEXTS[st.session_state['lang']]

# --- SUPABASE FUNCTIONS ---
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

def salva_errore_db(user_email, categoria, mossa, spiegazione):
    if supabase:
        try:
            data_ora = datetime.datetime.now().strftime("%Y-%m-%d")
            supabase.table("errori_utenti").insert({
                "user_email": user_email,
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
    return pd.DataFrame(columns=["data", "categoria_errore", "mossa_critica", "spiegazione"])

# ==========================================
# 1. LANDING / LOGIN PAGE
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
# 2. CONFIGURAZIONE PROFILI POST-LOGIN
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
# 3. APPLICAZIONE PRINCIPALE
# ==========================================
def analizza_partita_chess_api(pgn_text):
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if not game:
        return [], None, "Impossibile leggere il PGN fornito."

    board = game.board()
    evaluations = []
    headers_req = {"User-Agent": "ChessCoachPro/1.0", "Content-Type": "application/json"}
    prev_eval = 0.0
    
    main_moves = list(game.mainline_moves())
    progress_bar = st.progress(0, text="Analisi cloud in corso...")
    
    for idx, move in enumerate(main_moves):
        fen_before = board.fen()
        board.push(move)
        fen_after = board.fen()
        
        num_mossa = (idx // 2) + 1
        is_white_move = (idx % 2 == 0)
        label_mossa = f"{num_mossa}. {move.uci()}" if is_white_move else f"{num_mossa}... {move.uci()}"
        
        progress_bar.progress((idx + 1) / len(main_moves), text=f"Analisi mossa {num_mossa}/{len(main_moves)}...")
        
        curr_eval = prev_eval
        valid_eval_found = False
        
        for attempt in range(2):
            try:
                payload = {"fen": fen_after, "depth": 12}
                r = requests.post("https://chess-api.com/v1", json=payload, headers=headers_req, timeout=6)
                if r.status_code == 200:
                    data = r.json()
                    eval_val = data.get("eval")
                    mate_val = data.get("mate")
                    
                    if eval_val is not None:
                        curr_eval = float(eval_val)
                        valid_eval_found = True
                        break
                    elif mate_val is not None:
                        curr_eval = 100.0 if mate_val > 0 else -100.0
                        valid_eval_found = True
                        break
            except Exception:
                time.sleep(0.1)

        if not valid_eval_found and idx > 0:
            curr_eval = prev_eval

        delta = (prev_eval - curr_eval) if is_white_move else (curr_eval - prev_eval)
        
        if delta >= 2.0:
            tipo_problema = "🔴 Errore Grave (Blunder)"
        elif delta >= 1.0:
            tipo_problema = "🟠 Errore (Mistake)"
        elif delta >= 0.5:
            tipo_problema = "🟡 Imprecisione (Inaccuracy)"
        else:
            tipo_problema = None

        if tipo_problema:
            evaluations.append({
                "mossa_num": idx + 1,
                "label_mossa": label_mossa,
                "fen_prima": fen_before,
                "fen_dopo": fen_after,
                "mossa_giocata": move.uci(),
                "perdita_cp": round(delta, 2),
                "eval_dopo": curr_eval,
                "tipo_problema": tipo_problema
            })
            
        prev_eval = curr_eval
        
    progress_bar.empty()
    return evaluations, None, None

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

# --- SIDEBAR COMPATTA ---
with st.sidebar:
    st.header(t["settings"])
    badge_class = "badge-free" if user_tier == "Free" else ("badge-pro" if user_tier == "Pro" else "badge-diamond")
    st.markdown(f"👤 **{user_email}**<br>Piano: <span class='tier-badge {badge_class}'>{user_tier}</span>", unsafe_allow_html=True)
    st.divider()
    
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
# TAB 0: ANALIZZA PGN (STOCKFISH + GEMINI 1.5 FLASH OPTIMIZED)
# ==========================================
if current_tab == 0:
    st.subheader(t["tab1"])
    
    pgn_val = st.session_state.get('pgn_manual_input', '')
    pgn_input = st.text_area("Incolla PGN della partita:", value=pgn_val, height=160, key="pgn_area_input")
    
    if st.button(t["analyze_btn"], type="primary", use_container_width=True):
        if not pgn_input.strip():
            st.warning("Inserisci un PGN valido.")
        else:
            st.session_state['pgn_manual_input'] = pgn_input
            with st.spinner("Scansione cloud in corso..."):
                errori, game_url, err_msg = analizza_partita_chess_api(pgn_input.strip())
                st.session_state['stockfish_errors'] = errori
                
                if errori:
                    st.success(f"Stockfish: {len(errori)} {t['critique_found']}")
                    if MASTER_GEMINI_KEY:
                        try:
                            genai.configure(api_key=MASTER_GEMINI_KEY)
                            # UTILIZZO GEMINI 1.5 FLASH (GRATUITO / COSTI MINIMI) CON PROMPT COMPATTO MINIMIZZATORE DI TOKEN
                            model = genai.GenerativeModel("gemini-1.5-flash")
                            prompt_c = f"Classifica in tag brevi (Tattica, Strategia, Apertura, Finale) questi errori scacchistici: {json.dumps(errori)}. {t['prompt_lang']} Restituisci SOLO JSON puro: [{{\"label_mossa\": \"14. e5\", \"categoria\": \"Tattica\"}}]"
                            resp_c = model.generate_content(prompt_c)
                            clusters = json.loads(resp_c.text.replace("```json", "").replace("```", "").strip())
                            for item in clusters:
                                salva_errore_db(user_email, item.get("categoria", "Tattica"), item.get("label_mossa", "Mossa"), "Errore")
                        except Exception:
                            pass
                else:
                    st.info(t["no_errors"])

    if 'stockfish_errors' in st.session_state and st.session_state['stockfish_errors']:
        st.divider()
        for idx, err in enumerate(st.session_state['stockfish_errors']):
            with st.expander(f"{err['tipo_problema']}: Mossa `{err['label_mossa']}`", expanded=(idx==0)):
                col_b, col_t = st.columns([1, 1])
                with col_b:
                    st.write(chess.svg.board(board=chess.Board(err['fen_prima']), size=280), unsafe_allow_html=True)
                with col_t:
                    st.markdown(f"**Perdita:** `-{err['perdita_cp']}` pedoni")
                    btn_key = f"btn_lesson_{idx}"
                    if st.button(f"{t['gm_lesson_btn']} {err['label_mossa']}", key=btn_key, type="primary"):
                        if not MASTER_GEMINI_KEY:
                            st.error("Chiave Master Gemini non configurata.")
                        else:
                            with st.spinner("Analisi GM..."):
                                try:
                                    genai.configure(api_key=MASTER_GEMINI_KEY)
                                    # MODELLO FLASH E PROMPT ULTRA-COMPATTO PER MINIMIZZARE I TOKEN DI INPUT/OUTPUT
                                    model_gm = genai.GenerativeModel("gemini-1.5-flash")
                                    prompt_lesson = f"""
                                    Sei un GM di scacchi. FEN: {err['fen_prima']} | Errore: {err['tipo_problema']} ({err['mossa_giocata']}).
                                    {t['prompt_lang']}
                                    Scrivi un'analisi concisa in 3 righe esatte:
                                    1. Perché è un errore.
                                    2. La mossa corretta.
                                    3. Regola chiave.
                                    Sii brevissimo ed efficiente.
                                    """
                                    resp = model_gm.generate_content(prompt_lesson)
                                    st.session_state[f"lesson_{idx}"] = resp.text
                                except Exception as e:
                                    st.error(f"Errore AI: {e}")
                    if f"lesson_{idx}" in st.session_state:
                        st.info(st.session_state[f"lesson_{idx}"])

# ==========================================
# TAB 1: DASHBOARD ERRORI PERSISTENTE
# ==========================================
elif current_tab == 1:
    st.subheader(t["tab2"])
    df_err = carica_errori_db(user_email)
    if not df_err.empty:
        c1, c2 = st.columns([1, 1])
        with c1: st.bar_chart(df_err['categoria_errore'].value_counts())
        with c2: st.dataframe(df_err[['data', 'categoria_errore', 'mossa_critica']], hide_index=True, use_container_width=True)
    else:
        st.info("Nessun errore salvato nel tuo database cloud.")

# ==========================================
# TAB 2: STUDIO LIBRI INTERATTIVO
# ==========================================
elif current_tab == 2:
    st.subheader(t["tab3"])
    testo_libro_input = st.text_area("Incolla il testo del libro:", height=140)
    if st.button("🚀 Elabora Testo con AI", type="primary"):
        if MASTER_GEMINI_KEY and testo_libro_input:
            try:
                genai.configure(api_key=MASTER_GEMINI_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
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
# TAB 3: DIARIO & GENERATORE PDF
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
# TAB 4: IMPORTA & FILTRA PARTITE
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

                if st.button("🚀 Invia ad Analisi Stockfish + AI", type="primary", use_container_width=True):
                    st.session_state['pgn_manual_input'] = chosen_pgn
                    st.session_state['active_nav_tab'] = 0
                    st.rerun()
            else:
                st.warning("Nessuna partita corrisponde ai filtri.")