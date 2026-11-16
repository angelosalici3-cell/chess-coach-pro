"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "../../lib/supabase";
import { LangSwitch, useLang } from "../../components/lang";
import { Logo } from "../../components/Logo";

export default function ResetPassword() {
  const router = useRouter();
  const { t } = useLang();
  const [ready, setReady] = useState(false);
  const [expired, setExpired] = useState(false);
  const [pass, setPass] = useState("");
  const [pass2, setPass2] = useState("");
  const [msg, setMsg] = useState("");
  const [ok, setOk] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const { data: sub } = supabase.auth.onAuthStateChange((e, s) => { if (e === "PASSWORD_RECOVERY" || (e === "SIGNED_IN" && s)) setReady(true); });
    // il link di recupero crea la sessione da solo: se dopo 2.5s non c'è, il link non è valido
    const timer = setTimeout(async () => {
      const { data } = await supabase.auth.getSession();
      if (data.session) setReady(true); else setExpired(true);
    }, 2500);
    return () => { sub.subscription.unsubscribe(); clearTimeout(timer); };
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg("");
    if (pass.length < 8) return setMsg(t("passMin"));
    if (pass !== pass2) return setMsg(t("passMismatch"));
    setBusy(true);
    const { error } = await supabase.auth.updateUser({ password: pass });
    setBusy(false);
    if (error) return setMsg(error.message);
    setOk(true); setMsg(t("passUpdated"));
    setTimeout(() => router.replace("/dashboard"), 1500);
  };

  return (
    <div className="auth" style={{ gridTemplateColumns: "1fr" }}>
      <main className="auth-main">
        <div className="auth-top"><Link href="/"><Logo size={34} /></Link><LangSwitch /></div>
        {expired && !ready ? (
          <div className="auth-card">
            <h1>{t("forgotTitle")}</h1>
            <div className="note err" role="alert">{t("linkExpired")}</div>
            <Link href="/login" className="btn btn-primary btn-lg">{t("requestNew")}</Link>
          </div>
        ) : !ready ? (
          <div className="auth-card"><p className="muted">{t("loading")}</p></div>
        ) : (
          <form className="auth-card" onSubmit={submit}>
            <h1>{t("newPassTitle")}</h1>
            <label>{t("newPass")}<input type="password" required minLength={8} autoComplete="new-password" value={pass} onChange={(e) => setPass(e.target.value)} /></label>
            <label>{t("confirmPass")}<input type="password" required minLength={8} autoComplete="new-password" value={pass2} onChange={(e) => setPass2(e.target.value)} /></label>
            {msg && <div className={"note " + (ok ? "ok" : "err")} role="alert">{msg}</div>}
            <button className="btn btn-primary btn-lg" disabled={busy || ok}>{t("savePass")}</button>
          </form>
        )}
      </main>
    </div>
  );
}
