export function LineChart({ points }: { points: { d: string; r: number }[] }) {
  if (points.length < 2) return <p className="muted small">—</p>;
  const W = 600, H = 190, P = 30;
  const rs = points.map((p) => p.r), min = Math.min(...rs) - 10, max = Math.max(...rs) + 10;
  const x = (i: number) => P + (i * (W - 2 * P)) / (points.length - 1);
  const y = (r: number) => H - P - ((r - min) / (max - min)) * (H - 2 * P);
  const line = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.r).toFixed(1)}`).join(" ");
  const area = `${line} L${x(points.length - 1).toFixed(1)},${H - P} L${x(0).toFixed(1)},${H - P} Z`;
  const last = points[points.length - 1];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto" }} role="img" aria-label="Rating">
      <defs><linearGradient id="lc" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ff6b3d" stopOpacity=".35" /><stop offset="1" stopColor="#ff6b3d" stopOpacity="0" /></linearGradient></defs>
      <path d={area} fill="url(#lc)" />
      <path d={line} fill="none" stroke="#ff6b3d" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={x(points.length - 1)} cy={y(last.r)} r="4.5" fill="#ff6b3d" />
      <text x={P} y={14} fill="#8d97b8" fontSize="12">{max - 10}</text>
      <text x={P} y={H - 8} fill="#8d97b8" fontSize="12">{min + 10}  {points[0].d}</text>
      <text x={W - P} y={H - 8} fill="#8d97b8" fontSize="12" textAnchor="end">{last.d}  {last.r}</text>
    </svg>
  );
}

export function Bar({ pct, color = "var(--ember)" }: { pct: number; color?: string }) {
  return <div className="bar"><div style={{ width: `${Math.max(0, Math.min(100, pct))}%`, background: color }} /></div>;
}
