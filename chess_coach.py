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

# --- CONFIGURAZIONE CENTRALIZZATA (ZERO CONFIGURAZIONE PER IL CLIENTE) ---
# Legge la Gemini API Key centralizzata dai secret di Streamlit
MASTER_GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "INSERISCI_LA_TUA_GEMINI_API_KEY_MASTER_QUI")

# Configurazione Supabase (Database utenti e storico errori)
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "INSERISCI_LA_TUA_SUPABASE_URL_QUI")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "INSERISCI_LA_TUA_SUPABASE_ANON_KEY_QUI")

@st.cache_resource
def init_supabase() -> Client:
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
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
        "prompt_lang": "Rispondi in LINGUA ITALIANA."
    },
    "en": {
        "title": "♟️ Chess Coach Pro",
        "subtitle": "Your advanced AI-powered chess coaching platform",
        "tab1": "📖 Analyze PGN (Stockfish + AI)",
        "tab2": "📊 Mistakes Dashboard",
        "tab3": "📚 Book Study",
        "tab4": "📝 Diary & PDF",
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
        "prompt_lang": "Respond in ENGLISH language."
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
        "prompt_lang": "Responde en IDIOMA ESPAÑOL."
    }
}

# --- IMPOSTAZIONE PAGINA STREAMLIT ---
st.set_page_config(page_title="Chess Coach Pro", layout="wide", page_icon="♟️")

# --- GESTIONE SESSIONE E STATO UTENTE ---
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'lang' not in st.session_state:
    st.session_state['lang'] = 'it'

t = TEXTS[st.session_state['lang']]

# --- FUNZIONI DATABASE SUPABASE ---
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
# SEZIONE 1: SCHERMATA DI LOGIN / REGISTRAZIONE (PRIMA PAGINA)
# ==========================================
if not st.session_state['user']:
    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    
    with col_l2:
        st.markdown(f"<h1 style='text-align: center;'>{t['title']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: gray;'>{t['subtitle']}</p>", unsafe_allow_html=True)
        st.divider()
        
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
        
        with tab_log:
            email_log = st.text_input(t["email_label"], key="login_email")
            pass_log = st.text_input(t["password_label"], type="password", key="login_pass")
            
            if st.button(t["login_btn"], type="primary", use_container_width=True):
                if supabase and email_log and pass_log:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email_log, "password": pass_log})
                        st.session_state['user'] = res.user.email
                        st.success("Accesso effettuato con successo!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Credenziali non valide o errore di accesso: {e}")
                else:
                    st.session_state['user'] = email_log if email_log else "beta_tester@chess.com"
                    st.success("Accesso in modalità Beta Demo!")
                    st.rerun()
                    
        with tab_reg:
            email_reg = st.text_input(t["email_label"], key="reg_email")
            pass_reg = st.text_input(t["password_label"], type="password", key="reg_pass")
            
            if st.button(t["register_btn"], type="primary", use_container_width=True):
                if supabase and email_reg and pass_reg:
                    try:
                        supabase.auth.sign_up({"email": email_reg, "password": pass_reg})
                        st.success("Registrazione completata! Controlla la tua email per confermare l'account o effettua il login.")
                    except Exception as e:
                        st.error(f"Errore durante la registrazione: {e}")
                else:
                    st.warning("Inserisci email e password validi.")
                    
    st.stop()

# ==========================================
# SEZIONE 2: APPLICAZIONE PRINCIPALE (ACCESSIBILE SOLO DOPO IL LOGIN)
# ==========================================

# --- MOTORE DI ANALISI CHESS-API CLOUD ---
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

# --- GENERAZIONE IMMAGINE SCACCHIERA PER PDF ---
def salva_immagine_scacchiera_png(board, path_temp):
    svg_data = chess.svg.board(board=board, size=400)
    try:
        import cairosvg
        cairosvg.svg2png(bytestring=svg_data.encode('utf-8'), write_to=path_temp)
    except Exception:
        img = Image.new('RGB', (400, 400), color=(240, 217, 181))
        img.save(path_temp)

# --- GENERAZIONE PDF A DUE COLONNE ---
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

# --- SIDEBAR DELL'APP PRINCIPALE ---
with st.sidebar:
    st.header(t["settings"])
    st.info(f"👤 Utente: **{st.session_state['user']}**")
    
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
        st.rerun()

# --- TITOLO E TABS ---
st.title(t["title"])

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    t["tab1"], t["tab2"], t["tab3"], t["tab4"], t["tab5"]
])

# --- TAB 1: ANALISI PGN CON MASTER GEMINI KEY ---
with tab1:
    st.subheader(t["tab1"])
    pgn_input = st.text_area("PGN:", height=150, key="pgn_manual_input")
    
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
                                salva_errore_db(st.session_state['user'], item.get("categoria", "Tattica"), item.get("label_mossa", "Mossa"), "Criticità rilevata")
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
                            st.error("Chiave Master Gemini non configurata dal proprietario dell'app.")
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
    df_err = carica_errori_db(st.session_state['user'])
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

# --- TAB 5: IMPORTA E FILTRA PARTITE ---
with tab5:
    st.subheader(t["tab5"])
    plat = st.radio("Piattaforma:", ["Lichess", "Chess.com"], horizontal=True)
    usr = st.text_input("Username:", value="Chene91")
    if st.button("📥 Scarica Partite"):
        if usr.strip():
            with st.spinner("Download..."):
                try:
                    if plat == "Lichess":
                        r = requests.get(f"https://lichess.org/api/games/user/{usr.strip().lower()}?max=10", headers={"Accept": "application/x-chess-pgn"}, timeout=15)
                        if r.status_code == 200:
                            st.session_state['partite_importate'] = r.text
                            st.success("Partite scaricate con successo!")
                    else:
                        r_a = requests.get(f"https://api.chess.com/pub/player/{usr.strip().lower()}/games/archives", timeout=10)
                        if r_a.status_code == 200 and r_a.json().get("archives"):
                            r_g = requests.get(r_a.json()["archives"][-1], timeout=10)
                            if r_g.status_code == 200:
                                pgn_all = "\n\n".join([g.get("pgn", "") for g in r_g.json().get("games", [])[-10:] if g.get("pgn")])
                                st.session_state['partite_importate'] = pgn_all
                                st.success("Partite scaricate con successo!")
                except Exception as e: st.error(f"Errore download: {e}")

    if 'partite_importate' in st.session_state:
        st.code(st.session_state['partite_importate'][:1000] + "...", language="text")