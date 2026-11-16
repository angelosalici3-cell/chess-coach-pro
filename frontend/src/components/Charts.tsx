export function LineChart({ points }: { points: { d: string; r: number }[] }) {
  if (points.length < 2) return <p className="muted small">—</p>;
  const W = 600, H = 180, P = 28;
  const rs = points.map((p) => p.r), min = Math.min(...rs) - 10, max = Math.max(...rs) + 10;
  const x = (i: number) => P + (i * (W - 2 * P)) / (points.length - 1);
  const y = (r: number) => H - P - ((r - min) / (max - min)) * (H - 2 * P);
  const path = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.r).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto" }}>
      <path d={path} fill="none" stroke="#ffd700" strokeWidth="2.5" strokeLinejoin="round" />
      <text x={P} y={14} fill="#8892a6" fontSize="12">{max - 10}</text>
      <text x={P} y={H - 8} fill="#8892a6" fontSize="12">{min + 10} · {points[0].d}</text>
      <text x={W - P} y={H - 8} fill="#8892a6" fontSize="12" textAnchor="end">{points[points.length - 1].d} · {points[points.length - 1].r}</text>
    </svg>
  );
}

export function Bar({ pct, color = "#ffd700" }: { pct: number; color?: string }) {
  return <div className="bar"><div style={{ width: `${Math.max(0, Math.min(100, pct))}%`, background: color }} /></div>;
}
