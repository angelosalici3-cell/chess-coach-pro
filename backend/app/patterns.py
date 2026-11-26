"""Schemi di errore personali: dalle partite già analizzate ricava dove l'utente sbaglia più del suo normale.
Tutto è calcolato con regole fisse (nessuna IA): la scheda in Home e l'esercizio dedicato leggono da qui."""
import collections
import datetime
import math
import re

from . import cache, pgnlite, shared

ERR_WIN = 15          # errore = almeno 15 punti di probabilità di vittoria persi (perdere pedoni quando la partita è già decisa non conta)
BLUNDER_WIN = 30
MIN_MOVES, MIN_ERRS, MIN_GAMES, MIN_Z, MIN_LIFT = 30, 5, 3, 2.0, 1.4
MIN_GAMES_READY, RECENT = 30, 20     # partite analizzate per mostrare schemi; finestra "ultime partite" per la tendenza

# etichette in italiano usate solo dalla sonda; l'app traduce gli id nel frontend
LABELS = {
    "ph_opening": "fase: apertura", "ph_middle": "fase: mediogioco", "ph_end": "fase: finale",
    "t_low": "poco tempo sull'orologio", "t_fast": "mossa rapida (≤ 3 s)", "after_loss": "subito dopo una sconfitta (≤ 1 h)",
    "st_won": "già vinta (> +5)", "st_adv": "in vantaggio (+2…+5)", "st_slight_adv": "leggero vantaggio (+1…+2)", "st_even": "in equilibrio",
    "st_slight_behind": "leggero svantaggio (−2…−1)", "st_behind": "in svantaggio (−5…−2)", "st_lost": "già persa (< −5)",
    "c_white": "con il Bianco", "c_black": "con il Nero",
}


def win(cp):
    """Probabilità di vittoria 0-100 per chi gioca (formula di Lichess)."""
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * max(-1500, min(1500, cp)))) - 1)


def speed(tc):
    m = re.match(r"^(\d+)(?:\+(\d+))?$", tc or "")
    if not m:
        return "daily" if tc and "/" in tc else "other"
    est = int(m.group(1)) + 40 * int(m.group(2) or 0)
    return "bullet" if est < 180 else "blitz" if est < 480 else "rapid" if est < 1500 else "classical"


def pieces(fen):
    return sum(c.isalpha() for c in (fen or "").split(" ")[0])


def family(name):
    return (name or "?").split(":")[0].split(",")[0].strip()


def piece_key(san):
    s = (san or "").lstrip()
    return "K" if s.startswith("O") else s[:1] if s[:1] in "KQRBN" else "P"


def when(s):
    try:
        return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception:
        return None


def norm(s):
    return re.sub(r"[+#!?]", "", s or "")


def label(tag):
    return LABELS.get(tag) or (f"pezzo mosso: {tag[3:]}" if tag.startswith("pc_") else f"ritmo: {tag[3:]}" if tag.startswith("sp_")
                                else f"apertura: {tag[3:]}" if tag.startswith("op:") else tag)


def analyze(games, moves_by_game):
    """games: righe di 'games'; moves_by_game: {game_id: [{ply, san, eval_cp, fen_after, best_move_san, is_user_move}]}."""
    recs, per_game, suspicious = [], {}, []
    order = sorted(games, key=lambda g: g.get("played_at") or "")
    prev_lost_at = None
    for g in order:
        rows = sorted(moves_by_game.get(g["id"], []), key=lambda r: r["ply"])
        white = g["user_color"] == "white"
        res = g["result"]
        lost = (res == "0-1" and white) or (res == "1-0" and not white)
        won = (res == "1-0" and white) or (res == "0-1" and not white)
        t = when(g.get("played_at"))
        after_loss = bool(prev_lost_at and t and 0 <= (t - prev_lost_at).total_seconds() <= 3600)
        if lost:
            prev_lost_at = t
        n_pl = len(pgnlite.plies(g["pgn"]))
        if ((g.get("accuracy_user") or 0) >= 99 and lost) or (n_pl and len(rows) < 0.8 * n_pl):
            suspicious.append(g["id"])
            continue                                   # analisi incompleta: non entra nelle statistiche
        mt = pgnlite.move_times(g["pgn"], g.get("time_control"))
        thr = pgnlite.trouble_threshold(g.get("time_control"))
        by_ply = {r["ply"]: r for r in rows}
        sp, fam = speed(g.get("time_control")), family(g.get("opening_name"))
        best_pov = -10 ** 6
        sgn = 1 if white else -1
        for r in rows:
            p = r["ply"]
            if r.get("eval_cp") is None:
                continue
            prev = by_ply.get(p - 1, {}).get("eval_cp", 0) if p > 1 else 0
            prev = 0 if prev is None else prev
            if (p % 2 == 1) != white:                       # mossa dell'avversario: serve solo per il massimo vantaggio
                best_pov = max(best_pov, sgn * r["eval_cp"])
                continue
            before, after = sgn * prev, sgn * r["eval_cp"]
            best_pov = max(best_pov, after)
            wl = win(before) - win(after)
            m = mt[p - 1] if mt and p - 1 < len(mt) else None
            reply = (by_ply.get(p + 1) or {}).get("san") or ""
            best = r.get("best_move_san") or ""
            same = bool(best) and norm(best) == norm(r.get("san"))     # mossa uguale alla migliore: è rumore del motore, non un errore
            low = bool(m and m["clock"] is not None and m["clock"] < thr)
            fast = bool(m and m["spent"] is not None and m["spent"] <= 3 and p > 2)
            state = ("st_won" if before > 500 else "st_adv" if before >= 200 else "st_slight_adv" if before >= 100 else "st_lost" if before < -500
                     else "st_behind" if before <= -200 else "st_slight_behind" if before <= -100 else "st_even")
            tags = ["ph_opening" if p <= 20 else "ph_end" if pieces(r.get("fen_after")) <= 10 else "ph_middle", state,
                    "c_white" if white else "c_black", "sp_" + sp, "pc_" + piece_key(r.get("san"))]
            if low:
                tags.append("t_low")
            if fast:
                tags.append("t_fast")
            if after_loss:
                tags.append("after_loss")
            if fam != "?":
                tags.append("op:" + fam)
            recs.append({"game": g["id"], "date": (g.get("played_at") or "")[:10], "ply": p, "san": r.get("san"), "best": best, "wl": wl,
                         "before": before, "err": wl >= ERR_WIN and not same, "tags": tags, "state": state,
                         "clock": m["clock"] if m else None, "spent": m["spent"] if m else None,
                         "opp_cap": "x" in reply, "opp_chk": ("+" in reply or "#" in reply), "missed": any(c in best for c in "x+#")})
        per_game[g["id"]] = {"best": best_pov, "won": won, "lost": lost, "date": (g.get("played_at") or "")[:10], "opp": g["black"] if white else g["white"]}

    n, e = len(recs), sum(r["err"] for r in recs)
    out = {"games_used": len(per_game), "games_skipped": len(suspicious), "suspicious_ids": suspicious,
           "moves": n, "errors": e, "base_rate": round(e / n, 4) if n else None,
           "with_clock": sum(1 for r in recs if r["clock"] is not None), "patterns": [], "strengths": [], "_keys": {}}
    if not n or not e:
        return out
    p0 = e / n
    recent_games = set(list(g["id"] for g in order if g["id"] in per_game)[-RECENT:])
    groups: dict = {}
    for r in recs:
        for tg in r["tags"]:
            g = groups.setdefault(tg, {"n": 0, "e": 0, "games": set(), "ex": [], "nr": 0, "er": 0})
            g["n"] += 1
            recent = r["game"] in recent_games
            g["nr"] += recent
            if r["err"]:
                g["e"] += 1
                g["er"] += recent
                g["games"].add(r["game"])
                g["ex"].append(r)
    found, strong = [], []
    for tg, g in groups.items():
        if g["n"] < MIN_MOVES:
            continue
        rate = g["e"] / g["n"]
        z = (rate - p0) / math.sqrt(p0 * (1 - p0) / g["n"])
        item = {"id": tg, "label": label(tg), "moves": g["n"], "errors": g["e"], "games": len(g["games"]), "rate": round(rate, 3),
                "lift": round(rate / p0, 2), "z": round(z, 1),
                "examples": [{"game": x["game"], "ply": x["ply"], "move": x["san"], "best": x["best"], "win_loss": round(x["wl"]), "date": x["date"]}
                             for x in sorted(g["ex"], key=lambda x: -x["wl"])[:3]]}
        n_before = g["n"] - g["nr"]
        if g["nr"] >= MIN_MOVES and n_before >= MIN_MOVES:      # tendenza: ultime partite contro le precedenti
            item["trend"] = {"recent": round(g["er"] / g["nr"], 3), "before": round((g["e"] - g["er"]) / n_before, 3)}
        if g["e"] >= MIN_ERRS and len(g["games"]) >= MIN_GAMES and z >= MIN_Z and item["lift"] >= MIN_LIFT:
            found.append(item)
            out["_keys"][tg] = [(x["game"], x["ply"]) for x in g["ex"]]
        elif z <= -MIN_Z and item["lift"] <= 0.7 and g["n"] >= 2 * MIN_MOVES:
            strong.append(item)
    out["patterns"] = sorted(found, key=lambda x: -x["z"])[:8]
    out["strengths"] = sorted(strong, key=lambda x: x["z"])[:3]

    errs = [r for r in recs if r["err"]]
    if errs:
        out["anatomy"] = {
            "gravi (≥ 30 punti di probabilità)": round(100 * sum(r["wl"] >= BLUNDER_WIN for r in errs) / len(errs)),
            "l'avversario cattura subito": round(100 * sum(r["opp_cap"] for r in errs) / len(errs)),
            "l'avversario risponde con scacco": round(100 * sum(r["opp_chk"] for r in errs) / len(errs)),
            "il motore aveva una cattura/scacco/matto": round(100 * sum(r["missed"] for r in errs) / len(errs)),
        }
    mine_by_game = collections.defaultdict(list)
    for r in recs:
        mine_by_game[r["game"]].append(r)
    reached, thrown = [], []
    for gid, v in per_game.items():
        if v["best"] < 300:
            continue
        reached.append(v)
        if v["won"]:
            continue
        rs = mine_by_game[gid]
        peak = max(rs, key=lambda r: r["before"]) if rs else None
        after_peak = [r for r in rs if peak and r["ply"] >= peak["ply"]]
        worst = max(after_peak, key=lambda r: r["wl"]) if after_peak else None
        thrown.append({"game": gid, "date": v["date"], "opp": v["opp"], "result": "persa" if v["lost"] else "patta", "peak": round(v["best"] / 100, 1),
                       "move": (worst["ply"] + 1) // 2 if worst else None, "played": worst["san"] if worst else None,
                       "best": worst["best"] if worst else None, "clock": worst["clock"] if worst else None, "hung": bool(worst and worst["opp_cap"])})
    out["advantage"] = {"reached_plus3": len(reached), "not_won": len(thrown), "lost": sum(t["result"] == "persa" for t in thrown), "examples": thrown[:12]}
    ahead = [r["spent"] for r in recs if r["spent"] is not None and r["state"] in ("st_adv", "st_slight_adv") and r["ply"] > 2]
    even = [r["spent"] for r in recs if r["spent"] is not None and r["state"] == "st_even" and r["ply"] > 2]
    med = lambda a: sorted(a)[len(a) // 2] if a else None  # noqa: E731
    out["time_when_ahead"] = {"median_s_ahead": med(ahead), "median_s_even": med(even)}
    return out


def load(email, limit=150):
    from .db import sb
    prof = {(p["piattaforma"], (p["username"] or "").lower()) for p in
            sb.table("profili_scacchi").select("piattaforma,username").eq("user_email", email).execute().data}
    cols = "id,played_at,time_control,result,pgn,user_color,opening_name,accuracy_user,white,black,source" + shared.extra()
    games = (sb.table("games").select(cols).eq("user_email", email).not_.is_("analyzed_at", "null").not_.is_("user_color", "null")
             .order("played_at", desc=True).limit(limit).execute().data)
    games = [g for g in games if not prof or (g["source"], ((g["white"] if g["user_color"] == "white" else g["black"]) or "").lower()) in prof]
    by: dict = {}
    ids = list(dict.fromkeys(shared.mid(g) for g in games))
    for i in range(0, len(ids), 10):
        start = 0
        while True:
            rows = (sb.table("moves").select("game_id,ply,san,eval_cp,fen_after,best_move_san,is_user_move")
                    .in_("game_id", ids[i:i + 10]).range(start, start + 999).execute().data)
            for r in rows:
                by.setdefault(r["game_id"], []).append(r)
            if len(rows) < 1000:
                break
            start += 1000
    for g in games:                       # le partite con analisi condivisa vedono le mosse della partita originale
        if g["id"] not in by and shared.mid(g) in by:
            by[g["id"]] = by[shared.mid(g)]
    return games, by


def get(email):
    """Risultato completo (con le chiavi degli errori per l'esercizio), in memoria 10 minuti per utente."""
    key = ("patterns", email)
    hit = cache.get(key)
    if hit is not None:
        return hit
    out = analyze(*load(email))
    out["ready"] = out["games_used"] >= MIN_GAMES_READY
    out["need"] = max(0, MIN_GAMES_READY - out["games_used"])
    cache.put(key, out, 600)
    return out


def public(out):
    """Versione per il frontend: senza le liste interne."""
    skip = {"_keys", "suspicious_ids", "anatomy", "strengths"}
    o = {k: v for k, v in out.items() if k not in skip}
    o["patterns"] = o["patterns"][:3] if o.get("ready") else []
    return o
