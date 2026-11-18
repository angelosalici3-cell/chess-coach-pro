import { Chess } from "chess.js";

/** Posizione dopo ogni semimossa: 64 caselle (a8 = 0), lettere FEN, e ultima mossa. L'indice 0 è la posizione iniziale. */
export type Pos = { sq: string[]; from: number; to: number };

const idx = (s: string) => (8 - Number(s[1])) * 8 + (s.charCodeAt(0) - 97);

export function positions(sans: string[]): Pos[] {
  const c = new Chess();
  const snap = (from = -1, to = -1): Pos => ({
    sq: c.board().flat().map((p) => (p ? (p.color === "w" ? p.type.toUpperCase() : p.type) : "")), from, to,
  });
  const out: Pos[] = [snap()];
  for (const s of sans) {
    try { const m = c.move(s); out.push(snap(idx(m.from), idx(m.to))); } catch { break; }   // SAN illeggibile: la rigiocata si ferma qui
  }
  return out;
}
