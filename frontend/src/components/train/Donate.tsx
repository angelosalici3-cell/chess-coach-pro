"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "../app";
import Shield from "../Shield";
import { tc } from "../../lib/train-copy";
import { cardFonts, shareOrSave } from "../../lib/cardExport";
import { makeShieldPng } from "../../lib/shieldShare";

const TH = {
  it: { h: "Grazie di cuore!", p: "Con {n} € ci aiuti a tenere acceso il motore che analizza ogni tua partita e a costruire nuovi allenamenti. Questo scudo è il nostro modo di dirti grazie: è tuo, e puoi mostrarlo.", name: "Scudo Sostenitore", tiers: ["Bronzo", "Argento", "Oro"], next: "Ancora {x} € e il tuo scudo diventa {t}.", top: "Hai il massimo livello: sei tra le persone che reggono EloRise.", share: "Condividi lo scudo", see: "Vedi i tuoi scudi", sign: "Angelo, EloRise", wait: "Sto preparando il tuo scudo…", close: "Chiudi", show: "Mostra", late: "Il pagamento è arrivato, ma lo scudo non è ancora comparso. Riapri questa pagina tra qualche minuto: lo troverai qui e in Profilo > Traguardi.", back: "Il tuo scudo Sostenitore", total: "Totale donato", again: "Vuoi aggiungere altro?", under: "Da 5 € ricevi lo scudo Sostenitore: bronzo da 5 €, argento da 10 €, oro da 20 €.", gets: "Con questo importo ricevi lo scudo {t}." },
  en: { h: "Thank you, truly!", p: "With €{n} you help keep the engine running that analyses every one of your games, and fund new training. This shield is our way of saying thanks: it is yours to show.", name: "Supporter shield", tiers: ["Bronze", "Silver", "Gold"], next: "€{x} more and your shield becomes {t}.", top: "You are at the top level: you help keep EloRise going.", share: "Share the shield", see: "See your shields", sign: "Angelo, EloRise", wait: "Preparing your shield…", close: "Close", show: "Show", late: "Your payment went through, but the shield has not shown up yet. Reopen this page in a few minutes: you will find it here and under Profile > Milestones.", back: "Your Supporter shield", total: "Total donated", again: "Want to add more?", under: "From €5 you get the Supporter shield: bronze from €5, silver from €10, gold from €20.", gets: "This amount gets you the {t} shield." },
  es: { h: "¡Gracias de corazón!", p: "Con {n} € ayudas a mantener el motor que analiza cada una de tus partidas y a crear nuevos entrenamientos. Este escudo es nuestra forma de darte las gracias: es tuyo y puedes enseñarlo.", name: "Escudo Mecenas", tiers: ["Bronce", "Plata", "Oro"], next: "Con {x} € más tu escudo pasa a {t}.", top: "Tienes el nivel máximo: ayudas a sostener EloRise.", share: "Compartir el escudo", see: "Ver tus escudos", sign: "Angelo, EloRise", wait: "Preparando tu escudo…", close: "Cerrar", show: "Mostrar", late: "El pago llegó, pero el escudo aún no ha aparecido. Vuelve a abrir esta página en unos minutos: lo encontrarás aquí y en Perfil > Logros.", back: "Tu escudo Mecenas", total: "Total donado", again: "¿Quieres añadir más?", under: "Desde 5 € recibes el escudo Mecenas: bronce desde 5 €, plata desde 10 €, oro desde 20 €.", gets: "Con este importe recibes el escudo de {t}." },
} as const;
const CONF = ["#ff6b3d", "#ffd56a", "#4ee3b0", "#5aa9ff", "#ff5d8f"];
const TIERS = [5, 10, 20];   // soglie dello scudo Sostenitore: bronzo, argento, oro (stesse del backend)

function Thanks({ thanks }: { thanks: boolean }) {
  const { call, lang } = useApp();
  const t = TH[lang] || TH.it;
  const [sh, setSh] = useState<any>(null);
  const [tries, setTries] = useState(0);
  const [burst, setBurst] = useState<{ dx: number; dy: number; rot: number; c: string }[]>([]);
  const [msg, setMsg] = useState("");
  const [failed, setFailed] = useState(false);
  const [closed, setClosed] = useState(false);
  const ck = (v: number) => "elo:thx:closed:" + v;
  useEffect(() => { if (sh) { try { setClosed(localStorage.getItem(ck(sh.value)) === "1" && !thanks); } catch {} } }, [sh, thanks]);
  const close = () => {
    setClosed(true); setBurst([]);
    try { localStorage.setItem(ck(sh.value), "1"); } catch {}
    try { const u = new URL(window.location.href); u.searchParams.delete("thanks"); u.searchParams.delete("session_id"); window.history.replaceState(null, "", u.pathname + u.search); } catch {}
  };
  useEffect(() => {
    let live = true;
    const sid = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("session_id") : null;
    const read = () => call("/achievements", { cache: "no-store" }).then((a: any) => {   // no-store: la memoria dell'app darebbe l'elenco di prima
      if (!live) return;
      const x = (a.shields || []).find((y: any) => y.id === "supporter");
      if (x) setSh(x); else if (thanks && tries < 40) setTimeout(() => live && setTries((n) => n + 1), 3000);
      else if (thanks) setFailed(true);
    }).catch(() => { if (live && thanks && tries < 40) setTimeout(() => live && setTries((n) => n + 1), 3000); });
    // al primo giro conferma il pagamento direttamente con Stripe: non si aspetta il webhook
    if (thanks && sid && tries === 0) call("/billing/donate/confirm", { method: "POST", body: JSON.stringify({ session_id: sid }) }).catch(() => {}).finally(read);
    else read();
    return () => { live = false; };
  }, [call, tries, thanks]);
  useEffect(() => {
    if (!sh || !thanks) return;
    try { if (sessionStorage.getItem("elo:thx")) return; sessionStorage.setItem("elo:thx", "1"); } catch {}
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    setBurst(Array.from({ length: 46 }, (_, i) => ({ dx: (Math.random() - 0.5) * 520, dy: -120 + Math.random() * 520, rot: Math.random() * 720 - 360, c: CONF[i % CONF.length] })));
    const id = setTimeout(() => setBurst([]), 1800);
    return () => clearTimeout(id);
  }, [sh, thanks]);
  if (!sh && !thanks) return null;
  if (!sh) return <section className="card thx thx-wait"><div className="thx-ph" aria-hidden="true" /><div><h2>{t.h}</h2><p className="muted">{failed ? t.late : t.wait}</p></div></section>;
  const tier = Math.max(1, sh.tier), tname = t.tiers[tier - 1], nextAt = TIERS[sh.tier] ?? null;
  const share = async () => {
    try {
      const png = await makeShieldPng({ id: "supporter", tier, title: t.name, tierLabel: tname, detail: `${sh.value} €`, brand: "CHESS COACH" }, await cardFonts());
      const r = await shareOrSave(png, `elorise-supporter-${tier}.png`, `${t.name} · ${tname}`);
      setMsg(r === "shared" ? tc("cardShared", lang) : r === "saved" ? tc("cardSaved", lang) : "");
    } catch { setMsg(tc("cardFail", lang)); }
  };
  if (closed) return (
    <button type="button" className={"card thx-mini t" + tier} onClick={() => setClosed(false)} aria-label={t.show}>
      <span className="thx-mini-sh"><Shield id="supporter" tier={tier} /></span>
      <span className="thx-mini-tx"><b>{t.name} · {tname}</b><small>{t.total}: {sh.value} €</small></span>
      <span className="thx-mini-go">{t.show}</span>
    </button>
  );
  return (
    <section className={"card thx t" + tier} aria-live="polite">
      <button type="button" className="thx-x" onClick={close} aria-label={t.close}>
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
      </button>
      {burst.length > 0 && <div className="burst" aria-hidden="true">{burst.map((b, i) => <i key={i} style={{ background: b.c, ["--dx" as string]: `${b.dx}px`, ["--dy" as string]: `${b.dy}px`, ["--rot" as string]: `${b.rot}deg` }} />)}</div>}
      <div className="thx-shield"><Shield id="supporter" tier={tier} /></div>
      <div className="thx-tag">{t.name} · {tname}</div>
      <h2>{thanks ? t.h : t.back}</h2>
      {thanks ? <p>{t.p.replace("{n}", String(sh.value))}</p> : <p className="muted">{t.total}: <b>{sh.value} €</b></p>}
      <p className="thx-next muted small">{nextAt ? t.next.replace("{x}", String(nextAt - sh.value)).replace("{t}", t.tiers[tier]) : t.top}</p>
      <div className="thx-btns">
        <button className="btn btn-primary" onClick={share}>{t.share}</button>
        <Link className="btn btn-ghost" href="/dashboard/rewards?tab=badges">{t.see}</Link>
      </div>
      {msg && <div className="muted small">{msg}</div>}
      {thanks && <div className="thx-sign">{t.sign}</div>}
    </section>
  );
}

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
    <>
    <Thanks thanks={thanks} />
    <section id="support" className="card don">
      <h2 className="jy-h" style={{ margin: 0 }}>{thanks ? TH[lang]?.again || TH.it.again : t.h}</h2>
      <p className="muted" style={{ margin: ".4rem 0 .8rem", maxWidth: "62ch" }}>{t.p}</p>
      <div className="chips">
        {[5, 10, 20].map((v) => <button key={v} className={"chip" + (!custom && n === v ? " on" : "")} onClick={() => { setN(v); setCustom(""); }}>{v} €</button>)}
        <input className="don-in" inputMode="numeric" placeholder={t.o} value={custom} onChange={(e) => setCustom(e.target.value.replace(/\D/g, "").slice(0, 3))} aria-label={t.o} />
      </div>
      <p className="muted small don-hint">{(() => { const th = TH[lang] || TH.it, k = TIERS.filter((x) => amount >= x).length; return k ? th.gets.replace("{t}", th.tiers[k - 1].toLowerCase()) : th.under; })()}</p>
      <button className="btn btn-primary" style={{ marginTop: ".4rem" }} disabled={busy} onClick={go}>{t.go.replace("{n}", String(amount))}</button>
      {err && <div className="note err">{err}</div>}
    </section>
    </>
  );
}
