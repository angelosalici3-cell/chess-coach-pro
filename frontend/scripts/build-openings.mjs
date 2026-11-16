// Scarica il database delle aperture di Lichess (CC0) e lo trasforma in public/openings.json (albero compatto).
// Girà automaticamente prima di `next build` (prebuild). Se il download fallisce, resta il file già presente (seed incluso).
import { readFile, writeFile, mkdir, access } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const BASE = "https://raw.githubusercontent.com/lichess-org/chess-openings/master/";
const OUT = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "openings.json");
const DIR = process.env.OPENINGS_DIR;
const FILES = (process.env.OPENINGS_FILES || "a.tsv,b.tsv,c.tsv,d.tsv,e.tsv").split(",");

async function load(f) {
  if (DIR) return readFile(join(DIR, f), "utf8");
  const r = await fetch(BASE + f, { signal: AbortSignal.timeout(30000) });
  if (!r.ok) throw new Error(`${f}: HTTP ${r.status}`);
  return r.text();
}

export function tokens(pgn) {
  return pgn.replace(/\{[^}]*\}/g, " ").replace(/\d+\.(\.\.)?/g, " ").replace(/\b(1-0|0-1|1\/2-1\/2|\*)\b/g, " ").split(/\s+/).filter(Boolean);
}

export function build(rows) {
  const root = { kids: new Map() };
  let count = 0;
  for (const { eco, name, pgn } of rows) {
    const toks = tokens(pgn);
    if (!toks.length) continue;
    let n = root;
    for (const san of toks) {
      if (!n.kids.has(san)) n.kids.set(san, { kids: new Map() });
      n = n.kids.get(san);
    }
    if (!n.name) { n.eco = eco; n.name = name; count++; }
  }
  const ser = (m) => [...m].map(([san, n]) => (n.name ? [san, ser(n.kids), n.eco, n.name] : [san, ser(n.kids)]));
  return { tree: ser(root.kids), count };
}

export function parse(text) {
  return text.split(/\r?\n/).map((l) => l.split("\t")).filter((c) => c.length >= 3 && c[0].trim().toLowerCase() !== "eco")
    .map((c) => ({ eco: c[0].trim(), name: c[1].trim().replace(/^"|"$/g, ""), pgn: c[2].trim() }));
}

async function main() {
  try {
    const rows = [];
    for (const f of FILES) {
      try { rows.push(...parse(await load(f))); } catch (e) { if (DIR) continue; throw e; }
    }
    const { tree, count } = build(rows);
    if (count < 50) throw new Error(`troppe poche aperture (${count})`);
    await mkdir(dirname(OUT), { recursive: true });
    await writeFile(OUT, JSON.stringify({ v: 1, count, t: tree }));
    console.log(`openings.json: ${count} aperture`);
  } catch (e) {
    let have = true;
    try { await access(OUT); } catch { have = false; }
    console.warn(`build-openings: ${e.message}. ${have ? "Uso il file esistente." : "Nessun file disponibile!"}`);
    if (!have) process.exit(1);
  }
}
if (process.argv[1] && process.argv[1].endsWith("build-openings.mjs")) main();
