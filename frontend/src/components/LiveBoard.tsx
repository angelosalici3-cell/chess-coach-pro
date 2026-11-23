"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { Chess } from "chess.js";
import ChessBoard from "./ChessBoard";
import { EMO, LIVE, SAN, TAG } from "../lib/live-copy";
import { Lang } from "../lib/i18n";

/** Partita dell'Opera (Morphy, 1858) con il commento del Gran Maestro in diretta, mossa per mossa. */
export default function LiveBoard({ lang }: { lang: Lang }) {
  const T = LIVE[lang];
  const frames = useMemo(() => {
    const c = new Chess();
    const out = [{ fen: c.fen(), last: null as string | null }];
    for (const san of SAN) { const m = c.move(san); out.push({ fen: c.fen(), last: m.from + m.to }); }
    return out;
  }, []);
  const [i, setI] = useState(0);            // numero di mosse giocate
  const [typed, setTyped] = useState(0);    // caratteri già "scritti" del commento
  const [paused, setPaused] = useState(false);
  const [still, setStill] = useState(false);
  const bump = useRef(0);

  useEffect(() => { if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setStill(true); setI(19); } }, []);

  // Una mossa dopo l'altra: il tempo dipende dalla lunghezza del commento, così si fa in tempo a leggerlo
  useEffect(() => {
    if (paused || still) return;
    const end = i >= frames.length - 1;
    const text = i > 0 ? T.lines[i - 1] : "";
    const wait = end ? 5200 : i === 0 ? 1200 : Math.max(2300, 900 + text.length * 48);
    const t = setTimeout(() => { bump.current++; setI(end ? 0 : i + 1); }, wait);
    return () => clearTimeout(t);
  }, [i, paused, still, frames.length, T]);

  // Il commento si scrive lettera per lettera, come in una chat dal vivo
  const line = i > 0 ? T.lines[i - 1] : "";
  useEffect(() => {
    if (still) { setTyped(line.length); return; }
    setTyped(0);
    let n = 0;
    const t = setInterval(() => { n += 2; setTyped(n); if (n >= line.length) clearInterval(t); }, 28);
    return () => clearInterval(t);
  }, [line, still]);

  const f = frames[i];
  const tag = i > 0 ? TAG[i - 1] : undefined;
  const mood = Math.min(1, 0.5 + 0.5 * Math.pow(i / SAN.length, 1.5));    // barra decorativa: la tensione cresce
  const shown = SAN.slice(Math.max(0, i - 3), i);
  const first = Math.max(0, i - 3);

  return (
    <div className="lv">
      <div className="lv-top">
        <span className="lv-live"><i />{T.live}</span>
        <span className="lv-title">{T.gm}</span>
        <button type="button" className="lv-ctl" onClick={() => (i === frames.length - 1 ? (setI(0), setPaused(false)) : setPaused((p) => !p))} aria-label={paused ? T.play : T.pause}>
          {i === frames.length - 1 ? "↺" : paused ? "▶" : "❚❚"}
        </button>
      </div>
      <div className="lv-stage">
        <div className="lv-bar" aria-hidden="true"><div style={{ height: `${mood * 100}%` }} /></div>
        <div className="lv-board">
          <ChessBoard fen={f.fen} last={f.last} notation={false} />
          {tag && <span key={i} className={"lv-tag " + tag}>{T.tags[tag]}</span>}
        </div>
      </div>
      <div className="lv-chat" aria-live="off">
        <span className="lv-av" aria-hidden="true">♛</span>
        <div className="lv-bubble">
          <div className="lv-moves">
            {shown.map((m, k) => {
              const ply = first + k;
              return <span key={ply} className={k === shown.length - 1 ? "now" : ""}>{ply % 2 === 0 ? `${ply / 2 + 1}. ` : ""}{m}</span>;
            })}
          </div>
          <p>{i === 0 ? <span className="lv-dots"><b /><b /><b /></span> : line.slice(0, typed)}{i > 0 && typed < line.length && <span className="lv-caret" />}</p>
        </div>
        {i > 0 && <span key={"e" + i} className="lv-emoji" aria-hidden="true">{EMO[i - 1]}</span>}
      </div>
      <div className="lv-prog" aria-hidden="true">{SAN.map((_, k) => <i key={k} className={k < i ? "on" : ""} />)}</div>
    </div>
  );
}
