import os
import time
import datetime
import io
import requests
import chess
import chess.pgn
from supabase import create_client
from google.genai import types

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Credenziali Supabase mancanti nelle variabili d'ambiente.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
        except Exception: time.sleep(0.3)
    return None

def classifica_errore_con_ai_veloce(fen_prima, mossa_san):
    if not GEMINI_API_KEY:
        return "Positional Weakness"
    
    prompt = f"""
    FEN: {fen_prima} | Mossa SAN: {mossa_san}.
    Classifica l'errore scegliendo SOLO UNA di queste etichette in inglese:
    Fork, Pin, Skewer, Hanging Piece, Discovered Attack, Double Check, Interference, Clearance, Zugzwang, Mate in 1, Mate in 2, Mate in 3+, Back Rank Mate, Smothered Mate, Endgame, Quiet Move, Defensive Move, Positional Weakness, Opening Mistake.
    Rispondi solo con il nome esatto dell'etichetta.
    """
    try:
        from google import genai as new_genai
        client = new_genai.Client(api_key=GEMINI_API_KEY)
        config_veloce = types.GenerateContentConfig(max_output_tokens=30, temperature=0.0)
        
        resp = client.models.generate_content(model="gemini-3.8-flash", contents=prompt, config=config_veloce)
        tag = resp.text.strip().replace('"', '').replace("'", "")
        
        valid_tags = [
            "Fork", "Pin", "Skewer", "Hanging Piece", "Discovered Attack", 
            "Double Check", "Interference", "Clearance", "Zugzwang", 
            "Mate in 1", "Mate in 2", "Mate in 3+", "Back Rank Mate", 
            "Smothered Mate", "Endgame", "Quiet Move", "Defensive Move", 
            "Positional Weakness", "Opening Mistake"
        ]
        for vt in valid_tags:
            if vt.lower() == tag.lower() or vt.lower() in tag.lower():
                return vt
        return "Positional Weakness"
    except Exception:
        return "Positional Weakness"
def analizza_e_salva_partita(user_email, pgn_text, target_username):
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if not game: return

    headers = game.headers
    white_player = headers.get('White', 'Unknown').strip().lower()
    black_player = headers.get('Black', 'Unknown').strip().lower()
    
    user_is_white = target_username.lower() in white_player
    user_is_black = target_username.lower() in black_player
    if not user_is_white and not user_is_black:
        user_is_white = user_is_black = True

    partita_id = f"{headers.get('White', 'Unknown')}_vs_{headers.get('Black', 'Unknown')}_{headers.get('Date', 'Live')}"
    
    # Verifica se già analizzata per l'utente
    existing = supabase.table("errori_utenti").select("id").eq("user_email", user_email).eq("partita_id", partita_id).execute()
    if existing.data and len(existing.data) > 0:
        return

    board = game.board()
    headers_req = {"User-Agent": "ChessCoachProWorker/1.0 (support@chesscoachpro.com)", "Content-Type": "application/json"}
    main_moves = list(game.mainline_moves())
    
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

        eval_after = fetch_stockfish_eval(session, fen_after, depth=10)
        if eval_after is None: eval_after = eval_before

        is_user_move = (is_white_move and user_is_white) or (not is_white_move and user_is_black)
        if is_user_move:
            delta = (eval_before - eval_after) if is_white_move else (eval_after - eval_before)
            if delta >= 1.0: # Solo Mistake (>=1.0) e Blunder (>=2.0)
                tipo_problema = "🔴 Blunder" if delta >= 2.0 else "🟠 Mistake"
                label_mossa = f"{num_mossa}. {move_san}" if is_white_move else f"{num_mossa}... {move_san}"
                
                # Classificazione AI coerente e ultra-veloce
                cat_mossa = classifica_errore_con_ai_veloce(fen_before, move.san)
                
                try:
                    supabase.table("errori_utenti").insert({
                        "user_email": user_email,
                        "partita_id": partita_id,
                        "data": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "categoria_errore": cat_mossa,
                        "mossa_critica": label_mossa,
                        "spiegazione": f"Perdita di {round(delta, 2)} CP ({tipo_problema})"
                    }).execute()
                except Exception:
                    pass
        prev_eval = eval_after
        time.sleep(0.05)

def main():
    print("🔄 Avvio sincronizzazione notturna abbonati Pro/Diamond...")
    res_users = supabase.table("config_utenti").select("user_email, tier, data_scadenza").in_("tier", ["Pro", "Diamond"]).execute()
    
    if not res_users.data:
        print("Nessun utente Pro o Diamond trovato.")
        return

    for user in res_users.data:
        email = user["user_email"]
        scadenza = user["data_scadenza"]
        
        if scadenza and datetime.datetime.fromisoformat(scadenza.replace("Z", "+00:00")) < datetime.datetime.now(datetime.timezone.utc):
            continue

        res_prof = supabase.table("profili_scacchi").select("piattaforma, username").eq("user_email", email).execute()
        if not res_prof.data: continue

        for prof in res_prof.data:
            plat = prof["piattaforma"]
            usr = prof["username"].strip().lower()
            try:
                if plat == "Lichess":
                    url = f"https://lichess.org/api/games/user/{usr}"
                    headers = {"Accept": "application/x-chess-pgn", "User-Agent": "ChessCoachProWorker/1.0 (support@chesscoachpro.com)"}
                    r = requests.get(url, params={"max": 5}, headers=headers, timeout=20)
                    if r.status_code == 200 and r.text.strip():
                        pgns = [p.strip() for p in r.text.split("\n[Event ") if p.strip()]
                        for p in pgns:
                            full_pgn = "[Event " + p if not p.startswith("[Event") else p
                            analizza_e_salva_partita(email, full_pgn, usr)
                elif plat == "Chess.com":
                    headers_c = {"User-Agent": "ChessCoachProWorker/1.0 (support@chesscoachpro.com)"}
                    arch_url = f"https://api.chess.com/pub/player/{usr}/games/archives"
                    r_arch = requests.get(arch_url, headers=headers_c, timeout=10)
                    if r_arch.status_code == 200:
                        archives = r_arch.json().get("archives", [])
                        if archives:
                            r_m = requests.get(archives[-1], headers=headers_c, timeout=10)
                            if r_m.status_code == 200:
                                games_j = r_m.json().get("games", [])[-5:][::-1]
                                for g in games_j:
                                    pgn_text = g.get("pgn", "")
                                    if pgn_text:
                                        analizza_e_salva_partita(email, pgn_text, usr)
            except Exception as e:
                print(f"Errore sync {usr}: {e}")

    print("✅ Sincronizzazione notturna completata!")

if __name__ == "__main__":
    main()
