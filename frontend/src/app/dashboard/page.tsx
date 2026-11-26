"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import InitBanner from "../../components/InitBanner";
import type { Lang } from "../../lib/i18n";

const SYNC = {
  it: { lim: "Hai analizzato {d} partite oggi (limite Free: {m}). Con Plus, Pro o Elite scarichi e analizzi tutte le tue partite, anche di notte.", dl: "Scaricate {n} nuove partite.", none: "Tutto aggiornato.", upto: "Tutto aggiornato: le tue {n} partite sono già qui e analizzate.", have: "Le tue {n} partite sono già qui: le stiamo analizzando.", empty: "Non ci sono ancora partite per i tuoi account. Controlla il nome utente o gioca qualche partita.", run: "Analizzo {d} di {t} partite…", queued: "C'è già un'analisi in corso: i risultati compaiono man mano.", done: "Fatto: {o} partite analizzate.", fail: "{f} partite non analizzate. Riprova tra poco: se il problema resta, le ritento stanotte." },
  en: { lim: "You analysed {d} games today (Free limit: {m}). Plus, Pro and Elite download and analyse all your games, even overnight.", dl: "Downloaded {n} new games.", none: "All up to date.", upto: "All up to date: your {n} games are already here and analysed.", have: "Your {n} games are already here: we are analysing them.", empty: "No games yet for your accounts. Check the username or play a few games.", run: "Analyzing {d} of {t} games…", queued: "An analysis is already running: results appear as they are ready.", done: "Done: {o} games analyzed.", fail: "{f} games could not be analyzed. Try again shortly: if it persists, I'll retry tonight." },
  es: { lim: "Hoy has analizado {d} partidas (límite Free: {m}). Con Plus, Pro o Elite descargas y analizas todas tus partidas, también de noche.", dl: "Descargadas {n} partidas nuevas.", none: "Todo al día.", upto: "Todo al día: tus {n} partidas ya están aquí y analizadas.", have: "Tus {n} partidas ya están aquí: las estamos analizando.", empty: "Aún no hay partidas para tus cuentas. Revisa el nombre de usuario o juega alguna partida.", run: "Analizando {d} de {t} partidas…", queued: "Ya hay un análisis en curso: los resultados aparecen poco a poco.", done: "Hecho: {o} partidas analizadas.", fail: "{f} partidas sin analizar. Inténtalo de nuevo en breve: si sigue, las reintento esta noche." },
} as const;
import { useApp } from "../../components/app";
import { MultiLineChart } from "../../components/Charts";
import { K, tr } from "../../lib/i18n";
import Mission from "../../components/Mission";
import TimeCard from "../../components/TimeCard";
import PatternCard from "../../components/PatternCard";
import { Seg } from "../../components/ui/Seg";

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

const HS = {
  it: { level: "Il tuo livello", pts: "in {n} giorni", games: "partite", win: "vittorie", acc: "precisione", tabs: ["Rating", "Quando giochi", "Errori ricorrenti"], noRating: "Collega un account per vedere il rating." },
  en: { level: "Your level", pts: "in {n} days", games: "games", win: "wins", acc: "accuracy", tabs: ["Rating", "When you play", "Recurring mistakes"], noRating: "Link an account to see your rating." },
  es: { level: "Tu nivel", pts: "en {n} días", games: "partidas", win: "victorias", acc: "precisión", tabs: ["Rating", "Cuándo juegas", "Errores recurrentes"], noRating: "Vincula una cuenta para ver tu rating." },
} as const;

/** Riepilogo a colpo d'occhio: rating attuale con andamento, risultati in un anello, precisione. */
function Summary({ s, lang }: { s: any; lang: Lang }) {
  const x = HS[lang];
  // serie principale: quella con più punti
  let best: any = null;
  (s.rating || []).forEach((a: any) => a.series.forEach((r: any) => { if (!best || r.points.length > best.points.length) best = r; }));
  const pts: { d: string; r: number }[] = best?.points || [];
  const last = pts.length ? pts[pts.length - 1].r : null;
  const tEnd = pts.length ? new Date(pts[pts.length - 1].d).getTime() : 0;
  const old = pts.find((p) => new Date(p.d).getTime() >= tEnd - 30 * 864e5) || pts[0];
  const days = old && pts.length ? Math.max(1, Math.round((tEnd - new Date(old.d).getTime()) / 864e5)) : 0;
  const delta = last != null && old ? last - old.r : 0;
  const spark = pts.slice(-40);
  const lo = Math.min(...spark.map((p) => p.r)), hi = Math.max(...spark.map((p) => p.r));
  const sx = (i: number) => (spark.length > 1 ? (i / (spark.length - 1)) * 120 : 0), sy = (r: number) => 34 - (hi === lo ? 0.5 : (r - lo) / (hi - lo)) * 30;
  const tot = Math.max(1, s.w + s.d + s.l), C = 2 * Math.PI * 38;
  const seg = [["var(--mint)", s.w], ["var(--mute)", s.d], ["var(--bad)", s.l]] as const;
  let off = 0;
  return (
    <section className="card hm-sum" aria-label={x.level}>
      <div className="hm-lvl">
        <span className="muted small">{x.level}{best ? ` · ${(best.speed || "")}` : ""}</span>
        {last != null ? (
          <>
            <div className="hm-big">{last}<em className={delta >= 0 ? "up" : "down"}>{delta >= 0 ? "+" : "−"}{Math.abs(delta)}</em></div>
            <span className="muted small">{x.pts.replace("{n}", String(days))}</span>
            {spark.length > 1 && (
              <svg viewBox="0 0 120 38" className="hm-spark" aria-hidden="true" preserveAspectRatio="none">
                <polyline points={spark.map((p, i) => `${sx(i).toFixed(1)},${sy(p.r).toFixed(1)}`).join(" ")} fill="none" stroke="var(--ember)" strokeWidth="2.4" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
              </svg>
            )}
          </>
        ) : <p className="muted small">{x.noRating}</p>}
      </div>
      <div className="hm-ring">
        <svg viewBox="0 0 100 100" role="img" aria-label={`${s.w}/${s.d}/${s.l}`}>
          <circle cx="50" cy="50" r="38" fill="none" stroke="var(--ink-3)" strokeWidth="14" />
          {seg.map(([c, v], i) => { const len = (v / tot) * C; const el = <circle key={i} cx="50" cy="50" r="38" fill="none" stroke={c} strokeWidth="14" strokeDasharray={`${Math.max(0, len - 1.5)} ${C}`} strokeDashoffset={-off} transform="rotate(-90 50 50)" />; off += len; return el; })}
        </svg>
        <div className="hm-ring-c"><b>{s.win_rate ?? "—"}{s.win_rate != null && <small>%</small>}</b><span>{x.win}</span></div>
      </div>
      <div className="hm-facts">
        <div><b>{s.games}</b><span>{x.games}</span></div>
        <div><b>{s.accuracy ?? "—"}{s.accuracy != null && <small>%</small>}</b><span>{x.acc}</span></div>
        <div className="hm-wdl"><i style={{ background: "var(--mint)" }} />{s.w}<i style={{ background: "var(--mute)" }} />{s.d}<i style={{ background: "var(--bad)" }} />{s.l}</div>
      </div>
    </section>
  );
}

function Insights({ s, lang }: { s: any; lang: Lang }) {
  const x = HS[lang];
  const [tab, setTab] = useState<"rating" | "time" | "patterns">(s.rating.length ? "rating" : "patterns");
  return (
    <section className="hm-ins">
      <Seg<"rating" | "time" | "patterns"> value={tab} onChange={setTab} items={[
        ...(s.rating.length ? [{ v: "rating" as const, label: x.tabs[0] }] : []),
        { v: "time", label: x.tabs[1] }, { v: "patterns", label: x.tabs[2] },
      ]} />
      {tab === "rating" && <RatingCard accounts={s.rating} />}
      {tab === "time" && <TimeCard />}
      {tab === "patterns" && <PatternCard />}
    </section>
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

  useEffect(() => {   // se un'analisi è già in corso (per esempio dopo una partita giocata qui) il contatore riappare
    call("/sync/status").then((j: any) => { if (j && (j.state === "running" || j.state === "queued")) setJob(j); }).catch(() => {});
  }, [call]); // eslint-disable-line

  const sync = async () => {
    setBusy(true); setErr(""); setInfo(""); setJob(null);
    try {
      const r = await call("/sync", { method: "POST" });
      setJob(r.job);
      if (r.fetch_error) setErr(String(r.fetch_error));
      if (r.job?.state === "done") { bust(); load(); refreshMe(); }
    } catch (e: any) { setErr(e.message); }
    setBusy(false);
  };

  return (
    <>
      <div className="pagehead">
        <h1>{t("navHome")}</h1>
        <div className="row" style={{ gap: ".5rem" }}>
          <button className="btn btn-primary" onClick={sync} disabled={busy}>{busy ? t("syncing") : t("sync")}</button>
        </div>
      </div>
      <p className="muted small" style={{ marginTop: 0 }}>{me?.auto_sync ? t("autoSyncOn") : <>{t("autoSyncOff")}. <Link href="/dashboard/plans" className="accent">{t("navPlans")}</Link></>}</p>
      {job && (
        <div className="card init-banner" role="status" aria-live="polite">
          {job.state === "limit"
            ? <><b>{fm(SY.lim, { d: job.done_today, m: job.daily })}</b> <Link href="/dashboard/plans" className="accent">{t("navPlans")}</Link></>
            : <b>{job.imported > 0 ? fm(SY.dl, { n: job.imported }) : job.have > 0 ? fm(job.total > 0 ? SY.have : SY.upto, { n: job.have }) : job.have === 0 ? SY.empty : SY.none}</b>}
          {job.total > 0 && (job.state === "running" || job.state === "queued") && (
            <>
              <div className="muted small" style={{ margin: ".25rem 0" }}>{job.state === "queued" ? SY.queued : fm(SY.run, { d: job.done, t: job.total })}</div>
              <div className="bar"><div style={{ width: `${job.state === "queued" ? 6 : Math.round((100 * job.done) / job.total)}%`, background: "var(--ember)", transition: "width .6s" }} /></div>
            </>
          )}
          {job.state === "done" && job.total > 0 && <div className="muted small" style={{ marginTop: ".25rem" }}>{fm(SY.done, { o: job.ok })}</div>}
          {job.state === "done" && job.failed > 0 && <div className="note err" style={{ marginTop: ".5rem" }}>{fm(SY.fail, { f: job.failed })}{job.error ? ` (${job.error})` : ""} <Link href="/dashboard/diag" className="accent">{lang === "en" ? "Check status" : lang === "es" ? "Ver estado" : "Controlla lo stato"}</Link></div>}
        </div>
      )}
      {/* un solo contatore alla volta: se è in corso una sincronizzazione, il suo conteggio sostituisce quello dell'analisi iniziale */}
      {!(job && (job.state === "running" || job.state === "queued")) && <InitBanner onDone={() => { bust(); load(); refreshMe(); }} />}
      {info && <div className="note">{info}</div>}
      {err && <div className="note err">{err}</div>}

      {s && s.games === 0 && <div className="card muted">{t("noData")} <Link href="/dashboard/accounts" className="accent">{t("navAccounts")}</Link></div>}
      {s && s.games > 0 ? (
        <>
          <div className="hm-top"><Mission /><Summary s={s} lang={lang as Lang} /></div>
          <Insights s={s} lang={lang as Lang} />
        </>
      ) : <Mission />}
    </>
  );
}
