"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "../../components/app";
import { Bar, MultiLineChart } from "../../components/Charts";
import { K, tr } from "../../lib/i18n";

const SPEED_COLOR: Record<string, string> = { bullet: "#ff5d8f", blitz: "#ffb84d", rapid: "#4ee3b0", classical: "#5aa9ff", daily: "#b7c0dc", other: "#8d97b8" };
const RANGES: [K, number | null][] = [["range30", 30], ["range90", 90], ["range365", 365], ["rangeAll", null]];

function RatingCard({ a }: { a: any }) {
  const { t, lang } = useApp();
  const [off, setOff] = useState<string[]>([]);
  const [range, setRange] = useState<number | null>(null);
  const series = a.series.map((s: any) => ({ key: s.speed, label: tr(("speed" + s.speed[0].toUpperCase() + s.speed.slice(1)) as K, lang), color: SPEED_COLOR[s.speed] || "#8d97b8", points: s.points }));
  const shown = series.filter((s: any) => !off.includes(s.key));
  const toggle = (k: string) => setOff((o) => (o.includes(k) ? o.filter((x) => x !== k) : [...o, k]));
  const solo = (k: string) => setOff(series.filter((s: any) => s.key !== k).map((s: any) => s.key));
  return (
    <div className="card">
      <div className="row"><b>{t("rating")}</b><span className="muted small">{a.source === "lichess" ? "Lichess" : "Chess.com"} · {a.username}</span></div>
      <div className="row" style={{ margin: ".6rem 0 .2rem" }}>
        <div className="chips" style={{ margin: 0 }} role="group" aria-label={t("speedsFilter")}>
          {series.map((s: any) => (
            <button key={s.key} className={"chip" + (off.includes(s.key) ? "" : " on")} style={{ borderColor: off.includes(s.key) ? undefined : s.color }}
              onClick={() => toggle(s.key)} onDoubleClick={() => solo(s.key)} aria-pressed={!off.includes(s.key)}>
              <i className="dotc" style={{ background: s.color }} />{s.label} <span className="muted">{s.points[s.points.length - 1].r}</span>
            </button>
          ))}
        </div>
        <div className="lang" role="group">
          {RANGES.map(([k, v]) => <button key={k} className={range === v ? "on" : ""} onClick={() => setRange(v)}>{t(k)}</button>)}
        </div>
      </div>
      <MultiLineChart series={shown} days={range} />
      <p className="muted small" style={{ margin: ".3rem 0 0" }}>{t("ratingDaily")}</p>
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
          {s.rating.map((a: any) => <RatingCard key={a.source + a.username} a={a} />)}
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
