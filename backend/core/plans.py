"""Unica fonte di verità per piani e limiti (app, worker e webhook importano da qui)."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Plan:
    key: str
    price_eur: float
    profiles: int                    # account scacchistici collegabili
    gm_lessons_month: Optional[int]  # None = illimitate
    auto_sync: bool                  # download + analisi automatici
    auto_games_month: int            # tetto partite analizzate dal worker
    stripe_price_env: str            # nome della variabile d'ambiente
    history_games: int = 50          # storico importabile per account collegato
    initial_games: int = 20          # partite più recenti scaricate E analizzate subito dopo il collegamento dell'account
    price_year_eur: float = 0.0      # prezzo annuale (circa 10 mensilità: 2 mesi gratis)


PLANS = {
    "Free":  Plan("Free", 0.00, 1, 3, False, 0, "", history_games=50, initial_games=20),
    "Plus":  Plan("Plus", 4.99, 2, 20, True, 30, "STRIPE_PRICE_PLUS", history_games=200, initial_games=50, price_year_eur=49.0),
    "Pro":   Plan("Pro", 8.99, 3, None, True, 200, "STRIPE_PRICE_PRO", history_games=500, initial_games=100, price_year_eur=89.0),
    "Elite": Plan("Elite", 14.99, 5, None, True, 600, "STRIPE_PRICE_ELITE", history_games=1000, initial_games=150, price_year_eur=149.0),
}


def get_plan(tier: Optional[str]) -> Plan:
    return PLANS.get(tier or "Free", PLANS["Free"])


def stripe_price_id(tier: str, interval: str = "month") -> str:
    """Ogni piano (e ogni periodicità) ha il suo price id: niente fallback silenzioso su un altro piano."""
    import os
    name = get_plan(tier).stripe_price_env
    if name and interval == "year":
        name += "_YEAR"
    value = os.environ.get(name, "") if name else ""
    if not value:
        raise RuntimeError(f"Price id Stripe mancante per il piano {tier} ({name})")
    return value
