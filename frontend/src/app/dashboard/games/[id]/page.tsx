"use client";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useApp } from "../../../../components/app";
import ChessBoard from "../../../../components/ChessBoard";
import { EvalChart, LossChart, LossPt } from "../../../../components/Charts";
import TimeChart from "../../../../components/TimeChart";
import { tc } from "../../../../lib/train-copy";
import { u } from "../../../../lib/ui-copy";
import { Seg } from "../../../../components/ui/Seg";

const GT = {
  it: { errors: "Errori", charts: "Grafici", moves: "Mosse", eval: "Valutazione", loss: "Perdita", time: "Tempo" },
  en: { errors: "Mistakes", charts: "Charts", moves: "Moves", eval: "Evaluation", loss: "Loss", time: "Time" },
  es: { errors: "Errores", charts: "Gráficos", moves: "Jugadas", eval: "Evaluación", loss: "Pérdida", time: "Tiempo" },
} as const;

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
  const [timeData, setTimeData] = useState<any>(null);
  const [tab, setTab] = useState<"errors" | "charts" | "moves">("errors");
  const [chart, setChart] = useState<"eval" | "loss" | "time">("eval");

  useEffect(() => {
    call(`/games/${id}`).then((x) => {
      setD(x);
      setLessons(Object.fromEntries(x.errors.filter((e: any) => e.gm_lesson).map((e: any) => [e.id, e.gm_lesson])));
    }).catch((e) => setErr(e.message));
    call(`/games/${id}/time`).then(setTimeData).catch(() => setTimeData({ available: false }));
  }, [id, call]);

  const msg = (e: any) => (e.message === "quota_exhausted" ? t("quota") : e.message === "gm_busy" ? t("gmBusy") : e.message === "gm_failed" ? t("gmFailed") : e.message);

  // elenco unico: errori gravi, errori e imprecisioni di chi gioca; la lezione GM si può chiedere per ogni voce
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

  // valutazione dopo ogni mossa dal punto di vista di chi gioca (sopra lo zero stai meglio tu)
  const evals: number[] = useMemo(() => {
    if (!d?.moves?.length) return [];
    const sgn = d.game.user_color === "black" ? -1 : 1;
    return [0, ...d.moves.map((m: any) => sgn * (m.eval_cp ?? 0))];
  }, [d]);
  // mossa critica: la tua mossa che ha fatto perdere più valutazione, se è davvero pesante
  const critical = useMemo(() => {
    if (!d?.moves?.length) return null;
    const mine = d.moves.filter((m: any) => m.is_user_move && (m.loss_cp ?? 0) >= 100);
    if (!mine.length) return null;
    const m = mine.reduce((b: any, x: any) => ((x.loss_cp ?? 0) > (b.loss_cp ?? 0) ? x : b), mine[0]);
    const e = d.errors.find((z: any) => z.ply === m.ply);
    return { m, before: evals[m.ply - 1], after: evals[m.ply], best: e?.best_move || m.best_move_san };
  }, [d, evals]);
  const sgnEv = (v: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${(Math.abs(v) / 100).toFixed(1)}`;

  const frame = ply === 0 ? null : d?.moves.find((m: any) => m.ply === ply);
  const fenNow = frame?.fen_after || START;

  const analyze = async () => { try { await call(`/games/${id}/analyze`, { method: "POST" }); setQueued(true); } catch (e: any) { setErr(msg(e)); } };
  // chiave della lezione: id dell'errore salvato, oppure -ply per le imprecisioni (la riga si crea alla richiesta)
  const lesson = async (key: number, ply: number, hasErr: boolean) => {
    setBusy(key); setErr("");
    try {
      const r = await call(hasErr ? `/errors/${key}/lesson` : `/games/${id}/moves/${ply}/lesson`, { method: "POST", body: JSON.stringify({ lang }) });
      setLessons((s) => ({ ...s, [key]: r.lesson })); refreshMe();
    }
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
      <div className="gv">
        <div className="gv-board">
          <ChessBoard fen={fenNow} flip={g.user_color === "black"} last={frame?.uci} />
          <div className="ctrls">
            <button onClick={() => setPly(0)} aria-label="Start">⏮</button>
            <button onClick={() => setPly(Math.max(0, ply - 1))} aria-label="Back">◀</button>
            <span className="muted small">{t("moveNo")} {ply === 0 ? "—" : `${lbl(ply)}`}</span>
            <button onClick={() => setPly(Math.min(d.moves.length, ply + 1))} aria-label="Next">▶</button>
            <button onClick={() => setPly(d.moves.length)} aria-label="End">⏭</button>
          </div>
        </div>
        <div className="gv-panel">
          {g.analyzed_at && critical && (
            <div className="critical">
              <div><span className="ctag">{u("critTitle", lang)}</span>
                <p>{u("critText", lang, { m: `${lbl(critical.m.ply)} ${critical.m.san}`, a: sgnEv(critical.before), b: sgnEv(critical.after), best: critical.best || "—" })}</p></div>
              <button className="btn btn-primary btn-sm" onClick={() => setPly(critical.m.ply)}>{u("critShow", lang)}</button>
            </div>
          )}
          {g.analyzed_at && !critical && d.moves.length > 0 && <p className="muted small" style={{ margin: ".2rem 0" }}>{u("critNone", lang)}</p>}
          <Seg<"errors" | "charts" | "moves"> value={tab} onChange={setTab} items={[{ v: "errors", label: GT[lang].errors, n: items.length }, { v: "charts", label: GT[lang].charts }, { v: "moves", label: GT[lang].moves }]} />

          {tab === "errors" && (
            <div className="gv-scroll">
              {items.length === 0 && <p className="muted">{g.analyzed_at ? t("noMistakes") : t("notAnalyzed")}</p>}
              {items.map(({ m, e, loss, best }: any) => {
                const key = e ? e.id : -m.ply;
                return (
                  <div key={m.ply} className={"card gv-err" + (m.ply === ply ? " on" : "")}>
                    <div className="row">
                      <button className="gv-pick" onClick={() => setPly(m.ply)} aria-label="Show">
                        <b>{lbl(m.ply)} {m.san}</b> <span className="tag" style={{ color: CLS[m.classification] }}>{tagName(m.classification)}</span>
                        <span className="muted small"> {t("best")}: {best || "—"}{loss ? `, −${(loss / 100).toFixed(1)}` : ""}</span>
                      </button>
                      {!lessons[key] && <button className="btn btn-primary btn-sm" disabled={busy === key} onClick={() => lesson(key, m.ply, !!e)}>{busy === key ? t("thinking") : t("askLesson")}</button>}
                    </div>
                    {lessons[key] && <p className="pre">{lessons[key]}</p>}
                  </div>
                );
              })}
            </div>
          )}

          {tab === "charts" && (
            <div className="card chartcard gv-chart">
              <Seg<"eval" | "loss" | "time"> value={chart} onChange={setChart} items={[
                { v: "eval", label: GT[lang].eval }, { v: "loss", label: GT[lang].loss },
                ...(timeData?.available ? [{ v: "time" as const, label: GT[lang].time }] : []),
              ]} />
              {chart === "eval" && (evals.length > 2 && g.analyzed_at
                ? <><p className="muted small" style={{ margin: ".5rem 0" }}>{u("evalNote", lang)}</p><EvalChart evals={evals} active={ply} onPick={setPly} critical={critical?.m.ply} /></>
                : <p className="muted">{t("notAnalyzed")}</p>)}
              {chart === "loss" && (chartPts.some((p) => p.loss > 0)
                ? <>
                    <p className="muted small" style={{ margin: ".5rem 0" }}>{t("lossNote")}</p>
                    <LossChart pts={chartPts} active={ply} onPick={setPly} />
                    <div className="loss-legend">
                      <span><i style={{ background: "var(--bad)" }} />{t("clsBlunder")}</span>
                      <span><i style={{ background: "var(--ember)" }} />{t("clsMistake")}</span>
                      <span><i style={{ background: "var(--amber)" }} />{t("clsInacc")}</span>
                      <span><i style={{ background: "var(--mint)" }} />{t("lossYou")}</span>
                      <span><i style={{ background: "var(--mute)", opacity: 0.5 }} />{t("lossOpp")}</span>
                    </div>
                  </>
                : <p className="muted">{t("notAnalyzed")}</p>)}
              {chart === "time" && timeData?.available && <TimeChart data={timeData} active={ply} onPick={setPly} />}
              {timeData && !timeData.available && chart !== "time" && <p className="muted small" style={{ marginTop: ".6rem" }}>{tc("noClock", lang)}</p>}
            </div>
          )}

          {tab === "moves" && (
            <div className="card movelist gv-scroll">
              <div className="chips">
                {d.moves.map((m: any) => (
                  <button key={m.ply} className={m.ply === ply ? "chip on" : "chip"} style={{ color: CLS[m.classification] }} onClick={() => setPly(m.ply)}>
                    {lbl(m.ply)} {m.san}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
