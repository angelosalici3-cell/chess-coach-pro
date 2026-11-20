"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useApp } from "./app";
import { K, tr } from "../lib/i18n";
import { u } from "../lib/ui-copy";

/** Quante lezioni del GM restano: sempre in cima, perché è la prima cosa che si vuole sapere prima di chiederne una. */
export function LessonQuota() {
  const { me, lang } = useApp();
  if (!me) return null;
  const used = me.lessons?.used ?? 0, lim = me.lessons?.limit as number | null, bonus = me.bonus_lessons || 0;
  const total = lim == null ? null : lim + bonus, left = total == null ? null : Math.max(0, total - used);
  const pct = total ? Math.min(100, (100 * used) / total) : 0;
  return (
    <div className="quota">
      <div className="quota-top">
        <div>
          <span className="muted small">{u("lqTitle", lang)}</span>
          <b className="quota-n">{total == null ? "∞" : left}</b>
          <span className="muted small">{total == null ? u("lqUnlimited", lang) : u("lqLeft", lang, { n: left as number, m: total })}</span>
        </div>
        {bonus > 0 && <span className="chip on">{u("lqBonus", lang, { n: bonus })}</span>}
        {total != null && left === 0 && <Link href="/dashboard/plans" className="btn btn-primary btn-sm">{u("lqUpgrade", lang)}</Link>}
      </div>
      {total != null && <div className="bar"><div style={{ width: `${pct}%`, background: pct >= 100 ? "var(--bad)" : pct >= 80 ? "var(--amber)" : "var(--ember)" }} /></div>}
    </div>
  );
}

export default function Lessons() {
  const { call, t, lang } = useApp();
  const [rows, setRows] = useState<any[] | null>(null);
  const [cat, setCat] = useState("all");
  const [op, setOp] = useState("all");
  const [q, setQ] = useState("");
  const [err, setErr] = useState("");
  useEffect(() => { call("/lessons").then(setRows).catch((e) => setErr(e.message)); }, [call]);
  const cats = useMemo(() => Array.from(new Set((rows || []).map((r) => r.categoria_errore).filter(Boolean))), [rows]);
  const ops = useMemo(() => Array.from(new Set((rows || []).map((r) => r.apertura).filter(Boolean))), [rows]);
  const shown = (rows || []).filter((r) =>
    (cat === "all" || r.categoria_errore === cat) && (op === "all" || r.apertura === op) &&
    (!q.trim() || (r.gm_lesson + " " + r.mossa_critica).toLowerCase().includes(q.toLowerCase())));
  return (
    <>
      <LessonQuota />
      {err && <div className="note err">{err}</div>}
      {rows && rows.length > 0 && (
        <div className="gfilters">
          <input className="search" placeholder={t("searchLessons")} value={q} onChange={(e) => setQ(e.target.value)} />
          <div className="fscroll">
            <div className="seg" role="tablist">
              <button className={cat === "all" ? "on" : ""} onClick={() => setCat("all")}>{t("all")}</button>
              {cats.map((c: any) => <button key={c} className={cat === c ? "on" : ""} onClick={() => setCat(c)}>{tr(("cat_" + c) as K, lang)}</button>)}
            </div>
            {ops.length > 0 && <select value={op} onChange={(e) => setOp(e.target.value)} aria-label={t("allOpenings")}><option value="all">{t("allOpenings")}</option>{ops.map((o: any) => <option key={o} value={o}>{o}</option>)}</select>}
          </div>
        </div>
      )}
      {rows && rows.length === 0 && <div className="card muted">{u("lessonsEmpty", lang)}</div>}
      {shown.map((r) => (
        <details key={r.id} className="lcard">
          <summary>
            <span className="lmove">{r.mossa_critica}</span>
            <span className="muted small ellip">{r.games?.white} vs {r.games?.black}{r.apertura ? ` · ${r.apertura}` : ""}</span>
            {r.categoria_errore && <span className="tag">{tr(("cat_" + r.categoria_errore) as K, lang)}</span>}
          </summary>
          <p className="pre">{r.gm_lesson}</p>
          <Link href={`/dashboard/games/${r.game_id}`} className="accent small">{u("lessonOpen", lang)}</Link>
        </details>
      ))}
    </>
  );
}
