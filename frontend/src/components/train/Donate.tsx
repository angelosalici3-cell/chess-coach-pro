"use client";
import { useState } from "react";
import { useApp } from "../app";

const T = {
  it: { h: "Sostieni EloRise", p: "EloRise cresce grazie a chi lo usa. Una donazione una tantum finanzia il motore di analisi e i nuovi allenamenti. Come grazie ricevi lo scudo Sostenitore, da condividere.", o: "Altro importo", go: "Dona {n} €", thanks: "Grazie! Il tuo scudo Sostenitore è nella scheda Scudi.", err: "Non è partito il pagamento. Riprova." },
  en: { h: "Support EloRise", p: "EloRise grows thanks to the people who use it. A one-time donation funds the analysis engine and new training. As a thank you, you get the Supporter shield to share.", o: "Other amount", go: "Donate €{n}", thanks: "Thank you! Your Supporter shield is in the Shields tab.", err: "Payment did not start. Try again." },
  es: { h: "Apoya EloRise", p: "EloRise crece gracias a quienes lo usan. Una donación única financia el motor de análisis y nuevos entrenamientos. Como gracias, recibes el escudo Mecenas para compartir.", o: "Otro importe", go: "Donar {n} €", thanks: "¡Gracias! Tu escudo Mecenas está en la pestaña Escudos.", err: "El pago no se inició. Inténtalo de nuevo." },
} as const;

export default function Donate() {
  const { call, lang } = useApp();
  const t = T[lang] || T.it;
  const [n, setN] = useState(5);
  const [custom, setCustom] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const thanks = typeof window !== "undefined" && new URLSearchParams(window.location.search).get("thanks") === "1";
  const amount = custom ? Math.max(1, Math.min(500, Math.round(Number(custom) || 0))) : n;
  const go = async () => {
    setBusy(true); setErr("");
    try { const r = await call("/billing/donate", { method: "POST", body: JSON.stringify({ amount, lang }) }); window.location.href = r.url; }
    catch { setErr(t.err); setBusy(false); }
  };
  return (
    <section id="support" className="card don">
      <h2 className="jy-h" style={{ margin: 0 }}>{t.h}</h2>
      {thanks ? <div className="note ok">{t.thanks}</div> : null}
      <p className="muted" style={{ margin: ".4rem 0 .8rem", maxWidth: "62ch" }}>{t.p}</p>
      <div className="chips">
        {[3, 5, 10].map((v) => <button key={v} className={"chip" + (!custom && n === v ? " on" : "")} onClick={() => { setN(v); setCustom(""); }}>{v} €</button>)}
        <input className="don-in" inputMode="numeric" placeholder={t.o} value={custom} onChange={(e) => setCustom(e.target.value.replace(/\D/g, "").slice(0, 3))} aria-label={t.o} />
      </div>
      <button className="btn btn-primary" style={{ marginTop: ".8rem" }} disabled={busy} onClick={go}>{t.go.replace("{n}", String(amount))}</button>
      {err && <div className="note err">{err}</div>}
    </section>
  );
}
