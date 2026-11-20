"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "./app";
import { patternTip, patternTitle, pc } from "../lib/pattern-copy";

type Pat = { id: string; moves: number; errors: number; games: number; rate: number; lift: number; trend?: { recent: number; before: number };
  examples: { game: string; ply: number; move: string; best: string; win_loss: number }[] };

/** Scheda "Il tuo schema di errore": la tendenza più marcata, le prove e il pulsante per allenarsi su quegli errori. */
export default function PatternCard() {
  const { call, lang } = useApp();
  const [d, setD] = useState<any>(null);
  useEffect(() => { call<any>("/patterns").then(setD).catch(() => {}); }, [call]);
  if (!d) return null;
  const pct = (v: number) => Math.round(v * 1000) / 10;
  if (!d.ready) {
    const done = Math.min(100, Math.round(((30 - d.need) / 30) * 100));
    return (
      <div className="card pattern">
        <b>{pc("cardTitle", lang)}</b>
        <p className="muted small" style={{ margin: ".3rem 0 .6rem" }}>{pc("needMore", lang, { n: d.need })}</p>
        <div className="bar"><div style={{ width: `${done}%`, background: "var(--ember)" }} /></div>
      </div>
    );
  }
  const pats: Pat[] = d.patterns || [];
  if (!pats.length) return <div className="card pattern"><b>{pc("cardTitle", lang)}</b><p className="muted small" style={{ margin: ".3rem 0 0" }}>{pc("none", lang)}</p></div>;
  const [top, ...rest] = pats;
  const tip = patternTip(top.id, lang);
  const adv = d.advantage && top.id.startsWith("st_") && ["st_adv", "st_slight_adv", "st_won"].includes(top.id) ? d.advantage : null;
  return (
    <div className="card pattern">
      <span className="muted small">{pc("cardTitle", lang)}</span>
      <h2 className="ptitle">{patternTitle(top.id, lang)}</h2>
      <p className="muted" style={{ margin: ".2rem 0" }}>{pc("body", lang, { e: top.errors, m: top.moves, r: pct(top.rate), b: pct(d.base_rate || 0), g: top.games })}</p>
      {top.trend && <p className="muted small" style={{ margin: ".2rem 0" }}>{pc("trend", lang, { n: 20, a: pct(top.trend.recent), b: pct(top.trend.before) })}</p>}
      {adv && adv.reached_plus3 > 0 && <p className="muted small" style={{ margin: ".2rem 0" }}>{pc("conv", lang, { n: adv.reached_plus3, k: adv.not_won })}</p>}
      {tip && <p className="ptip">{tip}</p>}
      {top.examples.length > 0 && (
        <div className="chips" style={{ margin: ".5rem 0" }} aria-label={pc("examples", lang)}>
          {top.examples.map((x) => (
            <Link key={x.game + x.ply} href={`/dashboard/games/${x.game}`} className="chip">{pc("move", lang, { n: Math.ceil(x.ply / 2) })}: {x.move}</Link>
          ))}
        </div>
      )}
      <Link href={`/dashboard/train?tag=${encodeURIComponent(top.id)}`} className="btn btn-primary btn-sm">{pc("cta", lang)}</Link>
      {rest.length > 0 && (
        <div style={{ marginTop: ".8rem" }}>
          <span className="muted small">{pc("more", lang)}</span>
          <ul className="plist">
            {rest.map((p) => (
              <li key={p.id}><Link href={`/dashboard/train?tag=${encodeURIComponent(p.id)}`}>{patternTitle(p.id, lang)}</Link> <span className="muted small">{p.errors}/{p.moves}</span></li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
