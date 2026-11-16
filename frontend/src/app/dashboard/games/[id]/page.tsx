"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useApp } from "../../../../components/app";
import ChessBoard from "../../../../components/ChessBoard";

const START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
const CLS: Record<string, string> = { blunder: "var(--bad)", mistake: "var(--ember)", inaccuracy: "var(--amber)", brilliant: "var(--mint)", best: "var(--mint)" };

export default function GamePage() {
  const { id } = useParams<{ id: string }>();
  const { call, t, lang, refreshMe } = useApp();
  const [d, setD] = useState<any>(null);
  const [ply, setPly] = useState(0);
  const [err, setErr] = useState("");
  const [lessons, setLessons] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const [q, setQ] = useState("");
  const [ans, setAns] = useState("");
  const [asking, setAsking] = useState(false);
  const [queued, setQueued] = useState(false);

  useEffect(() => {
    call(`/games/${id}`).then((x) => {
      setD(x);
      setLessons(Object.fromEntries(x.errors.filter((e: any) => e.gm_lesson).map((e: any) => [e.id, e.gm_lesson])));
    }).catch((e) => setErr(e.message));
  }, [id, call]);

  const msg = (e: any) => (e.message === "quota_exhausted" ? t("quota") : e.message === "gm_failed" ? t("gmFailed") : e.message);
  const frame = ply === 0 ? null : d?.moves.find((m: any) => m.ply === ply);
  const fenNow = frame?.fen_after || START;
  const fp = fenNow.split(" ");
  const moveLabel = ply === 0 ? "—" : `${fp[1] === "w" ? +fp[5] - 1 : fp[5]}${fp[1] === "w" ? "..." : "."}`;

  const analyze = async () => { try { await call(`/games/${id}/analyze`, { method: "POST" }); setQueued(true); } catch (e: any) { setErr(msg(e)); } };
  const lesson = async (eid: number) => {
    setBusy(eid); setErr("");
    try { const r = await call(`/errors/${eid}/lesson`, { method: "POST", body: JSON.stringify({ lang }) }); setLessons((s) => ({ ...s, [eid]: r.lesson })); refreshMe(); }
    catch (e: any) { setErr(msg(e)); }
    setBusy(null);
  };
  const ask = async () => {
    if (!q.trim()) return;
    setAsking(true); setErr(""); setAns("");
    try { const r = await call("/gm/ask", { method: "POST", body: JSON.stringify({ fen: fenNow, question: q, lang }) }); setAns(r.answer); refreshMe(); }
    catch (e: any) { setErr(msg(e)); }
    setAsking(false);
  };

  if (!d) return <p className="muted">{err || t("loading")}</p>;
  const g = d.game;
  return (
    <>
      <Link href="/dashboard/games" className="muted small">{t("back")}</Link>
      <div className="pagehead"><h1>{g.white} vs {g.black} <span className="muted">{g.result}</span></h1></div>
      {err && <div className="note err">{err} {err === t("quota") && <Link href="/dashboard/plans" className="accent">{t("navPlans")}</Link>}</div>}
      {!g.analyzed_at && (
        <div className="card row"><span className="muted">{queued ? t("analyzingGame") : t("notAnalyzed")}</span>{!queued && <button className="btn btn-primary" onClick={analyze}>{t("analyze")}</button>}</div>
      )}
      <div className="split">
        <div>
          <ChessBoard fen={fenNow} flip={g.user_color === "black"} last={frame?.uci} />
          <div className="ctrls">
            <button onClick={() => setPly(0)} aria-label="Start">⏮</button>
            <button onClick={() => setPly(Math.max(0, ply - 1))} aria-label="Back">◀</button>
            <span className="muted small">{t("moveNo")} {moveLabel}</span>
            <button onClick={() => setPly(Math.min(d.moves.length, ply + 1))} aria-label="Next">▶</button>
            <button onClick={() => setPly(d.moves.length)} aria-label="End">⏭</button>
          </div>
        </div>
        <div className="card movelist">
          <b>{t("moves")}</b>
          <div className="chips">
            {d.moves.map((m: any) => (
              <button key={m.ply} className={m.ply === ply ? "chip on" : "chip"} style={{ color: CLS[m.classification] }} onClick={() => setPly(m.ply)}>
                {Math.ceil(m.ply / 2)}{m.ply % 2 ? "." : "..."} {m.san}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <b>{t("askTitle")}</b>
        <div className="askrow">
          <input placeholder={t("askPlaceholder")} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask()} />
          <button className="btn btn-primary" onClick={ask} disabled={asking}>{asking ? t("thinking") : t("send")}</button>
        </div>
        {ans && <p className="pre">{ans}</p>}
      </div>

      <h2>{t("mistakes")}</h2>
      {d.errors.length === 0 && <p className="muted">{t("noMistakes")}</p>}
      {d.errors.map((e: any) => (
        <div key={e.id} className="card">
          <div className="row">
            <span>{Math.ceil((e.ply || 1) / 2)}{(e.ply || 1) % 2 ? "." : "..."} <b>{e.mossa_critica}</b> <span className="muted small">{t("best")}: {e.best_move || "—"}{e.eval_loss_cp ? `, −${(e.eval_loss_cp / 100).toFixed(1)}` : ""}</span></span>
            <span className="row">
              <button onClick={() => e.ply && setPly(e.ply)} aria-label="Show">♟</button>
              {!lessons[e.id] && <button className="btn btn-primary" disabled={busy === e.id} onClick={() => lesson(e.id)}>{busy === e.id ? t("thinking") : t("askLesson")}</button>}
            </span>
          </div>
          {lessons[e.id] && <p className="pre">{lessons[e.id]}</p>}
        </div>
      ))}
    </>
  );
}
