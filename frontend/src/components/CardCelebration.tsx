"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "./app";
import GameCard, { ApiCard, prepare } from "./GameCard";
import { cardFonts, shareOrSave } from "../lib/cardExport";
import { getFile } from "../lib/cardCache";
import { rarityColor } from "../lib/cardArt";
import { goalCopy, rarityName, tc } from "../lib/train-copy";

const CONF = ["#ff6b3d", "#ffd56a", "#4ee3b0", "#5aa9ff", "#ff5d8f"];

/** Appare appena c'è una carta nuova: preview statica subito (si disegna in pochi millisecondi), GIF e immagine si preparano intanto in sottofondo. */
export default function CardCelebration() {
  const { me, call, lang, refreshMe } = useApp();
  const router = useRouter();
  const [cards, setCards] = useState<ApiCard[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [parts] = useState(() => Array.from({ length: 30 }, (_, i) => ({ dx: (Math.random() - 0.5) * 760, dy: -200 + Math.random() * 520, rot: Math.random() * 720, c: CONF[i % CONF.length] })));

  useEffect(() => {
    if (!me?.new_cards || cards) return;
    let live = true;
    call("/cards").then(async (d) => {
      const fresh: ApiCard[] = d.cards.filter((c: ApiCard) => c.new);
      if (!live || !fresh.length) return;
      setCards(fresh);
      const f = await cardFonts(); for (const c of fresh.slice(0, 3)) prepare(c, lang, f);   // pronte prima che l'utente tocchi Condividi
    }).catch(() => {});
    return () => { live = false; };
  }, [me?.new_cards]); // eslint-disable-line

  if (!cards || !cards.length) return null;
  const c = cards[0], t = goalCopy(c.goal, lang);
  const close = async (go = false) => { setCards(null); await call("/cards/seen", { method: "POST" }).catch(() => {}); refreshMe(); if (go) router.push("/dashboard/train?tab=cards"); };
  const share = async () => {
    setBusy(true);
    try {
      const key = `${c.id}:${c.goal}:${lang}:gif`; let b = await getFile(key);
      if (!b) { const f = await cardFonts(); await prepare(c, lang, f); b = await getFile(key); }
      if (b) {
        const g = c.game, won = g.result !== "1/2-1/2" && (g.result === "1-0") === (g.color === "white");
        await shareOrSave(b, `chess-coach-${c.goal}.gif`, won ? tc("cardShareText", lang, { opp: g.opp, n: Math.ceil(g.sans.length / 2) }) : tc("cardShareTextNoWin", lang));
      }
    } catch { /* l'utente può riprovare dall'album */ }
    setBusy(false);
  };
  return (
    <div className="ob-back" role="dialog" aria-modal="true" aria-label={tc("celebTitle", lang, { rarity: rarityName(c.rarity, lang) })}>
      <div className="burst" aria-hidden="true">{parts.map((b, i) => <i key={i} style={{ background: b.c, ["--dx" as string]: `${b.dx}px`, ["--dy" as string]: `${b.dy}px`, ["--rot" as string]: `${b.rot}deg` }} />)}</div>
      <div className="viewer celeb">
        <h2 style={{ color: rarityColor(c.rarity), marginTop: 0 }}>{tc("celebTitle", lang, { rarity: rarityName(c.rarity, lang) })}</h2>
        <p className="muted" style={{ marginTop: 0 }}>{tc("celebSub", lang, { title: t.title })}</p>
        <GameCard card={{ ...c, new: false }} still />
        {cards.length > 1 && <p className="muted small" style={{ margin: ".7rem 0 0" }}>{tc("celebMore", lang, { n: cards.length - 1 })}</p>}
        <div className="gc-tools">
          <button className="btn btn-primary" onClick={share} disabled={busy}>{tc("celebShare", lang)}</button>
          <button className="btn" onClick={() => close(true)}>{tc("celebView", lang)}</button>
          <button className="btn btn-sm ob-skip" onClick={() => close()}>{tc("celebLater", lang)}</button>
        </div>
      </div>
    </div>
  );
}
