"use client";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useApp } from "../../../../components/app";
import ChessBoard from "../../../../components/ChessBoard";
import { LossChart, LossPt } from "../../../../components/Charts";

const START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
const CLS: Record<string, string> = { blunder: "var(--bad)", mistake: "var(--ember)", inaccuracy: "var(--amber)", brilliant: "var(--mint)", best: "var(--mint)" };
const lbl = (ply: number) => `${Math.ceil(ply / 2)}${ply % 2 ? "." : "..."}`;

export default function GamePage() {
  const { id } = useParams<{ id: string }>();
  const { call, t, lang, refreshMe } = useApp();
  const [d, setD] = useState<any>(null);
  const [ply, setPly] = useState(0);
  const [err, setErr] = useState("");
  const [lessons, setLessons] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const [queued, setQueued] = useState(false);

  useEffect(() => {
    call(`/games/${id}`).then((x) => {
      setD(x);
      setLessons(Object.fromEntries(x.errors.filter((e: any) => e.gm_lesson).map((e: any) => [e.id, e.gm_lesson])));
    }).catch((e) => setErr(e.message));
  }, [id, call]);

  const msg = (e: any) => (e.message === "quota_exhausted" ? t("quota") : e.message === "gm_failed" ? t("gmFailed") : e.message);

  // elenco unico: errori gravi, errori e imprecisioni di chi gioca; la lezione GM esiste solo per errori e errori gravi
  const items = useMemo(() => {
    if (!d) return [];
    const byPly: Record<number, any> = Object.fromEntries(d.errors.map((e: any) => [e.ply, e]));
    return d.moves
      .filter((m: any) => m.is_user_move && ["blunder", "mistake", "inaccuracy"].includes(m.classification))
      .map((m: any) => {
        const e = byPly[m.ply];
        return { m, e, loss: e?.eval_loss_cp ?? m.loss_cp ?? 0, best: e?.best_move || m.best_move_san };
      });
  }, [d]);

  const chartPts: LossPt[] = useMemo(() => (d?.moves || []).map((m: any) => ({
    ply: m.ply, loss: m.loss_cp ?? 0, you: !!m.is_user_move,
    color: m.is_user_move ? (CLS[m.classification] && m.classification !== "best" ? CLS[m.classification] : "var(--mint)") : "var(--mute)",
  })), [d]);

  const frame = ply === 0 ? null : d?.moves.find((m: any) => m.ply === ply);
  const fenNow = frame?.fen_after || START;

  const analyze = async () => { try { await call(`/games/${id}/analyze`, { method: "POST" }); setQueued(true); } catch (e: any) { setErr(msg(e)); } };
  const lesson = async (eid: number) => {
    setBusy(eid); setErr("");
    try { const r = await call(`/errors/${eid}/lesson`, { method: "POST", body: JSON.stringify({ lang }) }); setLessons((s) => ({ ...s, [eid]: r.lesson })); refreshMe(); }
    catch (e: any) { setErr(msg(e)); }
    setBusy(null);
  };

  if (!d) return <p className="muted">{err || t("loading")}</p>;
  const g = d.game;
  const tagName = (c: string) => (c === "blunder" ? t("clsBlunder") : c === "mistake" ? t("clsMistake") : t("clsInacc"));
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
            <span className="muted small">{t("moveNo")} {ply === 0 ? "—" : `${lbl(ply)}`}</span>
            <button onClick={() => setPly(Math.min(d.moves.length, ply + 1))} aria-label="Next">▶</button>
            <button onClick={() => setPly(d.moves.length)} aria-label="End">⏭</button>
          </div>
        </div>
        <div className="card movelist">
          <b>{t("moves")}</b>
          <div className="chips">
            {d.moves.map((m: any) => (
              <button key={m.ply} className={m.ply === ply ? "chip on" : "chip"} style={{ color: CLS[m.classification] }} onClick={() => setPly(m.ply)}>
                {lbl(m.ply)} {m.san}
              </button>
            ))}
          </div>
        </div>
      </div>

      {chartPts.some((p) => p.loss > 0) && (
        <div className="card loss-wrap">
          <b>{t("lossTitle")}</b>
          <p className="muted small" style={{ margin: ".2rem 0 .4rem" }}>{t("lossNote")}</p>
          <LossChart pts={chartPts} active={ply} onPick={setPly} />
          <div className="loss-legend">
            <span><i style={{ background: "var(--bad)" }} />{t("clsBlunder")}</span>
            <span><i style={{ background: "var(--ember)" }} />{t("clsMistake")}</span>
            <span><i style={{ background: "var(--amber)" }} />{t("clsInacc")}</span>
            <span><i style={{ background: "var(--mint)" }} />{t("lossYou")}</span>
            <span><i style={{ background: "var(--mute)", opacity: 0.5 }} />{t("lossOpp")}</span>
          </div>
        </div>
      )}

      <h2>{t("mistakes")}</h2>
      {items.length === 0 && <p className="muted">{t("noMistakes")}</p>}
      {items.map(({ m, e, loss, best }: any) => (
        <div key={m.ply} className="card">
          <div className="row">
            <span className="errline">
              <span>{lbl(m.ply)} <b>{m.san}</b></span>
              <span className="tag" style={{ color: CLS[m.classification] }}>{tagName(m.classification)}</span>
              <span className="muted small">{t("best")}: {best || "—"}{loss ? `, −${(loss / 100).toFixed(1)}` : ""}</span>
            </span>
            <span className="row">
              <button onClick={() => setPly(m.ply)} aria-label="Show">♟</button>
              {e && !lessons[e.id] && <button className="btn btn-primary" disabled={busy === e.id} onClick={() => lesson(e.id)}>{busy === e.id ? t("thinking") : t("askLesson")}</button>}
            </span>
          </div>
          {e && lessons[e.id] && <p className="pre">{lessons[e.id]}</p>}
        </div>
      ))}
    </>
  );
}
