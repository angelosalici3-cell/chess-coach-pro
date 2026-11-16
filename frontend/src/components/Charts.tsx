"use client";
import { useState } from "react";
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

export type LossPt = { ply: number; loss: number; color: string; you: boolean };
export function LossChart({ pts, active, onPick }: { pts: LossPt[]; active: number; onPick: (ply: number) => void }) {
  if (!pts.length) return null;
  const W = 640, H = 170, L = 34, B = 20, T = 8, CAP = 300;
  const bw = (W - L - 6) / pts.length;
  const y = (v: number) => H - B - (Math.min(v, CAP) / CAP) * (H - B - T);
  const ticks = [0, 100, 200, 300];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto" }} role="img" aria-label="Loss per move">
      {ticks.map((v) => (
        <g key={v}>
          <line x1={L} x2={W - 4} y1={y(v)} y2={y(v)} stroke="#26305a" strokeWidth="1" />
          <text x={L - 6} y={y(v) + 4} fill="#8d97b8" fontSize="11" textAnchor="end">{v === CAP ? `${v}+` : v}</text>
        </g>
      ))}
      {pts.map((p, i) => {
        const x = L + i * bw, top = y(p.loss), h = Math.max(p.loss > 0 ? 2 : 0, H - B - top);
        return (
          <g key={p.ply} onClick={() => onPick(p.ply)} style={{ cursor: "pointer" }}>
            <rect x={x} y={T} width={bw} height={H - B - T} fill="transparent" />
            <rect x={x + bw * 0.12} y={H - B - h} width={Math.max(1, bw * 0.76)} height={h} rx="1.5" style={{ fill: p.color }} opacity={p.ply === active ? 1 : p.you ? 0.9 : 0.35} />
            {p.ply === active && <rect x={x} y={T} width={bw} height={H - B - T} fill="none" stroke="#fff" strokeOpacity=".5" />}
          </g>
        );
      })}
      {pts.filter((p) => p.ply % 20 === 0).map((p) => (
        <text key={p.ply} x={L + (p.ply - 0.5) * bw} y={H - 5} fill="#8d97b8" fontSize="11" textAnchor="middle">{p.ply / 2}</text>
      ))}
    </svg>
  );
}

export type Series = { key: string; label: string; color: string; points: { d: string; r: number }[] };
const DAY = 86400000;
const ts = (d: string) => Date.parse(d + "T00:00:00Z");

/** Una linea per ritmo; scala adattata alle sole serie visibili e all'intervallo scelto; tooltip al passaggio del mouse/tocco. */
export function MultiLineChart({ series, days }: { series: Series[]; days: number | null }) {
  const [hover, setHover] = useState<number | null>(null);
  const all = series.flatMap((s) => s.points.map((p) => ts(p.d)));
  if (!all.length) return <p className="muted small">—</p>;
  const tMax = Math.max(...all);
  const tMin = days ? tMax - days * DAY : Math.min(...all);
  const vis = series.map((s) => ({ ...s, pts: s.points.filter((p) => ts(p.d) >= tMin) })).filter((s) => s.pts.length);
  if (!vis.length) return <p className="muted small">—</p>;
  const W = 640, H = 230, L = 42, R = 14, T = 12, B = 26;
  const rs = vis.flatMap((s) => s.pts.map((p) => p.r));
  const lo = Math.min(...rs), hi = Math.max(...rs), pad = Math.max(12, (hi - lo) * 0.12);
  const yMin = lo - pad, yMax = hi + pad, span = Math.max(1, tMax - tMin);
  const x = (t: number) => L + ((t - tMin) / span) * (W - L - R);
  const y = (r: number) => H - B - ((r - yMin) / (yMax - yMin)) * (H - B - T);
  const dates = Array.from(new Set(vis.flatMap((s) => s.pts.map((p) => ts(p.d))))).sort((a, b) => a - b);
  const step = (yMax - yMin) / 3;
  const grid = [0, 1, 2, 3].map((i) => Math.round(yMin + i * step));
  const fmt = (t: number) => new Date(t).toISOString().slice(5, 10).split("-").reverse().join("/");
  const at = (s: (typeof vis)[number], t: number) => { let v: number | null = null; for (const p of s.pts) { if (ts(p.d) <= t) v = p.r; else break; } return v; };
  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    let best = dates[0];
    for (const d of dates) if (Math.abs(x(d) - px) < Math.abs(x(best) - px)) best = d;
    setHover(best);
  };
  const tip = hover != null ? vis.map((s) => ({ s, v: at(s, hover) })).filter((z) => z.v != null) : [];
  const tipRight = hover != null && x(hover) > W * 0.6;
  return (
    <div className="mlc">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Rating" onPointerMove={onMove} onPointerDown={onMove} onPointerLeave={() => setHover(null)} style={{ touchAction: "pan-y" }}>
        {grid.map((v) => (
          <g key={v}><line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="#26305a" /><text x={L - 7} y={y(v) + 4} fill="#8d97b8" fontSize="11" textAnchor="end">{v}</text></g>
        ))}
        <text x={L} y={H - 7} fill="#8d97b8" fontSize="11">{fmt(tMin)}</text>
        <text x={W - R} y={H - 7} fill="#8d97b8" fontSize="11" textAnchor="end">{fmt(tMax)}</text>
        {vis.map((s) => (
          <g key={s.key}>
            {s.pts.length > 1 && <polyline fill="none" stroke={s.color} strokeWidth="2.4" strokeLinejoin="round" strokeLinecap="round" points={s.pts.map((p) => `${x(ts(p.d)).toFixed(1)},${y(p.r).toFixed(1)}`).join(" ")} />}
            {s.pts.length <= 40 && s.pts.map((p) => <circle key={p.d} cx={x(ts(p.d))} cy={y(p.r)} r="2.6" fill={s.color} />)}
            <circle cx={x(ts(s.pts[s.pts.length - 1].d))} cy={y(s.pts[s.pts.length - 1].r)} r="4.5" fill={s.color} />
          </g>
        ))}
        {hover != null && <line x1={x(hover)} x2={x(hover)} y1={T} y2={H - B} stroke="#fff" strokeOpacity=".35" strokeDasharray="3 3" />}
        {hover != null && tip.map(({ s, v }) => <circle key={s.key} cx={x(hover)} cy={y(v as number)} r="5" fill={s.color} stroke="#0b0f1e" strokeWidth="2" />)}
      </svg>
      {hover != null && (
        <div className="mlc-tip" style={{ [tipRight ? "right" : "left"]: `${tipRight ? 100 - (x(hover) / W) * 100 : (x(hover) / W) * 100}%` } as React.CSSProperties}>
          <b>{fmt(hover)}</b>
          {tip.map(({ s, v }) => <div key={s.key}><i style={{ background: s.color }} />{s.label} <b>{v}</b></div>)}
        </div>
      )}
    </div>
  );
}
