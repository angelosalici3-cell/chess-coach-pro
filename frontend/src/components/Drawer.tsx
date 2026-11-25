"use client";
import { useEffect, useRef } from "react";
import Link from "next/link";
import { LANGS, Lang } from "../lib/i18n";
import { useLang } from "./lang";

const LANG_NAME: Record<Lang, string> = { it: "Italiano", en: "English", es: "Español" };

const D = {
  it: { menu: "Menu", close: "Chiudi menu", usage: "Piano e consumi", plan: "Piano", ai: "Lezioni AI questo mese", bonus: "Lezioni bonus", chess: "Account scacchi collegati",
        renew: "Rinnovo o scadenza", none: "Nessuna scadenza", free: "Piano gratuito: nessun rinnovo", data: "Dati account", email: "Email", since: "Iscritto dal",
        manage: "Gestione account", linked: "Account scacchi", plans: "Piano e abbonamento", del: "Elimina account", manual: "Manuale dell'app", manualHint: "Come usare l'app, passo dopo passo",
        lang: "Lingua", install: "Installa l'app", installHint: "Aggiungi EloRise alla schermata Home", diag: "Stato analisi", diagHint: "Controlla perché una partita non si analizza", promo: "Codici promo", coffee: "Offrimi un caffè", coffeeHint: "Sostieni EloRise con una donazione", logout: "Esci", site: "Sito", account: "Account", help: "Aiuto", app: "App", used: "usate", accounts: "Account scacchi", studio: "Studio creator", promos: "Codici promo", lessonsLbl: "Lezioni AI del mese", unlimited: "illimitate", upgrade: "Cambia piano" },
  en: { menu: "Menu", close: "Close menu", usage: "Plan and usage", plan: "Plan", ai: "AI lessons this month", bonus: "Bonus lessons", chess: "Linked chess accounts",
        renew: "Renewal or expiry", none: "No expiry", free: "Free plan: no renewal", data: "Account details", email: "Email", since: "Member since",
        manage: "Manage account", linked: "Chess accounts", plans: "Plan and subscription", del: "Delete account", manual: "App manual", manualHint: "How to use the app, step by step",
        lang: "Language", install: "Install the app", installHint: "Add EloRise to your Home screen", diag: "Analysis status", diagHint: "Check why a game isn't being analysed", promo: "Promo codes", coffee: "Buy me a coffee", coffeeHint: "Support EloRise with a donation", logout: "Log out", site: "Website", account: "Account", help: "Help", app: "App", used: "used", accounts: "Chess accounts", studio: "Creator studio", promos: "Promo codes", lessonsLbl: "AI lessons this month", unlimited: "unlimited", upgrade: "Change plan" },
  es: { menu: "Menú", close: "Cerrar menú", usage: "Plan y consumo", plan: "Plan", ai: "Lecciones IA este mes", bonus: "Lecciones extra", chess: "Cuentas de ajedrez vinculadas",
        renew: "Renovación o vencimiento", none: "Sin vencimiento", free: "Plan gratuito: sin renovación", data: "Datos de la cuenta", email: "Correo", since: "Miembro desde",
        manage: "Gestión de la cuenta", linked: "Cuentas de ajedrez", plans: "Plan y suscripción", del: "Eliminar cuenta", manual: "Manual de la app", manualHint: "Cómo usar la app, paso a paso",
        lang: "Idioma", install: "Instalar la app", installHint: "Añade EloRise a la pantalla de inicio", diag: "Estado del análisis", diagHint: "Comprueba por qué una partida no se analiza", promo: "Códigos promo", coffee: "Invítame a un café", coffeeHint: "Apoya EloRise con una donación", logout: "Salir", site: "Sitio web", account: "Cuenta", help: "Ayuda", app: "App", used: "usadas", accounts: "Cuentas de ajedrez", studio: "Estudio creador", promos: "Códigos promo", lessonsLbl: "Lecciones IA del mes", unlimited: "ilimitadas", upgrade: "Cambiar plan" },
} as const;


const P = {
  board: "M4 4h16v16H4zM4 12h16M12 4v16",
  card: "M3 6h18v12H3zM3 10h18",
  studio: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  tag: "M20 12l-8 8-9-9V3h8l9 9zM7.5 7.5h.01",
  cup: "M4 9h12v5a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V9zM16 10h2a2.5 2.5 0 0 1 0 5h-2M7 3v2M10 3v2M13 3v2",
  book: "M4 4h12a3 3 0 0 1 3 3v13H7a3 3 0 0 1-3-3V4zM8 8h7",
  down: "M12 4v11M7 11l5 5 5-5M5 20h14",
  pulse: "M3 12h4l2-6 4 12 2-6h6",
};
function Ico({ n }: { n: keyof typeof P }) {
  return <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={P[n]} /></svg>;
}
function Item({ href, onClick, icon, label, hint, tone, ext }: { href?: string; onClick: () => void; icon: keyof typeof P; label: string; hint?: string; tone?: "warm"; ext?: boolean }) {
  const inner = (<><span className={"dn-ic" + (tone ? " " + tone : "")}><Ico n={icon} /></span><span className="dn-tx"><b>{label}</b>{hint && <small>{hint}</small>}</span><span className="dn-chev" aria-hidden="true">›</span></>);
  return href ? <Link href={href} onClick={onClick} className="dn-item">{inner}</Link> : <button type="button" onClick={onClick} className="dn-item">{inner}</button>;
}

const LOC: Record<Lang, string> = { it: "it-IT", en: "en-GB", es: "es-ES" };
const fmt = (v: string | null | undefined, lang: Lang) => {
  if (!v) return "";
  const d = new Date(v.length === 10 ? v + "T12:00:00" : v);
  return isNaN(+d) ? "" : d.toLocaleDateString(LOC[lang], { day: "numeric", month: "long", year: "numeric" });
};

export default function Drawer({ open, onClose, me, lang, email, onGuide, onLogout }: {
  open: boolean; onClose: () => void; me: any; lang: Lang; email: string; onGuide: () => void; onLogout: () => void;
}) {
  const x = D[lang] as any;
  const { setLang } = useLang();
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", key);
    const id = setTimeout(() => panel.current?.querySelector<HTMLElement>("button, a")?.focus(), 50);
    return () => { document.body.style.overflow = prev; window.removeEventListener("keydown", key); clearTimeout(id); };
  }, [open, onClose]);

  const L = me?.lessons, P = me?.profiles;
  const pct = L?.limit ? Math.min(100, (100 * L.used) / L.limit) : 0;
  const paid = me?.tier && me.tier !== "Free";
  const renews = paid ? fmt(me.renews, lang) || x.none : x.free;
  const since = me?.member_since ? fmt(me.member_since, lang) : "";
  const go = (fn: () => void) => () => { onClose(); fn(); };
  return (
    <div className={"drawer-root" + (open ? " open" : "")} aria-hidden={!open}>
      <div className="drawer-back" onClick={onClose} />
      <aside className="drawer" ref={panel} role="dialog" aria-modal="true" aria-label={x.menu}>
        <div className="drawer-head">
          <span className="avatar" aria-hidden="true">{(email[0] || "?").toUpperCase()}</span>
          <div className="drawer-who"><b className="ellip">{email}</b>{since && <span className="muted small">{x.since} {since}</span>}</div>
          <button className="drawer-x" onClick={onClose} aria-label={x.close}>✕</button>
        </div>

        <div className="drawer-body dn">
          <Link href="/dashboard/plans" onClick={onClose} className="dn-plan" aria-label={x.upgrade}>
            <div className="dn-plan-top"><span className="pill-tier">{me?.tier || "…"}</span><span className="dn-plan-go">{x.upgrade} ›</span></div>
            <div className="dn-plan-row"><span>{x.lessonsLbl}</span><b>{L ? `${L.used}/${L.limit ?? x.unlimited}` : "…"}</b></div>
            {L?.limit ? <div className="bar"><div style={{ width: `${pct}%`, background: pct > 85 ? "var(--bad)" : "var(--ember)" }} /></div> : null}
            <div className="dn-plan-meta">{me ? renews : "…"}{me?.bonus_lessons > 0 ? ` · ${x.bonus}: ${me.bonus_lessons}` : ""}</div>
          </Link>

          <nav aria-label={x.account} className="dn-group">
            <h3>{x.account}</h3>
            <Item href="/dashboard/accounts" onClick={onClose} icon="board" label={x.accounts} hint={P ? `${P.used}/${P.limit}` : undefined} />
            <Item href="/dashboard/plans" onClick={onClose} icon="card" label={x.plans} />
            {me?.studio && <Item href="/dashboard/studio" onClick={onClose} icon="studio" label={x.studio} />}
            {me?.is_admin && <Item href="/dashboard/promo" onClick={onClose} icon="tag" label={x.promos} />}
          </nav>

          <nav aria-label={x.help} className="dn-group">
            <h3>{x.help}</h3>
            <Item onClick={go(onGuide)} icon="book" label={x.manual} />
            <Item onClick={go(() => window.dispatchEvent(new Event("pwa-open")))} icon="down" label={x.install} />
            <Item href="/dashboard/diag" onClick={onClose} icon="pulse" label={x.diag} />
          </nav>

          <Link href="/dashboard/support" onClick={onClose} className="dn-coffee">
            <span className="dn-ic warm"><Ico n="cup" /></span>
            <span className="dn-tx"><b>{x.coffee}</b><small>{x.coffeeHint}</small></span>
          </Link>

          <div className="dn-group">
            <h3>{x.lang}</h3>
            <div className="dn-lang" role="group" aria-label={x.lang}>
              {LANGS.map((l: Lang) => <button key={l} type="button" aria-pressed={lang === l} className={lang === l ? "on" : ""} onClick={() => setLang(l)}>{LANG_NAME[l]}</button>)}
            </div>
          </div>
        </div>

        <div className="drawer-foot dn-foot">
          <button className="btn-out" onClick={go(onLogout)}>{x.logout}</button>
          <Link href="/dashboard/plans#delete" onClick={onClose} className="small dn-del">{x.del}</Link>
        </div>
      </aside>
    </div>
  );
}
