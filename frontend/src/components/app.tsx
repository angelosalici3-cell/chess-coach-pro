"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Session } from "@supabase/supabase-js";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "../lib/api";
import { supabase } from "../lib/supabase";
import { K, Lang } from "../lib/i18n";
import { LangSwitch, useLang } from "./lang";
import { Logo } from "./Logo";
import Onboarding from "./Onboarding";
import { ui } from "../lib/onboarding-copy";

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
  { href: "/dashboard/accounts", k: "navAccounts", icon: I("M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1") },
  { href: "/dashboard/plans", k: "navPlans", icon: I("M3 7h18v12H3zM3 11h18M7 15h3") },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { lang, t } = useLang();
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [me, setMe] = useState<any>(null);
  const [guide, setGuide] = useState(false);
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
  const refreshMe = useCallback(() => { if (token) api("/me", token).then(setMe).catch(() => {}); }, [token]);
  useEffect(() => { refreshMe(); }, [refreshMe]);

  // al primo accesso la guida si apre da sola (una volta per utente); poi si riapre dal pulsante Guida
  const ukey = session?.user?.email ? `onb:${session.user.email}` : "";
  useEffect(() => {
    if (!ukey || !me || path !== "/dashboard") return;
    let seen = "1";
    try { seen = localStorage.getItem(ukey) || ""; } catch {}
    if (!seen) { const id = setTimeout(() => setGuide(true), 700); return () => clearTimeout(id); }
  }, [ukey, me, path]);
  const closeGuide = () => { setGuide(false); try { localStorage.setItem(ukey, "1"); } catch {} };

  const logout = () => supabase.auth.signOut().then(() => router.replace("/"));

  if (!ready || !session) return <div className="splash"><Logo size={48} text={false} /></div>;

  const on = (h: string) => (h === "/dashboard" ? path === "/dashboard" : path.startsWith(h));
  const lessonsPct = me?.lessons?.limit ? Math.min(100, (100 * me.lessons.used) / me.lessons.limit) : 0;
  return (
    <C.Provider value={{ me, lang, t, call, refreshMe, openGuide: () => setGuide(true) }}>
      <div className="shell">
        <aside className="side">
          <Link href="/" aria-label="Home"><Logo size={34} /></Link>
          <nav aria-label="App">
            {NAV.map((n) => <Link key={n.href} href={n.href} className={on(n.href) ? "on" : ""}>{n.icon}<span>{t(n.k)}</span></Link>)}
          </nav>
          <div className="side-foot">
            {me && (
              <div className="meters">
                <div className="small muted">{t("accounts")}: {me.profiles.used}/{me.profiles.limit}</div>
                <div className="small muted" style={{ marginTop: ".5rem" }}>{t("lessons")}: {me.lessons.used}/{me.lessons.limit ?? t("unlimited")}</div>
                {me.lessons.limit && <div className="bar"><div style={{ width: `${lessonsPct}%`, background: lessonsPct > 85 ? "var(--bad)" : "var(--ember)" }} /></div>}
              </div>
            )}
            <div className="who"><span className="pill-tier">{me?.tier || "…"}</span><span className="small muted ellip">{session.user.email}</span></div>
            <div className="row"><LangSwitch /><button className="btn-out" onClick={logout}>{t("logout")}</button></div>
            <button className="btn-guide" onClick={() => setGuide(true)}>? {ui("guide", lang)}</button>
            <Link href="/" className="small muted">← {t("homeSite")}</Link>
          </div>
        </aside>
        <header className="topbar">
          <Link href="/" aria-label="Home"><Logo size={30} /></Link>
          <div className="row"><LangSwitch /><button className="btn-out" onClick={() => setGuide(true)}>? {ui("guide", lang)}</button><button className="btn-out" onClick={logout}>{t("logout")}</button></div>
        </header>
        <main className="content">{children}</main>
        <nav className="tabbar" aria-label="App">
          {NAV.map((n) => <Link key={n.href} href={n.href} className={on(n.href) ? "on" : ""}>{n.icon}<span>{t(n.k)}</span></Link>)}
        </nav>
      </div>
      {guide && <Onboarding lang={lang} me={me} onClose={closeGuide} />}
    </C.Provider>
  );
}
