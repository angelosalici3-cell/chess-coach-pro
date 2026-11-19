"use client";
import { useEffect, useRef, useState } from "react";
import { useApp } from "./app";
import type { Lang } from "../lib/i18n";

const T = {
  it: { title: "Stiamo preparando la tua analisi", dl: "Sto scaricando le tue partite…", prog: "{a} di {t} partite analizzate", eta: "pronte tra circa {n} min", etaSoon: "quasi pronte",
        hint: "Puoi usare l'app: i risultati compaiono man mano. Non serve restare su questa pagina.", done: "Analisi completata: {t} partite pronte." },
  en: { title: "Getting your analysis ready", dl: "Downloading your games…", prog: "{a} of {t} games analyzed", eta: "ready in about {n} min", etaSoon: "almost ready",
        hint: "You can keep using the app: results appear as they are ready. No need to stay on this page.", done: "Analysis complete: {t} games ready." },
  es: { title: "Estamos preparando tu análisis", dl: "Descargando tus partidas…", prog: "{a} de {t} partidas analizadas", eta: "listas en unos {n} min", etaSoon: "casi listas",
        hint: "Puedes seguir usando la app: los resultados aparecen poco a poco. No hace falta quedarse en esta página.", done: "Análisis completo: {t} partidas listas." },
} as const;
const f = (s: string, v: Record<string, number>) => Object.keys(v).reduce((a, k) => a.split(`{${k}}`).join(String(v[k])), s);

/** Avanza da solo: mostra quante partite iniziali sono già analizzate e quanto manca. */
export default function InitBanner({ onDone }: { onDone: () => void }) {
  const { call, lang } = useApp();
  const [st, setSt] = useState<any>(null);
  const [just, setJust] = useState(false);
  const was = useRef(false);
  const L = T[lang as Lang];

  useEffect(() => {
    let stop = false, timer: any;
    const tick = async () => {
      try {
        const s = await call("/onboarding/status");
        if (stop) return;
        setSt(s);
        if (s.state === "working") { was.current = true; timer = setTimeout(tick, 8000); }
        else if (s.state === "done" && was.current) { was.current = false; setJust(true); onDone(); setTimeout(() => !stop && setJust(false), 10000); }
      } catch { if (!stop) timer = setTimeout(tick, 20000); }
    };
    tick();
    return () => { stop = true; clearTimeout(timer); };
  }, [call]); // eslint-disable-line

  if (just) return <div className="note ok" role="status">{f(L.done, { t: st?.total ?? 0 })}</div>;
  if (!st || st.state !== "working") return null;
  const pct = st.total ? Math.round((100 * st.analyzed) / st.total) : 0;
  return (
    <div className="card init-banner" role="status" aria-live="polite">
      <div className="row"><b>{L.title}</b><span className="muted small">{st.importing ? "" : st.eta_min > 1 ? f(L.eta, { n: st.eta_min }) : L.etaSoon}</span></div>
      <div className="muted small" style={{ margin: ".25rem 0" }}>{st.importing ? L.dl : f(L.prog, { a: st.analyzed, t: st.total })}</div>
      <div className="bar"><div style={{ width: `${st.importing ? 8 : pct}%`, background: "var(--ember)", transition: "width .6s" }} /></div>
      <p className="muted small" style={{ margin: ".5rem 0 0" }}>{L.hint}</p>
    </div>
  );
}
