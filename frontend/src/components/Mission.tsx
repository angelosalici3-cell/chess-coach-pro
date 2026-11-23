"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "./app";

const X = {
  it: { t: "La tua missione di oggi", sub: "Tre mosse per crescere un po' ogni giorno.", streak: (n: number) => `🔥 ${n} giorni di fila`,
        s1: "Gioca una partita", s1d: "Rapid o classica su Lichess, senza aiuti", s2: "Ripassa i tuoi errori", s2d: (n: number) => n > 0 ? `${n} da rivedere oggi` : "Niente in coda: ottimo", s3: "Studia una lezione", s3d: "Il Gran Maestro spiega la tua partita", go: "Vai" },
  en: { t: "Your mission for today", sub: "Three moves to improve a little every day.", streak: (n: number) => `🔥 ${n}-day streak`,
        s1: "Play a game", s1d: "Rapid or classical on Lichess, no help", s2: "Review your mistakes", s2d: (n: number) => n > 0 ? `${n} to review today` : "Nothing queued: great", s3: "Study a lesson", s3d: "The Grandmaster explains your game", go: "Go" },
  es: { t: "Tu misión de hoy", sub: "Tres jugadas para mejorar un poco cada día.", streak: (n: number) => `🔥 ${n} días seguidos`,
        s1: "Juega una partida", s1d: "Rápida o clásica en Lichess, sin ayudas", s2: "Repasa tus errores", s2d: (n: number) => n > 0 ? `${n} por repasar hoy` : "Nada pendiente: genial", s3: "Estudia una lección", s3d: "El Gran Maestro explica tu partida", go: "Ir" },
} as const;

/** Home: cosa fare oggi, in tre passi, con la serie di giorni. */
export default function Mission() {
  const { call, lang } = useApp();
  const x = X[lang];
  const [o, setO] = useState<any>(null);
  useEffect(() => { call("/train/overview").then(setO).catch(() => {}); }, [call]);
  const due = o ? (o.mistakes_due || 0) + (o.mistakes_new || 0) : 0;
  const steps = [
    { href: "/dashboard/play", n: 1, t: x.s1, d: x.s1d, done: false },
    { href: "/dashboard/train", n: 2, t: x.s2, d: x.s2d(due), done: !!o?.done_today },
    { href: "/dashboard/games?tab=lessons", n: 3, t: x.s3, d: x.s3d, done: false },
  ];
  const streak = o?.stats?.current_streak || 0;
  return (
    <section className="mission">
      <div className="mission-top">
        <div><h2>{x.t}</h2><div className="muted small">{x.sub}</div></div>
        {streak > 0 && <span className="mission-streak">{x.streak(streak)}</span>}
      </div>
      <ul>
        {steps.map((s) => (
          <li key={s.n} className={s.done ? "done" : ""}>
            <Link href={s.href}><span className="step">{s.done ? "✓" : s.n}</span><span><b>{s.t}</b><small>{s.d}</small></span><span className="go">{x.go} ›</span></Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
