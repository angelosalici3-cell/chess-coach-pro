"use client";
import { useEffect, useRef, useState } from "react";

/** Larghezza reale del contenitore: i grafici si disegnano a misura dello schermo, così testi e assi restano leggibili anche su telefono. */
export function useWidth(initial = 340): [React.RefObject<HTMLDivElement | null>, number] {
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(initial);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const set = () => setW(Math.max(240, Math.round(el.getBoundingClientRect().width)));
    set();
    const ro = new ResizeObserver(set); ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}
const AXIS = "#a9b3d6", GRID = "#26305a", FS = 13;

export function Bar({ pct, color = "var(--ember)" }: { pct: number; color?: string }) {
  return <div className="bar"><div style={{ width: `${Math.max(0, Math.min(100, pct))}%`, background: color }} /></div>;
}

export type LossPt = { ply: number; loss: number; color: string; you: boolean };
export function LossChart({ pts, active, onPick }: { pts: LossPt[]; active: number; onPick: (ply: number) => void }) {
  const [ref, W] = useWidth();
  if (!pts.length) return <div ref={ref} />;
  const H = 210, L = 44, B = 26, T = 10, CAP = 300, R = 6;
  const bw = (W - L - R) / pts.length;
  const y = (v: number) => H - B - (Math.min(v, CAP) / CAP) * (H - B - T);
  const ticks = [0, 100, 200, 300];
  const every = W < 420 ? 20 : 10;      // un'etichetta ogni 10 o 20 mosse (in mosse intere)
  return (
    <div ref={ref}>
      <svg width={W} height={H} role="img" aria-label="Loss per move" style={{ display: "block" }}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke={GRID} strokeWidth="1" />
            <text x={L - 8} y={y(v) + 4} fill={AXIS} fontSize={FS} textAnchor="end">{v === 0 ? "0" : `−${v / 100}`}</text>
          </g>
        ))}
        {pts.map((p, i) => {
          const x = L + i * bw, top = y(p.loss), h = Math.max(p.loss > 0 ? 2 : 0, H - B - top);
          return (
            <g key={p.ply} onClick={() => onPick(p.ply)} style={{ cursor: "pointer" }}>
              <rect x={x} y={T} width={bw} height={H - B - T} fill="transparent" />
              <rect x={x + bw * 0.12} y={H - B - h} width={Math.max(1.5, bw * 0.76)} height={h} rx="1.5" style={{ fill: p.color }} opacity={p.ply === active ? 1 : p.you ? 0.92 : 0.35} />
              {p.ply === active && <rect x={x} y={T} width={bw} height={H - B - T} fill="none" stroke="#fff" strokeOpacity=".55" />}
            </g>
          );
        })}
        {pts.filter((p) => p.ply % (every * 2) === 0).map((p) => (
          <text key={p.ply} x={L + (p.ply - 0.5) * bw} y={H - 7} fill={AXIS} fontSize={FS} textAnchor="middle">{p.ply / 2}</text>
        ))}
      </svg>
    </div>
  );
}

/** Andamento della partita: valutazione dal punto di vista di chi gioca (sopra lo zero sei meglio), area colorata e mossa critica segnata. */
export function EvalChart({ evals, active, onPick, critical }: { evals: number[]; active: number; onPick: (ply: number) => void; critical?: number }) {
  const [ref, W] = useWidth();
  if (evals.length < 2) return <div ref={ref} />;
  const H = 220, L = 44, B = 26, T = 12, R = 8, CAP = 500;
  const x = (i: number) => L + (i / (evals.length - 1)) * (W - L - R);
  const y = (v: number) => T + (1 - (Math.max(-CAP, Math.min(CAP, v)) + CAP) / (2 * CAP)) * (H - T - B);
  const zero = y(0);
  const pts = evals.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`);
  const line = "M" + pts.join(" L");
  const area = `${line} L${x(evals.length - 1).toFixed(1)},${zero} L${x(0).toFixed(1)},${zero} Z`;
  const every = W < 420 ? 20 : 10;
  const onTap = (e: React.PointerEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const i = Math.round(((e.clientX - r.left - L) / (W - L - R)) * (evals.length - 1));
    onPick(Math.max(0, Math.min(evals.length - 1, i)));
  };
  return (
    <div ref={ref}>
      <svg width={W} height={H} role="img" aria-label="Evaluation" style={{ display: "block", touchAction: "pan-y" }} onPointerDown={onTap}>
        <defs>
          <clipPath id="ev-up"><rect x="0" y="0" width={W} height={zero} /></clipPath>
          <clipPath id="ev-dn"><rect x="0" y={zero} width={W} height={H} /></clipPath>
        </defs>
        {[-400, -200, 0, 200, 400].map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke={v === 0 ? "#6c78a8" : GRID} strokeWidth={v === 0 ? 1.4 : 1} />
            <text x={L - 8} y={y(v) + 4} fill={AXIS} fontSize={FS} textAnchor="end">{v > 0 ? "+" : v < 0 ? "−" : ""}{Math.abs(v) / 100}</text>
          </g>
        ))}
        <path d={area} fill="#4ee3b0" fillOpacity=".28" clipPath="url(#ev-up)" />
        <path d={area} fill="#ff5d6c" fillOpacity=".28" clipPath="url(#ev-dn)" />
        <path d={line} fill="none" stroke="#e9eeff" strokeWidth="2.4" strokeLinejoin="round" strokeLinecap="round" />
        {critical != null && critical > 0 && critical < evals.length && (
          <g>
            <line x1={x(critical)} x2={x(critical)} y1={T} y2={H - B} stroke="#ff6b3d" strokeWidth="1.6" strokeDasharray="4 4" />
            <circle cx={x(critical)} cy={y(evals[critical])} r="6" fill="#ff6b3d" stroke="#0b0f1e" strokeWidth="2" />
          </g>
        )}
        {active > 0 && active < evals.length && <circle cx={x(active)} cy={y(evals[active])} r="5" fill="#fff" stroke="#0b0f1e" strokeWidth="2" />}
        {Array.from({ length: Math.floor((evals.length - 1) / (every * 2)) }, (_, k) => (k + 1) * every * 2).map((p) => (
          <text key={p} x={x(p)} y={H - 7} fill={AXIS} fontSize={FS} textAnchor="middle">{p / 2}</text>
        ))}
      </svg>
    </div>
  );
}

export type Series = { key: string; label: string; color: string; dash?: string; points: { d: string; r: number }[] };
const DAY = 86400000;
const ts = (d: string) => Date.parse(d + "T00:00:00Z");

/** Una linea per ritmo; scala adattata alle sole serie visibili e all'intervallo scelto; tooltip al passaggio del mouse/tocco. */
export function MultiLineChart({ series, days }: { series: Series[]; days: number | null }) {
  const [ref, W] = useWidth();
  const [hover, setHover] = useState<number | null>(null);
  const all = series.flatMap((s) => s.points.map((p) => ts(p.d)));
  if (!all.length) return <p className="muted small">—</p>;
  const tMax = Math.max(...all);
  const tMin = days ? tMax - days * DAY : Math.min(...all);
  const vis = series.map((s) => ({ ...s, pts: s.points.filter((p) => ts(p.d) >= tMin) })).filter((s) => s.pts.length);
  if (!vis.length) return <p className="muted small">—</p>;
  const H = W < 480 ? 250 : 280, L = 50, R = 14, T = 14, B = 30;
  const rs = vis.flatMap((s) => s.pts.map((p) => p.r));
  const lo = Math.min(...rs), hi = Math.max(...rs), pad = Math.max(12, (hi - lo) * 0.12);
  // asse del punteggio con righe a multipli di 50 (100 solo se l'intervallo è molto ampio)
  const step = (Math.ceil((hi + pad) / 50) * 50 - Math.floor((lo - pad) / 50) * 50) / 50 > 9 ? 100 : 50;
  const yMin = Math.floor((lo - pad) / step) * step, yMax = Math.ceil((hi + pad) / step) * step, span = Math.max(1, tMax - tMin);
  const x = (t: number) => L + ((t - tMin) / span) * (W - L - R);
  const y = (r: number) => H - B - ((r - yMin) / (yMax - yMin)) * (H - B - T);
  const dates = Array.from(new Set(vis.flatMap((s) => s.pts.map((p) => ts(p.d))))).sort((a, b) => a - b);
  const grid = Array.from({ length: Math.round((yMax - yMin) / step) + 1 }, (_, i) => yMin + i * step);
  const fmt = (t: number) => new Date(t).toISOString().slice(5, 10).split("-").reverse().join("/");
  const at = (s: (typeof vis)[number], t: number) => { let v: number | null = null; for (const p of s.pts) { if (ts(p.d) <= t) v = p.r; else break; } return v; };
  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - r.left;
    let best = dates[0];
    for (const d of dates) if (Math.abs(x(d) - px) < Math.abs(x(best) - px)) best = d;
    setHover(best);
  };
  const tip = hover != null ? vis.map((s) => ({ s, v: at(s, hover) })).filter((z) => z.v != null) : [];
  const tipRight = hover != null && x(hover) > W * 0.55;
  return (
    <div className="mlc" ref={ref}>
      <svg width={W} height={H} role="img" aria-label="Rating" onPointerMove={onMove} onPointerDown={onMove} onPointerLeave={() => setHover(null)} style={{ touchAction: "pan-y", display: "block" }}>
        {grid.map((v) => (
          <g key={v}><line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke={GRID} /><text x={L - 8} y={y(v) + 4} fill={AXIS} fontSize={FS} textAnchor="end">{v}</text></g>
        ))}
        <text x={L} y={H - 8} fill={AXIS} fontSize={FS}>{fmt(tMin)}</text>
        <text x={W - R} y={H - 8} fill={AXIS} fontSize={FS} textAnchor="end">{fmt(tMax)}</text>
        {vis.map((s) => (
          <g key={s.key}>
            {s.pts.length > 1 && <polyline fill="none" stroke={s.color} strokeWidth="2.6" strokeDasharray={s.dash} strokeLinejoin="round" strokeLinecap="round" points={s.pts.map((p) => `${x(ts(p.d)).toFixed(1)},${y(p.r).toFixed(1)}`).join(" ")} />}
            {s.pts.length <= 40 && s.pts.map((p) => <circle key={p.d} cx={x(ts(p.d))} cy={y(p.r)} r="3" fill={s.color} />)}
            <circle cx={x(ts(s.pts[s.pts.length - 1].d))} cy={y(s.pts[s.pts.length - 1].r)} r="5" fill={s.color} />
          </g>
        ))}
        {hover != null && <line x1={x(hover)} x2={x(hover)} y1={T} y2={H - B} stroke="#fff" strokeOpacity=".35" strokeDasharray="3 3" />}
        {hover != null && tip.map(({ s, v }) => <circle key={s.key} cx={x(hover)} cy={y(v as number)} r="5.5" fill={s.color} stroke="#0b0f1e" strokeWidth="2" />)}
      </svg>
      {hover != null && (
        <div className="mlc-tip" style={{ [tipRight ? "right" : "left"]: `${tipRight ? W - x(hover) : x(hover)}px` } as React.CSSProperties}>
          <b>{fmt(hover)}</b>
          {tip.map(({ s, v }) => <div key={s.key}><i style={{ background: s.color }} />{s.label} <b>{v}</b></div>)}
        </div>
      )}
    </div>
  );
}
