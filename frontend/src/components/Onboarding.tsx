"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { STEPS, ui } from "../lib/onboarding-copy";
import { LogoMark } from "./Logo";
import Shield from "./Shield";
import type { Lang } from "../lib/i18n";

/** Piccole illustrazioni animate, una per passo. */
function Art({ id }: { id: string }) {
  const c = { stroke: "var(--ember)", strokeWidth: 3, fill: "none", strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (id === "welcome") return <div className="ob-logo"><LogoMark size={92} /></div>;
  if (id === "badges") return <div className="ob-shields"><Shield id="games" tier={1} size={64} /><Shield id="streak" tier={2} size={78} /><Shield id="puzzles" tier={3} size={64} /></div>;
  return (
    <svg viewBox="0 0 240 130" className="ob-svg" aria-hidden="true">
      {id === "connect" && (<><circle cx="60" cy="65" r="30" fill="var(--ink-3)" stroke="var(--line-2)" /><text x="60" y="71" textAnchor="middle" fill="var(--ice)" fontSize="16" fontWeight="800">Li</text>
        <circle cx="180" cy="65" r="30" fill="var(--ink-3)" stroke="var(--line-2)" /><text x="180" y="71" textAnchor="middle" fill="var(--ice)" fontSize="16" fontWeight="800">C.c</text>
        <path d="M92 65h56" {...c} className="ob-draw" /><circle cx="120" cy="65" r="11" fill="var(--mint)" /><path d="M114 65l4 4 8-8" stroke="#06231a" strokeWidth="3" fill="none" strokeLinecap="round" /></>)}
      {id === "home" && (<><path d="M14 14v102h212" stroke="var(--line-2)" fill="none" /><path d="M20 100 L55 84 L85 92 L120 60 L150 70 L185 36 L222 26" {...c} className="ob-draw" /><circle cx="222" cy="26" r="5" fill="var(--ember)" /></>)}
      {id === "game" && (<>{Array.from({ length: 16 }).map((_, i) => <rect key={i} x={20 + (i % 4) * 28} y={10 + Math.floor(i / 4) * 28} width="28" height="28" fill={(i + Math.floor(i / 4)) % 2 ? "#3b4a85" : "#222c57"} />)}
        <rect x="76" y="38" width="28" height="28" fill="var(--bad)" opacity=".7" /><rect x="48" y="66" width="28" height="28" fill="var(--mint)" opacity=".7" />
        {[0, 1, 2, 3, 4].map((i) => <rect key={i} className="ob-bar" style={{ animationDelay: `${i * 90}ms` }} x={150 + i * 16} y={118 - [30, 54, 22, 84, 40][i]} width="10" height={[30, 54, 22, 84, 40][i]} rx="3" fill={i === 3 ? "var(--bad)" : "var(--ember)"} />)}</>)}
      {id === "lessons" && (<><rect x="40" y="14" width="160" height="102" rx="14" fill="var(--ink-3)" stroke="var(--line-2)" />
        {[0, 1, 2].map((i) => <g key={i}><rect x="56" y={30 + i * 28} width="26" height="10" rx="5" fill="var(--ember)" /><rect className="ob-line" style={{ animationDelay: `${i * 160}ms` }} x="90" y={30 + i * 28} width={[96, 80, 64][i]} height="10" rx="5" fill="var(--line-2)" /></g>)}</>)}
      {id === "train" && (<><path d="M118 8L82 60h30l-8 54 46-64h-30z" fill="var(--ember)" className="ob-pop" />
        {[0, 1, 2, 3, 4].map((i) => <circle key={i} cx={70 + i * 25} cy="122" r="5" fill={i < 3 ? "var(--mint)" : "var(--line-2)"} />)}</>)}
      {id === "atlas" && (<><g stroke="var(--line-2)" strokeWidth="2" fill="none"><path d="M44 65H84M84 65Q104 65 104 38H128M84 65Q104 65 104 92H128M128 38H152M128 92Q148 92 148 112H172" className="ob-draw" /></g>
        {[[22, 65, "var(--ember)"], [86, 38, "var(--mint)"], [86, 92, "var(--amber)"], [150, 38, "var(--bad)"], [150, 112, "var(--mint)"]].map(([x, y, col], i) => <rect key={i} x={Number(x) + 20} y={Number(y) - 12} width="40" height="24" rx="8" fill="var(--ink-3)" stroke={String(col)} strokeWidth="2" />)}</>)}
      {id === "menu" && (<><rect x="14" y="10" width="86" height="110" rx="12" fill="var(--ink-3)" stroke="var(--line-2)" /><circle cx="36" cy="32" r="10" fill="var(--ember)" />
        {[0, 1, 2, 3].map((i) => <rect key={i} className="ob-line" style={{ animationDelay: `${i * 140}ms` }} x="24" y={54 + i * 15} width={[60, 48, 56, 40][i]} height="8" rx="4" fill="var(--line-2)" />)}
        <path d="M130 40h80M130 65h80M130 90h80" {...c} className="ob-draw" /></>)}
      {id === "plans" && [0, 1, 2, 3].map((i) => <g key={i}><rect x={14 + i * 56} y={52 - i * 12} width="48" height={70 + i * 12} rx="10" fill="var(--ink-3)" stroke={i === 3 ? "var(--ember)" : "var(--line-2)"} strokeWidth="2" /><rect x={22 + i * 56} y={62 - i * 12} width="32" height="8" rx="4" fill={i === 3 ? "var(--ember)" : "var(--line-2)"} /></g>)}
    </svg>
  );
}

export default function Onboarding({ lang, me, onClose }: { lang: Lang; me: any; onClose: () => void }) {
  const [i, setI] = useState(0);
  const router = useRouter();
  const s = STEPS[i], last = i === STEPS.length - 1;
  const main = useRef<HTMLButtonElement>(null);
  const go = (n: number) => setI(Math.max(0, Math.min(STEPS.length - 1, n)));

  useEffect(() => { main.current?.focus(); }, [i]);
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") go(i + 1);
      if (e.key === "ArrowLeft") go(i - 1);
    };
    window.addEventListener("keydown", k);
    const prev = document.body.style.overflow; document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", k); document.body.style.overflow = prev; };
  }, [i]); // eslint-disable-line

  // contenuto dinamico: legge lo stato reale dell'utente
  let live: React.ReactNode = null;
  if (s.id === "connect" && me) live = <div className={"ob-live " + (me.profiles.used > 0 ? "ok" : "todo")}>{me.profiles.used > 0 ? "✓ " + ui("linked", lang) : ui("notLinked", lang)}</div>;
  if (s.id === "lessons" && me) live = <div className="ob-live">{ui("lessonsLeft", lang, { a: me.lessons.used, b: me.lessons.limit ?? ui("unlimited", lang) })}</div>;
  if (s.id === "plans" && me) live = <div className="ob-live">{ui("plan", lang, { t: me.tier, n: me.history_games ?? 50 })}</div>;

  const open = () => { onClose(); if (s.href) router.push(s.href); };
  return (
    <div className="ob-back" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="ob" role="dialog" aria-modal="true" aria-labelledby="ob-t">
        <button className="ob-x" onClick={onClose} aria-label={ui("close", lang)}>×</button>
        <div className="ob-art" key={s.id}><Art id={s.id} /></div>
        <div className="ob-body" key={"b" + s.id}>
          <div className="muted small">{ui("step", lang, { a: i + 1, b: STEPS.length })}</div>
          <h2 id="ob-t">{s.title[lang]}</h2>
          <p>{s.body[lang]}</p>
          <ul>{s.points[lang].map((p) => <li key={p}>{p}</li>)}</ul>
          {live}
        </div>
        <div className="ob-dots" role="tablist">{STEPS.map((x, n) => <button key={x.id} className={n === i ? "on" : n < i ? "seen" : ""} onClick={() => go(n)} aria-label={x.title[lang]} aria-current={n === i} />)}</div>
        <div className="ob-foot">
          {i > 0 ? <button className="btn btn-sm" onClick={() => go(i - 1)}>{ui("back", lang)}</button> : <button className="btn btn-sm ob-skip" onClick={onClose}>{ui("skip", lang)}</button>}
          <div className="row">
            {s.href && !last && s.cta && <button className="btn btn-sm" onClick={open}>{s.cta[lang]}</button>}
            {last
              ? <button ref={main} className="btn btn-primary" onClick={onClose}>{ui("done", lang)}</button>
              : <button ref={main} className="btn btn-primary" onClick={() => go(i + 1)}>{ui("next", lang)}</button>}
          </div>
        </div>
      </div>
    </div>
  );
}
