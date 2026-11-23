import { useId } from "react";
import { BRAND } from "../lib/brand";

export function LogoMark({ size = 36 }: { size?: number }) {
  // Un pedone che sale una scalinata di case della scacchiera: gli scacchi e la crescita dell'Elo in un solo segno.
  const u = useId().replace(/[^a-zA-Z0-9]/g, "");
  const bg = `lmbg${u}`;
  const sq: [number, number, string][] = [
    [12.5, 40.5, "#e9eeff"], [26, 27, "#e9eeff"], [26, 40.5, "#6d7fb3"], [39.5, 27, "#6d7fb3"], [39.5, 40.5, "#e9eeff"],
  ];
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <defs><linearGradient id={bg} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#222c5e" /><stop offset="1" stopColor="#0b0f1e" /></linearGradient></defs>
      <rect width="64" height="64" rx="16" fill={`url(#${bg})`} />
      <rect x=".5" y=".5" width="63" height="63" rx="15.5" fill="none" stroke="#fff" strokeOpacity=".14" />
      {sq.map(([x, y, f]) => <rect key={x + "-" + y} x={x} y={y} width="12" height="12" rx="2" fill={f} />)}
      <g fill="#ff6b3d" transform="translate(39.5 11.5)">
        <circle cx="6" cy="3.7" r="3.5" /><rect x="2.4" y="7.3" width="7.2" height="1.8" rx=".9" />
        <path d="M4 9 H8 L10 13.2 H2 Z" /><rect x=".9" y="12.6" width="10.2" height="2.9" rx="1.3" />
      </g>
    </svg>
  );
}

export function Wordmark() {
  // "EloRise": la seconda parte prende l'arancio del marchio
  const i = BRAND.indexOf("Rise");
  if (i < 1) return <>{BRAND}</>;
  return <>{BRAND.slice(0, i)}<i>{BRAND.slice(i)}</i></>;
}

export function Logo({ size = 36, text = true }: { size?: number; text?: boolean }) {
  return (
    <span className="logo">
      <LogoMark size={size} />
      {text && <span className="logo-text"><Wordmark /></span>}
    </span>
  );
}
