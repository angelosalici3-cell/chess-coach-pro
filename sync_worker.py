import os
import time
import datetime
import io
import requests
import chess
import chess.pgn
from supabase import create_client

# Configurazione credenziali da variabili d'ambiente (GitHub Secrets)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") # Usa la service_role key per i permessi di scrittura completi

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Credenziali Supabase mancanti nelle variabili d'ambiente.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_stockfish_eval(session, fen, depth=10):
    for attempt in range(2):
        try:
            r = session.post("https://chess-api.com/v1", json={"fen": fen, "depth": depth}, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if data.get("eval") is not None:
                    return float(data.get("eval"))
                elif data.get("centipawns") is not None:
                    return float(data.get("centipawns")) / 100.0
                elif data.get("cp") is not None:
                    return float(data.get("cp")) / 100.0
                elif data.get("value") is not None:
                    return float(data.get("value")) / 100.0
                elif data.get("mate") is not None:
                    m = int(data.get("mate"))
                    return 100.0 if m > 0 else -100.0
        except Exception:
            time.sleep(0.3)
    return None

def determina_categoria_mossa(num_mossa, delta_cp, total_moves):
    if num_mossa <= 12: return "Apertura"
    elif num_mossa >= total_moves - 10 or (total_moves > 40 and num_mossa > 30): return "Finale"
    elif delta_cp >= 2.0: return "Tattica"
    else: return "Posizionale"

def analizza_e_salva_partita(user_email, pgn_text, target_username):
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if not game:
        return

    headers = game.headers
    white_player = headers.get('White', 'Unknown').strip().lower()
    black_player = headers.get('Black', 'Unknown').strip().lower()
    
    user_is_white = target_username.lower() in white_player
    user_is_black = target_username.lower() in black_player
    if not user_is_white and not user_is_black:
        user_is_white = True
        user_is_black = True # Fallback

    partita_id = f"{headers.get('White', 'Unknown')}_vs_{headers.get('Black', 'Unknown')}_{headers.get('Date', 'Live')}"
    
    # Verifica se la partita è già stata analizzata per questo utente
    existing = supabase.table("errori_utenti").select("id").eq("user_email", user_email).eq("partita_id", partita_id).execute()
    if existing.data and len(existing.data) > 0:
        return # Già analizzata, saltiamo

    board = game.board()
    headers_req = {"User-Agent": "ChessCoachProWorker/1.0", "Content-Type": "application/json"}
    main_moves = list(game.mainline_moves())
    total_full_moves = (len(main_moves) + 1) // 2

    session = requests.Session()
    session.headers.update(headers_req)
    prev_eval = 0.0

    for idx, move in enumerate(main_moves):
        fen_before = board.fen()
        try:
            move_san = board.san(move)
        except Exception:
            move_san = move.uci()

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
            if delta >= 1.0: # Salva inaccuracy, mistakes e blunders
                tipo_problema = "🔴 Blunder" if delta >= 2.0 else ("🟠 Mistake" if delta >= 1.0 else "🟡 Inaccuracy")
                label_mossa = f"{num_mossa}. {move_san}" if is_white_move else f"{num_mossa}... {move_san}"
                cat_mossa = determina_categoria_mossa(num_mossa, round(delta, 2), total_full_moves)
                
                # Salvataggio immediato nel DB Supabase
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
        time.sleep(0.1) # Pausa di cortesia per non sovraccaricare l'API di Stockfish

def main():
    print("🔄 Avvio sincronizzazione giornaliera abbonati Pro/Diamond...")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 1. Prendi tutti gli utenti con abbonamento Pro o Diamond attivo
    res_users = supabase.table("config_utenti").select("user_email, tier, data_scadenza").in_("tier", ["Pro", "Diamond"]).execute()
    
    if not res_users.data:
        print("Nessun utente Pro o Diamond trovato.")
        return

    for user in res_users.data:
        email = user["user_email"]
        scadenza = user["data_scadenza"]
        
        # Controlla se l'abbonamento è davvero valido
        if scadenza and datetime.datetime.fromisoformat(scadenza.replace("Z", "+00:00")) < datetime.datetime.now(datetime.timezone.utc):
            continue

        print(f"👉 Elaborazione utente: {email} ({user['tier']})")

        # 2. Recupera i profili scacchistici dell'utente
        res_prof = supabase.table("profili_scacchi").select("piattaforma, username").eq("user_email", email).execute()
        if not res_prof.data:
            continue

        for prof in res_prof.data:
            plat = prof["piattaforma"]
            usr = prof["username"].strip().lower()
            print(f"   -> Controllo profilo {plat}: {usr}")

            try:
                # 3. Scarica le ultime 5 partite per aggiornamento giornaliero
                if plat == "Lichess":
                    url = f"https://lichess.org/api/games/user/{usr}"
                    headers = {"Accept": "application/x-chess-pgn", "User-Agent": "ChessCoachPro/1.0"}
                    r = requests.get(url, params={"max": 5}, headers=headers, timeout=20)
                    if r.status_code == 200 and r.text.strip():
                        pgns = [p.strip() for p in r.text.split("\n[Event ") if p.strip()]
                        for p in pgns:
                            full_pgn = "[Event " + p if not p.startswith("[Event") else p
                            analizza_e_salva_partita(email, full_pgn, usr)
                elif plat == "Chess.com":
                    headers_c = {"User-Agent": "ChessCoachPro/1.0"}
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
                print(f"   ❌ Errore scaricamento partite per {usr}: {e}")

    print("✅ Sincronizzazione giornaliera completata con successo!")

if __name__ == "__main__":
    main()
