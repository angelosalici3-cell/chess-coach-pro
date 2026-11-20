"use client";
import { useApp } from "./app";
import { useWidth } from "./Charts";
import { tc } from "../lib/train-copy";

type M = { ply: number; san: string; spent: number | null; clock: number | null; you: boolean; loss_cp: number | null };

/** Secondi spesi su ogni mossa (barre), tempo residuo (linee), zona di zeitnot e errori (punto rosso). */
export default function TimeChart({ data, active, onPick }: { data: { moves: M[]; base: number | null; threshold: number }; active: number; onPick: (ply: number) => void }) {
  const { lang } = useApp();
  const [wref, W] = useWidth();
  const ms = data.moves;
  const mine = ms.filter((m) => m.you && m.spent != null && m.ply > 2);
  const sorted = mine.map((m) => m.spent as number).sort((a, b) => a - b);
  const median = sorted.length ? sorted[Math.floor(sorted.length / 2)] : 0;
  const all = ms.map((m) => m.spent || 0).sort((a, b) => a - b);
  const cap = Math.max(20, Math.min(120, all[Math.floor(all.length * 0.95)] || 20));
  const H = 210, L = 42, R = 8, T = 14, B = 26, bw = (W - L - R) / Math.max(1, ms.length);
  const y = (s: number) => H - B - (Math.min(s, cap) / cap) * (H - B - T);
  const base = data.base || Math.max(...ms.map((m) => m.clock || 0), 1);
  const yc = (c: number) => H - B - (Math.min(c, base) / base) * (H - B - T);
  const line = (you: boolean) => ms.filter((m) => m.you === you && m.clock != null).map((m) => `${(L + (m.ply - 0.5) * bw).toFixed(1)},${yc(m.clock as number).toFixed(1)}`).join(" ");

  const avg = mine.length ? mine.reduce((a, m) => a + (m.spent as number), 0) / mine.length : 0;
  const slow = mine.reduce((b, m) => ((m.spent as number) > (b?.spent as number) ? m : b), mine[0]);
  const trouble = mine.filter((m) => m.clock != null && m.clock < data.threshold).length;
  const hasty = mine.filter((m) => (m.spent as number) <= 3 && (m.loss_cp ?? 0) >= 100).length;
  const sec = tc("secShort", lang);
  const lbl = (m: M) => `${Math.ceil(m.ply / 2)}${m.ply % 2 ? "." : "…"}${m.san}`;
  return (
    <div>
      <div className="timestats">
        <div><span className="muted small">{tc("avgMove", lang)}</span><b>{avg.toFixed(1)}{sec}</b></div>
        {slow && <div><span className="muted small">{tc("slowest", lang)}</span><b>{(slow.spent as number).toFixed(0)}{sec}</b><span className="muted small">{lbl(slow)}</span></div>}
        <div><span className="muted small">{tc("troubleMoves", lang)}</span><b>{trouble}</b></div>
        <div><span className="muted small">{tc("fastMistakes", lang)}</span><b>{hasty}</b></div>
      </div>
      <div ref={wref}><svg width={W} height={H} style={{ display: "block" }} role="img" aria-label={tc("timeChartTitle", lang)}>
        <rect x={L} y={yc(data.threshold)} width={W - L - R} height={H - B - yc(data.threshold)} fill="rgba(255, 93, 108, .09)" />
        {[0, cap / 2, cap].map((v) => <g key={v}><line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="#26305a" /><text x={L - 6} y={y(v) + 4} fill="#8d97b8" fontSize="13" textAnchor="end">{Math.round(v)}{v === cap ? "+" : ""}</text></g>)}
        {ms.map((m) => {
          if (m.spent == null) return null;
          const x = L + (m.ply - 1) * bw, top = y(m.spent), h = Math.max(1, H - B - top);
          const color = !m.you ? "#8d97b8" : m.spent > Math.max(10, median * 2.5) ? "#ff6b3d" : "#4ee3b0";
          return (
            <g key={m.ply} onClick={() => onPick(m.ply)} style={{ cursor: "pointer" }}>
              <rect x={x} y={T} width={bw} height={H - B - T} fill="transparent" />
              <rect x={x + bw * 0.14} y={H - B - h} width={Math.max(1, bw * 0.72)} height={h} rx="1.5" style={{ fill: color }} opacity={m.ply === active ? 1 : m.you ? 0.9 : 0.4} />
              {m.you && (m.loss_cp ?? 0) >= 100 && <circle cx={x + bw / 2} cy={Math.max(T + 3, top - 6)} r="3" fill="#ff5d6c" />}
            </g>
          );
        })}
        <polyline points={line(false)} fill="none" stroke="#8d97b8" strokeWidth="1.6" strokeOpacity=".6" />
        <polyline points={line(true)} fill="none" stroke="#5aa9ff" strokeWidth="2.2" />
        {ms.filter((m) => m.ply % (W < 420 ? 40 : 20) === 0).map((m) => <text key={m.ply} x={L + (m.ply - 0.5) * bw} y={H - 6} fill="#a9b3d6" fontSize="13" textAnchor="middle">{m.ply / 2}</text>)}
      </svg></div>
      <div className="loss-legend">
        <span><i style={{ background: "#4ee3b0" }} />{tc("avgMove", lang)}</span>
        <span><i style={{ background: "#ff6b3d" }} />{tc("slowest", lang)}</span>
        <span><i style={{ background: "#5aa9ff" }} />{tc("clockLeft", lang)}</span>
        <span><i style={{ background: "#ff5d6c" }} />{tc("fastMistakes", lang)}</span>
      </div>
      <p className="muted small" style={{ margin: ".3rem 0 0" }}>{tc("timeChartNote", lang)}</p>
    </div>
  );
}
