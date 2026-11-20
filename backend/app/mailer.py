"""Email transazionali con Resend (HTTP): grazie per l'abbonamento e benvenuto con piani e video.
La mail di verifica dell'account la invia Supabase Auth (template in supabase/email-templates)."""
import logging
import os
import re


from core.plans import PLANS
from .db import sb

log = logging.getLogger("mailer")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
BRAND = "Chess Coach"
NAVY, NAVY2, ORANGE, TEXT, MUTED = "#0b0f1e", "#141a33", "#ff6b3d", "#eaeefc", "#9aa4c7"


def _video() -> tuple[str, str]:
    """Link al video e immagine di anteprima (le email non riproducono video: l'anteprima apre la pagina)."""
    url = os.environ.get("EMAIL_VIDEO_URL", "")
    thumb = os.environ.get("EMAIL_VIDEO_THUMB", "")
    if url and not thumb:
        m = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", url)
        if m:
            thumb = f"https://img.youtube.com/vi/{m.group(1)}/hqdefault.jpg"
    return url, thumb


COPY = {
    "it": {
        "subscribed_subject": "Benvenuto nel piano {plan}: ecco cosa hai sbloccato",
        "subscribed_title": "Grazie, sei nel piano {plan}",
        "subscribed_intro": "L'abbonamento è attivo. Da adesso hai tutto questo:",
        "welcome_subject": "Il tuo account è attivo: i piani e un video di 2 minuti",
        "welcome_title": "Benvenuto in Chess Coach",
        "welcome_intro": "Il tuo account è attivo. Collega Lichess o Chess.com e le tue partite vengono analizzate da sole: poi il Gran Maestro ti spiega gli errori che ripeti.",
        "video_title": "Guarda come funziona",
        "video_text": "In due minuti vedi tutte le funzioni dell'app.",
        "plans_title": "I piani",
        "month": "/mese", "year": "/anno", "open": "Apri Chess Coach", "plans_cta": "Vedi i piani",
        "acc": "{n} account collegati", "acc1": "1 account collegato",
        "les": "{n} lezioni del GM al mese", "lesU": "Lezioni del GM illimitate",
        "hist": "Fino a {n} partite di storico", "init": "{n} partite analizzate subito",
        "sync": "Download e analisi automatici ogni notte", "nosync": "Sincronizzazione manuale",
        "cards": "Carte da collezionare e allenamento sui tuoi errori",
        "manage": "Gestisci o disdici l'abbonamento quando vuoi dalla pagina Piani.",
        "foot": "Hai ricevuto questa email perché hai creato un account su Chess Coach.",
        "next_title": "Da dove partire", "next": ["Collega il tuo account Lichess o Chess.com", "Aspetta la prima analisi: la vedi in Home", "Apri una partita e chiedi la lezione del GM su un errore"],
    },
    "en": {
        "subscribed_subject": "Welcome to {plan}: here's what you unlocked",
        "subscribed_title": "Thank you, you're on {plan}",
        "subscribed_intro": "Your subscription is active. You now have all of this:",
        "welcome_subject": "Your account is active: the plans and a 2-minute video",
        "welcome_title": "Welcome to Chess Coach",
        "welcome_intro": "Your account is active. Connect Lichess or Chess.com and your games get analyzed on their own, then the Grandmaster explains the mistakes you keep repeating.",
        "video_title": "See how it works",
        "video_text": "Two minutes to see every feature of the app.",
        "plans_title": "The plans",
        "month": "/mo", "year": "/yr", "open": "Open Chess Coach", "plans_cta": "See the plans",
        "acc": "{n} linked accounts", "acc1": "1 linked account",
        "les": "{n} GM lessons per month", "lesU": "Unlimited GM lessons",
        "hist": "Up to {n} games of history", "init": "{n} games analyzed right away",
        "sync": "Automatic download and analysis every night", "nosync": "Manual sync",
        "cards": "Collectible cards and training on your own mistakes",
        "manage": "Manage or cancel your subscription any time from the Plans page.",
        "foot": "You received this email because you created a Chess Coach account.",
        "next_title": "Where to start", "next": ["Connect your Lichess or Chess.com account", "Wait for the first analysis: you'll see it on Home", "Open a game and ask the GM for a lesson on a mistake"],
    },
    "es": {
        "subscribed_subject": "Bienvenido al plan {plan}: esto es lo que has desbloqueado",
        "subscribed_title": "Gracias, ya estás en el plan {plan}",
        "subscribed_intro": "Tu suscripción está activa. Desde ahora tienes todo esto:",
        "welcome_subject": "Tu cuenta está activa: los planes y un vídeo de 2 minutos",
        "welcome_title": "Bienvenido a Chess Coach",
        "welcome_intro": "Tu cuenta está activa. Conecta Lichess o Chess.com y tus partidas se analizan solas; después el Gran Maestro te explica los errores que repites.",
        "video_title": "Mira cómo funciona",
        "video_text": "En dos minutos ves todas las funciones de la app.",
        "plans_title": "Los planes",
        "month": "/mes", "year": "/año", "open": "Abrir Chess Coach", "plans_cta": "Ver los planes",
        "acc": "{n} cuentas conectadas", "acc1": "1 cuenta conectada",
        "les": "{n} lecciones del GM al mes", "lesU": "Lecciones del GM ilimitadas",
        "hist": "Hasta {n} partidas de historial", "init": "{n} partidas analizadas al instante",
        "sync": "Descarga y análisis automáticos cada noche", "nosync": "Sincronización manual",
        "cards": "Cartas coleccionables y entrenamiento con tus errores",
        "manage": "Gestiona o cancela tu suscripción cuando quieras desde la página Planes.",
        "foot": "Recibes este correo porque creaste una cuenta en Chess Coach.",
        "next_title": "Por dónde empezar", "next": ["Conecta tu cuenta de Lichess o Chess.com", "Espera el primer análisis: lo ves en Inicio", "Abre una partida y pide al GM una lección sobre un error"],
    },
}


def _eur(v: float, lang: str) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".") if v == int(v) else f"{v:.2f}"
    return "€" + (s if lang == "en" else s.replace(".", ","))


def _benefits(tier: str, c: dict) -> list[str]:
    p = PLANS[tier]
    out = [c["acc1"] if p.profiles == 1 else c["acc"].format(n=p.profiles),
           c["les"].format(n=p.gm_lessons_month) if p.gm_lessons_month else c["lesU"],
           c["hist"].format(n=p.history_games), c["init"].format(n=p.initial_games),
           c["sync"] if p.auto_sync else c["nosync"], c["cards"]]
    return out


def _shell(lang: str, title: str, body: str, c: dict) -> str:
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title></head>
<body style="margin:0;padding:0;background:{NAVY};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{NAVY};"><tr><td align="center" style="padding:28px 12px;">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:{TEXT};">
<tr><td style="padding:0 4px 18px;font-size:20px;font-weight:700;color:{TEXT};letter-spacing:.2px;"><span style="color:{ORANGE};">&#9822;</span>&nbsp; {BRAND}</td></tr>
<tr><td style="background:{NAVY2};border-radius:16px;border-top:3px solid {ORANGE};padding:32px 28px;">
<h1 style="margin:0 0 12px;font-size:26px;line-height:1.25;color:{TEXT};">{title}</h1>
{body}
</td></tr>
<tr><td style="padding:18px 8px 0;font-size:12px;line-height:1.5;color:{MUTED};text-align:center;">{c["foot"]}<br>{BRAND}</td></tr>
</table></td></tr></table></body></html>"""


def _button(href: str, label: str) -> str:
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px 0 4px;"><tr><td style="background:{ORANGE};border-radius:10px;">'
            f'<a href="{href}" style="display:inline-block;padding:13px 26px;font-size:16px;font-weight:700;color:#fff;text-decoration:none;">{label}</a></td></tr></table>')


def _list(items: list[str]) -> str:
    rows = "".join(f'<tr><td style="padding:5px 10px 5px 0;color:{ORANGE};font-weight:700;vertical-align:top;">&#10003;</td><td style="padding:5px 0;font-size:15px;line-height:1.45;color:{TEXT};">{x}</td></tr>' for x in items)
    return f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:6px 0 0;">{rows}</table>'


def render_subscribed(lang: str, plan: str, interval: str = "month") -> tuple[str, str]:
    c = COPY.get(lang, COPY["it"]); p = PLANS[plan]
    price = _eur(p.price_year_eur, lang) + c["year"] if interval == "year" else _eur(p.price_eur, lang) + c["month"]
    body = (f'<p style="margin:0 0 6px;font-size:15px;line-height:1.55;color:{MUTED};">{c["subscribed_intro"]}</p>'
            f'<p style="margin:14px 0 4px;font-size:13px;color:{MUTED};">{plan} · {price}</p>'
            + _list(_benefits(plan, c))
            + _button(f"{FRONTEND_URL}/dashboard", c["open"])
            + f'<p style="margin:18px 0 0;font-size:13px;line-height:1.5;color:{MUTED};">{c["manage"]}</p>')
    return c["subscribed_subject"].format(plan=plan), _shell(lang, c["subscribed_title"].format(plan=plan), body, c)


def render_welcome(lang: str) -> tuple[str, str]:
    c = COPY.get(lang, COPY["it"])
    url, thumb = _video()
    video = ""
    if url:
        img = (f'<img src="{thumb}" width="504" alt="{c["video_title"]}" style="display:block;width:100%;max-width:504px;height:auto;border-radius:12px;border:0;">' if thumb
               else f'<div style="background:{NAVY};border-radius:12px;padding:46px 0;text-align:center;font-size:44px;color:{ORANGE};">&#9654;</div>')
        video = (f'<h2 style="margin:26px 0 6px;font-size:18px;color:{TEXT};">{c["video_title"]}</h2>'
                 f'<p style="margin:0 0 12px;font-size:14px;color:{MUTED};">{c["video_text"]}</p>'
                 f'<a href="{url}" style="text-decoration:none;display:block;">{img}</a>')
    cards = ""
    for k in ("Free", "Plus", "Pro", "Elite"):
        p = PLANS[k]
        price = "0 €" if k == "Free" else _eur(p.price_eur, lang) + c["month"]
        yr = "" if k == "Free" else f'<div style="font-size:12px;color:{MUTED};">{_eur(p.price_year_eur, lang)}{c["year"]}</div>'
        hot = f"border:1px solid {ORANGE};" if k == "Pro" else "border:1px solid #232b4d;"
        cards += (f'<tr><td style="padding:6px 0;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{NAVY};border-radius:12px;{hot}"><tr>'
                  f'<td style="padding:14px 16px;vertical-align:top;width:38%;"><div style="font-size:17px;font-weight:700;color:{TEXT};">{k}</div>'
                  f'<div style="font-size:15px;color:{ORANGE};font-weight:700;margin-top:2px;">{price}</div>{yr}</td>'
                  f'<td style="padding:14px 16px 14px 0;font-size:13px;line-height:1.55;color:{MUTED};">' + "<br>".join(_benefits(k, c)[:5]) + '</td></tr></table></td></tr>')
    body = (f'<p style="margin:0 0 6px;font-size:15px;line-height:1.55;color:{MUTED};">{c["welcome_intro"]}</p>'
            + _button(f"{FRONTEND_URL}/dashboard", c["open"])
            + video
            + f'<h2 style="margin:28px 0 8px;font-size:18px;color:{TEXT};">{c["next_title"]}</h2>' + _list(c["next"])
            + f'<h2 style="margin:28px 0 6px;font-size:18px;color:{TEXT};">{c["plans_title"]}</h2>'
            + f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{cards}</table>'
            + _button(f"{FRONTEND_URL}/dashboard/plans", c["plans_cta"]))
    return c["welcome_subject"], _shell(lang, c["welcome_title"], body, c)


def send(to: str, subject: str, html: str) -> bool:
    key = os.environ.get("RESEND_API_KEY", "")
    if not key:
        log.warning("RESEND_API_KEY mancante: email '%s' a %s non inviata", subject, to)
        return False
    try:
        import httpx
        r = httpx.post("https://api.resend.com/emails", timeout=15,
                       headers={"Authorization": f"Bearer {key}"},
                       json={"from": os.environ.get("MAIL_FROM", "Chess Coach <onboarding@resend.dev>"), "to": [to], "subject": subject, "html": html,
                             "reply_to": os.environ.get("MAIL_REPLY_TO") or None})
        if r.status_code >= 300:
            log.error("Resend %s: %s", r.status_code, r.text[:200])
        return r.status_code < 300
    except Exception:
        log.exception("invio email fallito")
        return False


def send_once(email: str, kind: str, template: str, lang: str = "it", **kw) -> None:
    """Invia una sola volta per (email, kind). Il registro viene scritto prima: se l'invio fallisce si toglie, così si riprova."""
    lang = lang if lang in COPY else "it"
    try:
        ins = sb.table("email_log").insert({"user_email": email, "kind": kind}).execute().data
    except Exception:
        return   # già inviata (chiave duplicata) o tabella assente (010 non eseguito)
    if not ins:
        return
    subject, html = render_welcome(lang) if template == "welcome" else render_subscribed(lang, kw.get("plan", "Pro"), kw.get("interval", "month"))
    if not send(email, subject, html):
        try:
            sb.table("email_log").delete().eq("user_email", email).eq("kind", kind).execute()
        except Exception:
            pass
