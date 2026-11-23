"use client";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { Session } from "@supabase/supabase-js";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "../lib/api";
import { supabase } from "../lib/supabase";
import { K, Lang } from "../lib/i18n";
import { LangSelect, useLang } from "./lang";
import Drawer from "./Drawer";
import Intro from "./Intro";
import { Logo } from "./Logo";
import Onboarding from "./Onboarding";
import Pwa from "./Pwa";
import CardCelebration from "./CardCelebration";

type Ctx = { me: any; lang: Lang; t: (k: K) => string; call: <T = any>(path: string, init?: RequestInit) => Promise<T>; refreshMe: () => void; openGuide: () => void; bust: () => void };
const C = createContext<Ctx>(null as any);
export const useApp = () => useContext(C);

const I = (d: string) => (
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={d} /></svg>
);
const NAV: { href: string; k: K; icon: React.ReactNode; match?: string[]; hero?: boolean }[] = [
  { href: "/dashboard", k: "navHome", icon: I("M3 11l9-8 9 8M5 10v10h14V10") },
  { href: "/dashboard/games", k: "navAnalysis", icon: I("M4 19V9M10 19V5M16 19v-7M22 19H2"), match: ["/dashboard/games", "/dashboard/openings", "/dashboard/lessons"] },
  { href: "/dashboard/play", k: "navPlay", icon: I("M7 4l13 8-13 8z"), hero: true },
  { href: "/dashboard/train", k: "navTrain", icon: I("M13 2L4 14h7l-1 8 9-12h-7z") },
  { href: "/dashboard/rewards", k: "navRewards", icon: I("M8 21h8M12 17v4M7 4h10v5a5 5 0 01-10 0zM17 5h3v2a3 3 0 01-3 3M7 5H4v2a3 3 0 003 3") },
];

const tMenu: Record<Lang, string> = { it: "Menu", en: "Menu", es: "Menú" };

/** Percorsi di sola lettura che si possono tenere in memoria (non quelli che cambiano a ogni richiesta, come il prossimo puzzle). */
const CACHEABLE = /^\/(stats(\/time)?|lessons|games(\/[\w-]+(\/time)?)?|openings\/mine|achievements|train\/overview|patterns|profiles|cards|admin\/promo)$/;

export function AppShell({ children }: { children: React.ReactNode }) {
  const { lang, t } = useLang();
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [me, setMe] = useState<any>(null);
  const [guide, setGuide] = useState(false);
  const [menu, setMenu] = useState(false);
  const path = usePathname();
  const router = useRouter();

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => { setSession(data.session); setReady(true); });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);
  useEffect(() => { if (ready && !session) router.replace("/login"); }, [ready, session, router]);

  const token = session?.access_token;
  // Dati già scaricati restano in memoria: cambiando pagina compaiono subito e si aggiornano in sottofondo.
  // Qualsiasi modifica (POST, DELETE...) svuota la memoria, così dopo una sincronizzazione o una lezione si legge il dato nuovo.
  const store = useRef(new Map<string, { t: number; d: any }>());
  const lsKey = (p: string) => "c:api:" + (session?.user?.email || "") + ":" + p;
  const call = useCallback(async <T,>(p: string, init?: RequestInit): Promise<T> => {
    const method = (init?.method || "GET").toUpperCase();
    if (method !== "GET") {
      if (p === "/cards/seen") {   // segnare le carte come viste non deve buttare via tutta la memoria: si aggiorna solo l'album
        const c = store.current.get("/cards");
        if (c) store.current.set("/cards", { t: c.t, d: { ...c.d, new: 0, cards: (c.d.cards || []).map((x: any) => ({ ...x, new: false })) } });
        return api<T>(p, token || "", init);
      }
      store.current.clear();
      try { Object.keys(localStorage).filter((k) => k.startsWith("c:api:")).forEach((k) => localStorage.removeItem(k)); } catch {}
      return api<T>(p, token || "", init);
    }
    if (!CACHEABLE.test(p) || init?.cache === "no-store") return api<T>(p, token || "", init);
    let hit = store.current.get(p);
    if (!hit) {   // dopo una nuova apertura dell'app: ultimi dati salvati sul telefono, poi si aggiornano in sottofondo
      try { const raw = localStorage.getItem(lsKey(p)); if (raw) { hit = { t: 0, d: JSON.parse(raw) }; store.current.set(p, hit); } } catch {}
    }
    const fresh = () => api<T>(p, token || "", init).then((d) => {
      store.current.set(p, { t: Date.now(), d });
      try { const raw = JSON.stringify(d); if (raw.length < 600000) localStorage.setItem(lsKey(p), raw); } catch {}
      return d;
    });
    if (hit && hit.t === 0) {   // dato del giro precedente: se il server risponde entro 1,2 s mostra quello nuovo, altrimenti subito il salvato
      const stale = hit.d as T;
      const f = fresh();
      f.catch(() => {});
      return Promise.race([f, new Promise<T>((r) => setTimeout(() => r(stale), 1200))]).catch(() => stale);
    }
    if (hit) { if (Date.now() - hit.t > 15000) fresh().catch(() => {}); return hit.d as T; }
    return fresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, session?.user?.email]);
  const bust = useCallback(() => {
    store.current.clear();
    try { Object.keys(localStorage).filter((k) => k.startsWith("c:api:")).forEach((k) => localStorage.removeItem(k)); } catch {}
  }, []);
  const email = session?.user?.email || "";
  const refreshMe = useCallback(() => {
    if (token) api("/me?lang=" + lang, token).then((d) => { setMe(d); try { localStorage.setItem("c:me:" + email, JSON.stringify(d)); } catch {} }).catch(() => {});
  }, [token, email, lang]);
  useEffect(() => {   // all'apertura mostra subito gli ultimi dati salvati; quelli nuovi li sostituiscono appena arrivano
    if (!email) return;
    try { const c = localStorage.getItem("c:me:" + email); if (c) setMe((m: any) => m || JSON.parse(c)); } catch {}
  }, [email]);
  useEffect(() => { refreshMe(); }, [refreshMe]);
  useEffect(() => {   // appena l'app è aperta scarica in sottofondo le schermate principali, una alla volta: quando le apri sono già pronte
    if (!token) return;
    let stop = false;
    const id = setTimeout(async () => {
      for (const p of ["/stats", "/games", "/cards", "/achievements", "/train/overview", "/patterns"]) {
        if (stop) return;
        try { await call(p); } catch {}
      }
    }, 1200);
    return () => { stop = true; clearTimeout(id); };
  }, [token, call]);
  useEffect(() => {   // codice promo arrivato da un link (?ref=): lo collega all'account una sola volta
    if (!token) return;
    let code = "";
    try { const r = JSON.parse(localStorage.getItem("ref") || "null"); if (r?.code && Date.now() - r.t < 30 * 864e5) code = r.code; } catch {}
    if (!code) return;
    api("/promo/claim", token, { method: "POST", body: JSON.stringify({ code }) })
      .then(() => { try { localStorage.removeItem("ref"); } catch {} refreshMe(); })
      .catch(() => {});
  }, [token, refreshMe]);
  useEffect(() => {   // ogni minuto, a scheda visibile: una carta nuova appare senza dover ricaricare la pagina
    const id = setInterval(() => { if (document.visibilityState === "visible") refreshMe(); }, 60000);
    return () => clearInterval(id);
  }, [refreshMe]);

  // al primo accesso la guida si apre da sola (una volta per utente); poi si riapre dal pulsante Guida
  const ukey = session?.user?.email ? `onb:${session.user.email}` : "";
  useEffect(() => {
    if (!ukey || !me || path !== "/dashboard") return;
    let seen = "1";
    try { seen = localStorage.getItem(ukey) || ""; } catch {}
    if (!seen) { const id = setTimeout(() => setGuide(true), 700); return () => clearTimeout(id); }
  }, [ukey, me, path]);
  const closeGuide = () => { setGuide(false); try { localStorage.setItem(ukey, "1"); } catch {} };

  useEffect(() => { setMenu(false); }, [path]);
  const closeMenu = useCallback(() => setMenu(false), []);
  const logout = () => {
    store.current.clear();
    try { Object.keys(localStorage).filter((k) => k.startsWith("c:")).forEach((k) => localStorage.removeItem(k)); } catch {}
    return supabase.auth.signOut().then(() => router.replace("/"));
  };

  if (!ready || !session) return <><Intro ready={false} /></>;

  const on = (n: { href: string; match?: string[] }) => (n.href === "/dashboard" ? path === "/dashboard" : (n.match || [n.href]).some((m) => path.startsWith(m)));
  const burger = (
    <button className="burger" onClick={() => setMenu(true)} aria-label={tMenu[lang]} aria-expanded={menu}>
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
    </button>
  );
  return (
    <>
    <Intro ready={!!me} />
    <C.Provider value={{ me, lang, t, call, refreshMe, bust, openGuide: () => setGuide(true) }}>
      <div className="shell">
        <aside className="side">
          <Link href="/" aria-label="Home"><Logo size={34} /></Link>
          <nav aria-label="App">
            {NAV.map((n) => <Link key={n.href} href={n.href} className={(on(n) ? "on" : "") + (n.hero ? " hero" : "")}>{n.icon}<span>{t(n.k)}</span></Link>)}
          </nav>
          <div className="side-foot">
            <div className="who"><span className="pill-tier">{me?.tier || "…"}</span><span className="small muted ellip">{session.user.email}</span></div>
            <button className="btn-out side-menu" onClick={() => setMenu(true)}>☰ {tMenu[lang]}</button>
          </div>
        </aside>
        <header className="topbar">
          <div className="row">{burger}<Link href="/" aria-label="Home"><Logo size={28} /></Link></div>
          <LangSelect />
        </header>
        <main className="content">{children}</main>
        <nav className="tabbar" aria-label="App">
          {NAV.map((n) => <Link key={n.href} href={n.href} className={(on(n) ? "on" : "") + (n.hero ? " hero" : "")}>{n.hero ? <b className="tab-play">{n.icon}</b> : n.icon}<span>{t(n.k)}</span></Link>)}
        </nav>
      </div>
      <Drawer open={menu} onClose={closeMenu} me={me} lang={lang} email={session.user.email || ""} onGuide={() => setGuide(true)} onLogout={logout} />
      <Pwa lang={lang} />
      <CardCelebration />
      {guide && <Onboarding lang={lang} me={me} onClose={closeGuide} />}
    </C.Provider>
    </>
  );
}
