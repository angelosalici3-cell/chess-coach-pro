"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { Chess } from "chess.js";
import ChessBoard from "../ChessBoard";
import { useApp } from "../app";
import { THEMES, tc, themeName } from "../../lib/train-copy";

type Phase = "loading" | "play" | "done" | "empty" | "nomatch";
const GREEN = "rgba(78, 227, 176, .55)";

export default function PuzzleTrainer({ onProgress }: { onProgress: () => void }) {
  const { call, lang } = useApp();
  const [theme, setTheme] = useState("");
  const [puzzle, setPuzzle] = useState<any>(null);
  const [rating, setRating] = useState<number | null>(null);
  const [delta, setDelta] = useState<number | null>(null);
  const [fen, setFen] = useState("");
  const [last, setLast] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [flip, setFlip] = useState(false);
  const [shake, setShake] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const [missed, setMissed] = useState(false);
  const [err, setErr] = useState("");
  const chess = useRef<Chess | null>(null);
  const idx = useRef(0);
  const uci = useRef<string[]>([]);
  const reported = useRef(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const later = (fn: () => void, ms: number) => { timers.current.push(setTimeout(fn, ms)); };
  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const report = useCallback(async (solved: boolean, id: string) => {
    if (reported.current) return;
    reported.current = true;
    try {
      const r = await call("/train/puzzle/result", { method: "POST", body: JSON.stringify({ puzzle_id: id, solved }) });
      setRating(r.rating); setDelta(r.delta); onProgress();
    } catch (x: any) { setErr(x.message); }
  }, [call, onProgress]);

  const play = (i: number) => {
    const u = uci.current[i], c = chess.current;
    if (!u || !c) return;
    c.move({ from: u.slice(0, 2), to: u.slice(2, 4), promotion: u[4] });
    setFen(c.fen()); setLast(u.slice(0, 4));
  };

  const load = useCallback(async (th: string) => {
    timers.current.forEach(clearTimeout); timers.current = [];
    setErr(""); setPhase("loading"); setDelta(null); setHint(null); setMissed(false); setLast(null);
    try {
      const r = await call(`/train/puzzle/next${th ? `?theme=${encodeURIComponent(th)}` : ""}`);
      const p = r.puzzle, c = new Chess(p.fen);
      chess.current = c; uci.current = p.moves.split(" "); idx.current = 0; reported.current = false;
      setPuzzle(p); setRating(r.rating); setFen(c.fen());
      setFlip(p.fen.split(" ")[1] === "w");          // la prima mossa è dell'avversario: tocca all'altro colore
      setPhase("play");
      later(() => { play(0); idx.current = 1; }, 650);
    } catch (x: any) {
      if (x.message === "no_puzzles") setPhase("empty"); else if (x.message === "no_match") setPhase("nomatch"); else { setErr(x.message); setPhase("empty"); }
    }
  }, [call]);
  useEffect(() => { load(theme); }, [theme, load]);

  const fail = () => { if (!missed && puzzle) { setMissed(true); report(false, puzzle.id); } };

  const finish = () => { setPhase("done"); if (puzzle && !reported.current) report(true, puzzle.id); };

  const drop = (from: string, to: string) => {
    const c = chess.current;
    if (phase !== "play" || !c || idx.current < 1 || idx.current % 2 === 0) return false;
    const exp = uci.current[idx.current];
    const promo = exp.length === 5 && exp.slice(0, 4) === from + to ? exp[4] : "q";
    let mv;
    try { mv = c.move({ from, to, promotion: promo }); } catch { return false; }
    if (!mv) return false;
    const played = from + to + (mv.promotion ?? "");
    if (played !== exp && !c.isCheckmate()) {   // qualunque matto vale come soluzione
      c.undo(); fail(); setShake(true); later(() => setShake(false), 380);
      return false;
    }
    setFen(c.fen()); setLast(from + to); setHint(null);
    idx.current += 1;
    if (idx.current >= uci.current.length || c.isCheckmate()) { later(finish, 250); return true; }
    later(() => { play(idx.current); idx.current += 1; if (idx.current >= uci.current.length) finish(); }, 480);
    return true;
  };

  const showHint = () => { const u = uci.current[idx.current]; if (u) { setHint(u.slice(0, 2)); fail(); } };
  const skip = () => { if (puzzle) report(false, puzzle.id); load(theme); };

  const turnWhite = puzzle ? puzzle.fen.split(" ")[1] === "b" : true;
  return (
    <div>
      <div className="themesel">
        <label className="muted small" htmlFor="pz-theme">{tc("themesLbl", lang)}</label>
        <select id="pz-theme" value={theme} onChange={(e) => setTheme(e.target.value)}>
          <option value="">{tc("themeAll", lang)}</option>
          {THEMES.map((k) => <option key={k} value={k}>{themeName(k, lang)}</option>)}
        </select>
      </div>
      {err && <div className="note err">{err}</div>}
      {phase === "empty" && <div className="card muted">{tc("noPuzzles", lang)}</div>}
      {phase === "nomatch" && <div className="card muted">{tc("noMatch", lang)}</div>}
      {(phase === "play" || phase === "done" || (phase === "loading" && puzzle)) && puzzle && (
        <div className="drill">
          <ChessBoard fen={fen} flip={flip} last={last} onDrop={phase === "play" ? drop : undefined} marks={hint ? { [hint]: GREEN } : undefined} shake={shake} />
          <div className="drill-info">
            <div className="chips" style={{ margin: 0 }}>
              <span className="chip on">{tc("puzzleLevel", lang, { n: puzzle.rating })}</span>
              {phase === "done" && puzzle.themes.slice(0, 4).map((k: string) => <span key={k} className="chip">{themeName(k, lang)}</span>)}
            </div>
            <h2>{turnWhite ? tc("puzzleTurnW", lang) : tc("puzzleTurnB", lang)}</h2>
            <p className="muted" style={{ margin: 0 }}>{tc("yourRating", lang)}: <b style={{ color: "var(--ice)" }}>{rating}</b>
              {delta != null && delta !== 0 && <b style={{ color: delta > 0 ? "var(--mint)" : "var(--bad)" }}> {delta > 0 ? "+" : ""}{delta}</b>}</p>
            {missed && phase === "play" && <div className="verdict ko" role="alert">{tc("puzzleWrong", lang)}</div>}
            {phase === "done" && <div className={"verdict " + (missed ? "ko" : "ok")}>{missed ? tc("puzzleSolvedHelp", lang) : tc("puzzleSolved", lang)}</div>}
            <div className="row" style={{ justifyContent: "flex-start" }}>
              {phase === "play" ? (
                <>
                  <button className="btn btn-ghost btn-sm" onClick={showHint}>{tc("hint", lang)}</button>
                  <button className="btn btn-ghost btn-sm" onClick={skip}>{tc("puzzleSkip", lang)}</button>
                </>
              ) : <button className="btn btn-primary" onClick={() => load(theme)}>{tc("puzzleNext", lang)}</button>}
            </div>
            <p className="muted small" style={{ margin: 0 }}>{tc("puzzleCredit", lang)}</p>
          </div>
        </div>
      )}
    </div>
  );
}
