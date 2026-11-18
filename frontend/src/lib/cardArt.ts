import type { Pos } from "./cardPositions";

export type Rarity = "common" | "rare" | "epic" | "legendary";
export type CardGame = { me: string; opp: string; color: "white" | "black"; result: string; opening?: string | null; date: string; acc?: number | null; elo?: number | null; opp_elo?: number | null; sans: string[]; hi?: number | null };
export type CardLabels = { rarity: string; title: string; subtitle: string; me: string; opp: string; win: string; loss: string; draw: string; moves: string; accuracy: string; opening: string; brand: string; ply: string };
export type CardView = { rarity: Rarity; game: CardGame; labels: CardLabels };
export type Fonts = { display: string; body: string };

export const CARD_W = 540, CARD_H = 760;

const THEME: Record<Rarity, { a: string; b: string; accent: string; dark: string; light: string; glow: string }> = {
  common: { a: "#34437d", b: "#121836", accent: "#a9b8f2", dark: "#4a5aa0", light: "#e9eeff", glow: "#8fa3e8" },
  rare: { a: "#127a80", b: "#0a2b40", accent: "#4ee3b0", dark: "#2f8f8a", light: "#e6fbf4", glow: "#4ee3b0" },
  epic: { a: "#6a2fb0", b: "#1b0f3f", accent: "#d3a4ff", dark: "#7a4fc0", light: "#f1e8ff", glow: "#c58bff" },
  legendary: { a: "#b8741a", b: "#2b1704", accent: "#ffd56a", dark: "#a8741f", light: "#fbefcf", glow: "#ffd56a" },
};
export const rarityColor = (r: Rarity) => THEME[r].accent;

const GLYPH: Record<string, string> = { k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟" };
const SYMBOLS = "'Segoe UI Symbol','Noto Sans Symbols 2','DejaVu Sans','Apple Symbols','Arial Unicode MS',sans-serif";

function rr(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}
/** Scrive il testo riducendo il corpo finché sta in maxW; poi, se serve, tronca con "…". */
function fit(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, maxW: number, px: number, weight: string, family: string, align: CanvasTextAlign = "left", minPx = 11) {
  let s = px;
  ctx.textAlign = align;
  for (; s >= minPx; s -= 1) { ctx.font = `${weight} ${s}px ${family}`; if (ctx.measureText(text).width <= maxW) break; }
  let t = text;
  while (t.length > 1 && ctx.measureText(t).width > maxW) t = t.slice(0, -1);
  ctx.fillText(t === text ? t : t.trimEnd() + "…", x, y);
}

/** Disegna la carta completa. `ply` = quante semimosse sono state giocate; `shine` anima il riflesso olografico (solo a schermo). */
export function drawCard(ctx: CanvasRenderingContext2D, v: CardView, pos: Pos[], ply: number, fonts: Fonts, shine = 0) {
  const T = THEME[v.rarity], g = v.game, L = v.labels, W = CARD_W, H = CARD_H;
  const D = fonts.display, B = fonts.body;
  ctx.save();
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = "#0b0f1e"; ctx.fillRect(0, 0, W, H);                 // sfondo pieno: la GIF non ha trasparenza
  // corpo
  rr(ctx, 8, 8, W - 16, H - 16, 34); ctx.save(); ctx.clip();
  const bg = ctx.createLinearGradient(0, 0, W * 0.5, H); bg.addColorStop(0, T.a); bg.addColorStop(1, T.b);
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
  // fasce diagonali (motivo olografico fisso)
  ctx.globalAlpha = v.rarity === "common" ? 0.05 : 0.09; ctx.fillStyle = "#fff";
  for (let i = -2; i < 9; i++) { ctx.beginPath(); ctx.moveTo(i * 90, 0); ctx.lineTo(i * 90 + 46, 0); ctx.lineTo(i * 90 + 46 + 380, H); ctx.lineTo(i * 90 + 380, H); ctx.fill(); }
  ctx.globalAlpha = 1;
  const glow = ctx.createRadialGradient(W / 2, 330, 40, W / 2, 330, 330); glow.addColorStop(0, T.glow + "55"); glow.addColorStop(1, T.glow + "00");
  ctx.fillStyle = glow; ctx.fillRect(0, 100, W, 500);
  ctx.restore();
  // cornice
  rr(ctx, 8, 8, W - 16, H - 16, 34);
  const fr = ctx.createLinearGradient(0, 0, W, H); fr.addColorStop(0, "#ffffff"); fr.addColorStop(0.5, T.accent); fr.addColorStop(1, "#ffffff");
  ctx.lineWidth = 4; ctx.strokeStyle = fr; ctx.stroke();
  rr(ctx, 16, 16, W - 32, H - 32, 28); ctx.lineWidth = 1.5; ctx.strokeStyle = "rgba(255,255,255,.22)"; ctx.stroke();

  // intestazione: numero grande (precisione) a sinistra, titolo a destra
  const acc = g.acc != null ? Math.round(Number(g.acc)) : null;
  ctx.fillStyle = "#fff"; ctx.textAlign = "center"; ctx.font = `800 ${acc != null ? 66 : 40}px ${D}`;
  ctx.fillText(acc != null ? String(acc) : (g.result === "1/2-1/2" ? "½" : "★"), 82, 100);
  ctx.fillStyle = T.accent; ctx.font = `700 12px ${B}`; ctx.fillText(acc != null ? L.accuracy : "", 82, 122);
  // pedina del colore dell'utente
  ctx.beginPath(); ctx.arc(82, 148, 11, 0, Math.PI * 2); ctx.fillStyle = g.color === "white" ? "#f4f7ff" : "#0f1430"; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = T.accent; ctx.stroke();
  ctx.fillStyle = T.accent; ctx.textAlign = "left";
  fit(ctx, L.rarity, 150, 52, 250, 13, "800", B);
  ctx.fillStyle = "#fff"; fit(ctx, L.title, 150, 92, 372, 32, "800", D, "left", 18);
  ctx.fillStyle = "rgba(233,238,255,.82)"; fit(ctx, L.subtitle, 150, 120, 372, 14, "500", B, "left", 10);
  ctx.strokeStyle = "rgba(255,255,255,.2)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(150, 136); ctx.lineTo(W - 30, 136); ctx.stroke();
  ctx.fillStyle = "rgba(233,238,255,.7)"; fit(ctx, g.opening || "", 150, 158, 372, 13, "500", B);

  // scacchiera
  const S = 44, bx = (W - S * 8) / 2, by = 176, flip = g.color === "black", p = pos[Math.max(0, Math.min(ply, pos.length - 1))];
  rr(ctx, bx - 8, by - 8, S * 8 + 16, S * 8 + 16, 14); ctx.fillStyle = "rgba(5,8,20,.55)"; ctx.fill();
  for (let r = 0; r < 8; r++) for (let c = 0; c < 8; c++) {
    const i = r * 8 + c, vi = flip ? 63 - i : i, x = bx + (i % 8) * S, y = by + Math.floor(i / 8) * S;
    ctx.fillStyle = (r + c) % 2 ? T.dark : T.light; ctx.fillRect(x, y, S, S);
    void vi;
  }
  const spot = (sq: number) => { const vi = flip ? 63 - sq : sq; return [bx + (vi % 8) * S, by + Math.floor(vi / 8) * S]; };
  if (p.from >= 0) for (const sq of [p.from, p.to]) { const [x, y] = spot(sq); ctx.fillStyle = "rgba(255,213,106,.55)"; ctx.fillRect(x, y, S, S); }
  ctx.textAlign = "center"; ctx.textBaseline = "alphabetic";
  for (let sq = 0; sq < 64; sq++) {
    const ch = p.sq[sq]; if (!ch) continue;
    const [x, y] = spot(sq), white = ch === ch.toUpperCase(), gl = GLYPH[ch.toLowerCase()] + "︎";
    ctx.font = `${Math.round(S * 0.86)}px ${SYMBOLS}`;
    ctx.lineJoin = "round"; ctx.lineWidth = white ? 3 : 2.2;
    ctx.strokeStyle = white ? "#0b0f1e" : "#f4f7ff"; ctx.strokeText(gl, x + S / 2, y + S * 0.8);
    ctx.fillStyle = white ? "#ffffff" : "#141a38"; ctx.fillText(gl, x + S / 2, y + S * 0.8);
  }
  if (g.hi && ply === g.hi && p.to >= 0) {                              // mossa brillante: segnalino sulla casella di arrivo
    const [x, y] = spot(p.to);
    ctx.beginPath(); ctx.arc(x + S - 6, y + 8, 13, 0, Math.PI * 2); ctx.fillStyle = "#19c6b2"; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = "#fff"; ctx.stroke();
    ctx.fillStyle = "#fff"; ctx.textAlign = "center"; ctx.font = `800 13px ${B}`; ctx.fillText("!!", x + S - 6, y + 13);
  }
  // avanzamento e ultima mossa giocata
  const total = pos.length - 1, py = by + S * 8 + 26;
  ctx.fillStyle = "rgba(255,255,255,.18)"; rr(ctx, bx, py, S * 8, 6, 3); ctx.fill();
  ctx.fillStyle = T.accent; rr(ctx, bx, py, Math.max(6, (S * 8 * Math.min(ply, total)) / Math.max(1, total)), 6, 3); ctx.fill();
  const cur = ply > 0 ? g.sans[Math.min(ply, total) - 1] : "";
  ctx.fillStyle = "#fff"; ctx.textAlign = "center"; ctx.font = `700 15px ${B}`;
  ctx.fillText(cur ? `${Math.ceil(Math.min(ply, total) / 2)}${ply % 2 ? "." : "..."} ${cur}` : "", W / 2, py + 26);

  // giocatori
  const row = (y: number, tag: string, name: string, el: number | null | undefined, white: boolean, strong: boolean) => {
    rr(ctx, 34, y, W - 68, 36, 12); ctx.fillStyle = strong ? "rgba(255,255,255,.14)" : "rgba(5,8,20,.38)"; ctx.fill();
    ctx.beginPath(); ctx.arc(54, y + 18, 7, 0, Math.PI * 2); ctx.fillStyle = white ? "#f4f7ff" : "#0f1430"; ctx.fill(); ctx.lineWidth = 1.6; ctx.strokeStyle = T.accent; ctx.stroke();
    ctx.fillStyle = T.accent; ctx.textAlign = "left"; ctx.font = `800 11px ${B}`; ctx.fillText(tag, 70, y + 22);
    ctx.fillStyle = "#fff"; fit(ctx, name, 104, y + 24, el ? 330 : 400, 18, "800", D, "left", 12);
    if (el) { ctx.fillStyle = "rgba(233,238,255,.8)"; ctx.textAlign = "right"; ctx.font = `700 14px ${B}`; ctx.fillText(String(el), W - 48, y + 23); }
  };
  const y0 = py + 42;
  row(y0, L.me, g.me, g.elo, g.color === "white", true);
  row(y0 + 42, L.opp, g.opp, g.opp_elo, g.color !== "white", false);

  // risultato e dati
  const res = g.result === "1/2-1/2" ? L.draw : ((g.result === "1-0") === (g.color === "white") ? L.win : L.loss);
  const rc = res === L.win ? "#4ee3b0" : res === L.loss ? "#ff5d6c" : "#c7cde6";
  const sy = y0 + 96;
  ctx.fillStyle = rc; ctx.textAlign = "left"; ctx.font = `800 15px ${D}`; ctx.fillText(res.toUpperCase(), 40, sy);
  ctx.fillStyle = "rgba(233,238,255,.8)"; ctx.font = `600 12px ${B}`;
  ctx.textAlign = "center"; ctx.fillText(`${Math.ceil(total / 2)} ${L.moves}`, W / 2, sy); 
  ctx.textAlign = "right"; ctx.fillText(g.date, W - 40, sy);
  ctx.fillStyle = "rgba(233,238,255,.55)"; ctx.font = `800 11px ${D}`; ctx.textAlign = "center"; ctx.fillText(L.brand, W / 2, H - 28);

  // riflesso olografico: solo a schermo
  if (shine > 0) {
    ctx.save(); rr(ctx, 8, 8, W - 16, H - 16, 34); ctx.clip();
    const x = -300 + ((shine % 1) * (W + 600)), sh = ctx.createLinearGradient(x, 0, x + 260, H * 0.6);
    sh.addColorStop(0, "rgba(255,255,255,0)"); sh.addColorStop(0.5, `rgba(255,255,255,${v.rarity === "legendary" ? 0.26 : v.rarity === "epic" ? 0.2 : 0.13})`); sh.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = sh; ctx.fillRect(0, 0, W, H); ctx.restore();
  }
  ctx.restore();
}

/** Indici di semimossa dei fotogrammi della GIF (al massimo ~46) con la durata di ciascuno in centesimi di secondo. `hi` = mossa da evidenziare. */
export function gifPlan(total: number, hi?: number | null): { ply: number; delay: number }[] {
  const step = Math.max(1, Math.ceil(total / 44)), out: { ply: number; delay: number }[] = [{ ply: 0, delay: 90 }];
  for (let p = step; p < total; p += step) out.push({ ply: p, delay: 55 });
  out.push({ ply: total, delay: 260 });
  if (hi && hi > 0 && hi < total) {
    const i = out.findIndex((f) => f.ply >= hi);
    if (out[i].ply === hi) out[i].delay = 170; else out.splice(i, 0, { ply: hi, delay: 170 });
  }
  return out;
}
