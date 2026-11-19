"use client";
import { useEffect, useRef, useState } from "react";
import { Logo } from "./Logo";

const MIN_MS = 1500;     // l'intro si vede almeno questo tempo, anche se i dati sono già pronti
const MAX_MS = 9000;     // e non resta mai bloccata se i dati non arrivano
const OPEN_MS = 1000;    // durata dell'apertura del portone

/** Cerchio che gira intorno al logo mentre si caricano i dati; poi un portone a due ante si apre e lascia spazio all'app. */
export default function Intro({ ready }: { ready: boolean }) {
  const [phase, setPhase] = useState<"load" | "open" | "gone">("load");
  const t0 = useRef(Date.now());

  useEffect(() => {
    if (phase !== "load") return;
    const left = ready ? Math.max(0, MIN_MS - (Date.now() - t0.current)) : Math.max(0, MAX_MS - (Date.now() - t0.current));
    const id = setTimeout(() => setPhase("open"), left);
    return () => clearTimeout(id);
  }, [ready, phase]);
  useEffect(() => {
    if (phase !== "open") return;
    const id = setTimeout(() => setPhase("gone"), OPEN_MS);
    return () => clearTimeout(id);
  }, [phase]);
  useEffect(() => {
    if (phase === "gone") return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, [phase]);

  if (phase === "gone") return null;
  return (
    <div className={"intro " + phase} role="status" aria-label="Loading" aria-live="polite">
      <div className="intro-door l" aria-hidden="true" />
      <div className="intro-door r" aria-hidden="true" />
      <div className="intro-mark" aria-hidden="true">
        <svg className="intro-ring" viewBox="0 0 140 140">
          <defs>
            <linearGradient id="introGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#ff6b3d" /><stop offset="1" stopColor="#ff3d5a" />
            </linearGradient>
          </defs>
          <circle cx="70" cy="70" r="62" fill="none" stroke="rgba(190,205,255,.12)" strokeWidth="3" />
          <circle className="intro-arc" cx="70" cy="70" r="62" fill="none" stroke="url(#introGrad)" strokeWidth="4" strokeLinecap="round" strokeDasharray="110 280" />
        </svg>
        <div className="intro-logo"><Logo size={64} text={false} /></div>
        <div className="intro-name">Chess Coach</div>
      </div>
    </div>
  );
}
