"use client";
import { useEffect, useState } from "react";
import { createClient, Session } from "@supabase/supabase-js";
import { api } from "../lib/api";
import { LANGS, Lang, tr } from "../lib/i18n";

// supabase-js salva e rinnova la sessione da solo: niente più logout quando il telefono si blocca.
const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!);

export default function Home() {
  const [lang, setLang] = useState<Lang>("it");
  const [session, setSession] = useState<Session | null>(null);
  const [me, setMe] = useState<any>(null);
  const [games, setGames] = useState<any[]>([]);
  const [email, setEmail] = useState("");
  const [pass, setPass] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem("lang") as Lang | null;
    if (saved) setLang(saved);
    else setLang((navigator.language.slice(0, 2) as Lang) in { it: 1, en: 1, es: 1 } ? (navigator.language.slice(0, 2) as Lang) : "en");
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!session) return;
    api("/me", session.access_token).then(setMe).catch(() => {});
    api("/games", session.access_token).then(setGames).catch(() => {});
  }, [session]);

  const changeLang = (l: Lang) => { setLang(l); localStorage.setItem("lang", l); };
  const login = async () => { const { error } = await supabase.auth.signInWithPassword({ email, password: pass }); setMsg(error?.message || ""); };
  const signup = async () => {
    const { data, error } = await supabase.auth.signUp({ email, password: pass });
    setMsg(error?.message || (data.session ? "" : tr("checkConfirm", lang)));
  };

  return (
    <div className="wrap">
      <div className="row">
        <h1>♟️ Chess Coach Pro</h1>
        <select value={lang} onChange={(e) => changeLang(e.target.value as Lang)}>
          {LANGS.map((l) => <option key={l} value={l}>{l.toUpperCase()}</option>)}
        </select>
      </div>
      <p className="muted">{tr("tagline", lang)}</p>

      {!session ? (
        <div className="card">
          <input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input placeholder={tr("password", lang)} type="password" value={pass} onChange={(e) => setPass(e.target.value)} />
          <div className="row"><button className="primary" onClick={login}>{tr("login", lang)}</button><button onClick={signup}>{tr("signup", lang)}</button></div>
          {msg && <p className="muted">{msg}</p>}
        </div>
      ) : (
        <>
          <div className="card row">
            <span>{session.user.email} · <b>{me?.tier}</b></span>
            <button onClick={() => supabase.auth.signOut()}>{tr("logout", lang)}</button>
          </div>
          {me && (
            <div className="card muted">
              {tr("accounts", lang)}: {me.profiles.used}/{me.profiles.limit} · {tr("lessons", lang)}: {me.lessons.used}/{me.lessons.limit ?? tr("unlimited", lang)}
            </div>
          )}
          <h2>{tr("games", lang)}</h2>
          {games.length === 0 && <p className="muted">{tr("empty", lang)}</p>}
          {games.map((g) => (
            <div key={g.id} className="card row">
              <span>{g.white} vs {g.black} <span className="muted">· {g.opening_name || ""}</span></span>
              <span className="muted">{g.result}</span>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
