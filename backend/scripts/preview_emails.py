"""Genera le anteprime HTML delle email in ./email-preview (nessun invio). Uso: python -m scripts.preview_emails (da backend/)."""
import os, sys, types
os.environ.setdefault("SUPABASE_URL", "http://x"); os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "x")
sys.modules.setdefault("app.db", types.SimpleNamespace(sb=None))
sys.modules.setdefault("app", types.ModuleType("app")); sys.modules["app"].__path__ = [os.path.join(os.path.dirname(os.path.dirname(__file__)), "app")]
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import mailer  # noqa: E402
os.makedirs("email-preview", exist_ok=True)
for lang in ("it", "en", "es"):
    open(f"email-preview/welcome-{lang}.html", "w").write(mailer.render_welcome(lang)[1])
    open(f"email-preview/subscribed-{lang}.html", "w").write(mailer.render_subscribed(lang, "Pro", "month")[1])
print("ok")
