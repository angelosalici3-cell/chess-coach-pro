"""Il percorso del giocatore: fatti calcolati dal server, parole scritte dal coach (Gemini) solo per i piani a pagamento.
Free: scheda + una prima impressione (regole, zero costo). Plus: lettera settimanale. Pro: settimanale + mensile. Elite: anche la stagione trimestrale."""
import datetime
import logging
import os
import re
from collections import Counter

from fastapi import APIRouter, Depends

from . import cache
from . import cardlogic as CL
from . import patterns as P
from .auth import current_user, tier_of
from .db import sb

log = logging.getLogger("profile")
router = APIRouter()
LANGS = {"it": "italiano", "en": "English", "es": "español"}
FIRST_AT = 20          # partite analizzate per la prima impressione (gratis)
MIN_PERIOD_GAMES = 3   # sotto questa soglia non si scrive una lettera
CADENCE = {"Free": [], "Plus": ["week"], "Pro": ["week", "month"], "Elite": ["week", "month", "season"]}


def _d(s):
    try:
        return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception:
        return None


def _rows(email: str) -> list[dict]:
    cols = "id,played_at,user_color,result,white,black,pgn,accuracy_user,opening_name,time_control,analyzed_at"
    r = (sb.table("games").select(cols).eq("user_email", email).not_.is_("user_color", "null")
         .order("played_at", desc=True).limit(1000).execute().data)
    for g in r:
        g["dt"] = _d(g.get("played_at"))
        g["out"] = CL.outcome(g)
        g["elo"] = CL.elo(g.get("pgn") or "", g["user_color"])
        g["fam"] = ((g.get("opening_name") or "").split(":")[0].split(",")[0]).strip()
        g["speed"] = CL.speed_of(g.get("time_control"))
    return [g for g in r if g["dt"]]


def facts(games: list[dict]) -> dict:
    n = len(games)
    if not n:
        return {"games": 0}
    w = sum(g["out"] == "w" for g in games); l = sum(g["out"] == "l" for g in games)
    accs = [float(g["accuracy_user"]) for g in games if g.get("accuracy_user") is not None]
    elos = [g["elo"] for g in sorted(games, key=lambda g: g["dt"]) if g["elo"]]
    fam: dict = {}
    for g in games:
        if g["fam"]:
            f = fam.setdefault(g["fam"], [0, 0]); f[0] += 1; f[1] += g["out"] == "w"
    fams = [(k, v[0], round(100 * v[1] / v[0])) for k, v in fam.items() if v[0] >= 3]
    sp = Counter(g["speed"] for g in games if g["speed"])
    return {"games": n, "wins": w, "losses": l, "draws": n - w - l, "win_pct": round(100 * w / n),
            "acc": round(sum(accs) / len(accs), 1) if accs else None, "analyzed": len(accs),
            "elo_first": elos[0] if elos else None, "elo_last": elos[-1] if elos else None,
            "best_opening": max(fams, key=lambda t: t[2])[:3] if fams else None,
            "worst_opening": min(fams, key=lambda t: t[2])[:3] if len(fams) > 1 else None,
            "main_speed": sp.most_common(1)[0][0] if sp else None}


def _window(games, a, b):
    return [g for g in games if a <= g["dt"].replace(tzinfo=None) < b]


def _period(kind: str, today: datetime.date):
    """Ultimo periodo concluso: (chiave, inizio, fine)."""
    if kind == "week":
        mon = today - datetime.timedelta(days=today.weekday())
        a = mon - datetime.timedelta(days=7)
        return f"{a.isocalendar()[0]}-W{a.isocalendar()[1]:02d}", a, mon
    if kind == "month":
        first = today.replace(day=1)
        a = (first - datetime.timedelta(days=1)).replace(day=1)
        return a.strftime("%Y-%m"), a, first
    q = (today.month - 1) // 3
    first = datetime.date(today.year, 3 * q + 1, 1)
    a = datetime.date(first.year - (1 if q == 0 else 0), 3 * ((q - 1) % 4) + 1, 1)
    return f"{a.year}-Q{(a.month - 1) // 3 + 1}", a, first


def _span(kind: str, key: str):
    """Date di inizio e fine (incluse) del periodo di una lettera, dalla sua chiave."""
    try:
        if kind == "week":
            y, w = key.split("-W")
            a = datetime.date.fromisocalendar(int(y), int(w), 1)
            return a, a + datetime.timedelta(days=6)
        if kind == "month":
            a = datetime.datetime.strptime(key, "%Y-%m").date()
            nxt = (a.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
            return a, nxt - datetime.timedelta(days=1)
        if kind == "season":
            y, q = key.split("-Q")
            a = datetime.date(int(y), 3 * (int(q) - 1) + 1, 1)
            nxt = datetime.date(a.year + (1 if a.month == 10 else 0), (a.month + 2) % 12 + 1, 1)
            return a, nxt - datetime.timedelta(days=1)
    except Exception:
        pass
    return None, None


def _dt(d):
    return datetime.datetime(d.year, d.month, d.day)


def _weak(email: str) -> list[str]:
    try:
        out = P.get(email)
        return [p.get("label") or p.get("tag", "") for p in (out.get("patterns") or [])[:3] if out.get("ready")]
    except Exception:
        return []


def _fallback(kind, f, prev, lang):
    """Testo di riserva senza AI: sempre vero perché usa solo i numeri."""
    n, wp = f["games"], f["win_pct"]
    acc = f"{f['acc']}%" if f.get("acc") is not None else "—"
    d = {"it": f"In questo periodo hai giocato {n} partite e ne hai vinte il {wp}%. Precisione media: {acc}.",
         "en": f"This period you played {n} games and won {wp}%. Average accuracy: {acc}.",
         "es": f"En este periodo jugaste {n} partidas y ganaste el {wp}%. Precisión media: {acc}."}[lang]
    if prev and prev.get("games") and prev.get("acc") is not None and f.get("acc") is not None:
        diff = round(f["acc"] - prev["acc"], 1)
        d += {"it": f" Rispetto al periodo precedente la precisione è {'salita' if diff >= 0 else 'scesa'} di {abs(diff)} punti.",
              "en": f" Compared with the previous period, accuracy {'rose' if diff >= 0 else 'fell'} by {abs(diff)} points.",
              "es": f" Frente al periodo anterior, la precisión {'subió' if diff >= 0 else 'bajó'} {abs(diff)} puntos."}[lang]
    return d


def _write(kind, f, prev, weak, lang, tier) -> str:
    """Il coach racconta i numeri: non può inventarne di nuovi."""
    try:
        from google import genai
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options={"timeout": 45000})
        system = (f"Sei il coach di scacchi personale dell'utente e gli scrivi una lettera in {LANGS[lang]}, in prima persona, tono caldo, concreto e sincero. "
                  "Usa SOLO i numeri forniti nei dati: non inventare partite, mosse, punteggi o avversari. Racconta l'evoluzione rispetto al periodo precedente, "
                  "cita un punto di forza e UN solo consiglio pratico per il prossimo periodo. Se il periodo precedente ha 0 partite non confrontare e non citare quello zero. Niente elenchi, niente titoli, niente saluti formali. "
                  + ("Massimo 120 parole." if kind != "season" else "Massimo 220 parole, come un riassunto di stagione."))
        prompt = f"Tipo: {kind}\nDati del periodo: {f}\nPeriodo precedente: {prev}\nErrori ricorrenti: {weak}"
        model = os.environ.get("GEMINI_MODEL_FREE") if tier == "Plus" else os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
        r = client.models.generate_content(model=model or "gemini-3.5-flash", contents=prompt, config={"system_instruction": system})
        if r.text and r.text.strip():
            return re.sub(r"[*#]+", "", r.text).strip()
    except Exception as e:
        log.warning("lettera coach non generata: %s", str(e)[:200])
    return _fallback(kind, f, prev, lang)


def _due(email: str, tier: str, games: list[dict], have: set) -> list[tuple]:
    today = datetime.date.today()
    due = []
    for kind in CADENCE.get(tier, []):
        key, a, b = _period(kind, today)
        if (kind, key) in have:
            continue
        cur = _window(games, _dt(a), _dt(b))
        if len(cur) >= MIN_PERIOD_GAMES:
            due.append((kind, key, a, b))
    return due


def _first_due(games, have):
    return ("first", "first") not in have and sum(1 for g in games if g.get("analyzed_at")) >= FIRST_AT


@router.get("/profile/journey")
def journey(u=Depends(current_user)):
    email, tier = u["email"], tier_of(u["email"])
    games = _rows(email)
    saved = sb.table("coach_reports").select("id,kind,period,facts,text,lang,created_at").eq("user_email", email).order("created_at", desc=True).limit(300).execute().data
    for r in saved:   # periodo coperto, per mostrare "17–23 nov" invece della chiave tecnica
        a, b = _span(r["kind"], r["period"])
        r["from"], r["to"] = (a.isoformat() if a else None), (b.isoformat() if b else None)
    have = {(r["kind"], r["period"]) for r in saved}
    now = datetime.datetime.now()
    f30, p30 = facts(_window(games, now - datetime.timedelta(days=30), now)), facts(_window(games, now - datetime.timedelta(days=60), now - datetime.timedelta(days=30)))
    # curva di rating: media mensile degli ultimi 12 mesi
    series: dict = {}
    for g in games:
        if g["elo"]:
            series.setdefault(g["dt"].strftime("%Y-%m"), []).append(g["elo"])
    curve = [{"m": k, "elo": round(sum(v) / len(v))} for k, v in sorted(series.items())[-12:]]
    due = _due(email, tier, games, have)
    today = datetime.date.today()
    mon = today - datetime.timedelta(days=today.weekday())
    nxt = None
    if tier != "Free" and "week" in CADENCE.get(tier, []):   # la lettera della settimana appena finita arriva il lunedì
        nxt = {"date": (mon + datetime.timedelta(days=7)).isoformat(), "min_games": MIN_PERIOD_GAMES,
               "have": len(_window(games, _dt(mon), datetime.datetime.now()))}
    return {"tier": tier, "next": nxt, "now": f30, "before": p30, "all": facts(games), "curve": curve, "reports": saved,
            "due": [{"kind": k, "period": p} for k, p, _, _ in due] + ([{"kind": "first", "period": "first"}] if _first_due(games, have) else []),
            "cadence": CADENCE.get(tier, []), "first_at": FIRST_AT,
            "weak": _weak(email) if tier != "Free" else []}


@router.post("/profile/journey/generate")
def generate(lang: str = "it", u=Depends(current_user)):
    """Scrive le lettere in arrivo (al massimo due per chiamata). Il costo resta limitato: un periodo si scrive una volta sola."""
    email, tier = u["email"], tier_of(u["email"])
    lang = lang if lang in LANGS else "it"
    games = _rows(email)
    have = {(r["kind"], r["period"]) for r in sb.table("coach_reports").select("kind,period").eq("user_email", email).execute().data}
    made = []
    if _first_due(games, have):
        an = [g for g in games if g.get("analyzed_at")]
        f = facts(an[:FIRST_AT])
        made.append(("first", "first", f, _fallback("first", f, None, lang)))
    weak = None
    for kind, key, a, b in _due(email, tier, games, have)[:2]:
        cur = facts(_window(games, _dt(a), _dt(b)))
        span = (b - a)
        prev = facts(_window(games, _dt(a - span), _dt(a)))
        weak = weak if weak is not None else _weak(email)
        made.append((kind, key, cur, _write(kind, cur, prev, weak, lang, tier)))
    for kind, key, f, text in made:
        sb.table("coach_reports").upsert({"user_email": email, "kind": kind, "period": key, "facts": f, "text": text, "lang": lang}, on_conflict="user_email,kind,period").execute()
    cache.bust(email)
    return {"made": len(made)}
