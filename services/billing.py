import stripe
import streamlit as st
from services.supabase_client import get_client
from services.analytics import track_context, capture_event, Events

def _init_stripe():
    stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY", "")

def get_or_create_customer(user_email: str) -> str | None:
    """Crea o recupera un customer Stripe per l'utente."""
    _init_stripe()
    if not stripe.api_key:
        return None
        
    client = get_client()
    try:
        # Cerca se esiste già
        res = client.table("config_utenti").select("stripe_customer_id").eq("user_email", user_email).execute()
        if res.data and res.data[0].get("stripe_customer_id"):
            return res.data[0]["stripe_customer_id"]
            
        # Crea un nuovo customer su Stripe
        customer = stripe.Customer.create(email=user_email)
        
        # Salva l'ID nel DB
        client.table("config_utenti").update({
            "stripe_customer_id": customer.id
        }).eq("user_email", user_email).execute()
        
        return customer.id
    except Exception as e:
        st.error(f"Errore creazione cliente Stripe: {e}")
        return None

def create_checkout_session(user_email: str, plan: str) -> str | None:
    """Crea una sessione di checkout Stripe e ritorna l'URL."""
    _init_stripe()
    
    price_id = (
        st.secrets.get("STRIPE_PRO_PRICE_ID") if plan == "pro"
        else st.secrets.get("STRIPE_DIAMOND_PRICE_ID")
    )
    if not price_id:
        st.error(f"Price ID per il piano {plan} non configurato in secrets.toml")
        return None

    base_url = st.secrets.get("APP_BASE_URL", "http://localhost:8501")
    customer_id = get_or_create_customer(user_email)
    
    if not customer_id:
        st.error("Impossibile creare il cliente Stripe.")
        return None

    with track_context(user_email):
        capture_event(Events.UPGRADE_CLICKED, {"plan": plan})
        capture_event(Events.CHECKOUT_STARTED, {"plan": plan})

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{base_url}/?checkout=success",
            cancel_url=f"{base_url}/?checkout=cancel",
            allow_promotion_codes=True,
            metadata={"plan": plan, "user_email": user_email},
        )
        return session.url
    except Exception as e:
        st.error(f"Errore Stripe Checkout: {e}")
        return None

def create_billing_portal(user_email: str) -> str | None:
    """Apre il portale di gestione abbonamento Stripe."""
    _init_stripe()
    base_url = st.secrets.get("APP_BASE_URL", "http://localhost:8501")
    
    client = get_client()
    try:
        res = client.table("config_utenti").select("stripe_customer_id").eq("user_email", user_email).execute()
        if not res.data or not res.data[0].get("stripe_customer_id"):
            st.warning("Nessun abbonamento attivo da gestire.")
            return None
            
        portal = stripe.billing_portal.Session.create(
            customer=res.data[0]["stripe_customer_id"],
            return_url=base_url,
        )
        return portal.url
    except Exception as e:
        st.error(f"Errore portale Stripe: {e}")
        return None
