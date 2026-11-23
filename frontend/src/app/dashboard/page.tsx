"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import InitBanner from "../../components/InitBanner";
import type { Lang } from "../../lib/i18n";

const SYNC = {
  it: { dl: "Scaricate {n} nuove partite.", none: "Nessuna partita nuova da scaricare.", run: "Analizzo {d} di {t} partite…", queued: "C'è già un'analisi in corso: i risultati compaiono man mano.", done: "Fatto: {o} partite analizzate.", fail: "{f} partite non analizzate. Riprova tra poco: se il problema resta, le ritento stanotte." },
  en: { dl: "Downloaded {n} new games.", none: "No new games to download.", run: "Analyzing {d} of {t} games…", queued: "An analysis is already running: results appear as they are ready.", done: "Done: {o} games analyzed.", fail: "{f} games could not be analyzed. Try again shortly: if it persists, I'll retry tonight." },
  es: { dl: "Descargadas {n} partidas nuevas.", none: "No hay partidas nuevas que descargar.", run: "Analizando {d} de {t} partidas…", queued: "Ya hay un análisis en curso: los resultados aparecen poco a poco.", done: "Hecho: {o} partidas analizadas.", fail: "{f} partidas sin analizar. Inténtalo de nuevo en breve: si sigue, las reintento esta noche." },
} as const;
import { useApp } from "../../components/app";
import { MultiLineChart } from "../../components/Charts";
import { K, tr } from "../../lib/i18n";
import TodayCard from "../../components/TodayCard";
import TimeCard from "../../components/TimeCard";
import PatternCard from "../../components/PatternCard";

const SPEED_COLOR: Record<string, string> = { bullet: "#ff5d8f", blitz: "#ffb84d", rapid: "#4ee3b0", classical: "#5aa9ff", daily: "#b7c0dc", other: "#8d97b8" };
const RANGES: [K, number | null][] = [["range30", 30], ["range90", 90], ["range365", 365], ["rangeAll", null]];

const DASHES = [undefined, "7 5", "2 5", "10 4 2 4"];
const plat = (src: string) => (src === "lichess" ? "Lichess" : "Chess.com");

/** Un solo grafico: i filtri Account e Ritmo passano dalla vista generale (tutte le linee) al dettaglio (una sola). */
function RatingCard({ accounts }: { accounts: any[] }) {
  const { t, lang } = useApp();
  const [acc, setAcc] = useState<string>("all");
  // grafico di partenza: il ritmo con più partite registrate (poi si cambia coi filtri)
  const [speed, setSpeed] = useState<string>(() => {
    const tot: Record<string, number> = {};
    accounts.forEach((a) => a.series.forEach((s: any) => { tot[s.speed] = (tot[s.speed] || 0) + (s.n ?? s.points.length); }));
    return Object.entries(tot).sort((x, y) => y[1] - x[1])[0]?.[0] || "all";
  });
  const [range, setRange] = useState<number | null>(null);
  const aKey = (a: any) => a.source + ":" + a.username;
  const label = (sp: string) => tr(("speed" + sp[0].toUpperCase() + sp.slice(1)) as K, lang);
  const inAcc = accounts.filter((a) => acc === "all" || aKey(a) === acc);
  const speeds = Array.from(new Set(inAcc.flatMap((a) => a.series.map((s: any) => s.speed)))) as string[];
  const sp = speed === "all" || speeds.includes(speed) ? speed : "all";
  const multiAcc = inAcc.length > 1;
  const series = inAcc.flatMap((a) => {
    const idx = accounts.indexOf(a);
    return a.series.filter((s: any) => sp === "all" || s.speed === sp).map((s: any) => ({
      key: aKey(a) + ":" + s.speed,
      label: multiAcc ? `${plat(a.source)} · ${label(s.speed)}` : label(s.speed),
      color: SPEED_COLOR[s.speed] || "#8d97b8", dash: DASHES[idx % DASHES.length], points: s.points,
    }));
  });
  return (
    <div className="card chartcard">
      <div className="row"><b className="ctitle">{t("rating")}</b>
        <div className="lang" role="group">{RANGES.map(([k, v]) => <button key={k} className={range === v ? "on" : ""} onClick={() => setRange(v)}>{t(k)}</button>)}</div>
      </div>
      <div className="filters">
        {accounts.length > 1 && (
          <div className="fgroup" role="group" aria-label={t("accountFilter")}>
            <span className="muted small">{t("accountFilter")}</span>
            <div className="chips" style={{ margin: 0 }}>
              <button className={"chip" + (acc === "all" ? " on" : "")} onClick={() => setAcc("all")} aria-pressed={acc === "all"}>{t("allAccounts")}</button>
              {accounts.map((a) => (
                <button key={aKey(a)} className={"chip" + (acc === aKey(a) ? " on" : "")} onClick={() => setAcc(aKey(a))} aria-pressed={acc === aKey(a)}>{plat(a.source)} · {a.username}</button>
              ))}
            </div>
          </div>
        )}
        <div className="fgroup" role="group" aria-label={t("speedFilter")}>
          <span className="muted small">{t("speedFilter")}</span>
          <div className="chips" style={{ margin: 0 }}>
            <button className={"chip" + (sp === "all" ? " on" : "")} onClick={() => setSpeed("all")} aria-pressed={sp === "all"}>{t("allSpeeds")}</button>
            {speeds.map((k) => (
              <button key={k} className={"chip" + (sp === k ? " on" : "")} style={{ borderColor: sp === k ? SPEED_COLOR[k] : undefined }} onClick={() => setSpeed(k)} aria-pressed={sp === k}>
                <i className="dotc" style={{ background: SPEED_COLOR[k] }} />{label(k)}
              </button>
            ))}
          </div>
        </div>
      </div>
      <MultiLineChart series={series} days={range} />
      <div className="loss-legend">
        {series.map((s: any) => (
          <span key={s.key}>
            <svg width="26" height="8" aria-hidden="true" style={{ verticalAlign: "middle", marginRight: ".4rem" }}><line x1="0" y1="4" x2="26" y2="4" stroke={s.color} strokeWidth="2.6" strokeDasharray={s.dash} /></svg>
            {s.label} <b style={{ color: "var(--ice)" }}>{s.points[s.points.length - 1].r}</b>
          </span>
        ))}
      </div>
      <p className="muted small" style={{ margin: ".4rem 0 0" }}>{t("ratingDaily")}</p>
    </div>
  );
}

export default function Home() {
  const { call, t, lang, me, refreshMe, bust } = useApp();
  const [s, setS] = useState<any>(null);
  const [err, setErr] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);

  const ck = me?.email ? "c:stats:" + me.email : "";
  const load = () => call("/stats").then((d) => { setS(d); if (ck) try { localStorage.setItem(ck, JSON.stringify(d)); } catch {} }).catch((e) => setErr(e.message));
  useEffect(() => {   // ultimi dati salvati subito, poi quelli aggiornati
    if (!ck) return;
    try { const c = localStorage.getItem(ck); if (c) setS((x: any) => x || JSON.parse(c)); } catch {}
  }, [ck]);
  useEffect(() => { load(); }, [call]); // eslint-disable-line

  const [job, setJob] = useState<any>(null);
  const SY = SYNC[lang as Lang] || SYNC.it;
  const fm = (x: string, v: Record<string, any>) => Object.keys(v).reduce((a, k) => a.split(`{${k}}`).join(String(v[k])), x);

  // Segue l'analisi avviata dal pulsante: aggiorna il contatore finché non finisce
  useEffect(() => {
    if (!job || (job.state !== "running" && job.state !== "queued")) return;
    const t = setTimeout(async () => {
      try {
        const j = await call("/sync/status");
        setJob((p: any) => ({ ...j, imported: p?.imported ?? j.imported }));
        if (j.state === "done") { bust(); load(); refreshMe(); }
      } catch {}
    }, 2500);
    return () => clearTimeout(t);
  }, [job, call]); // eslint-disable-line

  const sync = async () => {
    setBusy(true); setErr(""); setInfo(""); setJob(null);
    try {
      const r = await call("/sync", { method: "POST" });
      setJob(r.job);
      if (r.job?.state === "done") { bust(); load(); refreshMe(); }
    } catch (e: any) { setErr(e.message); }
    setBusy(false);
  };

  return (
    <>
      <div className="pagehead">
        <h1>{t("navHome")}</h1>
        <button className="btn btn-primary" onClick={sync} disabled={busy}>{busy ? t("syncing") : t("sync")}</button>
      </div>
      <p className="muted small" style={{ marginTop: 0 }}>{me?.auto_sync ? t("autoSyncOn") : <>{t("autoSyncOff")}. <Link href="/dashboard/plans" className="accent">{t("navPlans")}</Link></>}</p>
      {job && (
        <div className="card init-banner" role="status" aria-live="polite">
          <b>{job.imported > 0 ? fm(SY.dl, { n: job.imported }) : SY.none}</b>
          {job.total > 0 && (job.state === "running" || job.state === "queued") && (
            <>
              <div className="muted small" style={{ margin: ".25rem 0" }}>{job.state === "queued" ? SY.queued : fm(SY.run, { d: job.done, t: job.total })}</div>
              <div className="bar"><div style={{ width: `${job.state === "queued" ? 6 : Math.round((100 * job.done) / job.total)}%`, background: "var(--ember)", transition: "width .6s" }} /></div>
            </>
          )}
          {job.state === "done" && job.total > 0 && <div className="muted small" style={{ marginTop: ".25rem" }}>{fm(SY.done, { o: job.ok })}</div>}
          {job.state === "done" && job.failed > 0 && <div className="note err" style={{ marginTop: ".5rem" }}>{fm(SY.fail, { f: job.failed })}{job.error ? ` (${job.error})` : ""}</div>}
        </div>
      )}
      <InitBanner onDone={() => { bust(); load(); refreshMe(); }} />
      <TodayCard />
      {info && <div className="note">{info}</div>}
      {err && <div className="note err">{err}</div>}

      {s && s.games === 0 && <div className="card muted">{t("noData")} <Link href="/dashboard/accounts" className="accent">{t("navAccounts")}</Link></div>}
      {s && s.games > 0 && (
        <>
          <div className="kpis">
            <div><span>{t("statGames")}</span><b>{s.games}</b></div>
            <div><span>{t("statWin")}</span><b>{s.win_rate ?? "—"}{s.win_rate != null && <small>%</small>}</b></div>
            <div><span>{t("statAcc")}</span><b>{s.accuracy ?? "—"}{s.accuracy != null && <small>%</small>}</b></div>
          </div>
          <div className="wdl-line" title={`${t("wins")} ${s.w} · ${t("draws")} ${s.d} · ${t("losses")} ${s.l}`}>
            <div className="wdl"><div style={{ flex: s.w, background: "var(--mint)" }} /><div style={{ flex: s.d, background: "var(--mute)" }} /><div style={{ flex: s.l, background: "var(--bad)" }} /></div>
            <span className="muted small">{t("wins")} {s.w} · {t("draws")} {s.d} · {t("losses")} {s.l}</span>
          </div>
          <PatternCard />
          {s.rating.length > 0 && <RatingCard accounts={s.rating} />}
          <TimeCard />
        </>
      )}
    </>
  );
}
