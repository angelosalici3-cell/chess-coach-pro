import streamlit as st
import google.genai as genai
import chess
import chess.svg
import chess.pgn
import pandas as pd
import json
import datetime
import io
import os
import time
import requests

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
STRIPE_SECRET_KEY = st.secrets.get("STRIPE_SECRET_KEY", "")
if HAS_STRIPE and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
#GEMINI_MODEL_NAME = "gemini-3.5-flash"

# ==========================================
# HELPERS: NORMALIZZAZIONE (fix constraint violations)
# ==========================================
def _canonical_platform(p):
    """Normalizza la piattaforma a uno dei valori accettati dal CHECK DB."""
    if not p:
        return None
    s = str(p).strip().lower().replace(".", "").replace("_", "").replace("-", "").replace(" ", "")
    return {
        "lichess": "lichess",
        "chesscom": "chesscom",
        "chess": "chesscom",
        "fide": "fide",
    }.get(s)

def _canonical_source(s):
    """Normalizza la sorgente partita al CHECK DB."""
    if not s:
        return "manual"
    v = str(s).strip().lower()
    return v if v in ("lichess", "chesscom", "manual", "pgn_upload") else "manual"

def _canonical_categoria(c):
    """Normalizza la categoria errore al CHECK DB."""
    if not c:
        return "tactical"
    v = str(c).strip().lower()
    return v if v in ("tactical", "positional", "opening", "endgame", "time_trouble") else "tactical"

def _safe_date_str(raw):
    """Restituisce una stringa YYYY-MM-DD valida per Postgres DATE, o oggi."""
    today = datetime.date.today().isoformat()
    if not raw:
        return today
    s = str(raw).strip().replace(".", "-").replace("/", "-")[:10]
    if "?" in s or "Live" in s or not s:
        return today
    try:
        datetime.date.fromisoformat(s)
        return s
    except Exception:
        return today

def _utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def _normalize_pgn_date(raw_date):
    """'2024.01.01' → '2024-01-01'; date ignote → 'Live'."""
    if not raw_date or "?" in str(raw_date):
        return "Live"
    return str(raw_date).replace(".", "-")

def build_partita_id(headers):
    """ID canonico della partita — usato sia nel salvataggio sia nel check duplicati."""
    white = (headers.get("White", "Unknown") or "Unknown").strip()
    black = (headers.get("Black", "Unknown") or "Unknown").strip()
    date = _normalize_pgn_date(headers.get("Date", ""))
    return f"{white}_vs_{black}_{date}"

# ==========================================
# SUPABASE CLIENT (con sessione autenticata)
# ==========================================
def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY or "INSERISCI" in SUPABASE_URL:
        return None
    try:
        from supabase import create_client
        client = create_client(SUPABASE_URL.strip(), SUPABASE_KEY.strip())
        if "sb_access_token" in st.session_state and "sb_refresh_token" in st.session_state:
            client.auth.set_session(
                st.session_state["sb_access_token"],
                st.session_state["sb_refresh_token"],
            )
        return client
    except Exception:
        return None

st.set_page_config(page_title="Chess Coach Pro", layout="wide", page_icon="⚡",
                   initial_sidebar_state="expanded")

# ==========================================
# PERSISTENZA UTENTE
# ==========================================
query_params = st.query_params
persisted_user = query_params.get("user_email", None)

for key, default in {
    'user': persisted_user, 'lang': 'it', 'profile_setup_done': bool(persisted_user),
    'nav_selection': "📊 Dashboard & Insights", 'theme_mode': 'Dark',
    'last_analyzed_pgn': None, 'current_board_ply': 0,
    'eval_history': None, 'storico_errori_locale': [], 'storico_rating_locale': [],
    'lezioni_gm_salvate': {}
}.items():
    if key not in st.session_state or st.session_state[key] is None:
        st.session_state[key] = default

if st.session_state.get('user') and query_params.get("user_email") != st.session_state['user']:
    st.query_params["user_email"] = st.session_state['user']

if 'goto_tab' in st.session_state and st.session_state['goto_tab']:
    st.session_state['nav_selection'] = st.session_state['goto_tab']
    del st.session_state['goto_tab']

st.components.v1.html(
    "<script>setInterval(function(){fetch(window.location.href);},25000);</script>",
    height=0,
)

# ==========================================
# DB HELPERS — interazione tabelle (VERSIONE FIX)
# ==========================================
def get_user_profiles(email):
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("profili_scacchi").select("*").eq("user_email", email).execute()
            if res.data:
                return res.data
        except Exception:
            pass
    return []

def add_user_profile(email, piattaforma, username):
    """Insert robusto: normalizza piattaforma, gestisce CHECK e UNIQUE."""
    plat = _canonical_platform(piattaforma)
    if not plat:
        return False, f"Piattaforma non riconosciuta: '{piattaforma}'. Valori ammessi: lichess, chesscom, fide."
    if not username or not username.strip():
        return False, "Username obbligatorio."

    tier = get_user_tier(email)
    limit = 1 if tier == "Free" else (2 if tier == "Plus" else (3 if tier == "Pro" else 5))
    if len(get_user_profiles(email)) >= limit:
        return False, f"Limite raggiunto per il piano {tier} ({limit} profili)."

    sb = get_supabase()
    if not sb:
        return False, "Supabase non connesso."

    try:
        sb.table("profili_scacchi").insert({
            "user_email": email,
            "piattaforma": plat,
            "username": username.strip(),
        }).execute()
        return True, f"Profilo {plat.upper()} '{username.strip()}' aggiunto!"
    except Exception as e:
        err = str(e).lower()
        if "piattaforma_check" in err or "check constraint" in err:
            return False, (
                f"Il DB rifiuta la piattaforma '{plat}'. Esegui in Supabase:\n"
                f"ALTER TABLE profili_scacchi DROP CONSTRAINT IF EXISTS profili_scacchi_piattaforma_check; "
                f"ALTER TABLE profili_scacchi ADD CONSTRAINT profili_scacchi_piattaforma_check "
                f"CHECK (piattaforma IN ('lichess','chesscom','fide'));"
            )
        if "duplicate" in err or "unique" in err:
            return False, f"Hai già collegato un account {plat}."
        return False, f"Errore DB: {e}"

def delete_user_profile(profile_id):
    sb = get_supabase()
    if sb:
        try:
            sb.table("profili_scacchi").delete().eq("id", profile_id).execute()
            return True
        except Exception:
            pass
    return False

def get_user_tier(email):
    sb = get_supabase()
    if not sb or not email:
        return "Free"
    try:
        res = sb.table("config_utenti").select("tier, data_scadenza, subscription_status") \
                .eq("user_email", email).execute()
        if res.data:
            u = res.data[0]
            tier = u.get("tier", "Free") or "Free"
            scad = u.get("data_scadenza")
            if tier in ["Plus", "Pro", "Elite"] and scad:
                try:
                    scad_date = datetime.date.fromisoformat(str(scad)[:10])
                except Exception:
                    scad_date = None
                if scad_date and datetime.date.today() > scad_date:
                    sb.table("config_utenti").update({
                        "tier": "Free", "data_scadenza": None,
                        "subscription_status": "inactive",
                        "updated_at": _utc_now_iso(),
                    }).eq("user_email", email).execute()
                    registra_movimento_abbonamento(email, tier, "Free", "scadenza", 0.0)
                    return "Free"
            return tier
    except Exception:
        pass
    return "Free"

def get_current_gm_usage(email, tier):
    if tier in ["Pro", "Elite"]:
        return "Illimitate (Pro/Elite)"
    current_month = datetime.datetime.now().strftime("%Y-%m")
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("quota_usage").select("ai_analyses_used") \
                    .eq("user_email", email).eq("quota_month", current_month).execute()
            if res.data:
                used = res.data[0].get("ai_analyses_used", 0)
                limit = 5 if tier == "Free" else 20
                return f"{used} / {limit} usate questo mese"
        except Exception:
            pass
    limit = 5 if tier == "Free" else 20
    return f"0 / {limit} usate questo mese"

def check_and_consume_gm_quota(email, tier):
    if tier in ["Pro", "Elite"]:
        return True, ""
    current_month = datetime.datetime.now().strftime("%Y-%m")
    limit = 5 if tier == "Free" else 20
    used = 0
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("quota_usage").select("ai_analyses_used") \
                    .eq("user_email", email).eq("quota_month", current_month).execute()
            if res.data:
                used = res.data[0].get("ai_analyses_used", 0)
        except Exception:
            pass

    if used >= limit:
        return False, f"⚠️ Hai esaurito le {limit} analisi GM di questo mese per il piano {tier}. Passa a Pro o Elite per analisi illimitate!"

    if sb:
        try:
            sb.rpc("consume_quota", {
                "p_user": email, "p_month": current_month,
                "p_analyses": 1, "p_tokens": 0,
            }).execute()
        except Exception:
            # Fallback se RPC non esiste
            try:
                existing = sb.table("quota_usage").select("*") \
                             .eq("user_email", email).eq("quota_month", current_month).execute()
                if existing.data:
                    sb.table("quota_usage").update({
                        "ai_analyses_used": int(existing.data[0].get("ai_analyses_used", 0)) + 1
                    }).eq("user_email", email).eq("quota_month", current_month).execute()
                else:
                    sb.table("quota_usage").insert({
                        "user_email": email, "quota_month": current_month,
                        "ai_analyses_used": 1,
                    }).execute()
            except Exception:
                pass
    return True, ""

def registra_movimento_abbonamento(user_email, tier_precedente, tier_nuovo,
                                    azione, importo=0.0, stripe_id=None):
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("storico_abbonamenti").insert({
            "user_email": user_email,
            "tier_precedente": tier_precedente,
            "tier_nuovo": tier_nuovo,
            "azione": azione,
            "importo": importo,
            "stripe_session_id": stripe_id,
        }).execute()
    except Exception as e:
        st.error(f"Errore registrazione storico abbonamento: {e}")

def format_gm_lesson_html(raw_text):
    lines = raw_text.strip().split('\n')
    parts = []
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        low = line_clean.lower()
        if line_clean.startswith("1.") or "**analisi dell'errore:**" in low:
            txt = line_clean.replace("1.", "").replace("**Analisi dell'errore:**", "").replace("**Analisi dell'errore**:", "").strip()
            parts.append(f"<div class='gm-section'><b>❌ Analisi Errore:</b> {txt}</div>")
        elif line_clean.startswith("2.") or "**idea corretta:**" in low:
            txt = line_clean.replace("2.", "").replace("**Idea corretta:**", "").replace("**Idea corretta**:", "").strip()
            parts.append(f"<div class='gm-section'><b>💡 Idea Corretta:</b> {txt}</div>")
        elif line_clean.startswith("3.") or "**regola pratica:**" in low:
            txt = line_clean.replace("3.", "").replace("**Regola pratica:**", "").replace("**Regola pratica**:", "").strip()
            parts.append(f"<div class='gm-section'><b>♟️ Regola Pratica:</b> {txt}</div>")
        else:
            parts.append(f"<div class='gm-section'>{line_clean}</div>")
    if not parts:
        parts = [f"<div class='gm-section'>{raw_text}</div>"]
    content = "".join(parts)
    return f"""
    <div class='gm-card'>
        <div class='gm-header'>🎓 Lezione del Gran Maestro AI</div>
        {content}
    </div>
    """

def salva_partita_e_errori_db(user_email, pgn_text, source, source_game_id, headers,
                               errori, eval_history, rating_partita, data_partita,
                               opening_name, opening_eco, user_color, result, time_control):
    """Scrive su games, storico_rating, errori_utenti con normalizzazione campi."""
    sb = get_supabase()
    if not sb:
        for err in errori or []:
            st.session_state['storico_errori_locale'].append({
                "user_email": user_email,
                "partita_id": source_game_id,
                "data": data_partita,
                "categoria_errore": _canonical_categoria(err.get("categoria")),
                "mossa_critica": err.get("label_mossa", "N/A"),
                "spiegazione": err.get("spiegazione", ""),
                "apertura": opening_name,
            })
        return None

    try:
        src = _canonical_source(source)
        game_data = {
            "user_email": user_email,
            "source": src,
            "source_game_id": source_game_id,
            "pgn": pgn_text,
            "white": headers.get("White", "Unknown"),
            "black": headers.get("Black", "Unknown"),
            "user_color": user_color,
            "result": result,
            "time_control": time_control,
            "opening_eco": opening_eco or None,
            "opening_name": opening_name,
            "played_at": _utc_now_iso(),
            "analyzed_at": _utc_now_iso(),
            "analysis_depth": 12,
        }
        res_game = sb.table("games").upsert(
            game_data, on_conflict="user_email,source,source_game_id"
        ).execute()

        if res_game.data:
            game_id = res_game.data[0]["id"]
        else:
            r = sb.table("games").select("id") \
                  .eq("user_email", user_email).eq("source", src) \
                  .eq("source_game_id", source_game_id).execute()
            game_id = r.data[0]["id"] if r.data else None

        if not game_id:
            st.error("Impossibile recuperare ID partita dal DB.")
            return None

        # storico_rating (data sicura per DATE)
        if rating_partita:
            try:
                sb.table("storico_rating").upsert({
                    "user_email": user_email,
                    "data": _safe_date_str(data_partita),
                    "rating": int(rating_partita),
                    "partita_id": source_game_id,
                }, on_conflict="user_email,partita_id").execute()
            except Exception as e:
                st.warning(f"Rating non salvato: {e}")

        # errori — placeholder 'Partita Perfetta' con ply=0 (mai in collisione)
        errori_payload = errori if errori else [{
            "categoria": "tactical",
            "label_mossa": "Partita Perfetta",
            "perdita_cp": 0,
            "mossa_num": 0,
        }]

        for err in errori_payload:
            err_record = {
                "user_email": user_email,
                "game_id": game_id,
                "ply": int(err.get("mossa_num", 0)),
                "fen": err.get("fen_prima", "") or "",
                "mossa_critica": err.get("label_mossa", "N/A"),
                "best_move": err.get("best_move", "") or "",
                "categoria_errore": _canonical_categoria(err.get("categoria")),
                "eval_loss_cp": int(float(err.get("perdita_cp", 0)) * 100),
                "spiegazione": err.get("spiegazione", "") or "",
                "apertura": opening_name,
                "data": _utc_now_iso(),
            }
            try:
                sb.table("errori_utenti").upsert(
                    err_record, on_conflict="user_email,game_id,ply"
                ).execute()
            except Exception as e:
                st.warning(f"Errore salvataggio mossa '{err_record['mossa_critica']}': {e}")

        return game_id

    except Exception as e:
        st.error(f"Errore salvataggio DB completo: {e}")
        return None

def aggiorna_spiegazione_errore_db(user_email, game_id, mossa_critica, spiegazione_html):
    sb = get_supabase()
    if sb and game_id:
        try:
            sb.table("errori_utenti").update({"spiegazione": spiegazione_html}) \
                .eq("user_email", user_email).eq("game_id", game_id) \
                .eq("mossa_critica", mossa_critica).execute()
        except Exception:
            pass

def carica_errori_db(user_email):
    """Carica errori con JOIN su games (schema nuovo: game_id + games.source_game_id)."""
    rows = []
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("errori_utenti") \
                    .select("*, games(source_game_id, opening_name)") \
                    .eq("user_email", user_email).execute()
            if res.data:
                for r in res.data:
                    g = r.get("games") or {}
                    r["partita_id"] = g.get("source_game_id") or "Partita_Sconosciuta"
                    r["apertura"] = r.get("apertura") or g.get("opening_name") or "Standard"
                    r.pop("games", None)
                    rows.append(r)
        except Exception:
            pass

    local_rows = st.session_state.get('storico_errori_locale', [])
    combined = rows + [r for r in local_rows if r not in rows]

    if combined:
        df = pd.DataFrame(combined)
        if 'apertura' not in df.columns:
            df['apertura'] = "Standard"
        return df
    return pd.DataFrame(columns=["data", "partita_id", "categoria_errore",
                                  "mossa_critica", "spiegazione", "apertura", "game_id"])

def carica_rating_db(user_email):
    rows = []
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("storico_rating").select("*") \
                    .eq("user_email", user_email).order("data").execute()
            if res.data:
                rows = res.data
        except Exception:
            pass

    local_rows = st.session_state.get('storico_rating_locale', [])
    combined = rows + [r for r in local_rows if r not in rows]

    if combined:
        df = pd.DataFrame(combined)
        df['data'] = pd.to_datetime(df['data'], errors='coerce')
        df = df.dropna(subset=['data']).sort_values('data').reset_index(drop=True)
        return df
    return pd.DataFrame(columns=["data", "rating", "partita_id"])

def game_already_analyzed(user_email, p_id_check):
    """Dedup check basato su games.source_game_id (fonte di verità)."""
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("games").select("id") \
                    .eq("user_email", user_email) \
                    .eq("source_game_id", p_id_check).execute()
            if res.data:
                return True
        except Exception:
            pass
    df = carica_errori_db(user_email)
    return not df.empty and p_id_check in df['partita_id'].values

def tier_badge_html(tier):
    cls = f"badge-{tier.lower()}"
    return f"<span class='tier-badge {cls}'>{tier}</span>"

# ==========================================
# CSS DINAMICO (invariato)
# ==========================================
def get_dynamic_css(theme):
    common_fix = """
        #MainMenu { visibility: hidden !important; }
        footer { visibility: hidden !important; }
        [data-testid="stDecoration"] { visibility: hidden !important; }
    """
    if theme == 'Dark':
        return "<style>" + common_fix + """
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800;900&family=Inter:wght@300;400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        h1, h2, h3, h4, h5, h6, .brand-title { font-family: 'Outfit', sans-serif; }
        .stApp { background: radial-gradient(1200px 800px at 10% -10%, rgba(255,215,0,0.08), transparent 50%), radial-gradient(1000px 600px at 90% 110%, rgba(124,58,237,0.10), transparent 50%), linear-gradient(135deg, #070b14 0%, #0d1220 50%, #0a0e1a 100%); color: #e8eaf0; }
        .main .block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1200px; }
        h1, h2, h3, h4, h5, h6, p, span, label, div { color: #e8eaf0; }
        .hero { text-align: center; padding: 1rem 0 0.5rem 0; }
        .brand-title { background: linear-gradient(90deg, #FFD700 0%, #FFA500 50%, #FFB347 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.6rem; font-weight: 900; text-align: center; letter-spacing: -0.5px; margin-bottom: 0; }
        .brand-sub { text-align: center; color: #8892a6 !important; font-size: 0.95rem; margin: 0.2rem 0 1rem 0; letter-spacing: 1.5px; text-transform: uppercase; font-weight: 500; }
        .hero-logo { font-size: 3.5rem; display: block; text-align: center; margin-bottom: -0.4rem; }
        section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0b101c 0%, #080c15 100%) !important; border-right: 1px solid rgba(255,215,0,0.08); }
        .user-card { display: flex; align-items: center; gap: 0.9rem; padding: 0.9rem; border-radius: 14px; background: linear-gradient(135deg, rgba(255,215,0,0.10), rgba(255,165,0,0.03)); border: 1px solid rgba(255,215,0,0.18); margin-bottom: 1rem; }
        .avatar { width: 46px; height: 46px; border-radius: 50%; background: linear-gradient(135deg, #FFD700, #FFA500); display: flex; align-items: center; justify-content: center; color: #0a0e1a; font-weight: 800; font-size: 1.05rem; box-shadow: 0 4px 14px rgba(255,215,0,0.35); flex-shrink: 0; }
        .user-info { flex: 1; min-width: 0; }
        .user-name { font-size: 0.82rem; font-weight: 600; color: #e8eaf0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .tier-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-weight: 700; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
        .badge-free { background: rgba(136,146,166,0.15); color: #8892a6; border: 1px solid rgba(136,146,166,0.3); }
        .badge-plus { background: rgba(59,130,246,0.15); color: #3b82f6; border: 1px solid rgba(59,130,246,0.4); }
        .badge-pro { background: rgba(255,215,0,0.15); color: #FFD700; border: 1px solid rgba(255,215,0,0.4); }
        .badge-elite { background: rgba(0,210,255,0.15); color: #00d2ff; border: 1px solid rgba(0,210,255,0.4); }
        div[data-testid="stExpander"] { background: linear-gradient(135deg, rgba(20,26,42,0.75) 0%, rgba(15,20,32,0.75) 100%) !important; border: 1px solid rgba(255,215,0,0.12) !important; border-radius: 14px !important; color: #e8eaf0 !important; margin-bottom: 0.6rem; backdrop-filter: blur(6px); }
        .metric-card { background: linear-gradient(135deg, rgba(20,26,42,0.9), rgba(15,20,32,0.9)); border-radius: 16px; padding: 1.2rem 1.1rem; border: 1px solid rgba(255,255,255,0.06); position: relative; overflow: hidden; }
        .metric-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #FFD700, #FFA500); }
        .metric-card.blue::before { background: linear-gradient(90deg, #3b82f6, #6366f1); }
        .metric-card.purple::before { background: linear-gradient(90deg, #a855f7, #ec4899); }
        .metric-card.green::before { background: linear-gradient(90deg, #10b981, #34d399); }
        .metric-value { font-size: 2rem; font-weight: 800; font-family: 'Outfit', sans-serif; color: #fff; line-height: 1.1; }
        .metric-label { font-size: 0.8rem; color: #8892a6; text-transform: uppercase; letter-spacing: 0.8px; }
        .board-wrapper { display: flex; justify-content: center; align-items: center; padding: 1.2rem; border-radius: 20px; background: linear-gradient(135deg, rgba(255,215,0,0.05), rgba(255,165,0,0.02)); border: 1px solid rgba(255,215,0,0.12); box-shadow: 0 20px 50px rgba(0,0,0,0.35); max-width: fit-content; margin: 0 auto; }
        .gm-card { background: linear-gradient(135deg, rgba(30,41,59,0.85), rgba(15,23,42,0.95)); border: 1px solid rgba(255,215,0,0.25); border-radius: 16px; padding: 1.2rem 1.4rem; margin-top: 0.8rem; box-shadow: 0 8px 24px rgba(0,0,0,0.25); }
        .gm-header { display: flex; align-items: center; gap: 0.5rem; color: #FFD700; font-weight: 700; font-size: 1.05rem; margin-bottom: 0.8rem; border-bottom: 1px solid rgba(255,215,0,0.15); padding-bottom: 0.5rem; }
        .gm-section { margin-bottom: 0.7rem; font-size: 0.93rem; line-height: 1.5; color: #cbd5e1; }
        .gm-section b { color: #FFD700; }
        .pricing-card { background: linear-gradient(135deg, rgba(20,26,42,0.9), rgba(15,20,32,0.9)); border: 1px solid rgba(255,215,0,0.2); border-radius: 20px; padding: 2rem 1.5rem; text-align: center; height: 100%; }
        .pricing-card.featured { border: 2px solid #FFD700; background: linear-gradient(135deg, rgba(30,38,60,0.95), rgba(20,26,42,0.95)); }
        .pricing-title { font-size: 1.5rem; font-weight: 800; color: #FFD700; margin-bottom: 0.5rem; }
        .pricing-price { font-size: 2.5rem; font-weight: 900; color: #fff; margin-bottom: 1rem; }
        .pricing-features { text-align: left; margin: 1.5rem 0; font-size: 0.9rem; color: #cbd5e1; list-style: none; padding: 0; }
        .pricing-features li { margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.5rem; }
        .info-box, .success-box, .warning-box { border-radius: 12px; padding: 0.9rem 1.1rem; margin: 0.5rem 0; border-left: 3px solid; font-size: 0.92rem; }
        .info-box { background: rgba(59,130,246,0.08); border-color: #3b82f6; color: #93c5fd; }
        .success-box { background: rgba(16,185,129,0.08); border-color: #10b981; color: #6ee7b7; }
        .warning-box { background: rgba(234,179,8,0.08); border-color: #eab308; color: #fde047; }
        .section-title { font-family: 'Outfit', sans-serif; font-size: 1.4rem; font-weight: 700; margin: 1.4rem 0 0.8rem 0; display: flex; align-items: center; gap: 0.5rem; color: #fff; }
        .section-title::after { content: ''; flex: 1; height: 1px; background: linear-gradient(90deg, rgba(255,215,0,0.35), transparent); margin-left: 0.6rem; }
        .stButton > button { border-radius: 10px !important; font-weight: 600 !important; border: 1px solid rgba(255,215,0,0.25) !important; background: rgba(20,26,42,0.6) !important; color: #e8eaf0 !important; }
        .stButton > button[kind="primary"] { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important; color: #0a0e1a !important; font-weight: 800 !important; border: none !important; }
        input, textarea { color: #e8eaf0 !important; background-color: rgba(10,14,26,0.7) !important; border-radius: 10px !important; }
        </style>"""
    return "<style>" + common_fix + """
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800;900&family=Inter:wght@300;400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        h1, h2, h3, h4, h5, h6, .brand-title { font-family: 'Outfit', sans-serif; }
        .stApp { background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); color: #1a202c; }
        .main .block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1200px; }
        h1, h2, h3, h4, h5, h6, p, span, label, div { color: #1a202c; }
        .hero { text-align: center; padding: 1rem 0 0.5rem 0; }
        .brand-title { background: linear-gradient(90deg, #b8860b 0%, #d4af37 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.6rem; font-weight: 900; text-align: center; }
        .brand-sub { text-align: center; color: #64748b !important; font-size: 0.95rem; text-transform: uppercase; font-weight: 500; }
        section[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid rgba(0,0,0,0.06); }
        .user-card { display: flex; align-items: center; gap: 0.9rem; padding: 0.9rem; border-radius: 14px; background: rgba(212,175,55,0.10); border: 1px solid rgba(212,175,55,0.25); margin-bottom: 1rem; }
        .avatar { width: 46px; height: 46px; border-radius: 50%; background: linear-gradient(135deg, #d4af37, #b8860b); display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 800; }
        .user-name { font-size: 0.82rem; font-weight: 600; color: #1a202c; }
        .tier-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-weight: 700; font-size: 0.68rem; text-transform: uppercase; }
        .badge-free { background: #e2e8f0; color: #64748b; }
        .badge-plus { background: rgba(59,130,246,0.15); color: #2563eb; }
        .badge-pro { background: rgba(212,175,55,0.15); color: #b8860b; }
        .badge-elite { background: rgba(0,210,255,0.15); color: #00d2ff; }
        .gm-card { background: #ffffff; border: 1px solid rgba(212,175,55,0.3); border-radius: 16px; padding: 1.2rem 1.4rem; margin-top: 0.8rem; box-shadow: 0 4px 16px rgba(0,0,0,0.06); }
        .gm-header { display: flex; align-items: center; gap: 0.5rem; color: #b8860b; font-weight: 700; font-size: 1.05rem; margin-bottom: 0.8rem; border-bottom: 1px solid rgba(212,175,55,0.15); padding-bottom: 0.5rem; }
        .gm-section { margin-bottom: 0.7rem; font-size: 0.93rem; line-height: 1.5; color: #334155; }
        .gm-section b { color: #b8860b; }
        .metric-card { background: #ffffff; border-radius: 16px; padding: 1.2rem 1.1rem; border: 1px solid #e2e8f0; box-shadow: 0 2px 12px rgba(0,0,0,0.05); }
        .metric-value { font-size: 2rem; font-weight: 800; font-family: 'Outfit', sans-serif; color: #1a202c; }
        .metric-label { font-size: 0.8rem; color: #64748b; text-transform: uppercase; }
        .board-wrapper { display: flex; justify-content: center; align-items: center; padding: 1.2rem; border-radius: 20px; background: #ffffff; border: 1px solid #e2e8f0; box-shadow: 0 8px 30px rgba(0,0,0,0.08); max-width: fit-content; margin: 0 auto; }
        .pricing-card { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 20px; padding: 2.1rem 1.5rem; text-align: center; height: 100%; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }
        .pricing-card.featured { border: 2px solid #d4af37; box-shadow: 0 10px 30px rgba(212,175,55,0.15); }
        .pricing-title { font-size: 1.5rem; font-weight: 800; color: #b8860b; margin-bottom: 0.5rem; }
        .pricing-price { font-size: 2.5rem; font-weight: 900; color: #1a202c; margin-bottom: 1rem; }
        .pricing-features { text-align: left; margin: 1.5rem 0; font-size: 0.9rem; color: #475569; list-style: none; padding: 0; }
        .pricing-features li { margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.5rem; }
        .info-box, .success-box, .warning-box { border-radius: 12px; padding: 0.9rem 1.1rem; margin: 0.5rem 0; border-left: 3px solid; font-size: 0.92rem; }
        .info-box { background: rgba(59,130,246,0.08); border-color: #3b82f6; color: #1e40af; }
        .success-box { background: rgba(16,185,129,0.08); border-color: #10b981; color: #047857; }
        .warning-box { background: rgba(234,179,8,0.10); border-color: #eab308; color: #854d0e; }
        .section-title { font-family: 'Outfit', sans-serif; font-size: 1.4rem; font-weight: 700; margin: 1.4rem 0 0.8rem 0; display: flex; align-items: center; gap: 0.5rem; color: #1a202c; }
        .section-title::after { content: ''; flex: 1; height: 1px; background: linear-gradient(90deg, rgba(212,175,55,0.4), transparent); margin-left: 0.6rem; }
        .stButton > button { border-radius: 10px !important; font-weight: 600 !important; border: 1px solid #e2e8f0 !important; background: #ffffff !important; color: #1a202c !important; }
        .stButton > button[kind="primary"] { background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%) !important; color: #ffffff !important; font-weight: 800 !important; border: none !important; }
        </style>"""

st.markdown(get_dynamic_css(st.session_state['theme_mode']), unsafe_allow_html=True)

TEXTS = {
    "it": {
        "title": "Chess Coach Pro",
        "subtitle": "Coaching Scacchistico AI ad Altissima Efficienza",
        "login_header": "🔐 Accedi", "register_header": "📝 Registrati",
        "login_btn": "Accedi", "register_btn": "Crea Account", "logout_btn": "🚪 Disconnetti",
        "analyze_btn": "🔍 Avvia Analisi Motore (Depth 12)",
        "critique_found": "errori tuoi individuati dal motore!",
        "no_errors": "Partita eccellente! Nessun errore rilevato per te.",
        "gm_lesson_btn": "🎓 Spiegazione GM AI",
        "profile_setup_title": "Configura i tuoi Profili",
        "profile_setup_desc": "Collega i tuoi account Lichess o Chess.com per la sincronizzazione.",
        "continue_btn": "🚀 Entra nell'App",
        "already_analyzed": "⚠️ Questa partita è già stata analizzata ed è presente nel tuo archivio.",
    }
}
t = TEXTS['it']

# ==========================================
# LOGIN SCREEN
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

        tab_log, tab_reg = st.tabs([t["login_header"], t["register_header"]])

        with tab_log:
            email_log = st.text_input("Email:", key="login_email")
            pass_log = st.text_input("Password:", type="password", key="login_pass")
            if st.button("Accedi", type="primary", use_container_width=True):
                if email_log and pass_log:
                    sb = get_supabase()
                    if sb:
                        try:
                            res = sb.auth.sign_in_with_password(
                                {"email": email_log.strip(), "password": pass_log}
                            )
                            st.session_state['sb_access_token'] = res.session.access_token
                            st.session_state['sb_refresh_token'] = res.session.refresh_token
                            st.session_state['user'] = email_log.strip()
                            st.query_params["user_email"] = email_log.strip()
                            st.session_state['profile_setup_done'] = False
                            st.success("Login effettuato!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception:
                            st.error("Credenziali non valide o utente inesistente.")
                    else:
                        st.session_state['user'] = email_log.strip()
                        st.query_params["user_email"] = email_log.strip()
                        st.rerun()
                else:
                    st.warning("Inserisci email e password.")

        with tab_reg:
            email_reg = st.text_input("Email:", key="reg_email")
            pass_reg = st.text_input("Password:", type="password", key="reg_pass")
            if st.button("Crea Account", type="primary", use_container_width=True):
                if email_reg and pass_reg:
                    sb = get_supabase()
                    if sb:
                        try:
                            res = sb.auth.sign_up({"email": email_reg.strip(), "password": pass_reg})
                            if res.session:
                                st.session_state['sb_access_token'] = res.session.access_token
                                st.session_state['sb_refresh_token'] = res.session.refresh_token
                            st.session_state['user'] = email_reg.strip()
                            st.query_params["user_email"] = email_reg.strip()
                            st.session_state['profile_setup_done'] = False

                            try:
                                sb.table("config_utenti").upsert({
                                    "user_email": email_reg.strip(),
                                    "tier": "Free",
                                    "subscription_status": "inactive",
                                }, on_conflict="user_email").execute()
                                registra_movimento_abbonamento(email_reg.strip(), None, "Free", "attivazione", 0.0)
                            except Exception as e:
                                st.warning(f"Config utente: {e}")

                            st.success("Registrazione completata!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Errore di registrazione: {e}")
                    else:
                        st.session_state['user'] = email_reg.strip()
                        st.query_params["user_email"] = email_reg.strip()
                        st.rerun()
                else:
                    st.warning("Inserisci email e password.")
    st.stop()

# ==========================================
# ONBOARDING PROFILI
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
            piattaforma_in = st.selectbox("Piattaforma:", ["lichess", "chesscom", "fide"])
            username_in = st.text_input("Username:", placeholder="es. Chene91")
            submit_prof = st.form_submit_button("Salva Profilo", type="primary", use_container_width=True)
            if submit_prof:
                if username_in.strip():
                    success, msg = add_user_profile(user_email, piattaforma_in, username_in.strip())
                    if success:
                        st.success(msg)
                        time.sleep(0.4)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Inserisci un username valido.")

        st.markdown("<div class='section-title'>📋 Account Collegati</div>", unsafe_allow_html=True)
        profiles_attuali = get_user_profiles(user_email)
        if profiles_attuali:
            for p in profiles_attuali:
                cols_pr = st.columns([3, 1])
                cols_pr[0].markdown(
                    f"<div class='info-box'><b>{p['piattaforma'].upper()}</b>: <code>{p['username']}</code></div>",
                    unsafe_allow_html=True,
                )
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
# SIDEBAR
# ==========================================
with st.sidebar:
    initials = (user_email[:2] if user_email else "U").upper()
    gm_usage_str = get_current_gm_usage(user_email, user_tier)

    st.markdown(f"""
    <div class="user-card">
        <div class="avatar">{initials}</div>
        <div class="user-info">
            <div class="user-name">{user_email}</div>
            {tier_badge_html(user_tier)}
            <div style="font-size:0.75rem; color:#FFD700; margin-top:4px;">🎯 Quota GM: {gm_usage_str}</div>
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
        "📞 Contatti & Supporto",
    ]

    if 'nav_selection' not in st.session_state or st.session_state['nav_selection'] not in menu_options:
        st.session_state['nav_selection'] = menu_options[0]

    selected_nav = st.radio("Sezioni App", menu_options, key="nav_selection", label_visibility="collapsed")

    st.markdown("<div class='section-title' style='font-size:0.95rem;margin-top:1rem;'>⚙️ Preferenze</div>", unsafe_allow_html=True)
    scelta_tema = st.selectbox("Tema:", ["Dark", "Light"],
                                index=0 if st.session_state['theme_mode'] == 'Dark' else 1)
    if scelta_tema != st.session_state['theme_mode']:
        st.session_state['theme_mode'] = scelta_tema
        st.rerun()

    st.divider()
    if st.button("⚙️ Gestisci Profili", use_container_width=True):
        st.session_state['profile_setup_done'] = False
        st.rerun()

    if st.button(t["logout_btn"], use_container_width=True):
        sb = get_supabase()
        if sb:
            try:
                sb.auth.sign_out()
            except Exception:
                pass
        st.session_state['user'] = None
        if "user_email" in st.query_params:
            del st.query_params["user_email"]
        for k in ("sb_access_token", "sb_refresh_token"):
            if k in st.session_state:
                del st.session_state[k]
        st.session_state['profile_setup_done'] = False
        st.rerun()

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
# RILEVAMENTO APERTURA & MOTORE
# ==========================================
def detect_opening_from_api(main_moves_list):
    if not main_moves_list:
        return "Apertura Standard", ""
    uci_moves = ",".join([m.uci() for m in main_moves_list[:12]])
    try:
        r = requests.get(
            "https://explorer.lichess.ovh/lichess",
            params={"play": uci_moves, "moves": 0},
            headers={"User-Agent": "ChessCoachPro/1.0"},
            timeout=2.5,
        )
        if r.status_code == 200:
            data = r.json()
            op = data.get("opening")
            if op and op.get("name"):
                eco = op.get("eco", "")
                name = op.get("name", "")
                return (f"{name} ({eco})" if eco else name), eco
    except Exception:
        pass
    return "Apertura Personalizzata / Fuori Libro", ""

def fetch_stockfish_eval(session, fen, depth=12):
    try:
        r = session.post("https://chess-api.com/v1",
                          json={"fen": fen, "depth": depth}, timeout=3.0)
        if r.status_code == 200:
            data = r.json()
            if data.get("eval") is not None:
                return float(data.get("eval"))
            if data.get("centipawns") is not None:
                return float(data.get("centipawns")) / 100.0
            if data.get("cp") is not None:
                return float(data.get("cp")) / 100.0
            if data.get("value") is not None:
                return float(data.get("value")) / 100.0
            if data.get("mate") is not None:
                m = int(data.get("mate"))
                return 100.0 if m > 0 else -100.0
    except Exception:
        pass
    return None

def analizza_partita_stockfish(pgn_text, target_usernames):
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if not game:
        return [], None, "PGN non valido.", [], 1500, \
               datetime.datetime.now().strftime("%Y-%m-%d"), \
               "Apertura Standard", "", "white", "1/2-1/2", "unknown"

    headers = game.headers
    white_player = headers.get('White', 'Unknown').strip().lower()
    black_player = headers.get('Black', 'Unknown').strip().lower()
    white_elo = headers.get('WhiteElo', '1500')
    black_elo = headers.get('BlackElo', '1500')
    date_str = _normalize_pgn_date(headers.get('Date', ''))
    result = headers.get('Result', '*')
    time_control = headers.get('TimeControl', 'unknown')
    partita_id = build_partita_id(headers)

    opening_name = headers.get('Opening', '').strip()
    eco_code = headers.get('ECO', '').strip()

    main_moves_list = list(game.mainline_moves())
    tmp = game.board()
    san_moves = []
    for mv in main_moves_list:
        try:
            san_moves.append(tmp.san(mv))
        except Exception:
            san_moves.append(mv.uci())
        tmp.push(mv)

    if opening_name and opening_name != "?":
        opening_display = f"{opening_name} ({eco_code})" if eco_code and eco_code != "?" else opening_name
    else:
        opening_display, eco_code = detect_opening_from_api(main_moves_list)

    user_is_white, user_is_black = False, False
    user_rating = 1500

    if target_usernames:
        users = [u.strip().lower() for u in target_usernames]
        found = False
        for u in users:
            if u and u in white_player:
                user_is_white = True
                found = True
                if white_elo.isdigit():
                    user_rating = int(white_elo)
            if u and u in black_player:
                user_is_black = True
                found = True
                if black_elo.isdigit():
                    user_rating = int(black_elo)
        if not found:
            user_is_white = True
            if white_elo.isdigit():
                user_rating = int(white_elo)
    else:
        user_is_white = True
        if white_elo.isdigit():
            user_rating = int(white_elo)

    user_color = "white" if (user_is_white and not user_is_black) else (
        "black" if (user_is_black and not user_is_white) else "white"
    )

    board = game.board()
    errors, eval_history = [], []
    headers_req = {"User-Agent": "ChessCoachPro/1.0", "Content-Type": "application/json"}
    total_ply = len(main_moves_list)
    total_full = (total_ply + 1) // 2

    progress_bar = st.progress(0, text="♟️ Analisi approfondita Stockfish (Depth 12) in corso...")
    session = requests.Session()
    session.headers.update(headers_req)
    prev_eval = 0.0

    for idx, move in enumerate(main_moves_list):
        fen_before = board.fen()
        move_san = san_moves[idx]

        eval_before = fetch_stockfish_eval(session, fen_before, depth=12)
        if eval_before is None:
            eval_before = prev_eval

        board.push(move)
        fen_after = board.fen()
        num_mossa = (idx // 2) + 1
        is_white_move = (idx % 2 == 0)
        progress_bar.progress((idx + 1) / max(total_ply, 1),
                              text=f"♟️ Mossa {num_mossa}/{total_full} (Depth 12)...")

        eval_after = fetch_stockfish_eval(session, fen_after, depth=12)
        if eval_after is None:
            eval_after = eval_before

        clamped = max(min(eval_after, 10.0), -10.0)
        eval_history.append({
            "ply": idx + 1, "num_move": num_mossa, "san": move_san,
            "eval_cp": eval_after, "eval_clamped": clamped, "is_white": is_white_move,
        })

        is_user_move = (is_white_move and user_is_white) or (not is_white_move and user_is_black)
        if is_user_move:
            delta = (eval_before - eval_after) if is_white_move else (eval_after - eval_before)
            tipo = "🔴 Blunder" if delta >= 2.0 else (
                "🟠 Mistake" if delta >= 1.0 else (
                    "🟡 Inaccuracy" if delta >= 0.5 else None))
            if tipo:
                label = f"{num_mossa}. {move_san}" if is_white_move else f"{num_mossa}... {move_san}"
                cat = "tactical" if delta >= 1.5 else "positional"
                errors.append({
                    "mossa_num": idx + 1, "label_mossa": label,
                    "fen_prima": fen_before, "fen_dopo": fen_after,
                    "mossa_giocata": move.uci(),
                    "perdita_cp": round(delta, 2),
                    "eval_dopo": eval_after,
                    "tipo_problema": tipo, "categoria": cat,
                })
        prev_eval = eval_after

    progress_bar.empty()
    return (errors, partita_id, None, eval_history, user_rating, date_str,
            opening_display, eco_code, user_color, result, time_control)

def render_eval_graph(eval_history, errors):
    if not HAS_PLOTLY or not eval_history:
        return
    x_vals = [e["ply"] for e in eval_history]
    y_vals = [e["eval_clamped"] for e in eval_history]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode="lines", fill="tozeroy",
                              line=dict(color="#FFD700", width=2),
                              fillcolor="rgba(255,215,0,0.15)", name="Valutazione"))

    def get_y(ply):
        for e in eval_history:
            if e["ply"] == ply:
                return e["eval_clamped"]
        return 0

    blunders = [e["mossa_num"] for e in errors if "Blunder" in e["tipo_problema"]]
    mistakes = [e["mossa_num"] for e in errors if "Mistake" in e["tipo_problema"]]
    inaccuracies = [e["mossa_num"] for e in errors if "Inaccuracy" in e["tipo_problema"]]

    if inaccuracies:
        fig.add_trace(go.Scatter(x=inaccuracies, y=[get_y(n) for n in inaccuracies],
                                  mode="markers", marker=dict(color="#eab308", size=9), name="Inaccuracy"))
    if mistakes:
        fig.add_trace(go.Scatter(x=mistakes, y=[get_y(n) for n in mistakes],
                                  mode="markers", marker=dict(color="#f97316", size=10), name="Mistake"))
    if blunders:
        fig.add_trace(go.Scatter(x=blunders, y=[get_y(n) for n in blunders],
                                  mode="markers", marker=dict(color="#ef4444", size=12, symbol="x"), name="Blunder"))

    fig.update_layout(
        template='plotly_dark' if st.session_state['theme_mode'] == 'Dark' else 'plotly_white',
        height=320, margin=dict(l=10, r=10, t=30, b=10), showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 1) DASHBOARD
# ==========================================
if current_selection == "📊 Dashboard & Insights":
    st.markdown("<div class='section-title'>📊 Control Room & Rating in Tempo Reale</div>", unsafe_allow_html=True)
    df_err = carica_errori_db(user_email)
    df_rating = carica_rating_db(user_email)

    if user_tier in ["Plus", "Pro", "Elite"]:
        st.markdown(f"<div class='success-box'>🟢 Sincronizzazione automatica attiva per il piano <b>{user_tier}</b>.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='info-box'>⚪ Piano Free attivo.</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'>📈 Andamento Rating</div>", unsafe_allow_html=True)
    if not df_rating.empty and HAS_PLOTLY:
        df_rating['diff'] = df_rating['rating'].diff().fillna(0)
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatter(x=df_rating['data'], y=df_rating['rating'],
                                        mode='lines+markers',
                                        line=dict(color='#3b82f6', width=3), name="Rating"))
            fig_r.update_layout(
                template='plotly_dark' if st.session_state['theme_mode'] == 'Dark' else 'plotly_white',
                height=280, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig_r, use_container_width=True)
        with col_r2:
            colors = ['#10b981' if v >= 0 else '#ef4444' for v in df_rating['diff']]
            fig_d = go.Figure()
            fig_d.add_trace(go.Bar(x=df_rating['data'], y=df_rating['diff'],
                                    marker_color=colors, name="Variazione Elo"))
            fig_d.update_layout(
                template='plotly_dark' if st.session_state['theme_mode'] == 'Dark' else 'plotly_white',
                height=280, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig_d, use_container_width=True)
    else:
        st.markdown("<div class='info-box'>Analizza almeno una partita per visualizzare i grafici.</div>", unsafe_allow_html=True)

    st.divider()
    if not df_err.empty:
        # FIX: filtro su mossa_critica (non categoria_errore che ha CHECK constraint)
        df_real_err = df_err[df_err['mossa_critica'] != 'Partita Perfetta']
        n_errors = len(df_real_err)
        n_games = df_err['partita_id'].nunique() if 'partita_id' in df_err else 0
        avg = n_errors / max(n_games, 1)
        precision = max(0, min(100, int(100 - avg * 6)))

        k1, k2, k3 = st.columns(3)
        k1.markdown(f"<div class='metric-card blue'><div class='metric-value'>{n_errors}</div><div class='metric-label'>Totale Errori Censiti</div></div>", unsafe_allow_html=True)
        k2.markdown(f"<div class='metric-card purple'><div class='metric-value'>{n_games}</div><div class='metric-label'>Partite Analizzate</div></div>", unsafe_allow_html=True)
        k3.markdown(f"<div class='metric-card green'><div class='metric-value'>{precision}%</div><div class='metric-label'>Indice Precisione</div></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='info-box'>Nessuna partita registrata. Analizza una partita per popolare la dashboard!</div>", unsafe_allow_html=True)

# ==========================================
# 2) ANALIZZA PARTITA
# ==========================================
elif current_selection == "🔍 Analizza Partita":
    st.markdown("<div class='section-title'>📖 Analisi Dettagliata Partita</div>", unsafe_allow_html=True)

    pgn_val = st.session_state.get('pgn_manual_input', '')
    pgn_input = st.text_area("Incolla il PGN della partita:", value=pgn_val,
                              height=140, key="pgn_area_input")

    if st.button(t["analyze_btn"], type="primary", use_container_width=True):
        if not pgn_input.strip():
            st.warning("Inserisci un PGN valido.")
        else:
            current_pgn = pgn_input.strip()
            game_check = chess.pgn.read_game(io.StringIO(current_pgn))
            already = False
            if game_check:
                p_id_check = build_partita_id(game_check.headers)
                already = game_already_analyzed(user_email, p_id_check)

            if already:
                st.warning(t['already_analyzed'])
            else:
                with st.spinner("🔍 Analisi Stockfish (Depth 12)..."):
                    user_profs = get_user_profiles(user_email)
                    user_usernames = [p['username'] for p in user_profs]
                    (errori, p_id, err_msg, eval_hist, rating_partita, data_partita,
                     opening_used, eco_code, user_color, result, time_control) = \
                        analizza_partita_stockfish(current_pgn, user_usernames)

                    st.session_state['stockfish_errors'] = errori
                    st.session_state['current_game_id'] = p_id
                    st.session_state['eval_history'] = eval_hist
                    st.session_state['current_opening'] = opening_used

                    game_obj = chess.pgn.read_game(io.StringIO(current_pgn))
                    headers_dict = game_obj.headers if game_obj else {}

                    game_uuid = salva_partita_e_errori_db(
                        user_email, current_pgn, "manual", p_id, headers_dict,
                        errori, eval_hist, rating_partita, data_partita,
                        opening_used, eco_code, user_color, result, time_control,
                    )
                    st.session_state['current_game_uuid'] = game_uuid

                    if game_obj:
                        st.session_state['active_game_board'] = game_obj
                        st.session_state['active_game_moves'] = list(game_obj.mainline_moves())
                        st.session_state['current_board_ply'] = 0

                    if errori:
                        st.success(f"✅ Stockfish: {len(errori)} {t['critique_found']}")
                    else:
                        st.success(f"✅ {t['no_errors']}")

    if 'current_opening' in st.session_state and st.session_state['current_opening']:
        st.markdown(f"<div class='success-box'>📖 <b>Apertura Rilevata:</b> {st.session_state['current_opening']}</div>", unsafe_allow_html=True)

    if st.session_state.get('eval_history'):
        st.markdown("<div class='section-title'>📈 Grafico di Valutazione</div>", unsafe_allow_html=True)
        render_eval_graph(st.session_state['eval_history'], st.session_state.get('stockfish_errors', []))

    if st.session_state.get('active_game_board'):
        st.divider()
        game_moves = st.session_state['active_game_moves']
        max_ply = len(game_moves)
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

        current_ply = st.slider("🧭 Navigazione Rapida Mosse", 0, max_ply,
                                 value=st.session_state['current_board_ply'],
                                 key="slider_ply_widget")
        if current_ply != st.session_state['current_board_ply']:
            st.session_state['current_board_ply'] = current_ply
            st.rerun()

        tb = st.session_state['active_game_board'].board()
        for i in range(st.session_state['current_board_ply']):
            tb.push(game_moves[i])

        svg = chess.svg.board(board=tb, size=430,
                              colors={'square light': '#ebecd0', 'square dark': '#739552'})
        st.markdown(f'<div class="board-wrapper">{svg}</div>', unsafe_allow_html=True)

        st.markdown("<div class='section-title'>📋 Errori Rilevati dal Motore</div>", unsafe_allow_html=True)
        if st.session_state.get('stockfish_errors'):
            df_storico_DB = carica_errori_db(user_email)

            for idx, err in enumerate(st.session_state['stockfish_errors']):
                p_id_curr = st.session_state.get('current_game_id', 'Partita_Sconosciuta')

                lezione_esistente = ""
                if not df_storico_DB.empty and 'partita_id' in df_storico_DB.columns:
                    match = df_storico_DB[
                        (df_storico_DB['partita_id'] == p_id_curr) &
                        (df_storico_DB['mossa_critica'] == err['label_mossa'])
                    ]
                    if not match.empty:
                        lezione_esistente = match.iloc[0].get('spiegazione', '') or ''

                cols_err = st.columns([3, 1])
                with cols_err[0]:
                    exp_title = f"{err['tipo_problema']} · {err['label_mossa']} · -{err['perdita_cp']} CP"
                with cols_err[1]:
                    if st.button("♟️ Vedi", key=f"jump_err_{idx}", use_container_width=True):
                        st.session_state['current_board_ply'] = err['mossa_num']
                        st.rerun()

                with st.expander(exp_title, expanded=False):
                    st.markdown(f"**Mossa:** `{err['label_mossa']}` | **Perdita:** -{err['perdita_cp']} CP", unsafe_allow_html=True)

                    if st.button(t['gm_lesson_btn'], key=f"btn_lesson_{idx}", type="primary"):
                        allowed, limit_msg = check_and_consume_gm_quota(user_email, user_tier)
                        if not allowed:
                            st.error(limit_msg)
                        else:
                            with st.spinner("🎓 Il GM AI sta preparando la lezione..."):
                                prompt = (
                                    f"FEN prima della mossa: {err['fen_prima']}\n"
                                    f"Mossa errata giocata: {err['mossa_giocata']} ({err['label_mossa']})\n"
                                )
                                try:
                                    gc = genai.Client(api_key=MASTER_GEMINI_KEY)
                                    resp = gc.models.generate_content(
                                        model=GEMINI_MODEL_NAME,
                                        contents=prompt,
                                        config={
                                            "system_instruction": (
                                                "Sei un Gran Maestro di scacchi italiano. Rispondi ESCLUSIVAMENTE in italiano, "
                                                "senza mostrare calcoli preliminari o ragionamenti in inglese. "
                                                "Usa rigorosamente questa struttura a 3 punti:\n"
                                                "1. **Analisi dell'errore:** Spiega in 2-3 frasi perché la mossa giocata è debole.\n"
                                                "2. **Idea corretta:** Indica quale principio o mossa andava seguita.\n"
                                                "3. **Regola pratica:** Dai una regola generale da ricordare."
                                            ),
                                            "temperature": 0.3,
                                            "max_output_tokens": 1500,
                                            "thinking_config": {"thinking_budget": 0},
                                        },
                                    )
                                    lesson = format_gm_lesson_html(resp.text)
                                    game_uuid = st.session_state.get('current_game_uuid')
                                    aggiorna_spiegazione_errore_db(user_email, game_uuid,
                                                                    err['label_mossa'], lesson)
                                    st.success("Lezione generata!")
                                    time.sleep(0.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"⚠️ Errore API Gemini: {e}")

                    if lezione_esistente:
                        st.markdown(lezione_esistente, unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>Nessun errore registrato in questa partita.</div>", unsafe_allow_html=True)

# ==========================================
# 3) IMPORTA & SINCRONIZZA
# ==========================================
elif current_selection == "🌐 Importa & Sincronizza":
    st.markdown("<div class='section-title'>🌐 Importa e Sincronizza Partite</div>", unsafe_allow_html=True)
    saved = get_user_profiles(user_email)

    col_i1, col_i2 = st.columns([2, 1])
    with col_i1:
        if saved:
            opts = [f"{p['piattaforma'].upper()}: {p['username']}" for p in saved]
            scelta = st.selectbox("Seleziona account:", opts)
            idx_sel = opts.index(scelta)
            plat = saved[idx_sel]['piattaforma']
            usr = saved[idx_sel]['username']
        else:
            plat = st.radio("Piattaforma:", ["lichess", "chesscom", "fide"], horizontal=True)
            usr = st.text_input("Username:", value="")
    with col_i2:
        limite = st.number_input("Partite:", 5, 50, 20)

    if st.button("📥 Scarica e Analizza", type="primary", use_container_width=True):
        if usr.strip():
            with st.spinner(f"Scaricamento partite per {usr}..."):
                try:
                    u = usr.strip().lower()
                    if plat.lower() == "lichess":
                        r = requests.get(
                            f"https://lichess.org/api/games/user/{u}",
                            params={"max": limite, "opening": "true"},
                            headers={"Accept": "application/x-chess-pgn",
                                     "User-Agent": "ChessCoachPro/1.0"},
                            timeout=25,
                        )
                        if r.status_code == 200 and r.text.strip():
                            st.session_state['partite_importate'] = r.text
                            st.success("Scaricamento completato!")
                        else:
                            st.error(f"Errore Lichess (HTTP {r.status_code})")
                    elif plat.lower() in ["chesscom", "chess.com"]:
                        h = {"User-Agent": "ChessCoachPro/1.0"}
                        r_arch = requests.get(f"https://api.chess.com/pub/player/{u}/games/archives",
                                                headers=h, timeout=10)
                        if r_arch.status_code == 200 and r_arch.json().get("archives"):
                            r_m = requests.get(r_arch.json()["archives"][-1], headers=h, timeout=10)
                            games_j = r_m.json().get("games", [])[-limite:][::-1]
                            pgns = []
                            for g in games_j:
                                raw = g.get("pgn", "")
                                if raw:
                                    if "[Opening " not in raw and g.get("eco"):
                                        eco_name = g.get("eco").split("/")[-1].replace("-", " ").title()
                                        raw = f'[Opening "{eco_name}"]\n' + raw
                                    pgns.append(raw)
                            st.session_state['partite_importate'] = "\n\n".join(pgns)
                            st.success("Scaricamento da Chess.com completato!")
                        else:
                            st.error("Impossibile recuperare archivi Chess.com.")
                except Exception as e:
                    st.error(f"Errore download: {e}")
        else:
            st.warning("Inserisci uno username.")

    if st.session_state.get('partite_importate'):
        st.divider()
        raw_pgns = [p.strip() for p in st.session_state['partite_importate'].split("\n[Event ") if p.strip()]
        parsed = []
        for p in raw_pgns:
            full = "[Event " + p if not p.startswith("[Event") else p
            g = chess.pgn.read_game(io.StringIO(full))
            if g:
                op = g.headers.get('Opening', '')
                summary = f"{g.headers.get('White','?')} vs {g.headers.get('Black','?')}"
                if op and op != "?":
                    summary += f" — [{op}]"
                parsed.append({"summary": summary, "pgn": full})
        if parsed:
            sel = st.selectbox("Seleziona partita:", [g['summary'] for g in parsed])
            chosen = next(g['pgn'] for g in parsed if g['summary'] == sel)
            if st.button("🚀 Invia ad Analisi Motore", type="primary", use_container_width=True):
                st.session_state['pgn_manual_input'] = chosen
                st.session_state['goto_tab'] = "🔍 Analizza Partita"
                st.rerun()

# ==========================================
# 4) PALESTRA
# ==========================================
elif current_selection == "🎯 Palestra sui Tuoi Errori":
    st.markdown("<div class='section-title'>🎯 Palestra di Allenamento & Lezioni GM</div>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8892a6;'>Filtra e riconsulta tutte le lezioni e gli errori salvati dalle tue partite.</p>", unsafe_allow_html=True)

    df_errori = carica_errori_db(user_email)
    if df_errori.empty:
        st.markdown("<div class='info-box'>Nessun errore registrato finora. Analizza qualche partita!</div>", unsafe_allow_html=True)
    else:
        col_f1, col_f2, col_f3 = st.columns(3)
        p_list = ["Tutte"] + list(df_errori['partita_id'].unique())
        a_list = ["Tutte"] + list(df_errori['apertura'].unique()) if 'apertura' in df_errori.columns else ["Tutte"]
        c_list = ["Tutte"] + list(df_errori['categoria_errore'].unique())

        f_partita = col_f1.selectbox("Partita:", p_list)
        f_apertura = col_f2.selectbox("Apertura:", a_list)
        f_categoria = col_f3.selectbox("Categoria:", c_list)

        df_f = df_errori.copy()
        if f_partita != "Tutte":
            df_f = df_f[df_f['partita_id'] == f_partita]
        if f_apertura != "Tutte":
            df_f = df_f[df_f['apertura'] == f_apertura]
        if f_categoria != "Tutte":
            df_f = df_f[df_f['categoria_errore'] == f_categoria]

        st.divider()
        lezioni = df_f[df_f['spiegazione'].astype(str).str.len() > 0]
        if not lezioni.empty:
            st.markdown(f"<div class='section-title'>📚 Lezioni GM Trovate ({len(lezioni)})</div>", unsafe_allow_html=True)
            for _, row in lezioni.iterrows():
                dt_str = str(row['data'])[:10] if pd.notnull(row['data']) else ''
                with st.expander(f"Partita: {row['partita_id']} · Mossa: {row['mossa_critica']} · Apertura: {row.get('apertura', 'Standard')} ({dt_str})"):
                    st.markdown(row['spiegazione'], unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>Nessuna lezione GM corrisponde ai filtri. Clicca 'Spiegazione GM AI' durante l'analisi!</div>", unsafe_allow_html=True)

# ==========================================
# 5) STUDIO DA LIBRI
# ==========================================
elif current_selection == "📚 Studio da Libri":
    st.markdown("<div class='section-title'>📚 Studio da Libri con AI</div>", unsafe_allow_html=True)
    testo = st.text_area("Incolla il testo del libro:", height=140)
    if st.button("🚀 Elabora Testo", type="primary"):
        if MASTER_GEMINI_KEY and testo:
            try:
                gc = genai.Client(api_key=MASTER_GEMINI_KEY)
                resp = gc.models.generate_content(
                    model=GEMINI_MODEL_NAME,
                    contents=(
                        "Estrai mosse e commenti in JSON: "
                        '{"mosse_san": ["e4"], "commenti": {"0": "Inizio"}}. '
                        f"Testo: {testo}"
                    ),
                    config={"temperature": 0.2, "max_output_tokens": 1200,
                            "thinking_config": {"thinking_budget": 0}},
                )
                dati = json.loads(resp.text.replace("```json", "").replace("```", "").strip())
                board = chess.Board()
                steps = [{"ply": 0, "mossa_giocata": "Inizio", "fen": board.fen(),
                          "commento": dati.get("commenti", {}).get("0", "")}]
                for idx, san in enumerate(dati.get("mosse_san", [])):
                    try:
                        mv = board.parse_san(san)
                        board.push(mv)
                        steps.append({
                            "ply": idx + 1, "mossa_giocata": san, "fen": board.fen(),
                            "commento": dati.get("commenti", {}).get(str(idx + 1), ""),
                        })
                    except Exception:
                        break
                st.session_state['book_steps'] = steps
                st.session_state['book_ply'] = 0
                st.success("Studio pronto!")
            except Exception as e:
                st.error(f"Errore: {e}")

    if st.session_state.get('book_steps'):
        steps = st.session_state['book_steps']
        maxp = len(steps) - 1
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("⏪", use_container_width=True):
            st.session_state['book_ply'] = 0
            st.rerun()
        if c2.button("⬅️", use_container_width=True) and st.session_state['book_ply'] > 0:
            st.session_state['book_ply'] -= 1
            st.rerun()
        if c3.button("➡️", use_container_width=True) and st.session_state['book_ply'] < maxp:
            st.session_state['book_ply'] += 1
            st.rerun()
        if c4.button("⏩", use_container_width=True):
            st.session_state['book_ply'] = maxp
            st.rerun()

        cur = steps[st.session_state['book_ply']]
        col_v1, col_v2 = st.columns([1, 1])
        with col_v1:
            svg = chess.svg.board(board=chess.Board(cur['fen']), size=340)
            st.markdown(f'<div class="board-wrapper">{svg}</div>', unsafe_allow_html=True)
        with col_v2:
            st.markdown(f"<div class='info-box'>💬 {cur.get('commento', '')}</div>", unsafe_allow_html=True)

# ==========================================
# 6) DIARIO & PDF
# ==========================================
elif current_selection == "📝 Diario & PDF":
    st.markdown("<div class='section-title'>📝 Diario Partite & Report PDF</div>", unsafe_allow_html=True)
    inp = st.text_area("Inserisci sequenza di mosse:", height=100)
    if st.button("🔄 Carica Scacchiera", type="primary"):
        if inp.strip():
            try:
                b = chess.Board()
                l_m = []
                for m in inp.split():
                    mp = m.split(".")[-1]
                    if mp and not mp.isdigit():
                        b.push(b.parse_san(mp))
                        l_m.append(mp)
                st.session_state['diario_mosse'] = l_m
                st.session_state['diario_note_mosse'] = {}
                st.success("Caricato!")
            except Exception as e:
                st.error(f"Errore: {e}")

# ==========================================
# 7) PIANI ABBONAMENTO
# ==========================================
elif current_selection == "💎 Piani Abbonamento":
    st.markdown("<div class='section-title'>💎 Scegli il tuo Piano</div>", unsafe_allow_html=True)
    col_pr1, col_pr2, col_pr3, col_pr4 = st.columns(4)

    with col_pr1:
        st.markdown("<div class='pricing-card'><div class='pricing-title'>Free</div><div class='pricing-price'>€0</div><ul class='pricing-features'><li>✅ 1 Profilo</li><li>✅ 5 Analisi GM/mese</li><li>✅ Analisi Base</li></ul></div>", unsafe_allow_html=True)
        if user_tier == "Free":
            st.button("Piano Attuale", disabled=True, use_container_width=True, key="b_f")
        else:
            if st.button("Passa a Free", use_container_width=True, key="b_tf"):
                sb = get_supabase()
                if sb:
                    sb.table("config_utenti").upsert({
                        "user_email": user_email, "tier": "Free",
                        "data_scadenza": None, "subscription_status": "inactive",
                    }, on_conflict="user_email").execute()
                    registra_movimento_abbonamento(user_email, user_tier, "Free", "downgrade", 0.0)
                st.rerun()

    with col_pr2:
        is_plus = (user_tier == "Plus")
        st.markdown(f"<div class='pricing-card {'featured' if is_plus else ''}'><div class='tier-badge badge-plus'>Base</div><div class='pricing-title'>Plus</div><div class='pricing-price'>€2.99</div><ul class='pricing-features'><li>✅ 2 Profili</li><li>✅ 20 Analisi GM/mese</li><li>✅ Sync Standard</li></ul></div>", unsafe_allow_html=True)
        if is_plus:
            st.markdown("<div class='success-box' style='text-align:center;'>✨ Piano Attivo</div>", unsafe_allow_html=True)
        else:
            if st.button("Sottoscrivi Plus 🚀", type="primary", use_container_width=True, key="b_tplus"):
                sb = get_supabase()
                if sb:
                    scad = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
                    sb.table("config_utenti").upsert({
                        "user_email": user_email, "tier": "Plus",
                        "data_scadenza": scad, "subscription_status": "active",
                    }, on_conflict="user_email").execute()
                    registra_movimento_abbonamento(user_email, user_tier, "Plus", "attivazione", 2.99)
                st.success("Abbonamento Plus attivato!")
                time.sleep(1)
                st.rerun()

    with col_pr3:
        is_pro = (user_tier == "Pro")
        st.markdown(f"<div class='pricing-card {'featured' if is_pro else ''}'><div class='tier-badge badge-pro'>Popolare</div><div class='pricing-title'>Pro</div><div class='pricing-price'>€4.99</div><ul class='pricing-features'><li>✅ 3 Profili</li><li>✅ Analisi GM Illimitate</li><li>✅ Sync Notturna</li></ul></div>", unsafe_allow_html=True)
        if is_pro:
            st.markdown("<div class='success-box' style='text-align:center;'>✨ Piano Attivo</div>", unsafe_allow_html=True)
        else:
            if st.button("Sottoscrivi Pro 🚀", type="primary", use_container_width=True, key="b_tp"):
                sb = get_supabase()
                if sb:
                    scad = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
                    sb.table("config_utenti").upsert({
                        "user_email": user_email, "tier": "Pro",
                        "data_scadenza": scad, "subscription_status": "active",
                    }, on_conflict="user_email").execute()
                    registra_movimento_abbonamento(user_email, user_tier, "Pro", "attivazione", 4.99)
                st.success("Abbonamento Pro attivato!")
                time.sleep(1)
                st.rerun()

    with col_pr4:
        is_elite = (user_tier == "Elite")
        st.markdown(f"<div class='pricing-card {'featured' if is_elite else ''}'><div class='tier-badge badge-elite'>Elite</div><div class='pricing-title'>Elite</div><div class='pricing-price'>€9.99</div><ul class='pricing-features'><li>✅ 5 Profili</li><li>✅ Analisi GM Illimitate</li><li>✅ Sync 24/7</li></ul></div>", unsafe_allow_html=True)
        if is_elite:
            st.markdown("<div class='success-box' style='text-align:center;'>✨ Piano Attivo</div>", unsafe_allow_html=True)
        else:
            if st.button("Sottoscrivi Elite 💎", type="primary", use_container_width=True, key="b_telite"):
                sb = get_supabase()
                if sb:
                    scad = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
                    sb.table("config_utenti").upsert({
                        "user_email": user_email, "tier": "Elite",
                        "data_scadenza": scad, "subscription_status": "active",
                    }, on_conflict="user_email").execute()
                    registra_movimento_abbonamento(user_email, user_tier, "Elite", "attivazione", 9.99)
                st.success("Abbonamento Elite attivato!")
                time.sleep(1)
                st.rerun()

# ==========================================
# 8) CONTATTI
# ==========================================
elif current_selection == "📞 Contatti & Supporto":
    st.markdown("<div class='section-title'>📞 Contatti & Supporto</div>", unsafe_allow_html=True)
    st.markdown("<div class='info-box'>Hai domande? Scrivici a <b>support@chesscoachpro.com</b>.</div>", unsafe_allow_html=True)
