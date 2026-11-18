"use client";
import { useEffect, useRef } from "react";
import Link from "next/link";
import { Lang } from "../lib/i18n";
import { LangSelect } from "./lang";

const D = {
  it: { menu: "Menu", close: "Chiudi menu", usage: "Piano e consumi", plan: "Piano", ai: "Lezioni AI questo mese", bonus: "Lezioni bonus", chess: "Account scacchi collegati",
        renew: "Rinnovo o scadenza", none: "Nessuna scadenza", free: "Piano gratuito: nessun rinnovo", data: "Dati account", email: "Email", since: "Iscritto dal",
        manage: "Gestione account", linked: "Account scacchi", plans: "Piano e abbonamento", del: "Elimina account", manual: "Manuale dell'app", manualHint: "Come usare l'app, passo dopo passo",
        lang: "Lingua", promo: "Codici promo", logout: "Esci", site: "Sito", unlimited: "illimitate", upgrade: "Cambia piano" },
  en: { menu: "Menu", close: "Close menu", usage: "Plan and usage", plan: "Plan", ai: "AI lessons this month", bonus: "Bonus lessons", chess: "Linked chess accounts",
        renew: "Renewal or expiry", none: "No expiry", free: "Free plan: no renewal", data: "Account details", email: "Email", since: "Member since",
        manage: "Manage account", linked: "Chess accounts", plans: "Plan and subscription", del: "Delete account", manual: "App manual", manualHint: "How to use the app, step by step",
        lang: "Language", promo: "Promo codes", logout: "Log out", site: "Website", unlimited: "unlimited", upgrade: "Change plan" },
  es: { menu: "Menú", close: "Cerrar menú", usage: "Plan y consumo", plan: "Plan", ai: "Lecciones IA este mes", bonus: "Lecciones extra", chess: "Cuentas de ajedrez vinculadas",
        renew: "Renovación o vencimiento", none: "Sin vencimiento", free: "Plan gratuito: sin renovación", data: "Datos de la cuenta", email: "Correo", since: "Miembro desde",
        manage: "Gestión de la cuenta", linked: "Cuentas de ajedrez", plans: "Plan y suscripción", del: "Eliminar cuenta", manual: "Manual de la app", manualHint: "Cómo usar la app, paso a paso",
        lang: "Idioma", promo: "Códigos promo", logout: "Salir", site: "Sitio web", unlimited: "ilimitadas", upgrade: "Cambiar plan" },
} as const;

const LOC: Record<Lang, string> = { it: "it-IT", en: "en-GB", es: "es-ES" };
const fmt = (v: string | null | undefined, lang: Lang) => {
  if (!v) return "";
  const d = new Date(v.length === 10 ? v + "T12:00:00" : v);
  return isNaN(+d) ? "" : d.toLocaleDateString(LOC[lang], { day: "numeric", month: "long", year: "numeric" });
};

export default function Drawer({ open, onClose, me, lang, email, onGuide, onLogout }: {
  open: boolean; onClose: () => void; me: any; lang: Lang; email: string; onGuide: () => void; onLogout: () => void;
}) {
  const x = D[lang];
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
  const renews = me?.tier && me.tier !== "Free" ? fmt(me.renews, lang) || x.none : x.free;
  const go = (fn: () => void) => () => { onClose(); fn(); };
  return (
    <div className={"drawer-root" + (open ? " open" : "")} aria-hidden={!open}>
      <div className="drawer-back" onClick={onClose} />
      <aside className="drawer" ref={panel} role="dialog" aria-modal="true" aria-label={x.menu}>
        <div className="drawer-head">
          <span className="avatar" aria-hidden="true">{(email[0] || "?").toUpperCase()}</span>
          <div className="drawer-who"><b className="ellip">{email}</b><span className="pill-tier">{me?.tier || "…"}</span></div>
          <button className="drawer-x" onClick={onClose} aria-label={x.close}>✕</button>
        </div>

        <div className="drawer-body">
          <section>
            <h3>{x.usage}</h3>
            <div className="dr-row"><span>{x.ai}</span><b>{L ? `${L.used}/${L.limit ?? x.unlimited}` : "…"}</b></div>
            {L?.limit ? <div className="bar"><div style={{ width: `${pct}%`, background: pct > 85 ? "var(--bad)" : "var(--ember)" }} /></div> : null}
            {me?.bonus_lessons > 0 && <div className="dr-row"><span>{x.bonus}</span><b>{me.bonus_lessons}</b></div>}
            <div className="dr-row"><span>{x.chess}</span><b>{P ? `${P.used}/${P.limit}` : "…"}</b></div>
            <div className="dr-row"><span>{x.renew}</span><b>{me ? renews : "…"}</b></div>
            <Link href="/dashboard/plans" onClick={onClose} className="btn-out dr-btn">{x.upgrade}</Link>
          </section>

          <section>
            <h3>{x.data}</h3>
            <div className="dr-row"><span>{x.email}</span><b className="ellip">{email}</b></div>
            {me?.member_since && fmt(me.member_since, lang) && <div className="dr-row"><span>{x.since}</span><b>{fmt(me.member_since, lang)}</b></div>}
          </section>

          <section>
            <h3>{x.manage}</h3>
            <Link href="/dashboard/accounts" onClick={onClose} className="dr-link">{x.linked}</Link>
            <Link href="/dashboard/plans" onClick={onClose} className="dr-link">{x.plans}</Link>
            <Link href="/dashboard/plans#delete" onClick={onClose} className="dr-link dr-danger">{x.del}</Link>
            {me?.is_admin && <Link href="/dashboard/promo" onClick={onClose} className="dr-link">{x.promo}</Link>}
          </section>

          <section>
            <h3>{x.manual}</h3>
            <p className="muted small" style={{ margin: "0 0 .5rem" }}>{x.manualHint}</p>
            <button className="btn-out dr-btn" onClick={go(onGuide)}>? {x.manual}</button>
          </section>

          <section>
            <h3>{x.lang}</h3>
            <LangSelect full />
          </section>
        </div>

        <div className="drawer-foot">
          <button className="btn-out" onClick={go(onLogout)}>{x.logout}</button>
          <Link href="/" onClick={onClose} className="small muted">← {x.site}</Link>
        </div>
      </aside>
    </div>
  );
}
