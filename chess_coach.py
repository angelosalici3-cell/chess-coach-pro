import streamlit as st
import google.generativeai as genai
import chess
import chess.svg
import chess.pgn
import sqlite3
import pandas as pd
import json
import datetime
import io
import os
import tempfile
import requests
import berserk
from fpdf import FPDF
from PIL import Image

# --- CONFIGURAZIONE DATABASE ---
def init_db():
    conn = sqlite3.connect('coach_database.db')
    c = conn.cursor()   
    c.execute('''CREATE TABLE IF NOT EXISTS storico_errori 
                 (data TEXT, categoria_errore TEXT, mossa_critica TEXT, spiegazione TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS config 
                 (chiave TEXT PRIMARY KEY, valore TEXT)''')
    conn.commit()
    conn.close()

def salva_errore(categoria, mossa, spiegazione):
    conn = sqlite3.connect('coach_database.db')
    c = conn.cursor()
    data = datetime.datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT INTO storico_errori VALUES (?, ?, ?, ?)", (data, categoria, mossa, spiegazione))
    conn.commit()
    conn.close()

def carica_dati_errori():
    conn = sqlite3.connect('coach_database.db')
    df = pd.read_sql_query("SELECT * FROM storico_errori", conn)
    conn.close()
    return df

def get_api_key_from_db():
    conn = sqlite3.connect('coach_database.db')
    c = conn.cursor()
    c.execute("SELECT valore FROM config WHERE chiave = 'gemini_api_key'")
    res = c.fetchone()
    conn.close()
    return res[0] if res else ""

def save_api_key_to_db(api_key):
    conn = sqlite3.connect('coach_database.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO config (chiave, valore) VALUES ('gemini_api_key', ?)", (api_key,))
    conn.commit()
    conn.close()

# --- MOTORE DI VALUTAZIONE STOCKFISH (LICHESS CLOUD EVAL API) ---
def analizza_partita_stockfish_cloud(pgn_text):
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if not game:
        return [], None

    board = game.board()
    evaluations = []
    
    # Valutiamo mossa per mossa tramite Lichess Cloud Eval API
    headers_req = {"User-Agent": "ChessCoachPro/1.0"}
    
    prev_eval = 0.0 # Valutazione iniziale approssimata a parità
    
    for idx, move in enumerate(game.mainline_moves()):
        fen_before = board.fen()
        board.push(move)
        fen_after = board.fen()
        
        # Mossa corrente
        num_mossa = (idx // 2) + 1
        is_white_move = (idx % 2 == 0)
        label_mossa = f"{num_mossa}. {move.uci()}" if is_white_move else f"{num_mossa}... {move.uci()}"
        
        # Interroghiamo Lichess Cloud Eval per la FEN risultante
        try:
            r = requests.get("https://lichess.org/api/cloud-eval", params={"fen": fen_after}, headers=headers_req, timeout=3)
            if r.status_code == 200:
                data = r.json()
                pvs = data.get("pvs", [])
                if pvs:
                    cp = pvs[0].get("cp")
                    mate = pvs[0].get("mate")
                    if cp is not None:
                        curr_eval = cp / 100.0
                    elif mate is not None:
                        curr_eval = 100.0 if mate > 0 else -100.0
                    else:
                        curr_eval = prev_eval
                else:
                    curr_eval = prev_eval
            else:
                curr_eval = prev_eval
        except Exception:
            curr_eval = prev_eval

        # Calcolo delta dal punto di vista di chi ha mosso
        delta = (prev_eval - curr_eval) if is_white_move else (curr_eval - prev_eval)
        
        # Consideriamo Errore se la perdita supera 1.5 centipawns / pedoni
        if delta > 1.5:
            evaluations.append({
                "mossa_num": idx + 1,
                "label_mossa": label_mossa,
                "fen_prima": fen_before,
                "fen_dopo": fen_after,
                "mossa_giocata": move.uci(),
                "perdita_cp": round(delta, 2),
                "eval_dopo": curr_eval
            })
            
        prev_eval = curr_eval
        
    return evaluations, game

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
    pdf.cell(0, 10, "Chess Coach Pro - Diario Partita Giornaliera", ln=True, align="C")
    pdf.ln(3)
    
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 6, "Sequenza Mosse Giocate:", ln=True)
    pdf.set_font("helvetica", "", 9)
    
    testo_mosse = ""
    for idx, m in enumerate(mosse_lista):
        num = (idx // 2) + 1
        if idx % 2 == 0:
            testo_mosse += f"{num}. {m} "
        else:
            testo_mosse += f"{m}  "
    pdf.multi_cell(0, 5, testo_mosse if testo_mosse else "Nessuna mossa registrata.")
    pdf.ln(4)
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        tmp_img_path = tmp_file.name
    
    salva_immagine_scacchiera_png(board, tmp_img_path)
    
    y_inizio_griglia = pdf.get_y()
    
    if os.path.exists(tmp_img_path):
        pdf.image(tmp_img_path, x=10, y=y_inizio_griglia, w=85)
        os.remove(tmp_img_path)
    
    pdf.set_xy(100, y_inizio_griglia)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(95, 6, "Considerazioni per Mossa:", ln=True)
    
    for idx, m in enumerate(mosse_lista):
        num = (idx // 2) + 1
        etichetta = f"{num}. {m}" if idx % 2 == 0 else f"{num}... {m}"
        nota_utente = note_mosse.get(str(idx), "").strip()
        
        pdf.set_x(100)
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(95, 5, f"[{etichetta}]", ln=True)
        
        pdf.set_font("helvetica", "", 8)
        if nota_utente:
            pdf.set_x(100)
            pdf.multi_cell(95, 4, f"Note: {nota_utente}")
        
        pdf.set_x(100)
        pdf.cell(95, 4, "________________________________________", ln=True)
        pdf.ln(1)
    
    max_y = max(pdf.get_y(), y_inizio_griglia + 90)
    pdf.set_y(max_y + 5)
    
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 6, "Note Finali & Strategia Futura:", ln=True)
    pdf.set_font("helvetica", "", 9)
    
    if note_finali.strip():
        pdf.multi_cell(0, 5, f"Annotazioni: {note_finali}")
        pdf.ln(2)
        
    pdf.cell(0, 5, "__________________________________________________________________________________", ln=True)
    pdf.cell(0, 5, "__________________________________________________________________________________", ln=True)
    pdf.cell(0, 5, "__________________________________________________________________________________", ln=True)
    
    return bytes(pdf.output())

# --- INIZIALIZZAZIONE APP ---
st.set_page_config(page_title="Chess Coach Pro", layout="wide", page_icon="♟️")
init_db()

st.title("♟️ Chess Coach Pro (Stockfish Engine + Gemini AI)")

# --- SIDEBAR: GESTIONE API KEY E ACCOUNT LICHESS ---
with st.sidebar:
    st.header("⚙️ Impostazioni")
    saved_key = get_api_key_from_db()
    
    with st.form("api_key_form"):
        api_key_input = st.text_input("Inserisci Gemini API Key:", value=saved_key, type="password")
        submitted = st.form_submit_button("💾 Salva API Key", type="primary")
        
        if submitted:
            if api_key_input.strip():
                save_api_key_to_db(api_key_input.strip())
                st.success("API Key salvata con successo!")
                st.rerun()
            else:
                st.warning("Inserisci una chiave valida.")

    st.markdown("---")
    st.header("🔑 Connetti Account Lichess")
    
    if 'lichess_token' not in st.session_state:
        st.session_state['lichess_token'] = None
    if 'lichess_user' not in st.session_state:
        st.session_state['lichess_user'] = None

    token_input = st.text_input("Lichess Personal Token:", type="password", help="Generalo su https://lichess.org/account/oauth/token/create")
    if st.button("🔌 Autentica con Token", use_container_width=True):
        if token_input.strip():
            try:
                session = berserk.TokenSession(token_input.strip())
                client = berserk.Client(session=session)
                user_info = client.account.get()
                st.session_state['lichess_token'] = token_input.strip()
                st.session_state['lichess_user'] = user_info.get("username")
                st.success(f"Autenticato come: {st.session_state['lichess_user']}")
                st.rerun()
            except Exception as e:
                st.error(f"Errore Token: {e}")
        else:
            st.warning("Inserisci un token valido.")

    if st.session_state.get('lichess_user'):
        st.info(f"Utente attivo: **{st.session_state['lichess_user']}**")
        if st.button("🚪 Disconnetti Account"):
            st.session_state['lichess_token'] = None
            st.session_state['lichess_user'] = None
            st.rerun()

chiave_attiva = get_api_key_from_db()

# --- TABS APP ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📖 Analizza PGN (Stockfish + AI)", 
    "📊 Dashboard Errori", 
    "📚 Studio Libri", 
    "📝 Diario & PDF",
    "🌐 Importa & Filtra Partite"
])

# --- TAB 1: ANALISI PGN CON STOCKFISH + GEMINI ---
with tab1:
    st.subheader("🤖 Analisi Oggettiva Stockfish + Lezioni Gemini AI")
    st.write("Il motore Stockfish analizzerà prima la partita per isolare le mosse errate. Successivamente l'AI clusterizzerà gli errori nel tuo DB e potrai richiedere una lezione per ciascuna mossa.")
    
    pgn_input = st.text_area("Testo PGN:", height=180, placeholder="[Event \"Live Chess\"]\n[White \"Tu\"]\n[Black \"Avversario\"]\n\n1. e4 e5 2. Nf3...", key="pgn_manual_input")
    
    if st.button("🔍 Avvia Scansione Stockfish Engine", type="primary"):
        if not pgn_input.strip():
            st.warning("Inserisci un PGN valido.")
        else:
            with st.spinner("Stockfish sta valutando la partita mossa per mossa..."):
                errori, game_obj = analizza_partita_stockfish_cloud(pgn_input.strip())
                st.session_state['stockfish_errors'] = errori
                st.session_state['current_game_pgn'] = pgn_input.strip()
                
                if errori:
                    st.success(f"Stockfish ha identificato {len(errori)} sviste/errori critici nella partita!")
                    
                    # Clusterizzazione snella con Gemini per popolare il DB
                    if chiave_attiva:
                        with st.spinner("L'AI sta categorizzando gli errori per la tua Dashboard..."):
                            try:
                                genai.configure(api_key=chiave_attiva)
                                model = genai.GenerativeModel("gemini-2.5-flash")
                                
                                prompt_cluster = f"""
                                Data questa lista di mosse errate rilevate da Stockfish con relativa FEN prima della mossa e calo di valutazione:
                                {json.dumps(errori)}
                                
                                Categorizza CIASCUN errore assegnando UNA sola etichetta sintetica tra queste:
                                [Sicurezza del Re, Tattica / Pezzo Sospeso, Struttura Pedonale, Sviluppo, Controllo del Centro, Iniziativa, Finale].
                                
                                Restituisci ESCLUSIVAMENTE un JSON con questo formato:
                                [
                                  {{"label_mossa": "14. e5", "categoria": "Tattica / Pezzo Sospeso"}}, ...
                                ]
                                """
                                resp_c = model.generate_content(prompt_cluster)
                                testo_c = resp_c.text.replace("```json", "").replace("```", "").strip()
                                clusters = json.loads(testo_c)
                                
                                # Salva ogni errore nel database SQLite dell'utente
                                for item in clusters:
                                    salva_errore(item.get("categoria", "Tattica"), item.get("label_mossa", "Mossa"), "Errore rilevato da Stockfish")
                                
                                st.info("💾 Categorie salvate con successo nella tua Dashboard Errori!")
                            except Exception as e:
                                st.warning(f"Impossibile auto-categorizzare gli errori: {e}")
                else:
                    st.info("Stockfish non ha rilevato errori gravi (calo > 1.5 pedoni) in questa partita. Ottimo gioco!")

    # --- MOSTRA ELENCO ERRORI RILEVATI DA STOCKFISH ---
    if 'stockfish_errors' in st.session_state and st.session_state['stockfish_errors']:
        st.divider()
        st.subheader("📌 Errori Rilevati da Stockfish")
        
        for idx, err in enumerate(st.session_state['stockfish_errors']):
            with st.expander(f"⚠️ Errore #{idx+1}: Mossa `{err['label_mossa']}` (Perdita: -{err['perdita_cp']} pedoni)", expanded=(idx==0)):
                col_b, col_t = st.columns([1, 1])
                
                with col_b:
                    st.markdown("**Posizione PRIMA dell'errore:**")
                    b_prima = chess.Board(err['fen_prima'])
                    st.write(chess.svg.board(board=b_prima, size=320), unsafe_allow_html=True)
                    
                with col_t:
                    st.markdown(f"**Mossa Giocata:** `{err['mossa_giocata']}`")
                    st.markdown(f"**Calo Valutazione:** `-{err['perdita_cp']}` centipawns")
                    st.markdown(f"**Valutazione Risultante:** `{err['eval_dopo']}`")
                    
                    st.markdown("---")
                    btn_key = f"btn_lesson_{idx}"
                    if st.button(f"🎓 Chiedi Lezione al GM su Mossa {err['label_mossa']}", key=btn_key, type="primary"):
                        if not chiave_attiva:
                            st.error("Inserisci prima la tua Gemini API Key nella sidebar!")
                        else:
                            with st.spinner("Il Grande Maestro sta preparando la lezione didattica su questa posizione..."):
                                try:
                                    genai.configure(api_key=chiave_attiva)
                                    model_gm = genai.GenerativeModel("gemini-2.5-flash")
                                    
                                    prompt_lesson = f"""
                                    Sei un Grande Maestro di scacchi che allena un allievo di 1800 Elo.
                                    In questa posizione (FEN: {err['fen_prima']}), l'allievo ha giocato la mossa {err['mossa_giocata']}, subendo una perdita di valutazione di {err['perdita_cp']} pedoni secondo Stockfish.
                                    
                                    Fornisci una lezione strutturata in italiano che spieghi:
                                    1. **Perché la mossa giocata è un errore concettuale/tattico.**
                                    2. **Qual era il piano corretto o la mossa migliore e perché.**
                                    3. **La regola d'oro / modello mentale per evitare questo errore nelle prossime partite.**
                                    """
                                    resp_lesson = model_gm.generate_content(prompt_lesson)
                                    st.session_state[f"lesson_res_{idx}"] = resp_lesson.text
                                except Exception as e:
                                    st.error(f"Errore generazione lezione: {e}")
                    
                    if f"lesson_res_{idx}" in st.session_state:
                        st.markdown("### 🧑‍🏫 Lezione Didattica del GM")
                        st.success(st.session_state[f"lesson_res_{idx}"])

# --- TAB 2: DASHBOARD STATISTICHE ---
with tab2:
    st.subheader("📊 Analisi delle tue debolezze")
    df = carica_dati_errori()
    
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Frequenza Categorie di Errore**")
            st.bar_chart(df['categoria_errore'].value_counts())
        with col2:
            st.markdown("**Ultimi Errori Registrati**")
            st.dataframe(df[['data', 'categoria_errore', 'mossa_critica']].sort_values(by='data', ascending=False), hide_index=True)
    else:
        st.info("Nessun errore salvato nel database.")

# --- TAB 3: STUDIO LIBRI INTERATTIVO ---
with tab3:
    st.subheader("📚 Viewer Interattivo da Testi e Libri di Scacchi")
    testo_libro_input = st.text_area("Incolla qui il testo del libro:", height=180)
    
    if st.button("🚀 Elabora e Traduci", type="primary"):
        if not chiave_attiva:
            st.error("Inserisci la chiave API Gemini.")
        elif not testo_libro_input:
            st.warning("Incolla del testo valido.")
        else:
            with st.spinner("Elaborazione in corso..."):
                try:
                    genai.configure(api_key=chiave_attiva)
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    
                    prompt_libro = f"""
                    Analizza questo testo di scacchi. Traduci i commenti in italiano fluida.
                    Estrai le mosse SAN ed i commenti per semimossa (ply).
                    JSON richiesto:
                    {{
                      "mosse_san": ["e4", "e5"],
                      "commenti": {{"0": "Inizio", "1": "Mossa 1"}}
                    }}
                    Testo: {testo_libro_input}
                    """
                    
                    risposta = model.generate_content(prompt_libro)
                    testo_pulito = risposta.text.replace("```json", "").replace("```", "").strip()
                    dati_libro = json.loads(testo_pulito)
                    
                    board = chess.Board()
                    steps = [{"ply": 0, "mossa_giocata": "Inizio", "fen": board.fen(), "commento": dati_libro.get("commenti", {}).get("0", "")}]
                    
                    for idx, san in enumerate(dati_libro.get("mosse_san", [])):
                        try:
                            move = board.parse_san(san)
                            board.push(move)
                            ply = idx + 1
                            num_mossa = (ply + 1) // 2
                            etich = f"{num_mossa}. {san}" if ply % 2 == 1 else f"{num_mossa}... {san}"
                            steps.append({"ply": ply, "mossa_giocata": etich, "fen": board.fen(), "commento": dati_libro.get("commenti", {}).get(str(ply), "")})
                        except Exception:
                            break
                            
                    st.session_state['book_steps'] = steps
                    st.session_state['current_ply'] = 0
                    st.success("Studio sincronizzato!")
                except Exception as e:
                    st.error(f"Errore: {e}")

    if 'book_steps' in st.session_state and st.session_state['book_steps']:
        steps = st.session_state['book_steps']
        max_ply = len(steps) - 1
        
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("⏪ Inizio"): st.session_state['current_ply'] = 0; st.rerun()
        if c2.button("⬅️ Precedente") and st.session_state['current_ply'] > 0: st.session_state['current_ply'] -= 1; st.rerun()
        if c3.button("Successiva ➡️") and st.session_state['current_ply'] < max_ply: st.session_state['current_ply'] += 1; st.rerun()
        if c4.button("Fine ⏩"): st.session_state['current_ply'] = max_ply; st.rerun()
        
        step_corrente = steps[st.session_state['current_ply']]
        col_board_v, col_comm_v = st.columns([1, 1])
        with col_board_v:
            st.markdown(f"**Mossa:** `{step_corrente['mossa_giocata']}`")
            st.write(chess.svg.board(board=chess.Board(step_corrente['fen']), size=380), unsafe_allow_html=True)
        with col_comm_v:
            st.info(step_corrente['commento'] if step_corrente['commento'] else "Nessun commento disponibile.")

# --- TAB 4: DIARIO PARTITA & PDF ---
with tab4:
    st.subheader("📝 Diario Partita Giornaliera & Esportazione PDF")
    input_diario_mosse = st.text_area("Incolla sequenza mosse:", height=120, key="diario_input_text")
    
    if st.button("🔄 Carica Partita nel Diario", type="primary"):
        if input_diario_mosse.strip():
            try:
                parole = input_diario_mosse.split()
                mosse_pulite = [p.split(".")[-1] for p in parole if not p.endswith(".") and not (p[:-1].isdigit() and p.endswith("."))]
                board_temp = chess.Board()
                lista_valida = []
                for m in mosse_pulite:
                    if m:
                        move = board_temp.parse_san(m)
                        board_temp.push(move)
                        lista_valida.append(m)
                
                st.session_state['diario_mosse'] = lista_valida
                st.session_state['diario_note_mosse'] = {}
                st.session_state['diario_note_finali'] = ""
                st.session_state['pdf_version'] = 1
                if 'pdf_bytes_diario' in st.session_state: del st.session_state['pdf_bytes_diario']
                st.success(f"Caricate {len(lista_valida)} semimosse.")
            except Exception as e:
                st.error(f"Errore parsing: {e}")

    if 'diario_mosse' in st.session_state and st.session_state['diario_mosse']:
        mosse = st.session_state['diario_mosse']
        board_corrente = chess.Board()
        for m in mosse: board_corrente.push(board_corrente.parse_san(m))
            
        col_d_board, col_d_notes = st.columns([1, 1])
        with col_d_board:
            st.write(chess.svg.board(board=board_corrente, size=350), unsafe_allow_html=True)
        with col_d_notes:
            st.markdown("### ✍️ Note per Mossa")
            for idx, m in enumerate(mosse):
                num = (idx // 2) + 1
                etichetta = f"{num}. {m}" if idx % 2 == 0 else f"{num}... {m}"
                st.session_state['diario_note_mosse'][str(idx)] = st.text_input(f"Nota {etichetta}:", value=st.session_state['diario_note_mosse'].get(str(idx), ""), key=f"note_m_{idx}")

        note_finali_val = st.text_area("Note Finali:", value=st.session_state.get('diario_note_finali', ''), key="textarea_note_finali")
        st.session_state['diario_note_finali'] = note_finali_val
        
        if st.button("⚙️ Prepara PDF", type="primary", use_container_width=True):
            try:
                st.session_state['pdf_bytes_diario'] = genera_pdf_partita(board_corrente, mosse, st.session_state['diario_note_mosse'], st.session_state['diario_note_finali'])
                st.session_state['pdf_version'] = st.session_state.get('pdf_version', 0) + 1
                st.success("PDF Pronto!")
            except Exception as e:
                st.error(f"Errore PDF: {e}")

        if 'pdf_bytes_diario' in st.session_state:
            v = st.session_state.get('pdf_version', 1)
            t_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            st.download_button(f"📥 Scarica PDF (v{v})", data=st.session_state['pdf_bytes_diario'], file_name=f"diario_{t_str}_v{v}.pdf", mime="application/pdf", use_container_width=True)

# --- TAB 5: IMPORTAZIONE & FILTRI PARTITE (LICHESS / CHESS.COM) ---
with tab5:
    st.subheader("🌐 Importa, Filtra e Seleziona le Partite dal tuo Profilo")
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        piattaforma_sel = st.radio("Scegli Piattaforma:", ["Lichess", "Chess.com"], horizontal=True)
    with col_input2:
        username_cerca = st.text_input("Nome Utente:", value=st.session_state.get('lichess_user', 'Chene91'), placeholder="es. Chene91")

    st.markdown("### 🎛️ Filtri Partita Avanzati")
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        filtro_limite = st.number_input("Partite da scaricare:", min_value=5, max_value=50, value=15)
    with f_col2:
        filtro_colore = st.selectbox("Colore:", ["Tutti", "Bianco", "Nero"])
    with f_col3:
        filtro_esito = st.selectbox("Esito:", ["Tutti", "Vinte", "Perse", "Patte"])
    with f_col4:
        filtro_tempo = st.selectbox("Tempo di gioco:", ["Tutti", "Bullet", "Blitz", "Rapid", "Classical"])

    if st.button("📥 Scarica e Applica Filtri", type="primary", use_container_width=True):
        if not username_cerca.strip():
            st.warning("Inserisci un Nome Utente valido.")
        else:
            with st.spinner(f"Scaricamento e filtraggio partite da {piattaforma_sel} per '{username_cerca}'..."):
                partite_filtrate = []
                user_lower = username_cerca.strip().lower()
                
                try:
                    if piattaforma_sel == "Lichess":
                        url = f"https://lichess.org/api/games/user/{user_lower}"
                        params = {"max": filtro_limite}
                        headers = {
                            "Accept": "application/x-chess-pgn",
                            "User-Agent": "ChessCoachPro/1.0"
                        }
                        
                        if st.session_state.get('lichess_token') and st.session_state.get('lichess_user', '').lower() == user_lower:
                            headers["Authorization"] = f"Bearer {st.session_state['lichess_token']}"
                            
                        r = requests.get(url, params=params, headers=headers, timeout=20)
                        
                        if r.status_code == 200:
                            pgn_io = io.StringIO(r.text)
                            idx = 1
                            while True:
                                game = chess.pgn.read_game(pgn_io)
                                if game is None:
                                    break
                                
                                exporter = chess.pgn.StringExporter(headers=True, comments=True, variations=True)
                                pgn_str = game.accept(exporter)
                                
                                headers_game = game.headers
                                white_p = headers_game.get("White", "").lower()
                                black_p = headers_game.get("Black", "").lower()
                                result = headers_game.get("Result", "*")
                                
                                is_white = user_lower in white_p
                                is_black = user_lower in black_p
                                
                                if filtro_colore == "Bianco" and not is_white: idx += 1; continue
                                if filtro_colore == "Nero" and not is_black: idx += 1; continue
                                if filtro_esito == "Vinte" and not ((is_white and result == "1-0") or (is_black and result == "0-1")): idx += 1; continue
                                if filtro_esito == "Perse" and not ((is_white and result == "0-1") or (is_black and result == "1-0")): idx += 1; continue
                                if filtro_esito == "Patte" and result != "1/2-1/2": idx += 1; continue
                                    
                                avversario = headers_game.get("Black", "Avversario") if is_white else headers_game.get("White", "Avversario")
                                titolo_dettagliato = f"Partita #{idx}: vs {avversario} ({result})"
                                partite_filtrate.append((titolo_dettagliato, pgn_str))
                                idx += 1
                        else:
                            st.error(f"Errore di connessione a Lichess (Codice HTTP: {r.status_code}).")
                            
                    else:
                        headers_c = {"User-Agent": "ChessCoachProApp/1.0"}
                        arch_url = f"https://api.chess.com/pub/player/{user_lower}/games/archives"
                        r_arch = requests.get(arch_url, headers=headers_c, timeout=10)
                        if r_arch.status_code == 200:
                            archives = r_arch.json().get("archives", [])
                            if archives:
                                r_m = requests.get(archives[-1], headers=headers_c, timeout=10)
                                if r_m.status_code == 200:
                                    games_j = r_m.json().get("games", [])[-filtro_limite:][::-1]
                                    for g in games_j:
                                        pgn_g = g.get("pgn", "")
                                        if not pgn_g: continue
                                        
                                        game = chess.pgn.read_game(io.StringIO(pgn_g))
                                        if not game: continue
                                        
                                        headers_game = game.headers
                                        white_p = headers_game.get("White", "").lower()
                                        black_p = headers_game.get("Black", "").lower()
                                        result = headers_game.get("Result", "*")
                                        
                                        is_white = user_lower in white_p
                                        is_black = user_lower in black_p
                                        
                                        if filtro_colore == "Bianco" and not is_white: continue
                                        if filtro_colore == "Nero" and not is_black: continue
                                        if filtro_esito == "Vinte" and not ((is_white and result == "1-0") or (is_black and result == "0-1")): continue
                                        if filtro_esito == "Perse" and not ((is_white and result == "0-1") or (is_black and result == "1-0")): continue
                                        if filtro_esito == "Patte" and result != "1/2-1/2": continue
                                        
                                        w = headers_game.get("White", "Bianco")
                                        b = headers_game.get("Black", "Nero")
                                        partite_filtrate.append((f"Chess.com: {w} vs {b} ({result})", pgn_g))

                    st.session_state['partite_scaricate'] = partite_filtrate
                    if partite_filtrate:
                        st.success(f"Trovate e filtrate con successo {len(partite_filtrate)} partite per l'utente '{username_cerca}'!")
                    else:
                        st.warning("Nessuna partita trovata con i filtri attuali.")
                except Exception as e:
                    st.error(f"Errore durante il download o l'elaborazione: {e}")

    # --- MOSTRA E SELEZIONA LE PARTITE FILTRATE ---
    if 'partite_scaricate' in st.session_state and st.session_state['partite_scaricate']:
        st.divider()
        st.subheader("📋 Seleziona la Partita Filtrata")
        
        m_dict = {titolo: pgn for titolo, pgn in st.session_state['partite_scaricate']}
        partita_scelta_t = st.selectbox("Elenco Partite Disponibili:", list(m_dict.keys()))
        pgn_selezionato_val = m_dict[partita_scelta_t]
        
        with st.expander("Anteprima PGN completo"):
            st.code(pgn_selezionato_val, language="text")
            
        c_act1, c_act2 = st.columns(2)
        with c_act1:
            if st.button("🚀 Invia a Stockfish + AI (Tab 1)", use_container_width=True, type="primary"):
                st.session_state['pgn_manual_input'] = pgn_selezionato_val
                st.success("Partita trasferita! Apri la scheda '📖 Analizza PGN' per avviare la scansione di Stockfish.")
        with c_act2:
            if st.button("📝 Invia al Diario & PDF (Tab 4)", use_container_width=True):
                game = chess.pgn.read_game(io.StringIO(pgn_selezionato_val))
                if game:
                    board_g = game.board()
                    l_moves = [board_g.san(m) for m in game.mainline_moves() if not board_g.push(m)]
                    st.session_state['diario_mosse'] = l_moves
                    st.session_state['diario_note_mosse'] = {}
                    st.session_state['diario_note_finali'] = f"Partita importata: {partita_scelta_t}"
                    st.session_state['pdf_version'] = 1
                    if 'pdf_bytes_diario' in st.session_state: del st.session_state['pdf_bytes_diario']
                    st.success("Partita trasferita nel Diario! Apri la scheda '📝 Diario & PDF'.")