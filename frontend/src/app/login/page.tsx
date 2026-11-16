"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "../../lib/supabase";
import { LangSwitch, useLang } from "../../components/lang";
import { Logo } from "../../components/Logo";
import HeroBoard from "../../components/HeroBoard";
import { GoogleIcon, DiscordIcon } from "../../components/OAuthIcons";
import { COPY } from "../../lib/landing-copy";

type Mode = "login" | "signup" | "forgot";

export default function LoginPage() {
  const router = useRouter();
  const { t, lang } = useLang();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [pass, setPass] = useState("");
  const [agree, setAgree] = useState(false);
  const [msg, setMsg] = useState("");
  const [ok, setOk] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("mode") === "signup") setMode("signup");
    supabase.auth.getSession().then(({ data }) => { if (data.session) router.replace("/dashboard"); });
    const { data: sub } = supabase.auth.onAuthStateChange((e, s) => { if (s && e !== "PASSWORD_RECOVERY") router.replace("/dashboard"); });
    return () => sub.subscription.unsubscribe();
  }, [router]);

  const oauth = async (provider: "google" | "discord") => {
    setMsg("");
    const { error } = await supabase.auth.signInWithOAuth({ provider, options: { redirectTo: `${window.location.origin}/dashboard` } });
    if (error) setMsg(error.message);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setMsg(""); setOk(false);
    if (mode === "login") {
      const { error } = await supabase.auth.signInWithPassword({ email, password: pass });
      if (error) setMsg(error.message);
    } else if (mode === "signup") {
      const { data, error } = await supabase.auth.signUp({ email, password: pass });
      if (error) setMsg(error.message);
      else if (!data.session) { setMsg(t("checkConfirm")); setOk(true); }
    } else {
      const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo: `${window.location.origin}/reset-password` });
      if (error) setMsg(error.message); else { setMsg(t("linkSent")); setOk(true); }
    }
    setBusy(false);
  };

  const go = (m: Mode) => { setMode(m); setMsg(""); setOk(false); };
  const title = mode === "login" ? t("loginTitle") : mode === "signup" ? t("signupTitle") : t("forgotTitle");
  const sub = mode === "login" ? t("loginSub") : mode === "signup" ? t("signupSub") : t("forgotSub");

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
          <h1>{title}</h1>
          <p className="muted">{sub}</p>
          {mode !== "forgot" && (
            <>
              <div className="oauth">
                <button type="button" className="btn-oauth" onClick={() => oauth("google")}><GoogleIcon />{t("continueGoogle")}</button>
                <button type="button" className="btn-oauth" onClick={() => oauth("discord")}><DiscordIcon />{t("continueDiscord")}</button>
              </div>
              <div className="or">{t("orWith")}</div>
            </>
          )}
          <label>Email<input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
          {mode !== "forgot" && (
            <label>{t("password")}<input type="password" required minLength={mode === "signup" ? 8 : 6} autoComplete={mode === "login" ? "current-password" : "new-password"} value={pass} onChange={(e) => setPass(e.target.value)} /></label>
          )}
          {mode === "login" && <button type="button" className="linklike" onClick={() => go("forgot")}>{t("forgot")}</button>}
          {mode === "signup" && (
            <label className="check">
              <input type="checkbox" required checked={agree} onChange={(e) => setAgree(e.target.checked)} />
              <span>{t("acceptPre")} <Link href="/terms" target="_blank">{t("terms")}</Link> {t("and")} <Link href="/privacy" target="_blank">{t("privacy")}</Link>.</span>
            </label>
          )}
          {msg && <div className={"note " + (ok ? "ok" : "err")} role="alert">{msg}</div>}
          <button className="btn btn-primary btn-lg" disabled={busy}>{mode === "login" ? t("login") : mode === "signup" ? t("signup") : t("sendLink")}</button>
          {mode !== "forgot" && <p className="muted small" style={{ margin: 0 }}>{mode === "login" ? t("oauthConsent") : ""}</p>}
          {mode === "forgot"
            ? <button type="button" className="linklike" onClick={() => go("login")}>{t("backLogin")}</button>
            : <button type="button" className="linklike" onClick={() => go(mode === "login" ? "signup" : "login")}>{mode === "login" ? t("toSignup") : t("toLogin")}</button>}
        </form>
      </main>
    </div>
  );
}
