import streamlit as st
import google.generativeai as genai
import chess
import chess.svg
import sqlite3
import pandas as pd
import json
import datetime
import io
import os
import tempfile
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

# --- FUNZIONE GENERAZIONE IMMAGINE SCACCHIERA PER PDF ---
def salva_immagine_scacchiera_png(board, path_temp):
    svg_data = chess.svg.board(board=board, size=400)
    try:
        import cairosvg
        cairosvg.svg2png(bytestring=svg_data.encode('utf-8'), write_to=path_temp)
    except Exception:
        img = Image.new('RGB', (400, 400), color=(240, 217, 181))
        img.save(path_temp)

# --- FUNZIONE GENERAZIONE PDF A DUE COLONNE CON IMMAGINE ---
def genera_pdf_partita(board, mosse_lista, note_mosse, note_finali):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Intestazione principale
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "Chess Coach Pro - Diario Partita Giornaliera", ln=True, align="C")
    pdf.ln(3)
    
    # Sequenza mosse sintetica
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
    
    # Salva temporaneamente la scacchiera visiva come PNG
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        tmp_img_path = tmp_file.name
    
    salva_immagine_scacchiera_png(board, tmp_img_path)
    
    # --- LAYOUT A 2 COLONNE ---
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
    
    # Sezione Note Finali
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

# --- PROMPT OTTIMIZZATO PER ANALISI PGN ---
istruzioni_avanzate = """
Sei un Grande Maestro che allena un giocatore di 1800 Elo. 
Analizza l'intero PGN fornito. Ignora le sviste banali. Trova il momento strategico in cui la partita è andata male.
DEVI restituire la tua risposta ESCLUSIVAMENTE in formato JSON valido, usando questa struttura esatta:
{
  "numero_mossa_critica": "es. 14. Nero",
  "fen_momento_critico": "stringa FEN esatta PRIMA dell'errore dell'allievo",
  "categoria_errore": "Usa SOLO etichette brevi come: Struttura Pedonale, Sviluppo, Finale di Torri, Sicurezza del Re, Controllo del Centro, Iniziativa",
  "spiegazione_dettagliata": "La tua spiegazione didattica del perché il piano era sbagliato, cosa andava giocato, e il riferimento a una partita di Grandi Maestri storica."
}
"""

# --- INTERFACCIA WEB ---
st.title("♟️ Chess Coach Pro (Road to 2000 Elo)")

with st.sidebar:
    st.header("⚙️ Impostazioni")
    saved_key = get_api_key_from_db()
    
    with st.form("api_key_form"):
        api_key_input = st.text_input("Inserisci Gemini API Key:", value=saved_key, type="password")
        submitted = st.form_submit_button("💾 Salva API Key", type="primary")
        
        if submitted:
            if api_key_input.strip():
                save_api_key_to_db(api_key_input.strip())
                st.success("API Key salvata con successo nel DB!")
                st.rerun()
            else:
                st.warning("Inserisci una chiave valida.")

    st.markdown("---")
    st.markdown("Gestisci le tue partite giornaliere, analizza i PGN o studia i libri interattivamente.")

chiave_attiva = get_api_key_from_db()

tab1, tab2, tab3, tab4 = st.tabs([
    "📖 Analizza Nuova Partita", 
    "📊 La mia Dashboard Errori", 
    "📚 Studio Libri Interattivo", 
    "📝 Diario Partita & PDF"
])

# --- TAB 1: ANALISI PGN ---
with tab1:
    st.subheader("Incolla il PGN della partita da analizzare")
    pgn_input = st.text_area("Testo PGN:", height=200, placeholder="[Event \"Live Chess\"]\n[White \"Tu\"]\n[Black \"Avversario\"]\n\n1. e4 e5 2. Nf3...")
    
    col_btn, _ = st.columns([1, 4])
    if col_btn.button("🔍 Avvia Analisi Strategica", type="primary"):
        if not chiave_attiva:
            st.error("Devi inserire e salvare una chiave API valida nella barra laterale!")
        elif not pgn_input:
            st.warning("Inserisci un PGN valido.")
        else:
            with st.spinner('Il GM sta analizzando la partita. Generazione della lezione in corso...'):
                try:
                    genai.configure(api_key=chiave_attiva)
                    model = genai.GenerativeModel(model_name="gemini-3.8-flash", system_instruction=istruzioni_avanzate)
                    
                    prompt = f"Analizza questo PGN e restituisci il JSON:\n{pgn_input}"
                    risposta = model.generate_content(prompt)
                    
                    testo_pulito = risposta.text.replace("```json", "").replace("```", "").strip()
                    dati = json.loads(testo_pulito)
                    
                    salva_errore(dati["categoria_errore"], dati["numero_mossa_critica"], dati["spiegazione_dettagliata"])
                    
                    st.success(f"Analisi completata! Il tuo tallone d'Achille qui è stato: **{dati['categoria_errore']}**")
                    
                    col_board, col_text = st.columns([1, 2])
                    
                    with col_board:
                        st.markdown(f"**Momento Critico: {dati['numero_mossa_critica']}**")
                        board = chess.Board(dati["fen_momento_critico"])
                        boardsvg = chess.svg.board(board=board, size=350)
                        st.write(boardsvg, unsafe_allow_html=True)
                        
                    with col_text:
                        st.markdown("### 🧑‍🏫 La Lezione del GM")
                        st.write(dati["spiegazione_dettagliata"])
                        
                except Exception as e:
                    st.error(f"Si è verificato un errore nell'analisi o nella lettura del JSON: {e}")

# --- TAB 2: DASHBOARD STATISTICHE ---
with tab2:
    st.subheader("📊 Analisi delle tue debolezze")
    st.write("Per superare i 1800 Elo devi sapere dove perdi più partite. Ecco lo storico dei tuoi errori concettuali.")
    
    df = carica_dati_errori()
    
    if not df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Frequenza Categorie di Errore**")
            conteggio_errori = df['categoria_errore'].value_counts()
            st.bar_chart(conteggio_errori)
            
        with col2:
            st.markdown("**Ultimi Errori Registrati**")
            st.dataframe(df[['data', 'categoria_errore', 'mossa_critica']].sort_values(by='data', ascending=False), hide_index=True)
    else:
        st.info("Il tuo database è vuoto. Analizza la tua prima partita per iniziare a tracciare le statistiche!")

# --- TAB 3: STUDIO LIBRI INTERATTIVO ---
with tab3:
    st.subheader("📚 Viewer Interattivo da Testi e Libri di Scacchi")
    st.write("Incolla un estratto da un libro o articolo (anche in lingua straniera). L'AI estrarrà le mosse, tradurrà i commenti in italiano e ti permetterà di navigare la posizione con i pulsanti.")
    
    testo_libro_input = st.text_area("Incolla qui il testo del libro:", height=180, placeholder="1. e4 e5 (White immediately fights for the center...) 2. Nf3 Nc6 3. Bb5 a6...")
    
    if st.button("🚀 Elabora, Traduci e Sincronizza Libro", type="primary"):
        if not chiave_attiva:
            st.error("Inserisci e salva una chiave API valida nella barra laterale!")
        elif not testo_libro_input:
            st.warning("Incolla del testo valido prima di procedere.")
        else:
            with st.spinner("Estrazione sequenza, traduzione e sincronizzazione in corso..."):
                try:
                    genai.configure(api_key=chiave_attiva)
                    model = genai.GenerativeModel(model_name="gemini-3.8-flash")
                    
                    prompt_libro = f"""
                    Analizza questo testo tratto da un libro di scacchi. 
                    REQUISITO FONDAMENTALE: Traduci SEMPRE tutti i commenti, le note e le spiegazioni dell'autore in lingua italiana fluida e corretta.
                    Estrai la sequenza completa delle mosse in formato SAN (Notazione Algebrica Standard pura, es. ["e4", "e5", "Nf3", "Nc6"]) e mappa i commenti dell'autore associandoli esattamente al numero di semimossa (ply, dove 0 è la posizione iniziale prima di muovere, 1 è dopo la prima mossa, 2 dopo la seconda, ecc.).
                    Restituisci ESCLUSIVAMENTE un JSON valido con questa struttura esatta:
                    {{
                      "mosse_san": ["e4", "e5", "Nf3", "Nc6"],
                      "commenti": {{
                        "0": "Commento tradotto in italiano alla posizione iniziale se presente",
                        "1": "Commento specifico tradotto dopo la mossa 1 (e4)",
                        "3": "Commento specifico tradotto dopo la mossa 3 (Nf3)"
                      }}
                    }}
                    Testo da analizzare:
                    {testo_libro_input}
                    """
                    
                    risposta = model.generate_content(prompt_libro)
                    testo_pulito = risposta.text.replace("```json", "").replace("```", "").strip()
                    dati_libro = json.loads(testo_pulito)
                    
                    board = chess.Board()
                    steps = []
                    
                    steps.append({
                        "ply": 0,
                        "mossa_giocata": "Posizione Iniziale",
                        "fen": board.fen(),
                        "commento": dati_libro.get("commenti", {}).get("0", "Inizio della sequenza di studio.")
                    })
                    
                    for idx, san in enumerate(dati_libro.get("mosse_san", [])):
                        try:
                            move = board.parse_san(san)
                            board.push(move)
                            ply = idx + 1
                            commento = dati_libro.get("commenti", {}).get(str(ply), "")
                            
                            num_mossa = (ply + 1) // 2
                            etich_mossa = f"{num_mossa}. {san}" if ply % 2 == 1 else f"{num_mossa}... {san}"
                            
                            steps.append({
                                "ply": ply,
                                "mossa_giocata": etich_mossa,
                                "fen": board.fen(),
                                "commento": commento
                            })
                        except Exception:
                            break
                            
                    st.session_state['book_steps'] = steps
                    st.session_state['current_ply'] = 0
                    st.success(f"Analisi e traduzione riuscite! Estratte {len(steps)-1} semimosse.")
                    
                except Exception as e:
                    st.error(f"Errore durante l'elaborazione del testo del libro: {e}")

    if 'book_steps' in st.session_state and st.session_state['book_steps']:
        st.divider()
        st.subheader("🎮 Navigazione Guidata della Posizione")
        
        steps = st.session_state['book_steps']
        max_ply = len(steps) - 1
        
        if 'current_ply' not in st.session_state:
            st.session_state['current_ply'] = 0
        if st.session_state['current_ply'] > max_ply:
            st.session_state['current_ply'] = max_ply

        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        with col_b1:
            if st.button("⏪ Inizio", use_container_width=True, key="b_book_ini"):
                st.session_state['current_ply'] = 0
                st.rerun()
        with col_b2:
            if st.button("⬅️ Precedente", use_container_width=True, key="b_book_prev") and st.session_state['current_ply'] > 0:
                st.session_state['current_ply'] -= 1
                st.rerun()
        with col_b3:
            if st.button("Successiva ➡️", use_container_width=True, key="b_book_next") and st.session_state['current_ply'] < max_ply:
                st.session_state['current_ply'] += 1
                st.rerun()
        with col_b4:
            if st.button("Fine ⏩", use_container_width=True, key="b_book_end"):
                st.session_state['current_ply'] = max_ply
                st.rerun()
                
        st.markdown(f"<p align='center' style='font-size: 16px; font-weight: bold; margin-top: 5px;'>Posizione attuale: {st.session_state['current_ply']} / {max_ply}</p>", unsafe_allow_html=True)
        
        step_corrente = steps[st.session_state['current_ply']]
        
        col_board_v, col_comm_v = st.columns([1, 1])
        
        with col_board_v:
            st.markdown(f"**Mossa:** `{step_corrente['mossa_giocata']}`")
            board_view = chess.Board(step_corrente['fen'])
            svg_data = chess.svg.board(board=board_view, size=380)
            st.write(svg_data, unsafe_allow_html=True)
            
        with col_comm_v:
            st.markdown("### ✍️ Nota dell'Autore (Tradotta)")
            if step_corrente['commento']:
                st.info(step_corrente['commento'])
            else:
                st.caption("Nessun commento testuale specifico associato a questa specifica posizione dall'autore in questo punto.")
            
            st.markdown("---")
            st.markdown("### 🤖 Analisi Posizionale extra dall'AI")
            st.write("Vuoi che il GM analizzi questa esatta posizione (squilibri, piani, valutazioni) oltre al libro?")
            
            if st.button("💡 Chiedi Analisi GM della Posizione", type="primary", key=f"btn_ai_{st.session_state['current_ply']}"):
                with st.spinner("Il Grande Maestro sta esaminando la posizione..."):
                    try:
                        genai.configure(api_key=chiave_attiva)
                        model_ai = genai.GenerativeModel(model_name="gemini-3.8-flash")
                        fen_corrente = step_corrente['fen']
                        mossa_fatta = step_corrente['mossa_giocata']
                        
                        prompt_analisi = f"""
                        Sei un Grande Maestro di scacchi che allena un giocatore di 1700-1800 Elo.
                        Analizza approfonditamente questa specifica posizione sulla scacchiera.
                        Mossa appena giocata/raggiunta: {mossa_fatta}
                        Stringa FEN della posizione: {fen_corrente}
                        
                        Fornisci un'analisi strutturata in italiano che includa:
                        1. Valutazione generale della posizione (chi sta meglio e perché).
                        2. Elementi posizionali chiave (struttura pedonale, sicurezza del re, spazio, coppie di alfieri o avamposti/case forti).
                        3. Piani concreti raccomandati per il Bianco e per il Nero nei prossimi turni.
                        Usa un linguaggio tecnico adatto a un 1800 Elo e formatta con cura.
                        """
                        risposta_gm = model_ai.generate_content(prompt_analisi)
                        st.session_state[f"cache_ai_{st.session_state['current_ply']}"] = risposta_gm.text
                    except Exception as e:
                        st.error(f"Errore durante la richiesta all'AI: {e}")
                        
            cache_key = f"cache_ai_{st.session_state['current_ply']}"
            if cache_key in st.session_state:
                st.markdown("#### Parere del GM sulla Posizione:")
                st.success(st.session_state[cache_key])

# --- TAB 4: DIARIO PARTITA & PDF ---
with tab4:
    st.subheader("📝 Diario Partita Giornaliera & Esportazione PDF")
    st.write("Inserisci le mosse della tua partita giornaliera (es. `1.d4 d5 2.c4`), aggiungi le tue considerazioni e genera il PDF stampabile completo di immagine della scacchiera a due colonne.")
    
    input_diario_mosse = st.text_area("Incolla o scrivi la sequenza di mosse:", height=120, placeholder="1.d4 d5 2.c4")
    
    if st.button("🔄 Carica Partita nel Diario", type="primary"):
        if not input_diario_mosse.strip():
            st.warning("Inserisci una sequenza di mosse valida.")
        else:
            try:
                parole = input_diario_mosse.split()
                mosse_pulite = []
                for p in parole:
                    if not p.endswith(".") and not (p[:-1].isdigit() and p.endswith(".")):
                        if "." in p:
                            p = p.split(".")[-1]
                        if p:
                            mosse_pulite.append(p)
                
                board_temp = chess.Board()
                lista_valida = []
                for m in mosse_pulite:
                    move = board_temp.parse_san(m)
                    board_temp.push(move)
                    lista_valida.append(m)
                
                st.session_state['diario_mosse'] = lista_valida
                st.session_state['diario_note_mosse'] = {}
                st.session_state['diario_note_finali'] = ""
                st.session_state['pdf_version'] = 1
                if 'pdf_bytes_diario' in st.session_state:
                    del st.session_state['pdf_bytes_diario']
                    
                st.success(f"Partita caricata con successo! Elaborate {len(lista_valida)} semimosse.")
            except Exception as e:
                st.error(f"Errore nel parsing delle mosse. Assicurati che siano in notazione algebrica valida (es. 1.d4 d5 2.c4): {e}")

    if 'diario_mosse' in st.session_state and st.session_state['diario_mosse']:
        st.divider()
        st.subheader("♟️ Stato Attuale della Scacchiera & Note per Mossa")
        
        mosse = st.session_state['diario_mosse']
        board_corrente = chess.Board()
        for m in mosse:
            board_corrente.push(board_corrente.parse_san(m))
            
        col_d_board, col_d_notes = st.columns([1, 1])
        
        with col_d_board:
            st.markdown(f"**Posizione alla mossa {len(mosse)} (Semimossa):**")
            svg_d = chess.svg.board(board=board_corrente, size=350)
            st.write(svg_d, unsafe_allow_html=True)
            
        with col_d_notes:
            st.markdown("### ✍️ Considerazioni per singola mossa")
            if 'diario_note_mosse' not in st.session_state:
                st.session_state['diario_note_mosse'] = {}
                
            for idx, m in enumerate(mosse):
                num_mossa = (idx // 2) + 1
                etichetta = f"{num_mossa}. {m}" if idx % 2 == 0 else f"{num_mossa}... {m}"
                
                valore_precedente = st.session_state['diario_note_mosse'].get(str(idx), "")
                nota_inserita = st.text_input(f"Nota per {etichetta}:", value=valore_precedente, key=f"note_m_{idx}")
                st.session_state['diario_note_mosse'][str(idx)] = nota_inserita

        st.divider()
        st.subheader("📋 Spazio Note Finali sulla Partita")
        note_finali_val = st.text_area("Scrivi qui le tue considerazioni generali sulla posizione e sui piani futuri:", 
                                       value=st.session_state.get('diario_note_finali', ''), 
                                       key="textarea_note_finali", height=120)
        st.session_state['diario_note_finali'] = note_finali_val
        
        st.divider()
        
        if st.button("⚙️ Prepara file PDF", type="primary", use_container_width=True):
            try:
                pdf_bytes = genera_pdf_partita(
                    board=board_corrente,
                    mosse_lista=mosse,
                    note_mosse=st.session_state['diario_note_mosse'],
                    note_finali=st.session_state['diario_note_finali']
                )
                st.session_state['pdf_bytes_diario'] = pdf_bytes
                
                if 'pdf_version' not in st.session_state:
                    st.session_state['pdf_version'] = 1
                else:
                    st.session_state['pdf_version'] += 1
                    
                st.success(f"PDF generato con successo (Versione v{st.session_state['pdf_version']})!")
            except Exception as e:
                st.error(f"Errore nella generazione del PDF: {e}")

        if 'pdf_bytes_diario' in st.session_state:
            versione = st.session_state.get('pdf_version', 1)
            timestamp_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_file_pdf = f"diario_partita_{timestamp_str}_v{versione}.pdf"
            
            st.download_button(
                label=f"📥 Clicca qui per scaricare il file PDF ({nome_file_pdf})",
                data=st.session_state['pdf_bytes_diario'],
                file_name=nome_file_pdf,
                mime="application/pdf",
                use_container_width=True
            )