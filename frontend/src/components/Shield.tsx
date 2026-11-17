const METAL = [
  { a: "#2a3566", b: "#151c3d", edge: "#2f3a6e" },           // 0 bloccato
  { a: "#e9ab78", b: "#9b5a2a", edge: "#f6c79b" },           // 1 bronzo
  { a: "#f4f7fd", b: "#8d99b8", edge: "#ffffff" },           // 2 argento
  { a: "#ffe38f", b: "#d98d24", edge: "#fff3c2" },           // 3 oro
];
const PATH = "M50 4 L92 18 V52 C92 76 72 92 50 102 C28 92 8 76 8 52 V18 Z";

const ICONS: Record<string, string> = {
  streak: "M12 2c1 4 5 6 5 11a5 5 0 01-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3-1-6 1-10z",
  fixed: "M5 12.5l4.5 4.5L19 7.5",
  lessons: "M5 4h9a3 3 0 013 3v13H8a3 3 0 01-3-3zM8 8h6M8 12h6",
  accuracy: "M12 3a9 9 0 100 18 9 9 0 000-18zm0 5a4 4 0 100 8 4 4 0 000-8zm0 3a1 1 0 100 2 1 1 0 000-2z",
  openings: "M6 4v16M6 8h6a4 4 0 014 4v8M6 14h10",
  clean: "M12 3l2.2 6.3L21 12l-6.8 2.7L12 21l-2.2-6.3L3 12l6.8-2.7z",
};
const GLYPH: Record<string, string> = { games: "♟", analyzed: "♝", puzzles: "♞", puzzle_rating: "♛" };

/** Scudo araldico: bloccato (grigio), bronzo, argento oro. Il riflesso scorre solo sugli scudi conquistati. */
export default function Shield({ id, tier, size }: { id: string; tier: number; size?: number }) {
  const m = METAL[tier], uid = `sh-${id}-${tier}`, on = tier > 0;
  const glyph = GLYPH[id], icon = ICONS[id];
  return (
    <svg className="shield" viewBox="0 0 100 108" role="img" aria-hidden="true" style={size ? { width: size, height: size * 1.08 } : undefined}>
      <defs>
        <linearGradient id={uid} x1="0" y1="0" x2="0.6" y2="1"><stop offset="0" stopColor={m.a} /><stop offset="1" stopColor={m.b} /></linearGradient>
        <linearGradient id={uid + "s"} x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#fff" stopOpacity="0" /><stop offset=".5" stopColor="#fff" stopOpacity=".55" /><stop offset="1" stopColor="#fff" stopOpacity="0" /></linearGradient>
        <clipPath id={uid + "c"}><path d={PATH} /></clipPath>
      </defs>
      <path d={PATH} fill={`url(#${uid})`} stroke={m.edge} strokeWidth="2.5" strokeLinejoin="round" opacity={on ? 1 : 0.55} />
      <path d="M50 12 L84 23 V52 C84 71 68 84 50 93 C32 84 16 71 16 52 V23 Z" fill="none" stroke={on ? "rgba(255,255,255,.45)" : "rgba(255,255,255,.08)"} strokeWidth="1.4" />
      {on && <g clipPath={`url(#${uid}c)`}><rect className="shield-shine" x="0" y="0" width="34" height="108" fill={`url(#${uid}s)`} transform="skewX(-18)" /></g>}
      {glyph ? (
        <text x="50" y="62" textAnchor="middle" fontSize="40" fill={on ? "#1b1206" : "#4a5688"} fillOpacity={on ? 0.82 : 1}>{glyph}</text>
      ) : (
        <path d={icon} transform="translate(26 24) scale(2)" fill={id === "streak" || id === "clean" ? (on ? "#1b1206" : "#4a5688") : "none"} fillOpacity={on ? 0.82 : 1}
          stroke={on ? "#1b1206" : "#4a5688"} strokeOpacity={on ? 0.82 : 1} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      )}
    </svg>
  );
}
