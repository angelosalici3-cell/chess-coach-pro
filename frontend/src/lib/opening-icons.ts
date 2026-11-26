/** Emblemi a tratto (viewBox 24) per gli scudi delle aperture: stessa grafica degli scudi dei traguardi. */
export type Emblem = "pawn" | "knight" | "bishop" | "rook" | "queen" | "king" | "gambit";

export const EMBLEM: Record<Emblem, string> = {
  pawn: "M12 4.2a2.7 2.7 0 110 5.4 2.7 2.7 0 010-5.4zM9.8 13.4c0-1.6.9-2.7 2.2-3.5 1.3.8 2.2 1.9 2.2 3.5M9.4 13.4h5.2M10 13.4c-.2 2.4-.7 4-1.7 6h7.4c-1-2-1.5-3.6-1.7-6M7.5 20h9",
  knight: "M7 20h11M9 20c0-3 .5-5 2.5-7.5-2 0-3.700-1.200-4.500-3.500l4-3.500c4-1 7.500 1.500 7.500 6.500V20M13.600 9h.01",
  bishop: "M12 3.200v1.300M12 5c3 2.600 4.200 4.600 4.200 6.600 0 1.400-.9 2.400-2.200 3H10c-1.300-.6-2.200-1.600-2.200-3C7.800 9.600 9 7.600 12 5zM12 8.200v3.200M10.400 9.800h3.200M8.500 18.500h7M10 14.600v3.900M14 14.600v3.900",
  rook: "M7 5h2v2h2V5h2v2h2V5h2v5H7zM8.500 10v8M15.500 10v8M6.500 18h11v2h-11z",
  queen: "M5 8l3 7h8l3-7-4.500 3L12 5l-2.500 6zM7.500 18.500h9M8 15l-.5 3.500M16 15l.5 3.500",
  king: "M12 3v4M10 5h4M12 7c-3.500 0-5.500 2-5.500 4.500 0 1.500 1 3 2 3.800L8 18.500h8l-.5-3.200c1-.8 2-2.300 2-3.800C17.500 9 15.500 7 12 7zM7.500 20.500h9",
  gambit: "M4 4l10 10M20 4L10 14M12 12l-6 6M12 12l6 6M3.500 18.500l2 2M20.500 18.500l-2 2",
};

/** Sceglie l'emblema dal nome dell'apertura: gambetti = spade incrociate, difese = torre, e così via. */
export function emblemFor(nameEn: string): Emblem {
  const n = nameEn.toLowerCase();
  if (n.includes("gambit")) return "gambit";
  if (n.includes("mate")) return "king";
  if (n.includes("king")) return "king";
  if (n.includes("queen")) return "queen";
  if (/bishop|italian|ruy|spanish|london|giuoco|caro|alekhine/.test(n)) return "bishop";
  if (/defen[cs]e|philidor|pirc|scandinavian|sicilian|french|benoni|slav|russian|petroff|englund|grünfeld|grunfeld|damiano/.test(n)) return "rook";
  if (/knight|vienna|scotch|center|elephant|halloween/.test(n)) return "knight";
  return "pawn";
}
