"use client";
import { useEffect, useState } from "react";
import { useApp } from "./app";
import { tc } from "../lib/train-copy";

export default function TimeCard() {
  const { call, lang } = useApp();
  const [s, setS] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const load = () => call("/stats/time").then(setS).catch(() => setS({ games: 0 }));
  useEffect(() => { load(); }, [call]);

  const resync = async () => {
    setBusy(true);
    try { await call("/sync?n=100", { method: "POST" }); setTimeout(load, 2500); } catch {}
    setBusy(false);
  };
  if (!s) return null;
  const sec = tc("secShort", lang);
  const tips: string[] = [];
  if (s.games > 0) {
    if (s.lost_on_time > 0) tips.push(tc("insightFlag", lang, { n: s.lost_on_time }));
    if (s.loss_trouble != null && s.loss_normal != null && s.loss_trouble > s.loss_normal * 1.3) tips.push(tc("insightTrouble", lang, { a: s.loss_trouble, b: s.loss_normal }));
    if (s.fast_errors >= 3) tips.push(tc("insightFast", lang, { n: s.fast_errors }));
    if (!tips.length) tips.push(tc("insightOk", lang));
  }
  return (
    <div className="card">
      <div className="row"><b>{tc("timeTitle", lang)}</b>{s.games > 0 && <span className="muted small">{tc("basedOn", lang, { n: s.games })}</span>}</div>
      {s.games === 0 ? (
        <div className="row" style={{ marginTop: ".6rem" }}>
          <span className="muted small" style={{ flex: 1 }}>{tc("noClockHome", lang)}</span>
          <button className="btn btn-ghost btn-sm" onClick={resync} disabled={busy}>{tc("resync", lang)}</button>
        </div>
      ) : (
        <>
          <div className="timestats">
            <div><span className="muted small">{tc("avgMove", lang)}</span><b>{s.avg_spent}{sec}</b></div>
            <div><span className="muted small">{tc("troubleMoves", lang)}</span><b>{s.trouble_share}%</b></div>
            <div><span className="muted small">{tc("fastMistakes", lang)}</span><b>{s.fast_errors}</b></div>
            <div><span className="muted small">{tc("lostOnTime", lang)}</span><b>{s.lost_on_time}</b></div>
          </div>
          {tips.slice(0, 2).map((x) => <p key={x} className="insight">{x}</p>)}
        </>
      )}
    </div>
  );
}
