"""Logica pura (senza database) di carte e scudi delle aperture.

Carte: si ottengono con obiettivi particolari su una partita (es. la prima con almeno 10 mosse a testa e precisione >= 95%).
Scudi delle aperture: vittorie giocando una linea di apertura. Le linee non superano le 10 semimosse (5 mosse a testa).
"""
import datetime
import re

RARITIES = ["common", "rare", "epic", "legendary"]
MAX_OPENING_PLIES = 10
OPEN_TIERS = [3, 10, 25]                      # vittorie per bronzo / argento / oro: difficoltà media
OPEN_RARITY = {1: "rare", 2: "epic", 3: "legendary"}

# id, colore di chi gioca la linea, varianti (ognuna di al massimo 10 semimosse)
OPENINGS = [
    {"id": "italiana", "color": "w", "lines": [["e4", "e5", "Nf3", "Nc6", "Bc4"]]},
    {"id": "ruy", "color": "w", "lines": [["e4", "e5", "Nf3", "Nc6", "Bb5"]]},
    {"id": "scozzese", "color": "w", "lines": [["e4", "e5", "Nf3", "Nc6", "d4"]]},
    {"id": "londra", "color": "w", "lines": [["d4", "d5", "Bf4"], ["d4", "d5", "Nf3", "Nf6", "Bf4"], ["d4", "Nf6", "Nf3", "d5", "Bf4"], ["d4", "Nf6", "Bf4"]]},
    {"id": "gambetto", "color": "w", "lines": [["d4", "d5", "c4"]]},
    {"id": "inglese", "color": "w", "lines": [["c4"]]},
    {"id": "siciliana", "color": "b", "lines": [["e4", "c5"]]},
    {"id": "francese", "color": "b", "lines": [["e4", "e6"]]},
    {"id": "caro", "color": "b", "lines": [["e4", "c6"]]},
    {"id": "scandinava", "color": "b", "lines": [["e4", "d5"]]},
    {"id": "indiana", "color": "b", "lines": [["d4", "Nf6", "c4", "g6"]]},
    {"id": "nimzo", "color": "b", "lines": [["d4", "Nf6", "c4", "e6", "Nc3", "Bb4"]]},
]

# codice obiettivo -> rarità, quante carte al massimo (le prime partite che lo soddisfano)
STREAK_STEPS = {"all": [3, 5, 10]}   # serie di vittorie: totali, col Bianco, col Nero
TIER_RARITY = {1: "rare", 2: "epic", 3: "legendary"}
SPEEDS = ["bullet", "blitz", "rapid", "classical"]
HOUR_STEPS = [20]                                              # stesse ore giocate per ogni ritmo: l'impegno è equivalente
GOALS = {   # una sola carta per traguardo: l'album è un percorso, non una raccolta infinita
    "first_win": {"rarity": "common", "max": 1},
    "new_opening": {"rarity": "common", "max": 1},
    "short_win": {"rarity": "common", "max": 1},
    "first_95": {"rarity": "rare", "max": 1},
    "lightning": {"rarity": "rare", "max": 1},
    "flawless": {"rarity": "rare", "max": 1},
    "short_win_pro": {"rarity": "rare", "max": 1},
    "photo_finish": {"rarity": "epic", "max": 1},
    "revenge": {"rarity": "epic", "max": 1},
    "comeback": {"rarity": "epic", "max": 1},
    "brilliant": {"rarity": "epic", "max": 1},
    "giant": {"rarity": "epic", "max": 1},
    "master": {"rarity": "epic", "max": 1},
    "comeback_big": {"rarity": "legendary", "max": 1},
    "giant_big": {"rarity": "legendary", "max": 1},
    "masterpiece": {"rarity": "legendary", "max": 1},
}
# gruppi dell'album (solo per presentarli in ordine)
GROUPS = {
    "first": ["first_win", "first_95", "new_opening", "lightning"],
    "moments": ["short_win", "short_win_pro", "photo_finish", "revenge", "comeback", "comeback_big", "brilliant", "flawless"],
    "challenges": ["giant", "giant_big", "master", "masterpiece"],
}
RATING_STEPS = [1200, 1400, 1600, 1800, 2000]
RATING_RARITY = {1200: "common", 1400: "rare", 1600: "rare", 1800: "epic", 2000: "legendary"}


def catalog() -> list[dict]:
    """Tutte le carte ottenibili (esclusa la carta del mese, che si ripete ogni mese)."""
    out = [{"goal": k, "rarity": GOALS[k]["rarity"], "group": g} for g, ks in GROUPS.items() for k in ks]
    out += [{"goal": f"streak_all_{n}", "rarity": TIER_RARITY[i], "group": "streak"} for i, n in enumerate(STREAK_STEPS["all"], 1)]
    out += [{"goal": f"hours_{sp}_1", "rarity": "rare", "group": "pace"} for sp in SPEEDS]
    out += [{"goal": f"rating_{n}", "rarity": RATING_RARITY[n], "group": "rating"} for n in RATING_STEPS]
    return out


def in_catalog(goal: str) -> bool:
    return goal.startswith("month_") or any(c["goal"] == goal for c in catalog())


VS_STEP = 100                      # traguardi "prima vittoria contro un X+": uno ogni 100 punti
VS_MIN_PLIES = 16


def vs_rarity(gap: int) -> str:
    """Più il traguardo è lontano dal rating di partenza, più la carta è rara."""
    return "common" if gap <= 100 else "rare" if gap <= 300 else "epic" if gap <= 500 else "legendary"


def norm(s: str) -> str:
    return (s or "").replace("+", "").replace("#", "").replace("!", "").replace("?", "").strip()


def outcome(game: dict):
    """'w' vittoria, 'd' patta, 'l' sconfitta, None se non utilizzabile."""
    res, col = game.get("result"), game.get("user_color")
    if col not in ("white", "black") or res not in ("1-0", "0-1", "1/2-1/2"):
        return None
    if res == "1/2-1/2":
        return "d"
    return "w" if (res == "1-0") == (col == "white") else "l"


def elo(pgn: str, color: str):
    m = re.search(rf'\[{"White" if color == "white" else "Black"}Elo "(\d+)"\]', pgn or "")
    return int(m.group(1)) if m else None


def opening_match(sans: list[str], color: str, op: dict) -> bool:
    if (color == "white") != (op["color"] == "w"):
        return False
    s = [norm(x) for x in sans[:MAX_OPENING_PLIES]]
    return any(len(s) >= len(line) and s[:len(line)] == line for line in op["lines"])


def tier_of(value: int, tiers=OPEN_TIERS) -> int:
    return sum(1 for t in tiers if value >= t)


PIECE = {"p": 1, "n": 3, "b": 3, "r": 5, "q": 9}


def material(fen: str) -> int:
    """Bilancio materiale (Bianco meno Nero) dalla sola parte pezzi della FEN."""
    tot = 0
    for ch in (fen or "").split(" ")[0]:
        v = PIECE.get(ch.lower())
        if v:
            tot += v if ch.isupper() else -v
    return tot


def highlights_from_moves(rows: list[dict], color: str) -> dict:
    """Da `moves` (ply, eval_cp dal lato del Bianco, fen_after, is_user_move) ricava:
    low_cp = punto più basso della valutazione per l'utente (dalla 10ª semimossa), brilliant = semimosse con sacrificio che regge."""
    sign = 1 if color == "white" else -1
    by = {r["ply"]: r for r in rows}
    last = max(by) if by else 0
    ev = lambda p: sign * (by[p].get("eval_cp") or 0) if p in by else 0
    lows = [ev(p) for p in by if p >= 10 and by[p].get("eval_cp") is not None]
    brill = []
    for p, r in sorted(by.items()):
        if not r.get("is_user_move") or p + 1 > last or p + 1 not in by:
            continue
        mat_before = sign * material(by[p - 1]["fen_after"]) if p > 1 and p - 1 in by else 0
        mat_after = sign * material(by[p + 1]["fen_after"])
        e0, e1 = ev(p - 1) if p > 1 else 0, ev(p + 1)
        if mat_after - mat_before <= -2 and e1 >= 100 and e1 - e0 >= -30 and e0 <= 500:
            brill.append(p)
    return {"v": 1, "low_cp": min(lows) if lows else None, "brilliant": brill[:3]}


def speed_of(tc: str | None):
    m = re.match(r"^(\d+)(?:\+(\d+))?$", tc or "")
    if not m:
        return None
    est = int(m.group(1)) + 40 * int(m.group(2) or 0)
    return "bullet" if est < 180 else "blitz" if est < 480 else "rapid" if est < 1500 else "classical"


def duration_s(tc: str | None, clks: list, n: int) -> float:
    """Secondi complessivi di una partita (entrambi i giocatori). Con l'orologio nel PGN è esatto; altrimenti stimo il 60% del tempo a disposizione."""
    m = re.match(r"^(\d+)(?:\+(\d+))?$", tc or "")
    if not m or n == 0:
        return 0.0
    base, inc = int(m.group(1)), int(m.group(2) or 0)
    total = 0.0
    for side in (0, 1):
        k = len(range(side, n, 2))
        last = next((c for c in reversed(clks[side::2]) if c is not None), None) if clks else None
        used = (base + inc * max(0, k - 1) - last) if last is not None else 0.6 * (base + inc * k)
        total += max(0.0, min(used, base + inc * k))
    return total


def evaluate(games: list[dict], clean_ids: set) -> dict:
    """games: [{id, played_at, user_color, result, pgn, sans, accuracy_user}] (qualsiasi ordine).
    clean_ids: id delle partite analizzate senza errori. Restituisce {cards:[...], open_wins:{id: n}}."""
    games = sorted(games, key=lambda g: g.get("played_at") or "")
    counts = {k: 0 for k in GOALS}
    wins = {o["id"]: 0 for o in OPENINGS}
    cards = []
    runs = {"all": 0, "w": 0, "b": 0}
    best_runs = dict(runs)
    won_families: set = set()
    last_vs: dict = {}
    vs_base: dict = {}      # ritmo -> rating di chi gioca alla prima partita di quel ritmo (punto di partenza)
    vs_best: dict = {}      # ritmo -> ultimo traguardo raggiunto (multiplo di 100)
    rated: set = set()
    by_month: dict = {}
    secs = {k: 0.0 for k in SPEEDS}
    cnt = {k: 0 for k in SPEEDS}

    def give(goal, rarity, g, **extra):
        cards.append({"goal": goal, "rarity": rarity, "game_id": str(g["id"]), "data": extra})

    for g in games:
        o = outcome(g)
        sans = g.get("sans") or []
        n = len(sans)
        acc = g.get("accuracy_user")
        acc = float(acc) if acc is not None else None
        col = g.get("user_color")
        mine = elo(g.get("pgn"), col) if col else None
        opp = elo(g.get("pgn"), "black" if col == "white" else "white") if col else None
        base = {"acc": acc, "plies": n, "elo": mine, "opp_elo": opp}

        def hit(goal, **extra):
            if counts[goal] < GOALS[goal]["max"]:
                counts[goal] += 1
                give(goal, GOALS[goal]["rarity"], g, **base, **extra)

        if o == "w" and n >= 20:
            hit("first_win")
        if acc is not None and acc >= 95 and n >= 20:
            hit("first_95")
        if o == "w" and 8 <= n <= 20 and sans and sans[-1].endswith("#"):
            hit("lightning")
        if o == "w" and n >= 30 and acc is not None and acc >= 90 and g["id"] in clean_ids:
            hit("flawless")
        if acc is not None and acc >= 98 and n >= 40:
            hit("master")
        if o == "w" and mine and opp:
            if opp - mine >= 300:
                hit("giant_big")
            elif opp - mine >= 150:
                hit("giant")
        if o == "w" and acc is not None and acc >= 97 and n >= 50 and (not (mine and opp) or opp >= mine):
            hit("masterpiece")

        # --- soglie di rating raggiunte (da una partita decisa e non banale)
        if o and mine and n >= VS_MIN_PLIES:
            for thr in RATING_STEPS:
                if mine >= thr and thr not in rated:
                    rated.add(thr)
                    give(f"rating_{thr}", RATING_RARITY[thr], g, **base, rating=thr)
        # --- serie di vittorie (totali, Bianco, Nero): una patta o una sconfitta la interrompe
        if o:
            keys = ["all", "w" if col == "white" else "b"]
            for k in keys:
                runs[k] = runs[k] + 1 if o == "w" else 0
                best_runs[k] = max(best_runs[k], runs[k])
                if o == "w" and k in STREAK_STEPS and runs[k] in STREAK_STEPS[k]:
                    tier = STREAK_STEPS[k].index(runs[k]) + 1
                    code = f"streak_{k}_{runs[k]}"
                    if counts.setdefault(code, 0) < 1:
                        counts[code] += 1
                        give(code, TIER_RARITY[tier], g, **base, run=runs[k])
        # --- prima vittoria con un'apertura nuova
        fam = ((g.get("opening_name") or "").split(":")[0].split(",")[0]).strip()
        if o == "w" and fam and n >= 16 and fam not in won_families:
            won_families.add(fam)
            hit("new_opening", opening_name=fam)
        # --- vittoria breve e precisa (meno di 20 mosse)
        if o == "w" and 15 <= n <= 38 and acc is not None and acc >= 90:
            hit("short_win_pro" if acc >= 96 else "short_win")
        # --- vittoria all'ultimo secondo (serve l'orologio)
        clks = g.get("clks") or []
        tcm = re.match(r"^(\d+)(?:\+\d+)?$", g.get("tc") or "")
        if o == "w" and tcm and clks and int(tcm.group(1)) >= 60:
            mine_c = [c for c in clks[(0 if col == "white" else 1)::2] if c is not None]
            if mine_c and 0 <= mine_c[-1] <= max(5, 0.05 * int(tcm.group(1))):
                hit("photo_finish", left=round(mine_c[-1], 1))
        # --- rivincita: batto chi mi aveva battuto nella partita precedente
        opp_name = g.get("black") if col == "white" else g.get("white")
        if opp_name and o:
            if o == "w" and last_vs.get(opp_name) == "l":
                hit("revenge", opp=opp_name)
            last_vs[opp_name] = o
        # --- rimonta e mossa brillante (da highlights salvati all'analisi)
        hl = g.get("highlights") or {}
        low = hl.get("low_cp")
        if o == "w" and low is not None and low <= -300:
            hit("comeback_big" if low <= -600 else "comeback", low=round(-low / 100, 1))
        if o == "w" and hl.get("brilliant"):
            hit("brilliant", hi=hl["brilliant"][0])
        # --- ore giocate per ritmo (stesse soglie per ogni ritmo)
        sp = speed_of(g.get("tc"))
        if sp:
            before = secs[sp] / 3600
            secs[sp] += duration_s(g.get("tc"), clks, n); cnt[sp] += 1
            after = secs[sp] / 3600
            for i, h in enumerate(HOUR_STEPS, 1):
                if before < h <= after:
                    give(f"hours_{sp}_{i}", "rare", g, **base, speed=sp, hours=h, games=cnt[sp])
        if acc is not None and n >= 20 and g.get("played_at"):
            by_month.setdefault(g["played_at"][:7], []).append((acc, g, base))
        if o == "w":
            for op in OPENINGS:
                if opening_match(sans, col, op):
                    before = tier_of(wins[op["id"]])
                    wins[op["id"]] += 1
                    after = tier_of(wins[op["id"]])
                    # gli scudi delle aperture si calcolano da open_wins: non generano più carte
    cur = datetime.date.today().strftime("%Y-%m")
    for ym, lst in by_month.items():
        if ym < cur:   # la carta del mese arriva a mese concluso: la tua partita più precisa
            acc_m, g_m, base_m = max(lst, key=lambda t: t[0])
            give(f"month_{ym}", "rare", g_m, **base_m, month=ym)
    progress = {"hours": {k: round(secs[k] / 3600, 1) for k in SPEEDS}, "games": cnt, "runs": runs, "best_runs": best_runs,
                "rating_next": next((n for n in RATING_STEPS if n not in rated), None)}
    return {"cards": cards, "open_wins": wins, "progress": progress}
