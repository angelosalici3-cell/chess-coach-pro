"use client";
import dynamic from "next/dynamic";
import { Chess } from "chess.js";
import { useEffect, useMemo, useState } from "react";

// Caricata solo nel browser: la libreria misura il contenitore e non serve sul server.
const Chessboard = dynamic(() => import("react-chessboard").then((m) => m.Chessboard), {
  ssr: false,
  loading: () => <div className="board-skel" />,
});

type Props = {
  fen: string; flip?: boolean; last?: string | null; notation?: boolean;
  /** Se presente la scacchiera è interattiva: restituisci true per accettare la mossa. */
  onDrop?: (from: string, to: string, piece: string) => boolean;
  /** Caselle evidenziate (es. suggerimento o soluzione). */
  marks?: Record<string, string>;
  shake?: boolean;
};

const DOT = "radial-gradient(circle, rgba(255, 107, 61, .62) 0 22%, transparent 24%)";
const RING = "radial-gradient(circle, transparent 0 68%, rgba(255, 107, 61, .62) 70% 86%, transparent 88%)";

export default function ChessBoard({ fen, flip, last, notation = true, onDrop, marks, shake }: Props) {
  const [sel, setSel] = useState<string | null>(null);
  useEffect(() => { setSel(null); }, [fen]);   // dopo ogni mossa la selezione si azzera

  // Mosse legali del pezzo scelto: servono per i punti sulle case di arrivo (come su Lichess)
  const game = useMemo(() => { try { return new Chess(fen); } catch { return null; } }, [fen]);
  const targets = useMemo(() => {
    if (!game || !sel) return [] as { to: string; capture: boolean }[];
    try { return game.moves({ square: sel as any, verbose: true }).map((m: any) => ({ to: m.to as string, capture: !!m.captured || m.flags.includes("e") })); } catch { return []; }
  }, [game, sel]);

  const mine = (sq: string) => { const p = game?.get(sq as any); return !!p && p.color === game!.turn(); };
  const tryMove = (from: string, to: string) => {
    const p = game?.get(from as any);
    if (!p || !onDrop) return;
    onDrop(from, to, p.color + p.type.toUpperCase());
    setSel(null);
  };
  const click = (sq: string) => {
    if (!onDrop || !game) return;
    if (sel === sq) { setSel(null); return; }                       // secondo clic sullo stesso pezzo: lo deseleziona
    if (sel && targets.some((t) => t.to === sq)) { tryMove(sel, sq); return; }   // clic su una casa di arrivo: muove
    setSel(mine(sq) ? sq : null);                                   // altro pezzo tuo: cambia selezione; altrimenti deseleziona
  };

  const hl: Record<string, React.CSSProperties> = {};
  if (last && last.length >= 4) {
    hl[last.slice(0, 2)] = { backgroundColor: "rgba(255, 200, 61, .45)" };
    hl[last.slice(2, 4)] = { backgroundColor: "rgba(255, 200, 61, .6)" };
  }
  for (const [sq, color] of Object.entries(marks || {})) hl[sq] = { backgroundColor: color };
  if (sel) hl[sel] = { ...(hl[sel] || {}), backgroundColor: "rgba(255, 107, 61, .5)" };
  for (const t of targets) hl[t.to] = { ...(hl[t.to] || {}), backgroundImage: t.capture ? RING : DOT };
  return (
    <div className={"board-frame" + (shake ? " shake" : "")}>
      <Chessboard
        position={fen}
        boardOrientation={flip ? "black" : "white"}
        arePiecesDraggable={!!onDrop}
        onPieceDrop={onDrop ? (a: string, b: string, p: string) => { setSel(null); return onDrop(a, b, p); } : undefined}
        onPieceDragBegin={onDrop ? (_p: string, sq: string) => setSel(mine(sq) ? sq : null) : undefined}
        onSquareClick={onDrop ? (sq: string) => click(sq) : undefined}
        autoPromoteToQueen={true}
        animationDuration={240}
        showBoardNotation={notation}
        customDarkSquareStyle={{ backgroundColor: "#6d7fb3" }}
        customLightSquareStyle={{ backgroundColor: "#e6e9f2" }}
        customSquareStyles={hl}
        customBoardStyle={{ borderRadius: "10px", overflow: "hidden" }}
      />
    </div>
  );
}
