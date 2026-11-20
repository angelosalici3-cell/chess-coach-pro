"""Sonda degli schemi di errore: legge le partite già analizzate di UN account e stampa quali tendenze emergono.
Non scrive nulla sul database e non usa Gemini. Serve a capire, prima di costruire la funzione, se gli schemi sono netti o vaghi.

Uso (da backend/, con SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY nell'ambiente):
    python -m scripts.pattern_probe --email TUA_EMAIL [--limit 400]
Prova senza database:  python -m scripts.pattern_probe --selftest
Scrive anche pattern_probe.json nella cartella corrente."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.patterns import analyze, label, load  # noqa: E402

def report(o):
    L = []
    w = L.append
    w(f"Partite usate: {o['games_used']}  ·  mosse tue: {o['moves']}  ·  errori (≥ 15 punti di probabilità di vittoria): {o['errors']}"
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
            w(f"• {p['label']} — {p['errors']} errori su {p['moves']} mosse ({100 * p['rate']:.0f}%, "
              f"{p['lift']}× il tuo normale), in {p['games']} partite  [z={p['z']}]")
            for x in p["examples"]:
                w(f"    es. partita {x['game']} mossa {(x['ply'] + 1) // 2}: {x['move']} (meglio {x['best'] or '?'}), −{x['win_loss']} punti di probabilità")
    if o.get("strengths"):
        w("\n=== PUNTI DI FORZA ===")
        for p in o["strengths"]:
            w(f"• {p['label']} — solo {100 * p['rate']:.0f}% di errori ({p['lift']}× il tuo normale)")
    if o.get("anatomy"):
        w("\n=== COME SBAGLI (sul totale degli errori) ===")
        for k, v in o["anatomy"].items():
            w(f"• {k}: {v}%")
    a = o.get("advantage")
    if a:
        w(f"\n=== VANTAGGIO ===\nPartite in cui hai raggiunto almeno +3: {a['reached_plus3']}; non vinte: {a['not_won']} (di cui perse: {a['lost']})")
        for x in a["examples"]:
            w(f"    {x['date']} contro {x['opp']} ({x['result']}, picco +{x['peak']}): il crollo alla mossa {x['move']} con {x['played']} (meglio {x['best'] or '?'})"
              + (f", orologio {x['clock']:.0f} s" if x["clock"] is not None else "") + (", pezzo catturato subito" if x["hung"] else ""))
    t = o.get("time_when_ahead")
    if t and t["median_s_ahead"] is not None and t["median_s_even"] is not None:
        w(f"Tempo per mossa (mediana): in vantaggio {t['median_s_ahead']:.1f} s, in equilibrio {t['median_s_even']:.1f} s")
    return "\n".join(L)


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
    ap.add_argument("--reset", action="store_true", help="rimette 'da analizzare' le partite analizzate male (le rifà l'analisi notturna)")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        sys.exit(0)
    if not a.email:
        ap.error("serve --email")
    res = analyze(*load(a.email, a.limit))
    res.pop("_keys", None)
    print(report(res))
    with open("pattern_probe.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("\nDettagli completi in pattern_probe.json")
    if a.reset and res["suspicious_ids"]:
        from app.db import sb
        ids = res["suspicious_ids"]
        sb.table("games").update({"analyzed_at": None, "accuracy_user": None}).eq("user_email", a.email).in_("id", ids).execute()
        print(f"Rimesse in coda per la nuova analisi: {len(ids)} partite")
