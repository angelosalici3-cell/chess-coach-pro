"""Crea in Stripe prodotti e prezzi (mensili e annuali) dei piani a pagamento e stampa le variabili da copiare su Render.
Uso (da backend/): STRIPE_SECRET_KEY=sk_test_... python -m scripts.create_stripe_prices
Con una chiave sk_test_ lavora in modalità test; con sk_live_ crea i prezzi reali."""
import os
import sys

import stripe

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.plans import PLANS  # noqa: E402

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
print(f"# modalità: {'TEST' if stripe.api_key.startswith('sk_test') else 'LIVE'}")
for key in ("Plus", "Pro", "Elite"):
    p = PLANS[key]
    prod = stripe.Product.create(name=f"Chess Coach {key}", metadata={"plan": key})
    for interval, amount, suffix in (("month", p.price_eur, ""), ("year", p.price_year_eur, "_YEAR")):
        price = stripe.Price.create(product=prod.id, currency="eur", unit_amount=round(amount * 100),
                                    recurring={"interval": interval}, metadata={"plan": key})
        print(f"{p.stripe_price_env}{suffix}={price.id}")
