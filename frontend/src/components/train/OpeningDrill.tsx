"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { Chess } from "chess.js";
import ChessBoard from "../ChessBoard";
import { useApp } from "../app";
import { tc } from "../../lib/train-copy";
import type { Drill, T2 } from "../../lib/openings-data";

const norm = (s: string) => (s || "").replace(/[+#!?]/g, "");
const GREEN = "rgba(78, 227, 176, .55)";
const tx = (t: T2 | undefined, lang: string) => (t ? (lang === "it" ? t.it : t.en) : "");

/** Allenamento di una linea: l'avversario risponde da solo, tu giochi a memoria le mosse del tuo lato. */
export default function OpeningDrill({ drill, onFinish, onNext, onRepeat, onExit, hasNext }: {
  drill: Drill; onFinish: (ok: boolean) => void; onNext: () => void; onRepeat: () => void; onExit: () => void; hasNext: boolean;
}) {
  const { lang } = useApp();
  const { line, mode } = drill;
  const moves = useMemo(() => line.moves.split(" "), [line]);
  const { fens, lasts } = useMemo(() => {
    const ch = new Chess();
    const fens = [ch.fen()]; const lasts: (string | null)[] = [null];
    for (const s of moves) { const m = ch.move(s); fens.push(ch.fen()); lasts.push(m.from + m.to); }
    return { fens, lasts };
  }, [moves]);

  const userWhite = mode === "avoid" ? line.side === "b" : line.side === "w";
  const endAt = mode === "avoid" ? (line.blunderAt as number) : moves.length;
  const userTurn = (k: number) => (k % 2 === 0) === userWhite;

  const [i, setI] = useState(0);
  const [status, setStatus] = useState<"play" | "won" | "fell">("play");
  const [tries, setTries] = useState(0);
  const [errors, setErrors] = useState(0);
  const [shake, setShake] = useState(false);
  const [hint, setHint] = useState(false);
  const [over, setOver] = useState<{ fen: string; last: string } | null>(null);   // posizione dopo la mossa sicura
  const [safeShown, setSafeShown] = useState("");
  const reported = useRef(false);
  const finish = (ok: boolean) => { if (!reported.current) { reported.current = true; onFinish(ok); } };

  // l'avversario risponde da solo
  useEffect(() => {
    if (status !== "play" || i >= endAt || userTurn(i)) return;
    const t = setTimeout(() => setI((k) => k + 1), i === 0 ? 350 : 520);
    return () => clearTimeout(t);
  }, [i, status, endAt]);   // eslint-disable-line react-hooks/exhaustive-deps
  // fine della linea (non per «evita», che finisce con la mossa sicura)
  useEffect(() => {
    if (mode !== "avoid" && status === "play" && i >= moves.length) { setStatus("won"); finish(errors === 0); }
  }, [i, status]);   // eslint-disable-line react-hooks/exhaustive-deps
  // dopo la caduta nella trappola si vede il resto della linea
  useEffect(() => {
    if (status !== "fell" || i >= moves.length) return;
    const t = setTimeout(() => setI((k) => k + 1), 700);
    return () => clearTimeout(t);
  }, [status, i, moves.length]);
  useEffect(() => { setHint(false); setTries(0); }, [i]);

  const expected = moves[i];
  const isCritical = mode === "avoid" && i === line.blunderAt;
  const target = useMemo(() => {
    if (status !== "play" || !userTurn(i)) return null;
    try { const c = new Chess(fens[i]); const m = c.move(isCritical ? (line.safe as string[])[0] : expected); return m ? { from: m.from, to: m.to } : null; } catch { return null; }
  }, [i, status, fens]);   // eslint-disable-line react-hooks/exhaustive-deps

  const fen = over ? over.fen : fens[Math.min(i, fens.length - 1)];
  const last = over ? over.last : lasts[Math.min(i, lasts.length - 1)];
  const marks: Record<string, string> = {};
  if (hint && target) marks[target.from] = GREEN;

  const bad = () => { setShake(true); setTimeout(() => setShake(false), 380); };
  const drop = (from: string, to: string) => {
    if (status !== "play" || over || i >= endAt || !userTurn(i)) return false;
    const c = new Chess(fens[i]);
    let mv;
    try { mv = c.move({ from, to, promotion: "q" }); } catch { return false; }
    if (!mv) return false;
    const san = norm(mv.san);
    if (isCritical) {
      const safe = (line.safe || []).map(norm);
      if (safe.includes(san)) {
        setOver({ fen: c.fen(), last: from + to }); setStatus("won"); finish(errors === 0); return true;
      }
      if (san === norm(expected)) {   // la mossa della trappola
        setI(i + 1); setErrors((n) => n + 1); setStatus("fell"); finish(false); return true;
      }
      const n = tries + 1; setTries(n); setErrors((x) => x + 1); bad();
      if (n >= 3) {
        const sm = new Chess(fens[i]); const m = sm.move((line.safe as string[])[0]);
        setSafeShown(m.san); setOver({ fen: sm.fen(), last: m.from + m.to }); setStatus("won"); finish(false);
      }
      return false;
    }
    if (san === norm(expected)) { setI(i + 1); return true; }
    const n = tries + 1; setTries(n); setErrors((x) => x + 1); bad();
    if (n >= 3) setI(i + 1);   // mostra la mossa giusta e prosegue
    return false;
  };

  const white = userWhite ? tc("opWhite", lang) : tc("opBlack", lang);
  const modeTxt = mode === "learn" ? tc("opModeLearn", lang) : mode === "spring" ? tc("opSpring", lang) : tc("opAvoid", lang);
  const intro = mode === "learn" ? tc("opYouPlay", lang, { side: white }) : mode === "spring" ? tc("opYouPlaySpring", lang, { side: white }) : tc("opYouPlayAvoid", lang, { side: white });

  // elenco delle mosse già giocate
  const shown = moves.slice(0, over ? i : i);
  const pairs: string[] = [];
  shown.forEach((m, k) => { pairs.push(k % 2 === 0 ? `${k / 2 + 1}. ${m}` : m); });

  return (
    <div className="drill">
      <ChessBoard fen={fen} flip={!userWhite} last={last} onDrop={status === "play" && !over && userTurn(i) ? drop : undefined} marks={marks} shake={shake} />
      <div className="drill-info">
        <div className="chips" style={{ margin: 0 }}>
          <span className="chip on">{modeTxt}</span>
          <span className="chip">{drill.opening.eco}</span>
        </div>
        <h2>{tx(line.title, lang)}</h2>
        <p className="muted" style={{ margin: 0 }}>{status === "play" ? intro : tx(drill.opening.name, lang)}</p>
        {pairs.length > 0 && <p className="opmoves">{pairs.join(" ")}</p>}
        {tries > 0 && status === "play" && <div className="verdict ko" role="alert">{tc("opWrong", lang)}</div>}

        {status === "won" && (
          <div className="verdict ok">
            <b>{mode === "avoid" ? tc("opSafeFound", lang) : errors === 0 ? tc("opLineDone", lang) : tc("opLineDoneErr", lang)}</b>
            {safeShown && <p style={{ margin: ".3rem 0 0" }}>{tc("opSafeShown", lang, { m: safeShown })}</p>}
            {line.kind === "trap" && mode === "avoid" && <p style={{ margin: ".5rem 0 0" }}><b>{tc("opHowAvoid", lang)}:</b> {tx(line.avoid, lang)}</p>}
            <p style={{ margin: ".5rem 0 0" }}><b>{tc("opIdea", lang)}:</b> {tx(line.idea, lang)}</p>
            {line.kind === "trap" && mode === "spring" && line.result && <p style={{ margin: ".5rem 0 0" }}><b>{tc("opResult", lang)}:</b> {tx(line.result, lang)}</p>}
          </div>
        )}
        {status === "fell" && (
          <div className="verdict ko">
            <b>{tc("opFell", lang)}</b>
            {line.result && <p style={{ margin: ".4rem 0 0" }}>{tx(line.result, lang)}</p>}
            <p style={{ margin: ".5rem 0 0" }}><b>{tc("opIdea", lang)}:</b> {tx(line.idea, lang)}</p>
            <p style={{ margin: ".5rem 0 0" }}><b>{tc("opHowAvoid", lang)}:</b> {tx(line.avoid, lang)}</p>
          </div>
        )}

        <div className="row" style={{ justifyContent: "flex-start" }}>
          {status === "play" ? (
            <>
              <button className="btn btn-ghost btn-sm" onClick={() => setHint(true)} disabled={hint || !target}>{tc("opHint", lang)}</button>
              <button className="btn btn-ghost btn-sm" onClick={onExit}>{tc("opExit", lang)}</button>
            </>
          ) : (
            <>
              {hasNext && <button className="btn btn-primary" onClick={onNext} disabled={status === "fell" && i < moves.length}>{tc("opNext", lang)}</button>}
              <button className={"btn btn-sm " + (hasNext ? "btn-ghost" : "btn-primary")} onClick={onRepeat}>{tc("opRepeat", lang)}</button>
              <button className="btn btn-ghost btn-sm" onClick={onExit}>{tc("opExit", lang)}</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
