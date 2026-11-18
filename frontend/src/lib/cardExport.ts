import { encodeGif } from "./gif";
import { CARD_H, CARD_W, CardView, Fonts, drawCard, gifPlan } from "./cardArt";
import type { Pos } from "./cardPositions";

/** Legge i font dell'app (next/font li espone come variabili CSS) e li carica per il canvas. */
export async function cardFonts(): Promise<Fonts> {
  const css = getComputedStyle(document.documentElement);
  const pick = (v: string, fb: string) => (css.getPropertyValue(v).trim() || fb);
  const f = { display: pick("--font-display", "system-ui, sans-serif"), body: pick("--font-body", "system-ui, sans-serif") };
  try { await Promise.all([document.fonts.load(`800 32px ${f.display}`), document.fonts.load(`700 14px ${f.body}`)]); await document.fonts.ready; } catch { /* si usa il font di ripiego */ }
  return f;
}

const tick = () => new Promise<void>((r) => setTimeout(r, 0));

export async function makeGif(v: CardView, pos: Pos[], fonts: Fonts): Promise<Blob> {
  const c = document.createElement("canvas"); c.width = CARD_W; c.height = CARD_H;
  const ctx = c.getContext("2d", { willReadFrequently: true })!;
  const frames = [];
  for (const f of gifPlan(pos.length - 1, v.game.hi)) {
    drawCard(ctx, v, pos, f.ply, fonts, 0);
    frames.push({ rgba: new Uint8ClampedArray(ctx.getImageData(0, 0, CARD_W, CARD_H).data), delay: f.delay });
    await tick();                                              // lascia respirare l'interfaccia
  }
  return new Blob([encodeGif(CARD_W, CARD_H, frames) as BlobPart], { type: "image/gif" });
}

export function makePng(v: CardView, pos: Pos[], fonts: Fonts): Promise<Blob> {
  const c = document.createElement("canvas"); c.width = CARD_W * 2; c.height = CARD_H * 2;
  const ctx = c.getContext("2d")!; ctx.scale(2, 2);
  drawCard(ctx, v, pos, pos.length - 1, fonts, 0);
  return new Promise((res, rej) => c.toBlob((b) => (b ? res(b) : rej(new Error("png"))), "image/png"));
}

/** Video della partita (MP4 dove il browser lo permette, altrimenti WebM): è il formato che Instagram e TikTok accettano. */
export async function makeVideo(v: CardView, pos: Pos[], fonts: Fonts): Promise<Blob | null> {
  if (typeof MediaRecorder === "undefined") return null;
  const mime = ["video/mp4;codecs=avc1", "video/mp4", "video/webm;codecs=vp9", "video/webm"].find((m) => MediaRecorder.isTypeSupported(m));
  if (!mime) return null;
  const c = document.createElement("canvas"); c.width = CARD_W; c.height = CARD_H;
  const ctx = c.getContext("2d")!;
  drawCard(ctx, v, pos, 0, fonts, 0);
  const rec = new MediaRecorder(c.captureStream(30), { mimeType: mime, videoBitsPerSecond: 3_000_000 });
  const chunks: Blob[] = [];
  rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
  const done = new Promise<void>((r) => { rec.onstop = () => r(); });
  rec.start();
  for (const f of gifPlan(pos.length - 1, v.game.hi)) {
    drawCard(ctx, v, pos, f.ply, fonts, 0);
    await new Promise((r) => setTimeout(r, f.delay * 10));
  }
  rec.stop(); await done;
  return new Blob(chunks, { type: mime.split(";")[0] });
}

/** Apre il foglio di condivisione del telefono con il file; se non c'è, lo scarica. */
export async function shareOrSave(blob: Blob, filename: string, text: string): Promise<"shared" | "saved" | "cancelled"> {
  const file = new File([blob], filename, { type: blob.type });
  const nav = navigator as Navigator & { canShare?: (d: ShareData) => boolean };
  if (nav.canShare?.({ files: [file] })) {
    try { await nav.share({ files: [file], text, title: "Chess Coach" }); return "shared"; }
    catch (e: any) { if (e?.name === "AbortError") return "cancelled"; }
  }
  const url = URL.createObjectURL(blob), a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
  return "saved";
}
