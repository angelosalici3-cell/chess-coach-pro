/** Codificatore GIF animata senza dipendenze: palette globale a 256 colori e fotogrammi "a differenza" (si salva solo l'area che cambia). */
export type GifFrame = { rgba: Uint8ClampedArray | Uint8Array; delay: number }; // delay in centesimi di secondo

function buildPalette(frames: GifFrame[], npx: number): Uint8Array {
  const count = new Map<number, [number, number, number, number]>();
  const picks = new Set<number>([0, frames.length - 1, Math.floor(frames.length / 2), Math.floor(frames.length / 4), Math.floor((3 * frames.length) / 4)]);
  for (const fi of picks) {
    const d = frames[fi].rgba;
    for (let i = 0; i < npx; i += 2) {                         // un pixel su due basta per il campione
      const r = d[i * 4], g = d[i * 4 + 1], b = d[i * 4 + 2];
      const k = ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3);
      const e = count.get(k);
      if (e) { e[0]++; e[1] += r; e[2] += g; e[3] += b; } else count.set(k, [1, r, g, b]);
    }
  }
  const top = [...count.values()].sort((a, b) => b[0] - a[0]).slice(0, 256);
  const pal = new Uint8Array(768);
  top.forEach((e, i) => { pal[i * 3] = Math.round(e[1] / e[0]); pal[i * 3 + 1] = Math.round(e[2] / e[0]); pal[i * 3 + 2] = Math.round(e[3] / e[0]); });
  return pal;
}

function lzw(px: Uint8Array): number[] {
  const out: number[] = [];
  let cur = 0, nb = 0;
  const emit = (code: number, size: number) => { cur |= code << nb; nb += size; while (nb >= 8) { out.push(cur & 255); cur >>>= 8; nb -= 8; } };
  const CLEAR = 256, EOI = 257;
  let size = 9, next = 258, dict = new Map<number, number>();
  emit(CLEAR, size);
  let prefix = px[0];
  for (let i = 1; i < px.length; i++) {
    const k = px[i], key = (prefix << 8) | k, c = dict.get(key);
    if (c !== undefined) { prefix = c; continue; }
    emit(prefix, size);
    if (next < 4096) {
      dict.set(key, next);
      if (next === (1 << size)) size++;
      next++;
    } else { emit(CLEAR, size); dict = new Map(); size = 9; next = 258; }
    prefix = k;
  }
  emit(prefix, size); emit(EOI, size);
  if (nb > 0) out.push(cur & 255);
  return out;
}

export function encodeGif(w: number, h: number, frames: GifFrame[]): Uint8Array {
  const npx = w * h, pal = buildPalette(frames, npx);
  const cache = new Map<number, number>();
  const nearest = (r: number, g: number, b: number) => {
    const key = ((r >> 2) << 12) | ((g >> 2) << 6) | (b >> 2);   // 6 bit per canale come chiave di cache
    let v = cache.get(key);
    if (v !== undefined) return v;
    let best = 0, bd = 1e9;
    for (let i = 0; i < 256; i++) {
      const dr = pal[i * 3] - r, dg = pal[i * 3 + 1] - g, db = pal[i * 3 + 2] - b, d = dr * dr * 3 + dg * dg * 4 + db * db * 2;
      if (d < bd) { bd = d; best = i; }
    }
    cache.set(key, best);
    return best;
  };
  const out: number[] = [];
  const u16 = (n: number) => out.push(n & 255, (n >> 8) & 255);
  out.push(...[..."GIF89a"].map((c) => c.charCodeAt(0)));
  u16(w); u16(h); out.push(0xf7, 0, 0);
  for (let i = 0; i < 768; i++) out.push(pal[i]);
  out.push(0x21, 0xff, 0x0b, ...[..."NETSCAPE2.0"].map((c) => c.charCodeAt(0)), 3, 1, 0, 0, 0);   // ripetizione infinita

  let prev: Uint8Array | null = null, pending: { x: number; y: number; w: number; h: number; px: Uint8Array; delay: number } | null = null;
  const flush = () => {
    if (!pending) return;
    const p = pending;
    out.push(0x21, 0xf9, 4, 0x04); u16(Math.max(2, p.delay)); out.push(0, 0);
    out.push(0x2c); u16(p.x); u16(p.y); u16(p.w); u16(p.h); out.push(0, 8);
    const data = lzw(p.px);
    for (let i = 0; i < data.length; i += 255) { const n = Math.min(255, data.length - i); out.push(n); for (let j = 0; j < n; j++) out.push(data[i + j]); }
    out.push(0);
    pending = null;
  };
  for (const f of frames) {
    const idx = new Uint8Array(npx);
    for (let i = 0; i < npx; i++) idx[i] = nearest(f.rgba[i * 4], f.rgba[i * 4 + 1], f.rgba[i * 4 + 2]);
    let x0 = 0, y0 = 0, x1 = w - 1, y1 = h - 1;
    if (prev) {
      x0 = w; y0 = h; x1 = -1; y1 = -1;
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (idx[y * w + x] !== prev[y * w + x]) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
      if (x1 < 0) { if (pending) pending.delay += f.delay; continue; }   // fotogramma identico: allunga il precedente
    }
    flush();
    const bw = x1 - x0 + 1, bh = y1 - y0 + 1, sub = new Uint8Array(bw * bh);
    for (let y = 0; y < bh; y++) sub.set(idx.subarray((y0 + y) * w + x0, (y0 + y) * w + x0 + bw), y * bw);
    pending = { x: x0, y: y0, w: bw, h: bh, px: sub, delay: f.delay };
    prev = idx;
  }
  flush();
  out.push(0x3b);
  return Uint8Array.from(out);
}
