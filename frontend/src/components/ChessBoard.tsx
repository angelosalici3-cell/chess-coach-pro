"use client";
import dynamic from "next/dynamic";

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

export default function ChessBoard({ fen, flip, last, notation = true, onDrop, marks, shake }: Props) {
  const hl: Record<string, React.CSSProperties> = {};
  if (last && last.length >= 4) {
    hl[last.slice(0, 2)] = { backgroundColor: "rgba(255, 200, 61, .45)" };
    hl[last.slice(2, 4)] = { backgroundColor: "rgba(255, 200, 61, .6)" };
  }
  for (const [sq, color] of Object.entries(marks || {})) hl[sq] = { backgroundColor: color };
  return (
    <div className={"board-frame" + (shake ? " shake" : "")}>
      <Chessboard
        position={fen}
        boardOrientation={flip ? "black" : "white"}
        arePiecesDraggable={!!onDrop}
        onPieceDrop={onDrop ? (a: string, b: string, p: string) => onDrop(a, b, p) : undefined}
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
