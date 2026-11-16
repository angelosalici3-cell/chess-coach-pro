"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useApp } from "../../../components/app";
import { K, tr } from "../../../lib/i18n";

export default function LessonsPage() {
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
      <div className="pagehead"><h1>{t("navLessons")}</h1></div>
      <p className="muted small" style={{ marginTop: 0 }}>{t("lessonsHint")}</p>
      {err && <div className="note err">{err}</div>}
      {rows && rows.length > 0 && (
        <>
          <div className="filters">
            <input placeholder={t("searchLessons")} value={q} onChange={(e) => setQ(e.target.value)} />
            {ops.length > 0 && <select value={op} onChange={(e) => setOp(e.target.value)}><option value="all">{t("allOpenings")}</option>{ops.map((o: any) => <option key={o} value={o}>{o}</option>)}</select>}
          </div>
          <div className="chips" style={{ marginBottom: ".8rem" }}>
            <button className={cat === "all" ? "chip on" : "chip"} onClick={() => setCat("all")}>{t("all")}</button>
            {cats.map((c: any) => <button key={c} className={cat === c ? "chip on" : "chip"} onClick={() => setCat(c)}>{tr(("cat_" + c) as K, lang)}</button>)}
          </div>
        </>
      )}
      {rows && rows.length === 0 && <p className="muted">{t("noLessons")}</p>}
      {shown.map((r) => (
        <details key={r.id} className="card">
          <summary><b>{r.mossa_critica}</b> <span className="muted small">{r.games?.white} vs {r.games?.black}{r.apertura ? `, ${r.apertura}` : ""}</span></summary>
          <p className="pre">{r.gm_lesson}</p>
          <Link href={`/dashboard/games/${r.game_id}`} className="accent small">{t("games")}</Link>
        </details>
      ))}
    </>
  );
}
