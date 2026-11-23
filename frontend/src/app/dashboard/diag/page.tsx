"use client";
import { useCallback, useEffect, useState } from "react";
import { useApp } from "../../../components/app";

const X = {
  it: { t: "Stato analisi", s: "Se le partite non si analizzano, qui vedi cosa manca: database, motore di scacchi, servizi esterni.", run: "Controlla di nuovo", wait: "Controllo in corso…", fail: "Il server non risponde. Riprova tra un minuto.", allok: "Tutto a posto: sincronizza di nuovo le partite.", bad: "Qualcosa va sistemato (righe rosse): copia il testo e mandamelo." },
  en: { t: "Analysis status", s: "If games aren't being analysed, see what's missing: database, chess engine, external services.", run: "Check again", wait: "Checking…", fail: "The server isn't responding. Try again in a minute.", allok: "All good: sync your games again.", bad: "Something needs fixing (red rows): copy the text and send it to me." },
  es: { t: "Estado del análisis", s: "Si las partidas no se analizan, aquí ves qué falta: base de datos, motor, servicios externos.", run: "Comprobar de nuevo", wait: "Comprobando…", fail: "El servidor no responde. Inténtalo en un minuto.", allok: "Todo bien: sincroniza las partidas otra vez.", bad: "Algo hay que arreglar (filas rojas): copia el texto y envíamelo." },
} as const;

export default function DiagPage() {
  const { call, lang } = useApp();
  const x = X[lang];
  const [rows, setRows] = useState<{ name: string; ok: boolean; detail: string }[] | null>(null);
  const [err, setErr] = useState(false);
  const run = useCallback(() => { setRows(null); setErr(false); call<any>("/diag", { cache: "no-store" }).then((d) => setRows(Array.isArray(d) ? d : d?.checks || [])).catch(() => setErr(true)); }, [call]);
  useEffect(() => { run(); }, [run]);
  const bad = rows?.some((r) => !r.ok);
  return (
    <>
      <div className="pagehead"><h1>{x.t}</h1><button className="btn btn-sm" onClick={run}>{x.run}</button></div>
      <p className="muted">{x.s}</p>
      <div className="card">
        {err ? <p>{x.fail}</p> : !rows ? <p className="muted">{x.wait}</p> : rows.map((r, i) => (
          <div className="diag-row" key={i}>
            <i className={r.ok ? "ok" : "ko"} aria-hidden="true">{r.ok ? "✓" : "✕"}</i>
            <div><b>{r.name}</b>{r.detail && <div className="small muted" style={{ wordBreak: "break-word" }}>{r.detail}</div>}</div>
          </div>
        ))}
      </div>
      {rows && <p className={bad ? "note" : "muted"}>{bad ? x.bad : x.allok}</p>}
    </>
  );
}
