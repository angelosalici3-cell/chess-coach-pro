"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useApp } from "../../components/app";
import { K, tr } from "../../lib/i18n";

export default function LessonsPage() {
  const { call, t, lang } = useApp();
  const [rows, setRows] = useState<any[] | null>(null);
  const [cat, setCat] = useState("all");
  const [err, setErr] = useState("");
  useEffect(() => { call("/lessons").then(setRows).catch((e) => setErr(e.message)); }, [call]);
  const cats = useMemo(() => Array.from(new Set((rows || []).map((r) => r.categoria_errore).filter(Boolean))), [rows]);
  const shown = (rows || []).filter((r) => cat === "all" || r.categoria_errore === cat);
  return (
    <>
      <h2>{t("navLessons")}</h2>
      <p className="muted small">{t("lessonsHint")}</p>
      {err && <div className="card err">⚠️ {err}</div>}
      {cats.length > 0 && (
        <div className="chips" style={{ marginBottom: ".6rem" }}>
          <button className={cat === "all" ? "chip on" : "chip"} onClick={() => setCat("all")}>{t("all")}</button>
          {cats.map((c: any) => <button key={c} className={cat === c ? "chip on" : "chip"} onClick={() => setCat(c)}>{tr(("cat_" + c) as K, lang)}</button>)}
        </div>
      )}
      {rows && rows.length === 0 && <p className="muted">{t("noLessons")}</p>}
      {shown.map((r) => (
        <details key={r.id} className="card">
          <summary>
            <b>{r.mossa_critica}</b> <span className="muted small">· {r.games?.white} vs {r.games?.black}{r.apertura ? ` · ${r.apertura}` : ""}</span>
          </summary>
          <p className="pre">{r.spiegazione}</p>
          <Link href={`/games/${r.game_id}`} className="muted small">→ {t("games")}</Link>
        </details>
      ))}
    </>
  );
}
