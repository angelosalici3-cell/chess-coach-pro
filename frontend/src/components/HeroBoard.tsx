"use client";
import { useEffect, useMemo, useState } from "react";
import { Chess } from "chess.js";
import ChessBoard from "./ChessBoard";

// Partita pubblica "dell'Opera" (Morphy, 1858): serve solo come animazione della home.
const SAN = "e4 e5 Nf3 d6 d4 Bg4 dxe5 Bxf3 Qxf3 dxe5 Bc4 Nf6 Qb3 Qe7 Nc3 c6 Bg5 b5 Nxb5 cxb5 Bxb5+ Nbd7 O-O-O Rd8 Rxd7 Rxd7 Rd1 Qe6 Bxd7+ Nxd7 Qb8+ Nxb8 Rd8#".split(" ");

export default function HeroBoard({ onMove }: { onMove?: (san: string, ply: number) => void }) {
  const frames = useMemo(() => {
    const c = new Chess();
    const out = [{ fen: c.fen(), last: null as string | null, san: "" }];
    for (const san of SAN) { const m = c.move(san); out.push({ fen: c.fen(), last: m.from + m.to, san }); }
    return out;
  }, []);
  const [i, setI] = useState(0);

  useEffect(() => {
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (still) { setI(21); return; }
    let t: ReturnType<typeof setTimeout>;
    const tick = (n: number) => {
      setI(n);
      const end = n >= frames.length - 1;
      t = setTimeout(() => tick(end ? 0 : n + 1), end ? 3200 : n === 0 ? 1400 : 1050);
    };
    tick(0);
    return () => clearTimeout(t);
  }, [frames.length]);

  useEffect(() => { if (frames[i].san) onMove?.(frames[i].san, i); }, [i, frames, onMove]);
  const f = frames[i];
  return <ChessBoard fen={f.fen} last={f.last} notation={false} />;
}
