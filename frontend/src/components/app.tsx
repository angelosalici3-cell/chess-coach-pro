"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Session } from "@supabase/supabase-js";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "../lib/api";
import { supabase } from "../lib/supabase";
import { K, Lang } from "../lib/i18n";
import { LangSelect, useLang } from "./lang";
import Drawer from "./Drawer";
import { Logo } from "./Logo";
import Onboarding from "./Onboarding";
import Pwa from "./Pwa";
import CardCelebration from "./CardCelebration";

type Ctx = { me: any; lang: Lang; t: (k: K) => string; call: <T = any>(path: string, init?: RequestInit) => Promise<T>; refreshMe: () => void; openGuide: () => void };
const C = createContext<Ctx>(null as any);
export const useApp = () => useContext(C);

const I = (d: string) => (
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={d} /></svg>
);
const NAV: { href: string; k: K; icon: React.ReactNode }[] = [
  { href: "/dashboard", k: "navHome", icon: I("M3 11l9-8 9 8M5 10v10h14V10") },
  { href: "/dashboard/games", k: "navGames", icon: I("M4 4h16v16H4zM4 12h16M12 4v16") },
  { href: "/dashboard/lessons", k: "navLessons", icon: I("M4 5a2 2 0 012-2h12v16H6a2 2 0 00-2 2zM8 7h6M8 11h6") },
  { href: "/dashboard/openings", k: "navOpenings", icon: I("M6 4v16M6 8h6a4 4 0 014 4v8M6 14h10") },
  { href: "/dashboard/train", k: "navTrain", icon: I("M13 2L4 14h7l-1 8 9-12h-7z") },
];

const tMenu: Record<Lang, string> = { it: "Menu", en: "Menu", es: "Menú" };

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
  const call = useCallback(<T,>(p: string, init?: RequestInit) => api<T>(p, token || "", init), [token]);
  const email = session?.user?.email || "";
  const refreshMe = useCallback(() => {
    if (token) api("/me", token).then((d) => { setMe(d); try { localStorage.setItem("c:me:" + email, JSON.stringify(d)); } catch {} }).catch(() => {});
  }, [token, email]);
  useEffect(() => {   // all'apertura mostra subito gli ultimi dati salvati; quelli nuovi li sostituiscono appena arrivano
    if (!email) return;
    try { const c = localStorage.getItem("c:me:" + email); if (c) setMe((m: any) => m || JSON.parse(c)); } catch {}
  }, [email]);
  useEffect(() => { refreshMe(); }, [refreshMe]);
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
    try { Object.keys(localStorage).filter((k) => k.startsWith("c:")).forEach((k) => localStorage.removeItem(k)); } catch {}
    return supabase.auth.signOut().then(() => router.replace("/"));
  };

  if (!ready || !session) return <div className="splash"><Logo size={48} text={false} /></div>;

  const on = (h: string) => (h === "/dashboard" ? path === "/dashboard" : path.startsWith(h));
  const burger = (
    <button className="burger" onClick={() => setMenu(true)} aria-label={tMenu[lang]} aria-expanded={menu}>
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
    </button>
  );
  return (
    <C.Provider value={{ me, lang, t, call, refreshMe, openGuide: () => setGuide(true) }}>
      <div className="shell">
        <aside className="side">
          <Link href="/" aria-label="Home"><Logo size={34} /></Link>
          <nav aria-label="App">
            {NAV.map((n) => <Link key={n.href} href={n.href} className={on(n.href) ? "on" : ""}>{n.icon}<span>{t(n.k)}</span></Link>)}
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
          {NAV.map((n) => <Link key={n.href} href={n.href} className={on(n.href) ? "on" : ""}>{n.icon}<span>{t(n.k)}</span></Link>)}
        </nav>
      </div>
      <Drawer open={menu} onClose={closeMenu} me={me} lang={lang} email={session.user.email || ""} onGuide={() => setGuide(true)} onLogout={logout} />
      <Pwa lang={lang} />
      <CardCelebration />
      {guide && <Onboarding lang={lang} me={me} onClose={closeGuide} />}
    </C.Provider>
  );
}
