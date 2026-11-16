"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { createClient, Session } from "@supabase/supabase-js";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api } from "../lib/api";
import { K, LANGS, Lang, tr } from "../lib/i18n";

export const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!);

type Ctx = { me: any; lang: Lang; t: (k: K) => string; call: <T = any>(path: string, init?: RequestInit) => Promise<T>; refreshMe: () => void };
const C = createContext<Ctx>(null as any);
export const useApp = () => useContext(C);

export function AppShell({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<Lang>("it");
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [me, setMe] = useState<any>(null);
  const [email, setEmail] = useState("");
  const [pass, setPass] = useState("");
  const [msg, setMsg] = useState("");
  const path = usePathname();

  useEffect(() => {
    const saved = localStorage.getItem("lang") as Lang | null;
    const nav = navigator.language.slice(0, 2) as Lang;
    setLang(saved || (LANGS.includes(nav) ? nav : "en"));
    supabase.auth.getSession().then(({ data }) => { setSession(data.session); setReady(true); });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  const token = session?.access_token;
  const call = useCallback(<T,>(p: string, init?: RequestInit) => api<T>(p, token || "", init), [token]);
  const refreshMe = useCallback(() => { if (token) api("/me", token).then(setMe).catch(() => {}); }, [token]);
  useEffect(() => { refreshMe(); }, [refreshMe]);

  const t = (k: K) => tr(k, lang);
  const changeLang = (l: Lang) => { setLang(l); localStorage.setItem("lang", l); };
  const login = async () => { const { error } = await supabase.auth.signInWithPassword({ email, password: pass }); setMsg(error?.message || ""); };
  const signup = async () => {
    const { data, error } = await supabase.auth.signUp({ email, password: pass });
    setMsg(error?.message || (data.session ? "" : t("checkConfirm")));
  };

  const head = (
    <div className="row">
      <h1>♟️ Chess Coach Pro</h1>
      <select value={lang} onChange={(e) => changeLang(e.target.value as Lang)}>
        {LANGS.map((l) => <option key={l} value={l}>{l.toUpperCase()}</option>)}
      </select>
    </div>
  );

  if (!ready) return <div className="wrap muted">…</div>;
  if (!session)
    return (
      <div className="wrap">
        {head}
        <p className="muted">{t("tagline")}</p>
        <div className="card">
          <input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input placeholder={t("password")} type="password" value={pass} onChange={(e) => setPass(e.target.value)} />
          <div className="row"><button className="primary" onClick={login}>{t("login")}</button><button onClick={signup}>{t("signup")}</button></div>
          {msg && <p className="muted">{msg}</p>}
        </div>
      </div>
    );

  const links: [string, K][] = [["/", "navHome"], ["/games", "navGames"], ["/lessons", "navLessons"], ["/accounts", "navAccounts"], ["/plans", "navPlans"]];
  return (
    <C.Provider value={{ me, lang, t, call, refreshMe }}>
      <div className="wrap">
        {head}
        <nav className="nav">
          {links.map(([h, k]) => (
            <Link key={h} href={h} className={(h === "/" ? path === "/" : path.startsWith(h)) ? "on" : ""}>{t(k)}</Link>
          ))}
          <span className="grow" />
          <span className="muted small">{session.user.email} · <b>{me?.tier}</b></span>
          <button onClick={() => supabase.auth.signOut()}>{t("logout")}</button>
        </nav>
        {me && (
          <div className="card muted small">
            {t("accounts")}: {me.profiles.used}/{me.profiles.limit} · {t("lessons")}: {me.lessons.used}/{me.lessons.limit ?? t("unlimited")}
          </div>
        )}
        {children}
      </div>
    </C.Provider>
  );
}
