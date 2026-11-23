"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useApp } from "./app";
import { CARD_H, CARD_W, CardLabels, CardView, Fonts, Rarity, drawCard } from "../lib/cardArt";
import { positions } from "../lib/cardPositions";
import { cardFonts, makeGif, makePng, makeVideo, shareOrSave } from "../lib/cardExport";
import { getFile, putFile } from "../lib/cardCache";
import { goalCopy, rarityName, tc } from "../lib/train-copy";
import type { Lang } from "../lib/i18n";

export type ApiCard = { id: number; goal: string; rarity: Rarity; new: boolean; data: any; game: any };

export function viewOf(card: ApiCard, lang: Lang): CardView {
  const gc = goalCopy(card.goal, lang, card.data), g = card.game;
  const labels: CardLabels = {
    rarity: rarityName(card.rarity, lang), title: gc.title, subtitle: gc.sub, me: tc("cMe", lang), opp: tc("cOpp", lang),
    win: tc("cWin", lang), loss: tc("cLoss", lang), draw: tc("cDraw", lang), moves: tc("cMoves", lang), accuracy: tc("cAcc", lang),
    opening: g.opening || "", brand: "CHESS COACH",
  };
  return { rarity: card.rarity, labels, game: { me: g.me, opp: g.opp, color: g.color, result: g.result, opening: g.opening, hi: g.hi, date: g.date, acc: g.acc, elo: g.elo, opp_elo: g.opp_elo, sans: g.sans } };
}

/** La carta: la partita si rigioca da sola dentro la carta. `still` mostra solo la posizione finale (miniature dell'album). */
/** Prepara in anticipo GIF e immagine: finché sono pronte il pulsante Condividi risponde subito (e il telefono accetta la condivisione, che vuole un tocco recente). */
const queue: Promise<unknown>[] = [];
export function prepare(card: ApiCard, lang: Lang, fonts: Fonts): Promise<void> {
  const view = viewOf(card, lang), pos = positions(card.game.sans);
  const job = async () => {
    for (const kind of ["png", "gif"] as const) {
      const key = `${card.id}:${card.goal}:${lang}:${kind}`;
      if (await getFile(key)) continue;
      await putFile(key, kind === "gif" ? await makeGif(view, pos, fonts) : await makePng(view, pos, fonts));
    }
  };
  const p = (queue.length ? queue[queue.length - 1].catch(() => {}) : Promise.resolve()).then(job);   // una carta alla volta: l'interfaccia resta fluida
  queue.push(p); p.finally(() => { queue.splice(queue.indexOf(p), 1); }).catch(() => {});
  return p.catch(() => {});
}

export default function GameCard({ card, still = false, showTools = false }: { card: ApiCard; still?: boolean; showTools?: boolean }) {
  const { lang } = useApp();
  const ref = useRef<HTMLCanvasElement>(null);
  const [fonts, setFonts] = useState<Fonts | null>(null);
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState("");
  const view = useMemo(() => viewOf(card, lang), [card, lang]);
  const pos = useMemo(() => positions(card.game.sans), [card]);

  useEffect(() => { cardFonts().then(setFonts); }, []);
  useEffect(() => { if (fonts && showTools) prepare(card, lang, fonts); }, [fonts, card, lang, showTools]);
  useEffect(() => {
    const cv = ref.current; if (!cv || !fonts) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    cv.width = CARD_W * dpr; cv.height = CARD_H * dpr;
    const ctx = cv.getContext("2d")!; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const total = pos.length - 1;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (still || reduce) { drawCard(ctx, view, pos, total, fonts, 0); return; }
    const per = Math.max(260, Math.min(650, 24000 / Math.max(1, total)));
    const hi = view.game.hi && view.game.hi < total ? view.game.hi : 0, holdHi = hi ? 1600 : 0;
    let raf = 0, t0 = performance.now();
    const loop = (now: number) => {
      const t = now - t0, hold0 = 900, hold1 = 2800, run = total * per + holdHi, cycle = hold0 + run + hold1;
      const k = t % cycle;
      let ply = k < hold0 ? 0 : Math.min(total, Math.floor((k - hold0) / per) + 1);
      if (hi && k >= hold0 + hi * per) ply = k < hold0 + hi * per + holdHi ? hi : Math.min(total, hi + Math.floor((k - hold0 - hi * per - holdHi) / per) + 1);
      drawCard(ctx, view, pos, ply, fonts, (now / 3600) % 1);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [fonts, view, pos, still]);

  const run = async (kind: "gif" | "video" | "png") => {
    if (!fonts || busy) return;
    setBusy(kind); setMsg(tc("cardMaking", lang));
    try {
      const g = card.game, w = (g.result === "1-0") === (g.color === "white") && g.result !== "1/2-1/2";
      const text = w ? tc("cardShareText", lang, { opp: g.opp, n: Math.ceil((pos.length - 1) / 2) }) : tc("cardShareTextNoWin", lang);
      const key = `${card.id}:${card.goal}:${lang}:${kind}`;
      const cached = kind === "video" ? null : await getFile(key);   // già pronta in anticipo: nessuna attesa
      const blob = cached ?? (kind === "gif" ? await makeGif(view, pos, fonts) : kind === "png" ? await makePng(view, pos, fonts) : await makeVideo(view, pos, fonts));
      if (!blob) throw new Error("unsupported");
      const ext = kind === "gif" ? "gif" : kind === "png" ? "png" : blob.type.includes("mp4") ? "mp4" : "webm";
      const r = await shareOrSave(blob, `elorise-${card.goal}-${card.id}.${ext}`, text);
      setMsg(r === "shared" ? tc("cardShared", lang) : r === "saved" ? tc("cardSaved", lang) : "");
    } catch { setMsg(tc("cardFail", lang)); }
    setBusy("");
  };

  return (
    <div className="gc">
      <canvas ref={ref} className="gc-canvas" style={{ aspectRatio: `${CARD_W} / ${CARD_H}` }} aria-label={`${view.labels.title}: ${card.game.me} vs ${card.game.opp}`} role="img" />
      {card.new && <span className="gc-new">{tc("cardNewTag", lang)}</span>}
      {showTools && (
        <div className="gc-tools">
          <button className="btn btn-primary btn-sm" onClick={() => run("gif")} disabled={!!busy}>{tc("cardGif", lang)}</button>
          <button className="btn btn-sm" onClick={() => run("video")} disabled={!!busy}>{tc("cardVideo", lang)}</button>
          <button className="btn btn-sm" onClick={() => run("png")} disabled={!!busy}>{tc("cardPng", lang)}</button>
          {msg && <div className="muted small" role="status" style={{ width: "100%", textAlign: "center" }}>{msg}</div>}
        </div>
      )}
    </div>
  );
}
