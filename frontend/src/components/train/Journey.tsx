"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "../app";

const T = {
  it: {
    title: "Il tuo percorso", coach: "Dal tuo coach", last30: "Ultimi 30 giorni", games: "Partite", wins: "Vittorie", acc: "Precisione", vs: "rispetto ai 30 giorni prima",
    curve: "Rating medio per mese", empty: "Il coach scrive la prima lettera dopo {n} partite analizzate. Ne hai {a}.", firstTitle: "Prima impressione",
    letters: "Le lettere del coach", week: "Lettera settimanale", month: "Lettera mensile", season: "La tua stagione", first: "Prima impressione",
    weak: "Da sistemare", gen: "Il coach sta scrivendo…", none: "Nessuna lettera ancora", wait: "La prossima lettera arriva a fine {p}.",
    pw: "settimana", pm: "mese", up: "Con {plan} il coach ti scrive ogni {per} e confronta i tuoi progressi.", see: "Vedi i piani", from: "da",
    best: "Apertura più riuscita", worst: "Da migliorare",
  },
  en: {
    title: "Your journey", coach: "From your coach", last30: "Last 30 days", games: "Games", wins: "Wins", acc: "Accuracy", vs: "vs the 30 days before",
    curve: "Average rating per month", empty: "Your coach writes the first letter after {n} analysed games. You have {a}.", firstTitle: "First impression",
    letters: "Coach letters", week: "Weekly letter", month: "Monthly letter", season: "Your season", first: "First impression",
    weak: "To fix", gen: "The coach is writing…", none: "No letters yet", wait: "The next letter arrives at the end of the {p}.",
    pw: "week", pm: "month", up: "With {plan} your coach writes every {per} and compares your progress.", see: "See plans", from: "from",
    best: "Best opening", worst: "To improve",
  },
  es: {
    title: "Tu camino", coach: "De tu entrenador", last30: "Últimos 30 días", games: "Partidas", wins: "Victorias", acc: "Precisión", vs: "frente a los 30 días anteriores",
    curve: "Rating medio por mes", empty: "Tu entrenador escribe la primera carta tras {n} partidas analizadas. Tienes {a}.", firstTitle: "Primera impresión",
    letters: "Cartas del entrenador", week: "Carta semanal", month: "Carta mensual", season: "Tu temporada", first: "Primera impresión",
    weak: "Por corregir", gen: "El entrenador está escribiendo…", none: "Aún no hay cartas", wait: "La próxima carta llega a final de {p}.",
    pw: "semana", pm: "mes", up: "Con {plan} tu entrenador te escribe cada {per} y compara tus progresos.", see: "Ver planes", from: "desde",
    best: "Mejor apertura", worst: "A mejorar",
  },
} as const;


// lettera in paragrafi brevi (due frasi ciascuno) con i numeri in evidenza
function paras(text: string): (string)[][] {
  const sents = text.replace(/\s+/g, " ").trim().split(/(?<=[.!?])\s+(?=[A-ZÀ-Ý¿¡])/);
  const out: string[] = [];
  for (let i = 0; i < sents.length; i += 2) out.push(sents.slice(i, i + 2).join(" "));
  return out.map((p) => p.split(/(\d[\d.,]*\s?%?)/).filter(Boolean));
}

function Delta({ a, b, unit = "" }: { a: number | null | undefined; b: number | null | undefined; unit?: string }) {
  if (a == null || b == null) return null;
  const d = Math.round((a - b) * 10) / 10;
  if (!d) return <span className="jy-d">=</span>;
  return <span className={"jy-d " + (d > 0 ? "up" : "down")}>{d > 0 ? "▲" : "▼"} {Math.abs(d)}{unit}</span>;
}

function Curve({ pts }: { pts: { m: string; elo: number }[] }) {
  if (pts.length < 2) return null;
  const W = 600, H = 190, pad = 28, lo = Math.min(...pts.map((p) => p.elo)) - 30, hi = Math.max(...pts.map((p) => p.elo)) + 30;
  const x = (i: number) => pad + (i * (W - 2 * pad)) / (pts.length - 1), y = (v: number) => H - pad - ((v - lo) / (hi - lo)) * (H - 2 * pad);
  const d = pts.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(p.elo).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="jy-curve" role="img" aria-label="rating">
      <path d={`${d} L${x(pts.length - 1)} ${H - pad} L${x(0)} ${H - pad} Z`} fill="var(--ember)" opacity=".12" />
      <path d={d} fill="none" stroke="var(--ember)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      {pts.map((p, i) => (i === 0 || i === pts.length - 1 || pts.length < 7) && (
        <g key={p.m}><circle cx={x(i)} cy={y(p.elo)} r="4.5" fill="var(--ember)" /><text x={x(i)} y={y(p.elo) - 11} textAnchor="middle" fontSize="14" fontWeight="700" fill="var(--ice)">{p.elo}</text><text x={x(i)} y={H - 6} textAnchor="middle" fontSize="12" fill="var(--mute)">{p.m.slice(2)}</text></g>
      ))}
    </svg>
  );
}

export default function Journey() {
  const { call, lang } = useApp();
  const t = T[lang] || T.it;
  const [d, setD] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    let live = true;
    (async () => {
      try {
        let r = await call("/profile/journey");
        if (!live) return;
        setD(r);
        if (r.due?.length) {   // lettere in arrivo: si scrivono ora, una volta sola per periodo
          setBusy(true);
          await call(`/profile/journey/generate?lang=${lang}`, { method: "POST" });
          r = await call("/profile/journey");
          if (live) setD(r);
        }
      } catch (e: any) { if (live) setErr(e.message); } finally { if (live) setBusy(false); }
    })();
    return () => { live = false; };
  }, [call, lang]);

  if (err) return <div className="note err">{err}</div>;
  if (!d) return <p className="muted">…</p>;
  const n = d.now, b = d.before, all = d.all;
  const latest = d.reports[0], older = d.reports.slice(1);
  const kindName = (k: string) => (t as any)[k];
  const nextKind = d.cadence?.[0];
  const plan = d.tier === "Free" ? "Plus" : null;
  return (
    <div className="jy">
      <section className="card jy-letter">
        <div className="jy-lh">
          <span className="jy-av" aria-hidden="true">♞</span>
          <div><b>{t.coach}</b><div className="muted small">{latest ? `${kindName(latest.kind)} · ${new Date(latest.created_at).toLocaleDateString(lang, { day: "numeric", month: "long", year: "numeric" })}` : ""}</div></div>
        </div>
        {latest ? <div className="jy-body">{paras(latest.text).map((p, i) => <p key={i}>{p.map((x, k) => (/^\d/.test(x) ? <b key={k}>{x}</b> : x))}</p>)}</div>
          : busy ? <p className="jy-quote muted">{t.gen}</p>
          : <p className="jy-quote muted">{t.empty.replace("{n}", d.first_at).replace("{a}", all.analyzed ?? 0)}</p>}
        {nextKind && latest && <div className="muted small jy-next">{t.wait.replace("{p}", nextKind === "week" ? t.pw : t.pm)}</div>}
      </section>

      <section className="jy-stats">
        {[["games", t.games, n.games, b.games, ""], ["wins", t.wins, n.win_pct, b.win_pct, "%"], ["acc", t.acc, n.acc, b.acc, "%"]].map(([k, l, v, pv, u]: any) => (
          <div key={k} className="card jy-stat">
            <div className="muted small">{l}</div>
            <b className="jy-big">{v ?? "—"}{v != null ? u : ""}</b>
            <Delta a={v} b={pv} unit={u} />
          </div>
        ))}
        <div className="muted small jy-cap">{t.last30} · {t.vs}</div>
      </section>

      {d.curve.length > 1 && <section className="card"><div className="muted small">{t.curve}</div><Curve pts={d.curve} /></section>}

      {(all.best_opening || d.weak?.length > 0) && (
        <section className="jy-two">
          {all.best_opening && <div className="card"><div className="muted small">{t.best}</div><b>{all.best_opening[0]}</b><div className="muted small">{all.best_opening[2]}% · {all.best_opening[1]}</div></div>}
          {d.weak?.length > 0 && <div className="card"><div className="muted small">{t.weak}</div>{d.weak.map((w: string) => <div key={w}><b>{w}</b></div>)}</div>}
        </section>
      )}

      {older.length > 0 && (
        <section>
          <h2 className="jy-h">{t.letters}</h2>
          <div className="jy-tl">
            {older.map((r: any) => (
              <article key={r.id} className="card jy-item">
                <div className="muted small">{kindName(r.kind)} · {r.kind === "first" ? new Date(r.created_at).toLocaleDateString(lang) : r.period}</div>
                <p>{r.text}</p>
              </article>
            ))}
          </div>
        </section>
      )}

      {plan && (
        <section className="card jy-up">
          <p style={{ margin: 0 }}>{t.up.replace("{plan}", plan).replace("{per}", t.pm)}</p>
          <Link href="/dashboard/plans" className="btn btn-primary btn-sm">{t.see}</Link>
        </section>
      )}
    </div>
  );
}
