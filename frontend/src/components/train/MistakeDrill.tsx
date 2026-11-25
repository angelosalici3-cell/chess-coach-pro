"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Chess } from "chess.js";
import ChessBoard from "../ChessBoard";
import { useApp } from "../app";
import { tc } from "../../lib/train-copy";

const norm = (s: string) => (s || "").replace(/[+#!?]/g, "");
const GREEN = "rgba(78, 227, 176, .55)";

export default function MistakeDrill({ onProgress, tag }: { onProgress: () => void; tag?: string }) {
  const { call, lang } = useApp();
  const [card, setCard] = useState<any>(null);
  const [fen, setFen] = useState("");
  const [state, setState] = useState<"ask" | "right" | "late" | "reveal">("ask");
  const [tries, setTries] = useState(0);
  const [shake, setShake] = useState(false);
  const [hint, setHint] = useState(false);
  const [last, setLast] = useState<string | null>(null);
  const [back, setBack] = useState("");
  const [err, setErr] = useState("");
  const answered = useRef(false);
  const e = card?.error;

  const load = useCallback(async (revisit?: boolean) => {
    setErr("");
    try {
      const r = await call("/train/mistakes/next" + (tag ? "?tag=" + encodeURIComponent(tag) : revisit === true ? "?revisit=1" : ""), { cache: "no-store" });
      setCard(r);
      if (r.error) { setFen(r.error.fen); setState("ask"); setTries(0); setHint(false); setLast(null); setBack(""); answered.current = false; }
    } catch (x: any) { setErr(x.message); }
  }, [call, tag]);
  useEffect(() => { load(); }, [load]);
  const nextCard = () => load();

  const best = useMemo(() => {
    if (!e) return null;
    try { const m = new Chess(e.fen).move(e.best_move); return m ? { from: m.from, to: m.to } : null; } catch { return null; }
  }, [e]);

  const report = async (correct: boolean) => {
    if (answered.current || !e) return;
    answered.current = true;
    try {
      const r = await call("/train/mistakes/answer", { method: "POST", body: JSON.stringify({ error_id: String(e.id), correct }) });
      const days = Math.round((Date.parse(r.due_at) - Date.now()) / 86400000);
      setBack(r.solved ? tc("solvedMsg", lang)
        : tc("comesBack", lang, { d: days < 1 ? tc("inMinutes", lang) : days === 1 ? tc("inOneDay", lang) : tc("inDays", lang, { n: days }) }));
      onProgress();
    } catch (x: any) { setErr(x.message); }
  };

  const drop = (from: string, to: string) => {
    if (state !== "ask" || !e) return false;
    const c = new Chess(e.fen);
    let mv;
    try { mv = c.move({ from, to, promotion: "q" }); } catch { return false; }
    if (!mv) return false;
    if (norm(mv.san) === norm(e.best_move)) {
      setFen(c.fen()); setLast(from + to);
      setState(tries === 0 ? "right" : "late");
      report(tries === 0);
      return true;
    }
    const n = tries + 1;
    setTries(n); setShake(true); setTimeout(() => setShake(false), 380);
    if (n >= 3) reveal();
    return false;
  };
  const reveal = () => { setState("reveal"); report(false); };

  if (err) return <div className="note err">{err}</div>;
  if (!card) return <p className="muted">…</p>;
  if (!e) {
    return (
      <div className="card muted">
        <p style={{ margin: 0 }}>
          {card.reason === "no_errors" ? tc("emptyNoErrors", lang)
            : card.reason === "no_solved" ? tc("noSolved", lang)
            : card.next_due ? tc("emptyAllDone", lang, { when: new Date(card.next_due).toLocaleDateString(lang) })
            : tc("emptyAllDone", lang, { when: "—" }).split(".")[0] + "."}
        </p>
        {card.solved > 0 && !tag && (
          <div className="row" style={{ justifyContent: "flex-start", marginTop: 12, alignItems: "center" }}>
            <span className="chip">{tc("solvedCount", lang, { n: String(card.solved) })}</span>
            <button className="btn btn-ghost btn-sm" onClick={() => load(true)}>{tc("revisitBtn", lang)}</button>
          </div>
        )}
      </div>
    );
  }
  const white = e.fen.split(" ")[1] === "w";
  const marks: Record<string, string> = {};
  if (best && (hint || state === "reveal")) marks[best.from] = GREEN;
  if (best && state === "reveal") marks[best.to] = GREEN;
  const done = state !== "ask";
  return (
    <div className="drill">
      <ChessBoard fen={fen} flip={!white} last={last} onDrop={done ? undefined : drop} marks={marks} shake={shake} />
      <div className="drill-info">
        <div className="chips" style={{ margin: 0 }}>
          <span className="chip on">{card.revisit ? tc("cardRevisit", lang) : card.new ? tc("cardNew", lang) : tc("cardReview", lang)}</span>
          {e.categoria_errore && <span className="chip">{e.categoria_errore}</span>}
        </div>
        <h2>{tc("drillAsk", lang)}</h2>
        <p className="muted" style={{ margin: 0 }}>{white ? tc("drillTurnW", lang) : tc("drillTurnB", lang)}</p>
        <p style={{ margin: 0 }}>
          {tc("drillPlayed", lang, { a: String(e.mossa_critica || "").replace(/^\d+\.+\s*/, "") })}
          {e.eval_loss_cp ? <span className="muted">, {tc("drillCost", lang, { n: (e.eval_loss_cp / 100).toFixed(1) })}</span> : null}
        </p>
        {tries > 0 && state === "ask" && <div className="verdict ko" role="alert">{tc("wrongTry", lang)}</div>}
        {state === "right" && <div className="verdict ok">{tc("rightFirst", lang)} {back}</div>}
        {state === "late" && <div className="verdict ok">{tc("rightLate", lang)} {back}</div>}
        {state === "reveal" && <div className="verdict ko">{tc("solutionWas", lang, { a: e.best_move })} {back}</div>}
        <div className="row" style={{ justifyContent: "flex-start" }}>
          {state === "ask" ? (
            <>
              <button className="btn btn-ghost btn-sm" onClick={() => setHint(true)} disabled={hint}>{tc("hint", lang)}</button>
              <button className="btn btn-ghost btn-sm" onClick={reveal}>{tc("showSolution", lang)}</button>
            </>
          ) : (
            <>
              <button className="btn btn-primary" onClick={nextCard}>{tc("nextCard", lang)}</button>
              <Link href={`/dashboard/games/${e.game_id}`} className="btn btn-ghost btn-sm">{tc("seeGame", lang)}</Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
