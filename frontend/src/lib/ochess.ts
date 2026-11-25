import { Chess } from "chess.js";
import { OC_OPENINGS, OC_ROWS } from "./ochess-data";
import type { Opening, OpLine, Drill } from "./openings-data";

/**
 * Trappole importate da Ochess (dati in ochess-data.ts, generati da uno script che valida ogni mossa).
 * Qui le trasformiamo nel formato dell'app: SAN canoniche (chess.js), modalità «tendi» sempre,
 * «evita» solo se esiste almeno una mossa sicura valida. Le descrizioni sono in inglese (nessuna traduzione ancora).
 */
const t2 = (s: string) => ({ it: s, en: s });

function build(): Opening[] {
  const byOp = new Map<string, OpLine[]>();
  for (const [id, op, title, , moves, at, safe, by, desc] of OC_ROWS) {
    try {
      const ch = new Chess();
      const san: string[] = [];
      for (const s of moves.split(" ")) { san.push(ch.move(s).san.replace(/[+#]/g, "")); }
      if (at >= san.length) continue;
      const pre = new Chess();
      for (let k = 0; k < at; k++) pre.move(san[k]);
      const okSafe: string[] = [];
      for (const s of safe) { try { okSafe.push(new Chess(pre.fen()).move(s).san.replace(/[+#]/g, "")); } catch { /* scarta */ } }
      const where = `${Math.floor(at / 2) + 1}${at % 2 ? "..." : "."}`;
      const line: OpLine = {
        id, kind: "trap", title: t2(title), moves: san.join(" "), side: by,
        idea: t2(desc), blunderAt: at, safe: okSafe,
        avoid: { it: okSafe.length ? `Alla mossa ${where} gioca ${okSafe.join(" o ")} al posto della mossa della trappola.` : "", en: okSafe.length ? `At move ${where} play ${okSafe.join(" or ")} instead of the trap move.` : "" },
        springOnly: okSafe.length === 0,
      };
      (byOp.get(op) || byOp.set(op, []).get(op)!).push(line);
    } catch { /* riga non valida: saltata */ }
  }
  return [...byOp.entries()].map(([op, lines]): Opening => {
    const o = OC_OPENINGS[op];
    return { id: "oc-" + op, name: t2(o.name), eco: o.eco, side: o.side, blurb: t2(`${lines.length} ${lines.length === 1 ? "trap" : "traps"}`), lines };
  }).sort((a, b) => b.lines.length - a.lines.length || a.name.en.localeCompare(b.name.en));
}

export const OCHESS_OPENINGS: Opening[] = build();
export const OCHESS_DRILLS: Drill[] = OCHESS_OPENINGS.flatMap((o) =>
  o.lines.flatMap((l): Drill[] => [
    { key: l.id, line: l, mode: "spring", opening: o },
    ...(l.springOnly || !l.safe?.length ? [] : [{ key: l.id + ":a", line: l, mode: "avoid" as const, opening: o }]),
  ]));
