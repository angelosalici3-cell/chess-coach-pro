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

# --- DIZIONARIO MULTILINGUE (i18n) ---
TEXTS = {
    "it": {
        "title": "♟️ Chess Coach Pro",
        "subtitle": "La tua piattaforma di coaching scacchistico avanzato basata su AI",
        "tab1": "📖 Analizza PGN (Stockfish + AI)",
        "tab2": "📊 Dashboard Errori",
        "tab3": "📚 Studio Libri",
        "tab4": "📝 Diario & PDF",
        "tab5": "🌐 Importa & Filtra Partite",
        "settings": "⚙️ Account & Preferenze",
        "lang_select": "🌐 Lingua / Language:",
        "login_header": "🔐 Accedi a Chess Coach Pro",
        "register_header": "📝 Registrati",
        "email_label": "Email:",
        "password_label": "Password:",
        "login_btn": "Accedi alla Piattaforma",
        "register_btn": "Crea Nuovo Account",
        "logout_btn": "🚪 Disconnetti",
        "analyze_btn": "🔍 Avvia Analisi Cloud",
        "critique_found": "criticità identificate nella partita!",
        "no_errors": "Stockfish non ha rilevato imprecisioni o errori rilevanti. Partita eccellente!",
        "gm_lesson_btn": "🎓 Chiedi Lezione al GM su Mossa",
        "prompt_lang": "Rispondi in LINGUA ITALIANA.",
        "profile_setup_title": "🎯 Configura i tuoi Profili Scacchistici",
        "profile_setup_desc": "Collega i tuoi account ufficiali per analizzare le tue partite in un click.",
        "continue_btn": "🚀 Entra nella Piattaforma"
    },
    "en": {
        "title": "♟️ Chess Coach Pro",
        "subtitle": "Your advanced AI-powered chess coaching platform",
        "tab1": "📖 Analyze PGN (Stockfish + AI)",
        "tab2": "📊 Mistakes Dashboard",
        "tab3": "📚 Book Study",
        "tab4": "📝 Diario & PDF",
        "tab5": "🌐 Import & Filter Games",
        "settings": "⚙️ Account & Preferences",
        "lang_select": "🌐 Language:",
        "login_header": "🔐 Login to Chess Coach Pro",
        "register_header": "📝 Register",
        "email_label": "Email:",
        "password_label": "Password:",
        "login_btn": "Login to Platform",
        "register_btn": "Create New Account",
        "logout_btn": "🚪 Logout",
        "analyze_btn": "🔍 Start Cloud Analysis",
        "critique_found": "critical issues identified in the game!",
        "no_errors": "Stockfish detected no significant mistakes or inaccuracies. Great game!",
        "gm_lesson_btn": "🎓 Ask GM Lesson for Move",
        "prompt_lang": "Respond in ENGLISH language.",
        "profile_setup_title": "🎯 Setup your Chess Profiles",
        "profile_setup_desc": "Link your official accounts to analyze your games in one click.",
        "continue_btn": "🚀 Enter Platform"
    },
    "es": {
        "title": "♟️ Chess Coach Pro",
        "subtitle": "Tu plataforma avanzada de entrenamiento de ajedrez con IA",
        "tab1": "📖 Analizar PGN (Stockfish + IA)",
        "tab2": "📊 Panel de Errores",
        "tab3": "📚 Estudio de Libros",
        "tab4": "📝 Diario y PDF",
        "tab5": "🌐 Importar y Filtrar Partidas",
        "settings": "⚙️ Cuenta y Preferencias",
        "lang_select": "🌐 Idioma:",
        "login_header": "🔐 Iniciar Sesión",
        "register_header": "📝 Registrarse",
        "email_label": "Correo electrónico:",
        "password_label": "Contraseña:",
        "login_btn": "Iniciar Sesión",
        "register_btn": "Crear Cuenta",
        "logout_btn": "🚪 Cerrar Sesión",
        "analyze_btn": "🔍 Iniciar Análisis Cloud",
        "critique_found": "¡críticas identificadas en la partida!",
        "no_errors": "¡Stockfish no detectó errores ni imprecisiones importantes. Excelente partida!",
        "gm_lesson_btn": "🎓 Pedir Lección al Gran Maestro",
        "prompt_lang": "Responde en IDIOMA ESPAÑOL.",
        "profile_setup_title": "🎯 Configura tus Perfiles de Ajedrez",
        "profile_setup_desc": "Vincula tus cuentas oficiales para analizar tus partidas en un clic.",
        "continue_btn": "🚀 Entrar a la Plataforma"
    }
}

st.set_page_config(page_title="Chess Coach Pro", layout="wide", page_icon="♟️")

if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'lang' not in st.session_state:
    st.session_state['lang'] = 'it'
if 'profile_setup_done' not in st.session_state:
    st.session_state['profile_setup_done'] = False

t = TEXTS[st.session_state['lang']]

# --- FUNZIONI DATABASE SUPABASE (PROFILI E TIER) ---
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
        return False, f"Limite raggiunto per il tuo piano ({tier}): massimo {limit} profil{'io' if limit==1 else 'i'}."
    
    if supabase:
        try:
            supabase.table("profili_scacchi").insert({
                "user_email": email,
                "piattaforma": piattaforma,
                "username": username.strip()
            }).execute()
            return True, "Profilo aggiunto con successo!"
        except Exception as e:
            return False, f"Errore database: {e}"
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
# 1. SCHERMATA DI LOGIN / REGISTRAZIONE
# ==========================================
if not st.session_state['user']:
    col_l1, col_l2, col_l3 = st.columns([1, 1.3, 1])
    
    with col_l2:
        st.markdown(f"<h1 style='text-align: center;'>{t['title']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: gray;'>{t['subtitle']}</p>", unsafe_allow_html=True)
        st.divider()
        
        with st.expander("🛠️ Diagnostica di Connessione Supabase", expanded=False):
            st.write(f"**URL configurato:** `{SUPABASE_URL if SUPABASE_URL else 'Mancante'}`")
            if st.button("🧪 Esegui Test di Connessione"):
                if not SUPABASE_URL or not SUPABASE_KEY:
                    st.error("❌ Credenziali assenti nei Secrets.")
                else:
                    try:
                        test_client = create_client(SUPABASE_URL.strip(), SUPABASE_KEY.strip())
                        test_client.table("errori_utenti").select("*").limit(1).execute()
                        st.success("✅ Connessione a Supabase riuscita!")
                    except Exception as e:
                        st.error(f"❌ Errore: {e}")
        
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
                    st.warning("⚠️ Modalità Demo attiva.")
                    if email_reg:
                        st.session_state['user'] = email_reg
                        st.session_state['profile_setup_done'] = False
                        st.rerun()
                        
    st.stop()

# ==========================================
# 2. SCHERMATA ONBOARDING / CONFIGURAZIONE PROFILI
# ==========================================
user_email = st.session_state['user']
user_tier = get_user_tier(user_email)
user_profiles = get_user_profiles(user_email)

if not st.session_state.get('profile_setup_done', False):
    col_p1, col_p2, col_p3 = st.columns([1, 1.5, 1])
    with col_p2:
        st.markdown(f"<h2>{t['profile_setup_title']}</h2>", unsafe_allow_html=True)
        st.write(t['profile_setup_desc'])
        st.info(f"🏷️ Il tuo piano attuale: **{user_tier}** (Limite: {'1 profilo' if user_tier=='Free' else ('3 profili' if user_tier=='Pro' else '5 profili')})")
        st.divider()
        
        st.markdown("### ➕ Aggiungi un Profilo")
        with st.form("form_add_profile"):
            piattaforma_in = st.selectbox("Piattaforma:", ["Lichess", "Chess.com"])
            username_in = st.text_input("Nome Utente (Username):", placeholder="es. Chene91")
            submit_prof = st.form_submit_button("Salva Profilo", type="primary")
            
            if submit_prof:
                if username_in.strip():
                    success, msg = add_user_profile(user_email, piattaforma_in, username_in.strip())
                    if success:
                        st.success(msg)
                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Inserisci un username valido.")
                    
        st.markdown("### 📋 I tuoi Profili Salvati")
        profiles_attuali = get_user_profiles(user_email)
        if profiles_attuali:
            for p in profiles_attuali:
                cols_pr = st.columns([2, 1, 1])
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
    progress_bar = st.progress(0, text="Analisi cloud avanzata in corso...")
    
    for idx, move in enumerate(main_moves):
        fen_before = board.fen()
        board.push(move)
        fen_after = board.fen()
        
        num_mossa = (idx // 2) + 1
        is_white_move = (idx % 2 == 0)
        label_mossa = f"{num_mossa}. {move.uci()}" if is_white_move else f"{num_mossa}... {move.uci()}"
        
        progress_bar.progress((idx + 1) / len(main_moves), text=f"Analisi mossa {num_mossa} di {len(main_moves)}...")
        
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
                time.sleep(0.2)
                
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

# --- SIDEBAR PRINCIPALE ---
with st.sidebar:
    st.header(t["settings"])
    st.info(f"👤 **{user_email}**\n\n🏷️ Piano: **{user_tier}**")
    
    if st.button("⚙️ Gestisci Profili Scacchistici", use_container_width=True):
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

st.title(t["title"])

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    t["tab1"], t["tab2"], t["tab3"], t["tab4"], t["tab5"]
])

# --- TAB 1: ANALISI PGN CON MASTER GEMINI KEY ---
with tab1:
    st.subheader(t["tab1"])
    
    # Se arriva una partita trasferita dalla Tab 5, la inserisce in automatico nella textarea
    default_pgn = st.session_state.pop('selected_game_pgn', st.session_state.get('pgn_manual_input', ''))
    pgn_input = st.text_area("PGN della partita:", value=default_pgn, height=150, key="pgn_manual_input")
    
    if st.button(t["analyze_btn"], type="primary"):
        if not pgn_input.strip():
            st.warning("Inserisci un PGN valido.")
        else:
            with st.spinner("Scansione in corso..."):
                errori, game_url, err_msg = analizza_partita_chess_api(pgn_input.strip())
                st.session_state['stockfish_errors'] = errori
                
                if errori:
                    st.success(f"Stockfish: {len(errori)} {t['critique_found']}")
                    if MASTER_GEMINI_KEY:
                        try:
                            genai.configure(api_key=MASTER_GEMINI_KEY)
                            model = genai.GenerativeModel("gemini-2.5-flash")
                            prompt_c = f"Categorizza queste criticità scacchistiche: {json.dumps(errori)}. {t['prompt_lang']} Restituisci JSON: [{{\"label_mossa\": \"14. e5\", \"categoria\": \"Tattica\"}}]"
                            resp_c = model.generate_content(prompt_c)
                            clusters = json.loads(resp_c.text.replace("```json", "").replace("```", "").strip())
                            for item in clusters:
                                salva_errore_db(user_email, item.get("categoria", "Tattica"), item.get("label_mossa", "Mossa"), "Criticità rilevata")
                        except Exception:
                            pass
                else:
                    st.info(t["no_errors"])

    if 'stockfish_errors' in st.session_state and st.session_state['stockfish_errors']:
        st.divider()
        for idx, err in enumerate(st.session_state['stockfish_errors']):
            with st.expander(f"{err['tipo_problema']}: Mossa `{err['label_mossa']}`", expanded=(idx==0)):
                col_b, col_t = st.columns(2)
                with col_b:
                    st.write(chess.svg.board(board=chess.Board(err['fen_prima']), size=300), unsafe_allow_html=True)
                with col_t:
                    st.markdown(f"**Perdita:** `-{err['perdita_cp']}` pedoni")
                    btn_key = f"btn_lesson_{idx}"
                    if st.button(f"{t['gm_lesson_btn']} {err['label_mossa']}", key=btn_key, type="primary"):
                        if not MASTER_GEMINI_KEY:
                            st.error("Chiave Master Gemini non configurata.")
                        else:
                            with st.spinner("GM AI..."):
                                try:
                                    genai.configure(api_key=MASTER_GEMINI_KEY)
                                    model_gm = genai.GenerativeModel("gemini-2.5-flash")
                                    prompt_lesson = f"""
                                    Sei un GM di scacchi. Nella posizione FEN {err['fen_prima']}, l'allievo ha commesso un {err['tipo_problema']} giocando {err['mossa_giocata']}.
                                    {t['prompt_lang']}
                                    Spiega: 1. Perché la mossa è errata. 2. Il piano corretto. 3. Regola d'oro.
                                    """
                                    resp = model_gm.generate_content(prompt_lesson)
                                    st.session_state[f"lesson_{idx}"] = resp.text
                                except Exception as e:
                                    st.error(f"Errore: {e}")
                    if f"lesson_{idx}" in st.session_state:
                        st.success(st.session_state[f"lesson_{idx}"])

# --- TAB 2: DASHBOARD UTENTE PERSISTENTE ---
with tab2:
    st.subheader(t["tab2"])
    df_err = carica_errori_db(user_email)
    if not df_err.empty:
        c1, c2 = st.columns(2)
        with c1: st.bar_chart(df_err['categoria_errore'].value_counts())
        with c2: st.dataframe(df_err[['data', 'categoria_errore', 'mossa_critica']], hide_index=True)
    else:
        st.info("Nessun errore salvato nel tuo database cloud.")

# --- TAB 3: STUDIO LIBRI INTERATTIVO ---
with tab3:
    st.subheader(t["tab3"])
    testo_libro_input = st.text_area("Testo del libro:", height=150)
    if st.button("🚀 Elabora", type="primary"):
        if MASTER_GEMINI_KEY and testo_libro_input:
            try:
                genai.configure(api_key=MASTER_GEMINI_KEY)
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt_libro = f"Analizza il testo scacchistico e restituisci JSON: {{\"mosse_san\": [\"e4\"], \"commenti\": {{\"0\": \"Inizio\"}}}}. {t['prompt_lang']} Testo: {testo_libro_input}"
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
        col_v1, col_v2 = st.columns(2)
        with col_v1: st.write(chess.svg.board(board=chess.Board(cur['fen']), size=320), unsafe_allow_html=True)
        with col_v2: st.info(cur['commento'])

# --- TAB 4: DIARIO & PDF ---
with tab4:
    st.subheader(t["tab4"])
    input_diario = st.text_area("Mosse:", height=100)
    if st.button("🔄 Carica"):
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
        col_d1, col_d2 = st.columns(2)
        with col_d1: st.write(chess.svg.board(board=b_d, size=320), unsafe_allow_html=True)
        with col_d2:
            for idx, m in enumerate(mosse_d):
                st.session_state['diario_note_mosse'][str(idx)] = st.text_input(f"Nota {m}:", value=st.session_state['diario_note_mosse'].get(str(idx), ""), key=f"note_pdf_{idx}")
        if st.button("⚙️ Genera PDF"):
            pdf_b = genera_pdf_partita(b_d, mosse_d, st.session_state['diario_note_mosse'], "")
            st.download_button("📥 Scarica PDF", data=pdf_b, file_name="diario_partita.pdf", mime="application/pdf")

# --- TAB 5: IMPORTA E FILTRA PARTITE CON FILTRI AVANZATI ---
with tab5:
    st.subheader(t["tab5"])
    
    saved_profiles = get_user_profiles(user_email)
    
    col_i1, col_i2 = st.columns([2, 1])
    with col_i1:
        if saved_profiles:
            profile_options = [f"{p['piattaforma']}: {p['username']}" for p in saved_profiles]
            scelta_profilo = st.selectbox("Seleziona il tuo profilo salvato:", profile_options)
            idx_sel = profile_options.index(scelta_profilo)
            plat = saved_profiles[idx_sel]['piattaforma']
            usr = saved_profiles[idx_sel]['username']
        else:
            st.info("Nessun profilo salvato. Inseriscine uno al volo:")
            plat = st.radio("Piattaforma:", ["Lichess", "Chess.com"], horizontal=True)
            usr = st.text_input("Username:", value="")
    with col_i2:
        limite_partite = st.number_input("Partite da scaricare:", min_value=5, max_value=50, value=20)

    if st.button("📥 Scarica Ultime Partite", type="primary"):
        if usr.strip():
            with st.spinner(f"Scaricamento partite per {usr} da {plat} in corso..."):
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
                            st.error(f"Errore Lichess (Codice HTTP {r.status_code}).")
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
                                    st.error("Impossibile recuperare i dati dall'archivio Chess.com.")
                            else:
                                st.warning("Nessun archivio trovato per questo utente.")
                        else:
                            st.error(f"Utente non trovato o errore HTTP {r_arch.status_code}.")
                except Exception as e: 
                    st.error(f"Errore durante il download: {e}")
        else:
            st.warning("Inserisci o seleziona un username valido.")

    # --- FILTRI INTELLIGENTI SULLE PARTITE SCARICATE ---
    if 'partite_importate' in st.session_state and st.session_state['partite_importate']:
        st.divider()
        st.markdown("### 🔍 Filtra Partite Scaricate")
        
        # Suddividiamo il blocco PGN in singole partite
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
                
                # Determina il controllo del tempo in base all'evento o al tempo
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
                    "result": result,
                    "white": white,
                    "black": black
                })

        if parsed_games:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_tc = st.selectbox("Filtra per Controllo Tempo:", ["Tutti", "Blitz", "Rapid", "Bullet", "Classical", "Altro/Custom"])
            with col_f2:
                filtro_res = st.selectbox("Filtra per Risultato:", ["Tutti", "Vittorie Bianco (1-0)", "Vittorie Nero (0-1)", "Patte (1/2-1/2)"])

            # Applica i filtri
            filtered_games = parsed_games
            if filtro_tc != "Tutti":
                filtered_games = [g for g in filtered_games if g['tc'] == filtro_tc]
            if filtro_res == "Vittorie Bianco (1-0)":
                filtered_games = [g for g in filtered_games if g['result'] == "1-0"]
            elif filtro_res == "Vittorie Nero (0-1)":
                filtered_games = [g for g in filtered_games if g['result'] == "0-1"]
            elif filtro_res == "Patte (1/2-1/2)":
                filtered_games = [g for g in filtered_games if g['result'] == "1/2-1/2"]

            st.write(f"Trovate **{len(filtered_games)}** partite corrispondenti ai filtri (su {len(parsed_games)} totali).")

            if filtered_games:
                game_options = [g['summary'] for g in filtered_games]
                scelta_partita = st.selectbox("Seleziona la partita da analizzare:", game_options)
                
                # Trova la partita selezionata
                selected_idx = game_options.index(scelta_partita)
                chosen_pgn = filtered_games[selected_idx]['pgn']

                if st.button("🚀 Invia questa partita ad Analisi Stockfish + AI (Tab 1)", type="primary"):
                    st.session_state['selected_game_pgn'] = chosen_pgn
                    st.success("Partita inviata con successo! Spostati sulla scheda '📖 Analizza PGN (Stockfish + AI)' in alto per avviare l'analisi.")
            else:
                st.warning("Nessuna partita corrisponde ai filtri selezionati.")
        else:
            st.info("Impossibile estrarre le intestazioni delle partite scaricate.")