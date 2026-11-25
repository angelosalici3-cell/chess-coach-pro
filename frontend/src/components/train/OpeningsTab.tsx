"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useApp } from "../app";
import { tc } from "../../lib/train-copy";
import { ALL_DRILLS as BASE_DRILLS, OPENINGS as BASE_OPENINGS, type Drill, type Opening, type T2 } from "../../lib/openings-data";
import OpeningDrill from "./OpeningDrill";

type Card = { box: number; due_at: string };
type Status = "new" | "due" | "learning" | "learned";
const tx = (t: T2, lang: string) => (lang === "it" ? t.it : t.en);

export default function OpeningsTab({ onProgress }: { onProgress: () => void }) {
  const { call, lang } = useApp();
  const [cards, setCards] = useState<Record<string, Card>>({});
  const [ready, setReady] = useState(false);
  const [open, setOpen] = useState<string | null>(null);        // apertura aperta
  const [run, setRun] = useState<{ drill: Drill; n: number } | null>(null);
  const [err, setErr] = useState("");
  const [lib, setLib] = useState(false);                          // biblioteca Ochess (231 trappole) caricata solo quando serve
  const [extra, setExtra] = useState<{ openings: Opening[]; drills: Drill[] }>({ openings: [], drills: [] });
  const OPENINGS = useMemo(() => [...BASE_OPENINGS, ...extra.openings], [extra]);
  const ALL_DRILLS = useMemo(() => [...BASE_DRILLS, ...extra.drills], [extra]);
  const showLib = async () => {
    if (!extra.openings.length) { const m = await import("../../lib/ochess"); setExtra({ openings: m.OCHESS_OPENINGS, drills: m.OCHESS_DRILLS }); }
    setLib(true);
  };

  const load = useCallback(async () => {
    try {
      const r = await call("/train/openings/progress", { cache: "no-store" });
      const m: Record<string, Card> = {};
      for (const c of r.cards || []) m[c.line_id] = { box: c.box, due_at: c.due_at };
      setCards(m);
      if (Object.keys(m).some((k) => k.startsWith("oc-"))) {   // ha già progressi nella biblioteca: caricala subito
        const x = await import("../../lib/ochess"); setExtra({ openings: x.OCHESS_OPENINGS, drills: x.OCHESS_DRILLS }); setLib(true);
      }
    } catch (x: any) { setErr(x.message); }
    setReady(true);
  }, [call]);
  useEffect(() => { load(); }, [load]);

  const status = (key: string): Status => {
    const c = cards[key];
    if (!c) return "new";
    if (Date.parse(c.due_at) <= Date.now()) return "due";
    return c.box >= 4 ? "learned" : "learning";
  };
  const dueList = useMemo(
    () => ALL_DRILLS.filter((d) => status(d.key) === "due").sort((a, b) => Date.parse(cards[a.key].due_at) - Date.parse(cards[b.key].due_at)),
    [cards, ALL_DRILLS],   // eslint-disable-line react-hooks/exhaustive-deps
  );
  const learned = ALL_DRILLS.filter((d) => status(d.key) === "learned").length;

  const nextOf = (scope: Drill[], skip?: string): Drill | null => {
    const pool = scope.filter((d) => d.key !== skip);
    return pool.filter((d) => status(d.key) === "due")[0] || pool.filter((d) => status(d.key) === "new")[0] || null;
  };

  const report = async (d: Drill, ok: boolean) => {
    try {
      const r = await call("/train/openings/answer", { method: "POST", body: JSON.stringify({ line_id: d.key, correct: ok }) });
      setCards((m) => ({ ...m, [d.key]: { box: r.box, due_at: r.due_at } }));
      onProgress();
    } catch (x: any) { setErr(x.message); }
  };

  const start = (d: Drill) => setRun((r) => ({ drill: d, n: (r?.n || 0) + 1 }));

  if (err) return <div className="note err">{err}</div>;
  if (!ready) return <p className="muted">…</p>;

  if (run) {
    const scope = ALL_DRILLS.filter((d) => d.opening.id === run.drill.opening.id);
    const nxt = nextOf(scope, run.drill.key);
    return (
      <OpeningDrill
        key={run.n} drill={run.drill} hasNext={!!nxt}
        onFinish={(ok) => report(run.drill, ok)}
        onNext={() => nxt && start(nxt)}
        onRepeat={() => start(run.drill)}
        onExit={() => setRun(null)}
      />
    );
  }

  const op = open ? OPENINGS.find((o) => o.id === open) : null;
  if (op) return <OpeningPage op={op} drills={ALL_DRILLS} status={status} onBack={() => setOpen(null)} onStart={start} lang={lang} />;

  const cta = dueList[0] || nextOf(ALL_DRILLS);
  return (
    <div className="opwrap">
      <div className="opbar">
        <div className="opstats">
          <span><b>{learned}</b> / {ALL_DRILLS.length} {tc("opLearnedLbl", lang).toLowerCase()}</span>
        </div>
        {cta && (
          <button className="btn btn-primary" onClick={() => start(cta)}>
            {dueList.length ? tc("opReviewToday", lang, { n: dueList.length }) : tc("opContinue", lang)}
          </button>
        )}
      </div>
      <p className="muted small" style={{ margin: "0 0 .9rem" }}>{tc("opTrapNote", lang)}</p>
      <div className="opgrid">
        {OPENINGS.filter((o) => (lib ? true : !o.id.startsWith("oc-"))).map((o) => {
          const ds = ALL_DRILLS.filter((d) => d.opening.id === o.id);
          const due = ds.filter((d) => status(d.key) === "due").length;
          return (
            <button key={o.id} className="opcard" onClick={() => setOpen(o.id)}>
              <span className="opcard-top">
                <b>{tx(o.name, lang)}</b>
                <span className="chip">{o.eco}</span>
              </span>
              <span className="muted small opcard-blurb">{tx(o.blurb, lang)}</span>
              <span className="opdots" aria-hidden="true">
                {ds.map((d) => <i key={d.key} className={"opdot " + status(d.key)} />)}
              </span>
              <span className="opcard-foot small muted">
                {o.side === "w" ? tc("opWhite", lang) : tc("opBlack", lang)}
                {due > 0 && <em className="opdue">{due} {tc("opDue", lang).toLowerCase()}</em>}
              </span>
            </button>
          );
        })}
      </div>
      {!lib && (
        <div className="oplib">
          <button className="btn btn-ghost" onClick={showLib}>{tc("opLibOpen", lang)}</button>
          <span className="muted small">{tc("opLibNote", lang)}</span>
        </div>
      )}
      {lib && <p className="muted small" style={{ marginTop: "1rem" }}>{tc("opLibEn", lang)}</p>}
    </div>
  );
}

function OpeningPage({ op, drills, status, onBack, onStart, lang }: { op: Opening; drills: Drill[]; status: (k: string) => Status; onBack: () => void; onStart: (d: Drill) => void; lang: any }) {
  const label = (s: Status) => s === "new" ? tc("opNew", lang) : s === "due" ? tc("opDue", lang) : s === "learned" ? tc("opMastered", lang) : tc("opLearning", lang);
  return (
    <div className="opwrap">
      <button className="btn btn-ghost btn-sm" onClick={onBack}>← {tc("opBack", lang)}</button>
      <h2 style={{ marginTop: ".8rem" }}>{tx(op.name, lang)} <span className="chip" style={{ verticalAlign: "middle" }}>{op.eco}</span></h2>
      <p className="muted">{tx(op.blurb, lang)} · {op.side === "w" ? tc("opWhite", lang) : tc("opBlack", lang)}</p>
      <div className="oplist">
        {op.lines.map((l) => {
          const ds = drills.filter((d) => d.line.id === l.id);
          return (
            <div key={l.id} className="oprow">
              <div className="oprow-main">
                <span className={"chip " + (l.kind === "trap" ? "on" : "")}>{l.kind === "trap" ? tc("opTrap", lang) : tc("opLine", lang)}</span>
                <b>{tx(l.title, lang)}</b>
              </div>
              <div className="oprow-btns">
                {ds.map((d) => {
                  const s = status(d.key);
                  const name = d.mode === "learn" ? tc("opTrain", lang) : d.mode === "spring" ? tc("opSpring", lang) : tc("opAvoid", lang);
                  return (
                    <button key={d.key} className={"btn btn-sm " + (s === "due" || s === "new" ? "btn-primary" : "btn-ghost")} onClick={() => onStart(d)}>
                      {name}<em className={"opst " + s}>{label(s)}</em>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
