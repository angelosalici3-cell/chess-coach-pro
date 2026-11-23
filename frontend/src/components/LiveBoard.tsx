"use client";
import { useEffect, useMemo, useState } from "react";
import { Chess } from "chess.js";
import ChessBoard from "./ChessBoard";
import { GAMES, LIVE } from "../lib/live-copy";
import { Lang } from "../lib/i18n";

const SYM: Record<string, string> = { brill: "!!", sac: "!?", check: "+", mate: "#" };
const ORDER = [1, 0, 2];   // matto del barbiere (corto) → Légal → Opera: si parte subito con qualcosa di rapido

/** Tre partite famose commentate in diretta dal Gran Maestro, veloci come una clip: poi si ricomincia. */
export default function LiveBoard({ lang }: { lang: Lang }) {
  const T = LIVE[lang];
  const all = useMemo(() => GAMES.map((g) => {
    const c = new Chess(); const fr = [{ fen: c.fen(), last: null as string | null }];
    for (const san of g.sans) { const m = c.move(san); fr.push({ fen: c.fen(), last: m.from + m.to }); }
    return fr;
  }), []);
  const [k, setK] = useState(0);            // posizione nell'elenco ORDER
  const [i, setI] = useState(0);            // mosse giocate
  const [paused, setPaused] = useState(false);
  const [still, setStill] = useState(false);
  const gi = ORDER[k], G = GAMES[gi], frames = all[gi], lines = G.lines[lang];
  const end = i >= frames.length - 1;

  useEffect(() => { if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setStill(true); setK(1); setI(Math.min(9, GAMES[0].sans.length)); } }, []);

  useEffect(() => {
    if (paused || still) return;
    const len = i > 0 ? lines[i - 1].length : 0;
    const wait = end ? 2600 : i === 0 ? 500 : Math.max(1300, 800 + len * 15);
    const t = setTimeout(() => { if (end) { setK((k + 1) % ORDER.length); setI(0); } else setI(i + 1); }, wait);
    return () => clearTimeout(t);
  }, [i, k, paused, still, end, lines]);

  const f = frames[i];
  const tag = i > 0 ? G.tags[i - 1] : undefined;
  const mood = Math.min(1, 0.5 + 0.5 * Math.pow(i / G.sans.length, 1.5));
  const first = Math.max(0, i - 3), shown = G.sans.slice(first, i);
  const to = f.last ? f.last.slice(2, 4) : null;
  const ex = to ? ((to.charCodeAt(0) - 97) + 0.5) * 12.5 : 0, ey = to ? ((8 - Number(to[1])) + 0.5) * 12.5 : 0;
  const cur = i > 0 ? lines[i - 1] : "", prev = i > 1 ? lines[i - 2] : "";

  return (
    <div className="lv">
      <div className="lv-top">
        <span className="lv-live"><i />{T.live}</span>
        <span className="lv-title">{G.name[lang]}</span>
        <span className="lv-games" aria-hidden="true">{ORDER.map((g, n) => <i key={g} className={n === k ? "on" : ""} />)}</span>
        <button type="button" className="lv-ctl" onClick={() => setPaused((p) => !p)} aria-label={paused ? T.play : T.pause}>{paused ? "▶" : "❚❚"}</button>
      </div>
      <div className="lv-bar" aria-hidden="true"><div style={{ width: `${mood * 100}%` }} /></div>
      <div className="lv-board">
        <ChessBoard fen={f.fen} last={f.last} notation={false} animMs={170} />
        <div className="lv-ov" aria-hidden="true">
          {i > 0 && to && <span key={"e" + gi + "-" + i} className="lv-emoji" style={{ left: `${ex}%`, top: `${ey}%` }}>{G.emo[i - 1]}</span>}
          {tag && to && <span key={"b" + gi + "-" + i} className={"lv-badge " + tag} style={{ left: `${Math.min(ex + 6.25, 100)}%`, top: `${ey - 6.25}%` }}>{SYM[tag]}</span>}
          {tag && <span key={"t" + gi + "-" + i} className={"lv-tag " + tag}>{T.tags[tag]}</span>}
        </div>
      </div>
      <div className="lv-moves" aria-hidden="true">
        {shown.map((m, n) => { const ply = first + n; return <span key={ply} className={n === shown.length - 1 ? "now" : ""}>{ply % 2 === 0 ? `${ply / 2 + 1}. ` : ""}{m}</span>; })}
      </div>
      <div className="lv-chat" aria-live="off">
        {prev && <div key={"p" + gi + (i - 1)} className="lv-msg old"><span className="lv-av" aria-hidden="true">♛</span><div className="lv-bubble">{prev}</div></div>}
        {cur && <div key={"c" + gi + "-" + i} className="lv-msg new"><span className="lv-av" aria-hidden="true">♛</span><div className="lv-bubble">{cur}</div></div>}
      </div>
      <div className="lv-prog" aria-hidden="true">{G.sans.map((_, n) => <i key={n} className={n < i ? "on" : ""} />)}</div>
    </div>
  );
}
