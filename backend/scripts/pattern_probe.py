"""Sonda degli schemi di errore: legge le partite già analizzate di UN account e stampa quali tendenze emergono.
Non scrive nulla sul database e non usa Gemini. Serve a capire, prima di costruire la funzione, se gli schemi sono netti o vaghi.

Uso (da backend/, con SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY nell'ambiente):
    python -m scripts.pattern_probe --email TUA_EMAIL [--limit 400]
Prova senza database:  python -m scripts.pattern_probe --selftest
Scrive anche pattern_probe.json nella cartella corrente."""
import argparse
import collections
import datetime
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import pgnlite  # noqa: E402

ERR_CP = 100          # perdita di almeno 1 pedone = errore (come "mistake" in engine.py)
BLUNDER_CP = 200
MIN_MOVES, MIN_ERRS, MIN_GAMES, MIN_Z, MIN_LIFT = 30, 5, 3, 2.0, 1.4


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


def piece_of(san):
    s = (san or "").lstrip()
    if s.startswith("O"):
        return "re (arrocco)"
    return {"K": "re", "Q": "donna", "R": "torre", "B": "alfiere", "N": "cavallo"}.get(s[:1], "pedone")


def when(s):
    try:
        return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception:
        return None


def analyze(games, moves_by_game):
    """games: righe di 'games' (id, played_at, time_control, result, pgn, user_color, opening_name, accuracy_user).
    moves_by_game: {game_id: [{ply, san, eval_cp, fen_after, best_move_san, is_user_move}]}.  Restituisce un dizionario di risultati."""
    recs, per_game, suspicious = [], {}, []
    order = sorted(games, key=lambda g: g.get("played_at") or "")
    prev_lost_at = None
    fam_count = collections.Counter(family(g.get("opening_name")) for g in games)
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
        if (g.get("accuracy_user") or 0) >= 99 and lost or (n_pl and len(rows) < 0.8 * n_pl):
            suspicious.append(g["id"])
            continue                                   # analisi incompleta: non entra nelle statistiche
        mt = pgnlite.move_times(g["pgn"], g.get("time_control"))
        thr = pgnlite.trouble_threshold(g.get("time_control"))
        by_ply = {r["ply"]: r for r in rows}
        sp, fam = speed(g.get("time_control")), family(g.get("opening_name"))
        best_pov = -10 ** 6
        for r in rows:
            p = r["ply"]
            if r.get("eval_cp") is None:
                continue
            prev = by_ply.get(p - 1, {}).get("eval_cp", 0) if p > 1 else 0
            prev = 0 if prev is None else prev
            sgn = 1 if white else -1
            if (p % 2 == 1) != white:                       # mossa dell'avversario: serve solo per il massimo vantaggio
                best_pov = max(best_pov, sgn * r["eval_cp"])
                continue
            before, after = sgn * prev, sgn * r["eval_cp"]
            best_pov = max(best_pov, after)
            loss = before - after
            m = mt[p - 1] if mt and p - 1 < len(mt) else None
            nxt = by_ply.get(p + 1) or {}
            reply = nxt.get("san") or ""
            best = r.get("best_move_san") or ""
            recs.append({
                "game": g["id"], "ply": p, "san": r.get("san"), "best": best, "loss": loss, "err": loss >= ERR_CP,
                "phase": "apertura" if p <= 20 else "finale" if pieces(r.get("fen_after")) <= 10 else "mediogioco",
                "clock": m["clock"] if m else None,
                "low": bool(m and m["clock"] is not None and m["clock"] < thr),
                "fast": bool(m and m["spent"] is not None and m["spent"] <= 3 and p > 2),
                "state": "in vantaggio (≥ +2)" if before >= 200 else "in svantaggio (≤ −2)" if before <= -200 else "in equilibrio",
                "after_loss": after_loss, "color": "bianco" if white else "nero", "speed": sp, "fam": fam,
                "piece": piece_of(r.get("san")), "opp_cap": "x" in reply, "opp_chk": ("+" in reply or "#" in reply),
                "missed": any(c in best for c in "x+#"),
            })
        per_game[g["id"]] = {"best": best_pov, "won": won, "lost": lost, "date": (g.get("played_at") or "")[:10], "opp": g["black"] if white else g["white"]}

    n, e = len(recs), sum(r["err"] for r in recs)
    out = {"games_used": len(per_game), "games_skipped": len(suspicious), "suspicious_ids": suspicious[:20],
           "moves": n, "errors": e, "base_rate": round(e / n, 4) if n else None,
           "with_clock": sum(1 for r in recs if r["clock"] is not None)}
    if not n or not e:
        out["patterns"], out["strengths"] = [], []
        return out
    p0 = e / n

    def dims():
        yield "fase", lambda r: r["phase"]
        yield "tempo", lambda r: "poco tempo sull'orologio" if r["low"] else None
        yield "tempo", lambda r: "mossa rapida (≤ 3 s)" if r["fast"] else None
        yield "situazione", lambda r: r["state"]
        yield "serie", lambda r: "subito dopo una sconfitta (≤ 1 h)" if r["after_loss"] else None
        yield "colore", lambda r: r["color"]
        yield "ritmo", lambda r: r["speed"]
        yield "pezzo mosso", lambda r: r["piece"]
        yield "apertura", lambda r: r["fam"] if r["fam"] != "?" else None

    groups: dict = {}
    for dim, fn in dims():
        for r in recs:
            lab = fn(r)
            if lab is None:
                continue
            g = groups.setdefault((dim, lab), {"n": 0, "e": 0, "games": set(), "ex": []})
            g["n"] += 1
            if r["err"]:
                g["e"] += 1
                g["games"].add(r["game"])
                g["ex"].append(r)
    found, strong = [], []
    for (dim, lab), g in groups.items():
        if g["n"] < MIN_MOVES:
            continue
        rate = g["e"] / g["n"]
        z = (rate - p0) / math.sqrt(p0 * (1 - p0) / g["n"])
        item = {"dim": dim, "label": lab, "moves": g["n"], "errors": g["e"], "games": len(g["games"]), "rate": round(rate, 3),
                "lift": round(rate / p0, 2), "z": round(z, 1),
                "examples": [{"game": x["game"], "ply": x["ply"], "move": x["san"], "best": x["best"], "loss_cp": x["loss"]}
                             for x in sorted(g["ex"], key=lambda x: -x["loss"])[:3]]}
        if g["e"] >= MIN_ERRS and len(g["games"]) >= MIN_GAMES and z >= MIN_Z and item["lift"] >= MIN_LIFT:
            found.append(item)
        elif z <= -MIN_Z and item["lift"] <= 0.7 and g["n"] >= 2 * MIN_MOVES:
            strong.append(item)
    out["patterns"] = sorted(found, key=lambda x: -x["z"])[:8]
    out["strengths"] = sorted(strong, key=lambda x: x["z"])[:3]

    errs = [r for r in recs if r["err"]]
    out["anatomy"] = {
        "gravi (≥ 2 pedoni)": round(100 * sum(r["loss"] >= BLUNDER_CP for r in errs) / len(errs)),
        "l'avversario cattura subito": round(100 * sum(r["opp_cap"] for r in errs) / len(errs)),
        "l'avversario risponde con scacco": round(100 * sum(r["opp_chk"] for r in errs) / len(errs)),
        "il motore aveva una cattura/scacco/matto": round(100 * sum(r["missed"] for r in errs) / len(errs)),
    }
    reached = [v for v in per_game.values() if v["best"] >= 300]
    thrown = [v for v in reached if not v["won"]]
    out["advantage"] = {"reached_plus3": len(reached), "not_won": len(thrown),
                        "examples": [{"date": v["date"], "opp": v["opp"]} for v in thrown[:3]]}
    return out


def report(o):
    L = []
    w = L.append
    w(f"Partite usate: {o['games_used']}  ·  mosse tue: {o['moves']}  ·  errori (≥ 1 pedone): {o['errors']}"
      + (f"  ·  tasso base: {100 * o['base_rate']:.1f}% delle mosse" if o.get("base_rate") else ""))
    w(f"Mosse con orologio: {o['with_clock']}")
    if o["games_skipped"]:
        w(f"ATTENZIONE: {o['games_skipped']} partite sembrano analizzate male (100% di precisione in una sconfitta, o mosse mancanti) e sono escluse.")
        w("  Per rianalizzarle: update games set analyzed_at = null, accuracy_user = null where id in (…)  [id in pattern_probe.json]")
    if not o.get("patterns") and not o.get("strengths"):
        w("\nNessuno schema supera le soglie (campione piccolo o errori distribuiti in modo uniforme).")
    if o.get("patterns"):
        w("\n=== TENDENZE (dove sbagli più del tuo normale) ===")
        for p in o["patterns"]:
            w(f"• {p['dim']}: {p['label']} — {p['errors']} errori su {p['moves']} mosse ({100 * p['rate']:.0f}%, "
              f"{p['lift']}× il tuo normale), in {p['games']} partite  [z={p['z']}]")
            for x in p["examples"]:
                w(f"    es. partita {x['game']} mossa {(x['ply'] + 1) // 2}: {x['move']} (meglio {x['best'] or '?'}), −{x['loss_cp'] / 100:.1f}")
    if o.get("strengths"):
        w("\n=== PUNTI DI FORZA ===")
        for p in o["strengths"]:
            w(f"• {p['dim']}: {p['label']} — solo {100 * p['rate']:.0f}% di errori ({p['lift']}× il tuo normale)")
    if o.get("anatomy"):
        w("\n=== COME SBAGLI (sul totale degli errori) ===")
        for k, v in o["anatomy"].items():
            w(f"• {k}: {v}%")
    a = o.get("advantage")
    if a:
        w(f"\n=== VANTAGGIO ===\nPartite in cui hai raggiunto almeno +3: {a['reached_plus3']}, non vinte: {a['not_won']}")
        for x in a["examples"]:
            w(f"    es. {x['date']} contro {x['opp']}")
    return "\n".join(L)


def load(email, limit):
    from app.db import sb  # solo qui: serve l'ambiente di Supabase
    prof = {(p["piattaforma"], (p["username"] or "").lower()) for p in
            sb.table("profili_scacchi").select("piattaforma,username").eq("user_email", email).execute().data}
    cols = "id,played_at,time_control,result,pgn,user_color,opening_name,accuracy_user,white,black,source"
    games = (sb.table("games").select(cols).eq("user_email", email).not_.is_("analyzed_at", "null").not_.is_("user_color", "null")
             .order("played_at", desc=True).limit(limit).execute().data)
    games = [g for g in games if not prof or (g["source"], ((g["white"] if g["user_color"] == "white" else g["black"]) or "").lower()) in prof]
    by: dict = {}
    ids = [g["id"] for g in games]
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
    return games, by


def selftest():
    """Partite finte: gli errori si concentrano quando manca tempo. La sonda deve trovarlo."""
    import random
    random.seed(4)
    games, by = [], {}
    for k in range(30):
        gid = f"g{k}"
        pl, rows, ev = [], [], 0
        clock = 180.0
        for p in range(1, 61):
            mine = p % 2 == 1
            clock = max(1.0, clock - random.uniform(3, 9)) if mine else clock
            low = mine and clock < 18
            bad = mine and random.random() < (0.5 if low else 0.04)
            if mine and bad:
                ev -= random.choice([150, 250, 400])
            elif mine:
                ev += random.choice([-20, 0, 20])
            san = random.choice(["Nf3", "e4", "Qxd5", "Rd1", "Bc4"])
            pl.append(f"{(p + 1) // 2}{'.' if mine else '...'} {san} {{[%clk 0:{int(clock) // 60:02d}:{int(clock) % 60:02d}]}}")
            rows.append({"ply": p, "san": san, "eval_cp": ev, "fen_after": "8/8/8/8/8/8/8/8" if p > 40 else "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w",
                         "best_move_san": "Qxf7+" if bad else "e4", "is_user_move": mine})
        res = "0-1" if ev < 0 else "1-0"
        games.append({"id": gid, "played_at": f"2026-11-{1 + k % 20:02d}T1{k % 10}:00:00Z", "time_control": "180", "result": res,
                      "pgn": '[Event "x"]\n[TimeControl "180"]\n\n' + " ".join(pl) + f" {res}", "user_color": "white",
                      "opening_name": "Italian Game" if k % 2 else "Sicilian Defense", "accuracy_user": 80, "white": "me", "black": "opp"})
        by[gid] = rows
    print(report(analyze(games, by)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--email")
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        sys.exit(0)
    if not a.email:
        ap.error("serve --email")
    res = analyze(*load(a.email, a.limit))
    print(report(res))
    with open("pattern_probe.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("\nDettagli completi in pattern_probe.json")
