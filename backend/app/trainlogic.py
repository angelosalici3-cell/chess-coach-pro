"""Logica pura dell'allenamento (nessun database): Elo dei puzzle, ripetizione a intervalli, XP, scudi, ricompense."""
import datetime
import math

RATING_MIN, RATING_MAX, K_FACTOR = 400, 3000, 32

# giorni prima del prossimo ripasso dopo una risposta corretta, in base alla nuova casella (1..5)
LEITNER_DAYS = {2: 1, 3: 3, 4: 7, 5: 16}
LEITNER_MASTERED_DAYS = 35

# (id, soglie bronzo/argento/oro)
SHIELDS = [   # bronzo / argento / oro: per chi usa l'app con regolarità, circa 1 settimana / 1-2 mesi / 4-6 mesi
    ("games", [25, 150, 500]),
    ("analyzed", [10, 75, 300]),
    ("puzzles", [25, 150, 600]),
    ("streak", [3, 14, 60]),
    ("fixed", [15, 75, 300]),
    ("lessons", [3, 15, 50]),
    ("accuracy", [80, 88, 94]),
    ("openings", [5, 15, 40]),
    ("puzzle_rating", [1400, 1700, 2000]),
    ("clean", [3, 10, 30]),
]
TIER_XP = [50, 150, 400]
XP_PER_PUZZLE, XP_PER_FIX, XP_PER_DAY = 4, 6, 10

REWARDS = [
    {"lvl": 2, "kind": "bonus_lessons", "amount": 3},
    {"lvl": 3, "kind": "bonus_lessons", "amount": 5},
    {"lvl": 5, "kind": "trial", "tier": "Plus", "days": 3},
    {"lvl": 7, "kind": "bonus_lessons", "amount": 10},
    {"lvl": 10, "kind": "trial", "tier": "Pro", "days": 7},
    {"lvl": 15, "kind": "bonus_lessons", "amount": 20},
    {"lvl": 20, "kind": "trial", "tier": "Elite", "days": 30},
]


def norm_san(s: str | None) -> str:
    return (s or "").replace("+", "").replace("#", "").replace("!", "").replace("?", "").strip()


def elo_update(rating: int, puzzle_rating: int, solved: bool) -> int:
    expected = 1 / (1 + 10 ** ((puzzle_rating - rating) / 400))
    return max(RATING_MIN, min(RATING_MAX, round(rating + K_FACTOR * ((1 if solved else 0) - expected))))


RETIRED_BOX = 5            # errore risolto: esce dalla coda
RETIRED_AT = datetime.datetime(2099, 1, 1, tzinfo=datetime.timezone.utc)
SOLVE_AFTER = 2           # risposte giuste di fila per considerarlo risolto


def is_retired(box: int) -> bool:
    return box >= RETIRED_BOX


def leitner_next(box: int, correct: bool, now: datetime.datetime):
    """(nuova casella, prossima scadenza).
    Errore: si riparte dalla casella 1 tra 10 minuti (anche per un errore già risolto, che torna in coda).
    2 risposte giuste di fila (ripasso domani, poi risolto): l'errore esce dalla coda e non si ripresenta
    da solo; ricompare solo nei ripassi casuali occasionali."""
    if not correct:
        return 1, now + datetime.timedelta(minutes=10)
    if is_retired(box):
        return RETIRED_BOX, RETIRED_AT
    nb = box + 1
    if nb >= SOLVE_AFTER + 1:
        return RETIRED_BOX, RETIRED_AT
    return nb, now + datetime.timedelta(days=LEITNER_DAYS[nb])


def memo_next(box: int, correct: bool, now: datetime.datetime):
    """Ripasso a memoria (linee di apertura): 5 caselle, poi ogni 35 giorni. Errore: si riparte tra 10 minuti."""
    if not correct:
        return 1, now + datetime.timedelta(minutes=10)
    if box >= 5:
        return 5, now + datetime.timedelta(days=LEITNER_MASTERED_DAYS)
    nb = box + 1
    return nb, now + datetime.timedelta(days=LEITNER_DAYS[nb])


def touch_streak(stats: dict, today: datetime.date) -> dict:
    """Aggiorna serie giornaliera e giorni di allenamento (una sola volta al giorno)."""
    last = stats.get("last_train_date")
    if last == today.isoformat():
        return {}
    yesterday = (today - datetime.timedelta(days=1)).isoformat()
    streak = (stats.get("current_streak") or 0) + 1 if last == yesterday else 1
    return {"current_streak": streak, "best_streak": max(stats.get("best_streak") or 0, streak),
            "training_days": (stats.get("training_days") or 0) + 1, "last_train_date": today.isoformat()}


def shield_tier(value: float, tiers: list[int]) -> int:
    return sum(1 for t in tiers if value >= t)


def xp_total(metrics: dict, stats: dict) -> int:
    xp = 0
    for sid, tiers in SHIELDS:
        xp += sum(TIER_XP[: shield_tier(metrics.get(sid, 0), tiers)])
    return xp + XP_PER_PUZZLE * (stats.get("puzzles_solved") or 0) + XP_PER_FIX * (stats.get("mistakes_fixed") or 0) + XP_PER_DAY * (stats.get("training_days") or 0)


def level_of(xp: int) -> int:
    return int(math.sqrt(max(0, xp) / 40)) + 1


def xp_for_level(level: int) -> int:
    return 40 * (level - 1) ** 2
