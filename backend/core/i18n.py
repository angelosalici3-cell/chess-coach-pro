"""Traduzioni IT/EN/ES. Fallback: lingua richiesta -> inglese -> chiave."""
LANGS = {"it": "Italiano", "en": "English", "es": "Español"}

STRINGS = {
    "tagline": {
        "it": "Il tuo Gran Maestro AI, sempre con te",
        "en": "Your AI Grandmaster, always by your side",
        "es": "Tu Gran Maestro IA, siempre contigo"},
    "login": {"it": "Accedi", "en": "Log in", "es": "Iniciar sesión"},
    "signup": {"it": "Crea account", "en": "Sign up", "es": "Crear cuenta"},
    "logout": {"it": "Esci", "en": "Log out", "es": "Cerrar sesión"},
    "nav_dashboard": {"it": "Dashboard", "en": "Dashboard", "es": "Panel"},
    "nav_games": {"it": "Le mie partite", "en": "My games", "es": "Mis partidas"},
    "nav_training": {"it": "Allenamento", "en": "Training", "es": "Entrenamiento"},
    "nav_plans": {"it": "Piani", "en": "Plans", "es": "Planes"},
    "accounts_counter": {
        "it": "Account collegati: {used}/{limit}",
        "en": "Linked accounts: {used}/{limit}",
        "es": "Cuentas vinculadas: {used}/{limit}"},
    "lessons_counter": {
        "it": "Lezioni GM questo mese: {used}/{limit}",
        "en": "GM lessons this month: {used}/{limit}",
        "es": "Lecciones GM este mes: {used}/{limit}"},
    "unlimited": {"it": "illimitate", "en": "unlimited", "es": "ilimitadas"},
    "already_analyzed": {
        "it": "Partita già analizzata: la riapro senza rifare l'analisi.",
        "en": "Game already analyzed: opening it without re-running the analysis.",
        "es": "Partida ya analizada: se abre sin repetir el análisis."},
    "gm_failed": {
        "it": "Il GM non ha risposto: la lezione non è stata conteggiata.",
        "en": "The GM did not answer: this lesson was not counted.",
        "es": "El GM no respondió: la lección no se ha contado."},
    "delete_account": {
        "it": "Elimina il mio account", "en": "Delete my account",
        "es": "Eliminar mi cuenta"},
    "move_label": {"it": "Mossa {n}", "en": "Move {n}", "es": "Jugada {n}"},
}


def t(key: str, lang: str = "it", **kw) -> str:
    entry = STRINGS.get(key, {})
    text = entry.get(lang) or entry.get("en") or key
    return text.format(**kw) if kw else text
