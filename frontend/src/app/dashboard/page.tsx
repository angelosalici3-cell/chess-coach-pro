"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "../../components/app";
import { Bar, MultiLineChart } from "../../components/Charts";
import { K, tr } from "../../lib/i18n";
import TodayCard from "../../components/TodayCard";
import TimeCard from "../../components/TimeCard";

const SPEED_COLOR: Record<string, string> = { bullet: "#ff5d8f", blitz: "#ffb84d", rapid: "#4ee3b0", classical: "#5aa9ff", daily: "#b7c0dc", other: "#8d97b8" };
const RANGES: [K, number | null][] = [["range30", 30], ["range90", 90], ["range365", 365], ["rangeAll", null]];

const DASHES = [undefined, "7 5", "2 5", "10 4 2 4"];
const plat = (src: string) => (src === "lichess" ? "Lichess" : "Chess.com");

/** Un solo grafico: i filtri Account e Ritmo passano dalla vista generale (tutte le linee) al dettaglio (una sola). */
function RatingCard({ accounts }: { accounts: any[] }) {
  const { t, lang } = useApp();
  const [acc, setAcc] = useState<string>("all");
  const [speed, setSpeed] = useState<string>("all");
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
    <div className="card">
      <div className="row"><b>{t("rating")}</b>
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
  const { call, t, lang, me, refreshMe } = useApp();
  const [s, setS] = useState<any>(null);
  const [err, setErr] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => call("/stats").then(setS).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, [call]);

  const sync = async () => {
    setBusy(true); setErr(""); setInfo("");
    try {
      const r = await call("/sync", { method: "POST" });
      setInfo(tr("syncDone", lang).replace("{n}", r.imported).replace("{a}", r.analyzing));
      load(); refreshMe();
      setTimeout(load, 30000);
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
      <TodayCard />
      {info && <div className="note">{info}</div>}
      {err && <div className="note err">{err}</div>}

      {s && s.games === 0 && <div className="card muted">{t("noData")} <Link href="/dashboard/accounts" className="accent">{t("navAccounts")}</Link></div>}
      {s && s.games > 0 && (
        <>
          <div className="stats">
            <div className="card"><div className="muted small">{t("statGames")}</div><div className="big">{s.games}</div></div>
            <div className="card"><div className="muted small">{t("statWin")}</div><div className="big">{s.win_rate ?? "—"}{s.win_rate != null && "%"}</div></div>
            <div className="card"><div className="muted small">{t("statAcc")}</div><div className="big">{s.accuracy ?? "—"}{s.accuracy != null && "%"}</div></div>
          </div>
          {s.rating.length > 0 && <RatingCard accounts={s.rating} />}
          <TimeCard />
          <div className="grid2">
            <div className="card">
              <b>{t("results")}</b>
              <div className="wdl"><div style={{ flex: s.w, background: "var(--mint)" }} /><div style={{ flex: s.d, background: "var(--mute)" }} /><div style={{ flex: s.l, background: "var(--bad)" }} /></div>
              <span className="muted small">{t("wins")} {s.w}, {t("draws")} {s.d}, {t("losses")} {s.l}</span>
            </div>
            {s.categories.length > 0 && (
              <div className="card">
                <b>{t("weakAreas")}</b>
                {s.categories.map((c: any) => (
                  <div key={c.cat} style={{ marginTop: ".6rem" }}>
                    <div className="row small"><span>{tr(("cat_" + c.cat) as K, lang)}</span><span>{c.count}</span></div>
                    <Bar pct={(100 * c.count) / s.categories[0].count} color="var(--amber)" />
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="card">
            <b>{t("byOpening")}</b>
            {s.openings.map((o: any) => (
              <div key={o.name} style={{ marginTop: ".7rem" }}>
                <div className="row small"><span>{o.name} <span className="muted">({o.games})</span></span><span>{o.win_rate}%</span></div>
                <Bar pct={o.win_rate} color={o.win_rate >= 50 ? "var(--mint)" : "var(--ember)"} />
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}
