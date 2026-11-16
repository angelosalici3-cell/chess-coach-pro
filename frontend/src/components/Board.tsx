const G: Record<string, string> = { k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟" };

export default function Board({ fen, flip }: { fen: string; flip?: boolean }) {
  let rows = fen.split(" ")[0].split("/").map((r) => r.replace(/\d/g, (d) => ".".repeat(+d)).split(""));
  if (flip) rows = [...rows].reverse().map((r) => [...r].reverse());
  return (
    <div className="board">
      {rows.flatMap((r, i) =>
        r.map((c, j) => (
          <div key={i * 8 + j} className={"sq " + ((i + j) % 2 ? "d" : "l")}>
            {c !== "." && <span className={c === c.toUpperCase() ? "pw" : "pb"}>{G[c.toLowerCase()]}</span>}
          </div>
        ))
      )}
    </div>
  );
}
