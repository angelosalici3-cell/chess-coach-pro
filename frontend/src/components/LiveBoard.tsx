"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { Chess } from "chess.js";
import ChessBoard from "./ChessBoard";
import { GAMES, LIVE } from "../lib/live-copy";
import { Lang } from "../lib/i18n";

/** Tre partite famose commentate dal Gran Maestro in diretta, una dopo l'altra, poi si ricomincia dalla prima. */
export default function LiveBoard({ lang }: { lang: Lang }) {
  const T = LIVE[lang];
  const all = useMemo(() => GAMES.map((g) => {
    const c = new Chess(); const fr = [{ fen: c.fen(), last: null as string | null }];
    for (const san of g.sans) { const m = c.move(san); fr.push({ fen: c.fen(), last: m.from + m.to }); }
    return fr;
  }), []);
  const [gi, setGi] = useState(0);          // partita in corso
  const [i, setI] = useState(0);            // mosse giocate
  const [typed, setTyped] = useState(0);
  const [paused, setPaused] = useState(false);
  const [still, setStill] = useState(false);
  const G = GAMES[gi], frames = all[gi], lines = G.lines[lang];
  const end = i >= frames.length - 1;

  useEffect(() => { if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setStill(true); setI(Math.min(6, GAMES[0].sans.length)); } }, []);

  // una mossa dopo l'altra (il tempo dipende dalla lunghezza del commento); a fine partita si passa alla successiva e, dopo la terza, di nuovo alla prima
  useEffect(() => {
    if (paused || still) return;
    const text = i > 0 ? lines[i - 1] : "";
    const wait = end ? 4200 : i === 0 ? 1100 : Math.max(2200, 900 + text.length * 46);
    const t = setTimeout(() => { if (end) { setGi((gi + 1) % GAMES.length); setI(0); } else setI(i + 1); }, wait);
    return () => clearTimeout(t);
  }, [i, gi, paused, still, end, lines]);

  const line = i > 0 ? lines[i - 1] : "";
  useEffect(() => {
    if (still) { setTyped(line.length); return; }
    setTyped(0); let n = 0;
    const t = setInterval(() => { n += 2; setTyped(n); if (n >= line.length) clearInterval(t); }, 28);
    return () => clearInterval(t);
  }, [line, still]);

  const f = frames[i];
  const tag = i > 0 ? G.tags[i - 1] : undefined;
  const mood = Math.min(1, 0.5 + 0.5 * Math.pow(i / G.sans.length, 1.5));
  const first = Math.max(0, i - 3), shown = G.sans.slice(first, i);
  // l'emoji compare sulla casa di arrivo del pezzo appena mosso
  const to = f.last ? f.last.slice(2, 4) : null;
  const ex = to ? ((to.charCodeAt(0) - 97) + 0.5) * 12.5 : 0, ey = to ? ((8 - Number(to[1])) + 0.5) * 12.5 : 0;

  return (
    <div className="lv">
      <div className="lv-top">
        <span className="lv-live"><i />{T.live}</span>
        <span className="lv-title">{G.name[lang]}</span>
        <span className="lv-games" aria-hidden="true">{GAMES.map((_, k) => <i key={k} className={k === gi ? "on" : ""} />)}</span>
        <button type="button" className="lv-ctl" onClick={() => setPaused((p) => !p)} aria-label={paused ? T.play : T.pause}>{paused ? "▶" : "❚❚"}</button>
      </div>
      <div className="lv-stage">
        <div className="lv-bar" aria-hidden="true"><div style={{ height: `${mood * 100}%` }} /></div>
        <div className="lv-board">
          <ChessBoard fen={f.fen} last={f.last} notation={false} />
          {i > 0 && to && <span key={gi + "-" + i} className="lv-emoji" style={{ left: `${ex}%`, top: `${ey}%` }} aria-hidden="true">{G.emo[i - 1]}</span>}
          {tag && <span key={"t" + gi + "-" + i} className={"lv-tag " + tag}>{T.tags[tag]}</span>}
        </div>
      </div>
      <div className="lv-chat" aria-live="off">
        <span className="lv-av" aria-hidden="true">♛</span>
        <div className="lv-bubble">
          <div className="lv-moves">
            {shown.map((m, k) => { const ply = first + k; return <span key={ply} className={k === shown.length - 1 ? "now" : ""}>{ply % 2 === 0 ? `${ply / 2 + 1}. ` : ""}{m}</span>; })}
          </div>
          <p>{i === 0 ? <span className="lv-dots"><b /><b /><b /></span> : line.slice(0, typed)}{i > 0 && typed < line.length && <span className="lv-caret" />}</p>
        </div>
      </div>
      <div className="lv-prog" aria-hidden="true">{G.sans.map((_, k) => <i key={k} className={k < i ? "on" : ""} />)}</div>
    </div>
  );
}
