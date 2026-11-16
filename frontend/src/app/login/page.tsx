"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "../../lib/supabase";
import { LangSwitch, useLang } from "../../components/lang";
import { Logo } from "../../components/Logo";
import HeroBoard from "../../components/HeroBoard";
import { COPY } from "../../lib/landing-copy";

export default function LoginPage() {
  const router = useRouter();
  const { t, lang } = useLang();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [pass, setPass] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("mode") === "signup") setMode("signup");
    supabase.auth.getSession().then(({ data }) => { if (data.session) router.replace("/dashboard"); });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => { if (s) router.replace("/dashboard"); });
    return () => sub.subscription.unsubscribe();
  }, [router]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setMsg("");
    if (mode === "login") {
      const { error } = await supabase.auth.signInWithPassword({ email, password: pass });
      if (error) setMsg(error.message);
    } else {
      const { data, error } = await supabase.auth.signUp({ email, password: pass });
      if (error) setMsg(error.message);
      else if (!data.session) setMsg(t("checkConfirm"));
    }
    setBusy(false);
  };

  return (
    <div className="auth">
      <aside className="auth-art" aria-hidden="true">
        <div className="lp-aurora"><i /><i /></div>
        <Logo size={40} />
        <div className="auth-board"><HeroBoard /></div>
        <p className="auth-quote">{COPY[lang].hero.title}</p>
      </aside>
      <main className="auth-main">
        <div className="auth-top"><Link href="/" className="muted small">{t("backSite")}</Link><LangSwitch /></div>
        <form className="auth-card" onSubmit={submit}>
          <h1>{mode === "login" ? t("loginTitle") : t("signupTitle")}</h1>
          <p className="muted">{mode === "login" ? t("loginSub") : t("signupSub")}</p>
          <label>Email<input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
          <label>{t("password")}<input type="password" required minLength={6} autoComplete={mode === "login" ? "current-password" : "new-password"} value={pass} onChange={(e) => setPass(e.target.value)} /></label>
          {msg && <div className="note err" role="alert">{msg}</div>}
          <button className="btn btn-primary btn-lg" disabled={busy}>{mode === "login" ? t("login") : t("signup")}</button>
          <button type="button" className="linklike" onClick={() => { setMode(mode === "login" ? "signup" : "login"); setMsg(""); }}>
            {mode === "login" ? t("toSignup") : t("toLogin")}
          </button>
        </form>
      </main>
    </div>
  );
}
