/** Albero delle aperture: struttura dati, ricerca e calcolo del layout della mappa mentale. */
export type RawNode = [string, RawNode[], string?, string?];
export type VolKey = "A" | "B" | "C" | "D" | "E";
export type ONode = { id: string; san: string; ply: number; kids: ONode[]; eco?: string; name?: string; n: number; vol: VolKey };
export type Entry = { name: string; eco: string; path: string[] };

export const VOL_COLOR: Record<VolKey, string> = { A: "#4ee3b0", B: "#ffb84d", C: "#ff6b3d", D: "#5aa9ff", E: "#ff5d8f" };

/** Prepara l'albero: numero di linee con nome sotto ogni nodo e volume ECO prevalente (per il colore). */
export function prepare(raw: RawNode[]): { roots: ONode[]; entries: Entry[] } {
  const entries: Entry[] = [];
  const build = (r: RawNode[], parent: string[]): ONode[] =>
    r.map((x) => {
      const path = [...parent, x[0]];
      const kids = build(x[1], path);
      const eco = x[2], name = x[3];
      if (name) entries.push({ name, eco: eco || "", path });
      return { id: path.join(" "), san: x[0], ply: path.length, kids, eco, name, n: 0, vol: "A" as VolKey };
    });
  const roots = build(raw, []);
  // seconda passata: conteggi e volume prevalente
  const fill = (n: ONode): Record<string, number> => {
    const t: Record<string, number> = {};
    if (n.eco) t[n.eco[0]] = (t[n.eco[0]] || 0) + 1;
    for (const k of n.kids) { const s = fill(k); for (const v in s) t[v] = (t[v] || 0) + s[v]; }
    n.n = Object.values(t).reduce((a, b) => a + b, 0);
    const top = Object.entries(t).sort((a, b) => b[1] - a[1])[0];
    n.vol = ((top ? top[0] : "A") as VolKey);
    n.kids.sort((a, b) => b.n - a.n || a.san.localeCompare(b.san));
    return t;
  };
  roots.forEach(fill);
  roots.sort((a, b) => b.n - a.n || a.san.localeCompare(b.san));
  return { roots, entries };
}

/** Nodi lungo il percorso (si ferma al primo non trovato). */
export function resolve(roots: ONode[], path: string[]): ONode[] {
  const out: ONode[] = [];
  let level = roots;
  for (const san of path) {
    const n = level.find((x) => x.san === san);
    if (!n) break;
    out.push(n);
    level = n.kids;
  }
  return out;
}

export const moveLabel = (ply: number, san: string) => (ply % 2 ? `${(ply + 1) / 2}.${san}` : `${ply / 2}…${san}`);

/** Nome dell'apertura più specifica lungo il percorso. */
export function currentName(nodes: ONode[]): { name: string; eco: string } | null {
  for (let i = nodes.length - 1; i >= 0; i--) if (nodes[i].name) return { name: nodes[i].name!, eco: nodes[i].eco || "" };
  return null;
}

export function search(entries: Entry[], q: string, limit = 8): Entry[] {
  const s = q.trim().toLowerCase();
  if (s.length < 2) return [];
  const score = (e: Entry) => {
    const n = e.name.toLowerCase();
    if (e.eco.toLowerCase() === s) return 0;
    if (n.startsWith(s)) return 1;
    if (n.includes(s)) return 2;
    if (e.eco.toLowerCase().startsWith(s)) return 3;
    return 9;
  };
  return entries.map((e) => ({ e, s: score(e) })).filter((x) => x.s < 9).sort((a, b) => a.s - b.s || a.e.path.length - b.e.path.length).slice(0, limit).map((x) => x.e);
}

// ---------- layout ----------
export const W = 184, H = 56, GX = 64, GY = 8, PAD = 12;
export type LNode = { id: string; node: ONode; col: number; x: number; y: number; sel: boolean; path: string[] };
export type Edge = { key: string; d: string; on: boolean };
export type Layout = { nodes: LNode[]; edges: Edge[]; width: number; height: number; selY: number | null };

/** Colonna d = mosse possibili dopo path[0..d). Ogni colonna si centra sul nodo scelto della precedente. */
export function layout(roots: ONode[], path: string[]): Layout {
  const sel = resolve(roots, path);
  const cols: { kids: ONode[]; top: number }[] = [];
  let kids = roots, centerPrev = 0;
  for (let d = 0; d <= sel.length; d++) {
    if (!kids.length) break;
    const h = kids.length * (H + GY) - GY;
    cols.push({ kids, top: d === 0 ? 0 : centerPrev - h / 2 });
    if (d < sel.length) {
      const i = kids.findIndex((k) => k.san === sel[d].san);
      centerPrev = cols[d].top + i * (H + GY) + H / 2;
      kids = sel[d].kids;
    }
  }
  const minTop = Math.min(...cols.map((c) => c.top));
  cols.forEach((c) => (c.top = c.top - minTop + PAD));
  const nodes: LNode[] = [], edges: Edge[] = [];
  cols.forEach((c, d) => c.kids.forEach((n, i) => {
    nodes.push({ id: n.id, node: n, col: d, x: PAD + d * (W + GX), y: c.top + i * (H + GY), sel: sel[d]?.san === n.san, path: [...path.slice(0, d), n.san] });
  }));
  for (let d = 1; d < cols.length; d++) {
    const parent = nodes.find((n) => n.col === d - 1 && n.sel);
    if (!parent) continue;
    for (const ch of nodes.filter((n) => n.col === d)) {
      const x1 = parent.x + W, y1 = parent.y + H / 2, x2 = ch.x, y2 = ch.y + H / 2, mx = (x1 + x2) / 2;
      edges.push({ key: parent.id + ">" + ch.id, d: `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`, on: ch.sel });
    }
  }
  const width = PAD * 2 + cols.length * W + (cols.length - 1) * GX;
  const height = Math.max(...cols.map((c) => c.top + c.kids.length * (H + GY) - GY)) + PAD;
  const last = nodes.filter((n) => n.sel).pop();
  return { nodes, edges, width, height, selY: last ? last.y + H / 2 : null };
}
