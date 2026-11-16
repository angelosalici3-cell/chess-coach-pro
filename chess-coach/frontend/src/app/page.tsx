"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "../components/app";
import { Bar, LineChart } from "../components/Charts";
import { tr, K } from "../lib/i18n";

export default function Home() {
  const { call, t, lang, me, refreshMe } = useApp();
  const [s, setS] = useState<any>(null);
  const [err, setErr] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const [src, setSrc] = useState("");

  const load = () => call("/stats").then(setS).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, [call]);

  const sync = async () => {
    setBusy(true); setErr(""); setInfo("");
    try {
      const r = await call("/sync", { method: "POST" });
      setInfo(tr("syncDone", lang).replace("{n}", r.imported).replace("{a}", r.analyzing));
      load(); refreshMe();
    } catch (e: any) { setErr(e.message); }
    setBusy(false);
  };

  const ratingKeys = s ? Object.keys(s.rating) : [];
  const key = src || ratingKeys[0];
  return (
    <>
      <div className="row" style={{ margin: ".4rem 0" }}>
        <h2 style={{ margin: 0 }}>{t("navHome")}</h2>
        <button className="primary" onClick={sync} disabled={busy}>{busy ? t("syncing") : "⟳ " + t("sync")}</button>
      </div>
      <p className="muted small" style={{ marginTop: 0 }}>{me?.auto_sync ? "🟢 " + t("autoSyncOn") : <>⚪ {t("autoSyncOff")} · <Link href="/plans" style={{ color: "var(--gold)" }}>{t("navPlans")}</Link></>}</p>
      {info && <div className="card">{info}</div>}
      {err && <div className="card err">⚠️ {err === "profile_limit" ? "" : err}</div>}

      {s && s.games === 0 && <div className="card muted">{t("noData")} <Link href="/accounts" style={{ color: "var(--gold)" }}>{t("navAccounts")}</Link></div>}
      {s && s.games > 0 && (
        <>
          <div className="stats">
            <div className="card"><div className="muted small">{t("statGames")}</div><div className="big">{s.games}</div></div>
            <div className="card"><div className="muted small">{t("statWin")}</div><div className="big">{s.win_rate ?? "—"}{s.win_rate != null && "%"}</div></div>
            <div className="card"><div className="muted small">{t("statAcc")}</div><div className="big">{s.accuracy ?? "—"}{s.accuracy != null && "%"}</div></div>
          </div>

          <div className="card">
            <div className="row"><b>{t("rating")}</b>
              {ratingKeys.length > 1 && <select value={key} onChange={(e) => setSrc(e.target.value)}>{ratingKeys.map((k) => <option key={k} value={k}>{k}</option>)}</select>}
              {ratingKeys.length === 1 && <span className="muted small">{key}</span>}
            </div>
            {key ? <LineChart points={s.rating[key]} /> : <p className="muted small">—</p>}
          </div>

          <div className="card">
            <b>{t("results")}</b>
            <div className="wdl">
              <div style={{ flex: s.w, background: "#38d9a9" }} /><div style={{ flex: s.d, background: "#8892a6" }} /><div style={{ flex: s.l, background: "#ff6b6b" }} />
            </div>
            <span className="muted small">{t("wins")} {s.w} · {t("draws")} {s.d} · {t("losses")} {s.l}</span>
          </div>

          <div className="card">
            <b>{t("byOpening")}</b>
            {s.openings.map((o: any) => (
              <div key={o.name} style={{ marginTop: ".6rem" }}>
                <div className="row small"><span>{o.name} <span className="muted">({o.games})</span></span><span>{o.win_rate}%</span></div>
                <Bar pct={o.win_rate} color={o.win_rate >= 50 ? "#38d9a9" : "#ff9f6b"} />
              </div>
            ))}
          </div>

          {s.categories.length > 0 && (
            <div className="card">
              <b>{t("weakAreas")}</b>
              {s.categories.map((c: any) => (
                <div key={c.cat} style={{ marginTop: ".6rem" }}>
                  <div className="row small"><span>{tr(("cat_" + c.cat) as K, lang)}</span><span>{c.count}</span></div>
                  <Bar pct={(100 * c.count) / s.categories[0].count} color="#ffa94d" />
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}
