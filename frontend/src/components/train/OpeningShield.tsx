import { METAL, PATH } from "../Shield";
import { EMBLEM, emblemFor } from "../../lib/opening-icons";

/** Scudo di un'apertura: grigio finché non inizi, bronzo, argento (metà imparata), oro (tutto imparato). Il puntino indica il lato. */
export default function OpeningShield({ id, name, tier, side, size = 64 }: { id: string; name: string; tier: 0 | 1 | 2 | 3; side: "w" | "b"; size?: number }) {
  const m = METAL[tier], uid = `os-${id}`, on = tier > 0;
  const ink = on ? "#1b1206" : "#4a5688";
  return (
    <svg className="shield opshield" viewBox="0 0 100 108" aria-hidden="true" style={{ width: size, height: size * 1.08 }}>
      <defs>
        <linearGradient id={uid} x1="0" y1="0" x2="0.6" y2="1"><stop offset="0" stopColor={m.a} /><stop offset="1" stopColor={m.b} /></linearGradient>
        <linearGradient id={uid + "s"} x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#fff" stopOpacity="0" /><stop offset=".5" stopColor="#fff" stopOpacity=".55" /><stop offset="1" stopColor="#fff" stopOpacity="0" /></linearGradient>
        <clipPath id={uid + "c"}><path d={PATH} /></clipPath>
      </defs>
      <path d={PATH} fill={`url(#${uid})`} stroke={m.edge} strokeWidth="2.5" strokeLinejoin="round" opacity={on ? 1 : 0.55} />
      <path d="M50 12 L84 23 V52 C84 71 68 84 50 93 C32 84 16 71 16 52 V23 Z" fill="none" stroke={on ? "rgba(255,255,255,.45)" : "rgba(255,255,255,.08)"} strokeWidth="1.4" />
      {tier >= 3 && <g clipPath={`url(#${uid}c)`}><rect className="shield-shine" x="0" y="0" width="34" height="108" fill={`url(#${uid}s)`} transform="skewX(-18)" /></g>}
      <path d={EMBLEM[emblemFor(name)]} transform="translate(24 20) scale(2.1)" fill="none" stroke={ink} strokeOpacity={on ? 0.85 : 1} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="50" cy="84" r="5.2" fill={side === "w" ? "#f4f7fd" : "#10142e"} stroke={ink} strokeOpacity=".7" strokeWidth="1.3" />
    </svg>
  );
}
