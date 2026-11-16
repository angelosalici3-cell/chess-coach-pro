"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useApp } from "../../../components/app";
import Board from "../../../components/Board";

const START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
const CLS: Record<string, string> = { blunder: "#ff6b6b", mistake: "#ffa94d", inaccuracy: "#ffe066", brilliant: "#38d9a9", best: "#8ce99a" };

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

  useEffect(() => { call(`/games/${id}`).then((x) => { setD(x); setLessons(Object.fromEntries(x.errors.filter((e: any) => e.spiegazione).map((e: any) => [e.id, e.spiegazione]))); }).catch((e) => setErr(e.message)); }, [id, call]);

  const msg = (e: any) => (e.message === "quota_exhausted" ? t("quota") : e.message === "gm_failed" ? t("gmFailed") : e.message);
  const fenNow = ply === 0 ? START : d?.moves.find((m: any) => m.ply === ply)?.fen_after || START;
  const fp = fenNow.split(" "); const moveLabel = ply === 0 ? "—" : `${fp[5] ? (fp[1] === "w" ? +fp[5] - 1 : fp[5]) : Math.ceil(ply / 2)}${fp[1] === "w" ? "..." : "."}`;

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

  if (!d) return <p className="muted">{err ? `⚠️ ${err}` : t("loading")}</p>;
  const g = d.game;
  return (
    <>
      <Link href="/games" className="muted">{t("back")}</Link>
      <h2>{g.white} vs {g.black} <span className="muted">{g.result}</span></h2>
      {err && <div className="card err">⚠️ {err} {err === t("quota") && <Link href="/plans">→ {t("navPlans")}</Link>}</div>}
      {!g.analyzed_at && (
        <div className="card row"><span className="muted">{queued ? t("analyzingGame") : t("notAnalyzed")}</span>{!queued && <button className="primary" onClick={analyze}>{t("analyze")}</button>}</div>
      )}
      <div className="split">
        <div>
          <Board fen={fenNow} flip={g.user_color === "black"} />
          <div className="row" style={{ justifyContent: "center", marginTop: ".5rem" }}>
            <button onClick={() => setPly(0)}>⏮</button>
            <button onClick={() => setPly(Math.max(0, ply - 1))}>◀</button>
            <span className="muted small">{t("moveNo")} {moveLabel}</span>
            <button onClick={() => setPly(Math.min(d.moves.length, ply + 1))}>▶</button>
            <button onClick={() => setPly(d.moves.length)}>⏭</button>
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
        <div className="row" style={{ marginTop: ".5rem" }}>
          <input style={{ flex: 1 }} placeholder={t("askPlaceholder")} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask()} />
          <button className="primary" onClick={ask} disabled={asking}>{asking ? t("thinking") : t("send")}</button>
        </div>
        {ans && <p className="pre">{ans}</p>}
      </div>

      <h3>{t("mistakes")}</h3>
      {d.errors.length === 0 && <p className="muted">{t("noMistakes")}</p>}
      {d.errors.map((e: any) => (
        <div key={e.id} className="card">
          <div className="row">
            <span>{Math.ceil((e.ply || 1) / 2)}{(e.ply || 1) % 2 ? "." : "..."} <b>{e.mossa_critica}</b> <span className="muted">· {t("best")}: {e.best_move || "—"}{e.eval_loss_cp ? ` · −${(e.eval_loss_cp / 100).toFixed(1)}` : ""}</span></span>
            <span>
              <button onClick={() => e.ply && setPly(e.ply)}>♟</button>{" "}
              {!lessons[e.id] && <button className="primary" disabled={busy === e.id} onClick={() => lesson(e.id)}>{busy === e.id ? t("thinking") : t("askLesson")}</button>}
            </span>
          </div>
          {lessons[e.id] && <p className="pre">{lessons[e.id]}</p>}
        </div>
      ))}
    </>
  );
}
