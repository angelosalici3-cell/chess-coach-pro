import { GLYPH, ICONS, METAL, PATH } from "../components/Shield";
import type { Fonts } from "./cardArt";

export type ShieldShare = { id: string; tier: number; title: string; tierLabel: string; detail: string; brand: string };

/** Immagine verticale 4:5 (1080x1350) di uno scudo conquistato, pensata per storie e post. */
export async function makeShieldPng(s: ShieldShare, fonts: Fonts): Promise<Blob> {
  const W = 1080, H = 1350, c = document.createElement("canvas"); c.width = W; c.height = H;
  const ctx = c.getContext("2d")!, m = METAL[s.tier];
  const bg = ctx.createLinearGradient(0, 0, W * 0.4, H); bg.addColorStop(0, "#1a2250"); bg.addColorStop(1, "#080b18");
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
  const glow = ctx.createRadialGradient(W / 2, 560, 60, W / 2, 560, 620); glow.addColorStop(0, m.a + "88"); glow.addColorStop(1, m.a + "00");
  ctx.fillStyle = glow; ctx.fillRect(0, 0, W, H);
  // scintille
  let seed = s.title.length * 97 + s.tier * 13;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 46; i++) { ctx.globalAlpha = 0.15 + rnd() * 0.5; ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(rnd() * W, rnd() * 900, 1.5 + rnd() * 3.5, 0, Math.PI * 2); ctx.fill(); }
  ctx.globalAlpha = 1;
  // scudo: path 100x108 ingrandito 6.4x
  const k = 6.4;
  ctx.save(); ctx.translate((W - 100 * k) / 2, 190); ctx.scale(k, k);
  const g = ctx.createLinearGradient(0, 0, 60, 108); g.addColorStop(0, m.a); g.addColorStop(1, m.b);
  const p = new Path2D(PATH);
  ctx.shadowColor = m.a + "aa"; ctx.shadowBlur = 40; ctx.fillStyle = g; ctx.fill(p); ctx.shadowBlur = 0;
  ctx.lineWidth = 2.5; ctx.lineJoin = "round"; ctx.strokeStyle = m.edge; ctx.stroke(p);
  ctx.lineWidth = 1.4; ctx.strokeStyle = "rgba(255,255,255,.45)"; ctx.stroke(new Path2D("M50 12 L84 23 V52 C84 71 68 84 50 93 C32 84 16 71 16 52 V23 Z"));
  const glyph = GLYPH[s.id], icon = ICONS[s.id] ?? (s.id.startsWith("op_") ? ICONS.openings : undefined);
  ctx.fillStyle = "rgba(27,18,6,.82)"; ctx.strokeStyle = "rgba(27,18,6,.82)";
  if (glyph) { ctx.font = `40px 'Segoe UI Symbol','Noto Sans Symbols 2','DejaVu Sans',sans-serif`; ctx.textAlign = "center"; ctx.fillText(glyph + "︎", 50, 62); }
  else if (icon) { ctx.translate(26, 24); ctx.scale(2, 2); ctx.lineWidth = 1.6; ctx.lineCap = "round"; const ip = new Path2D(icon); if (s.id === "streak" || s.id === "clean") ctx.fill(ip); ctx.stroke(ip); }
  ctx.restore();
  // testi
  ctx.textAlign = "center";
  ctx.fillStyle = m.edge; ctx.font = `800 40px ${fonts.body}`; ctx.fillText(s.tierLabel.toUpperCase(), W / 2, 940);
  ctx.fillStyle = "#fff"; let px = 92; ctx.font = `800 ${px}px ${fonts.display}`;
  while (ctx.measureText(s.title).width > W - 140 && px > 40) { px -= 4; ctx.font = `800 ${px}px ${fonts.display}`; }
  ctx.fillText(s.title, W / 2, 1050);
  ctx.fillStyle = "rgba(233,238,255,.82)"; ctx.font = `600 38px ${fonts.body}`; ctx.fillText(s.detail, W / 2, 1120);
  ctx.fillStyle = "rgba(233,238,255,.5)"; ctx.font = `800 30px ${fonts.display}`; ctx.fillText(s.brand, W / 2, 1270);
  return new Promise((res, rej) => c.toBlob((b) => (b ? res(b) : rej(new Error("png"))), "image/png"));
}
