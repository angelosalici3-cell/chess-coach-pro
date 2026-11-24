"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useApp } from "../app";
import GameCard, { ApiCard } from "../GameCard";
import { rarityColor } from "../../lib/cardArt";
import { goalCopy, rarityName, tc } from "../../lib/train-copy";

export type Locked = { goal: string; rarity: string };
type Item = { key: string; card?: ApiCard; locked?: Locked };

/** Carosello: la carta scelta al centro, la precedente e la successiva ai lati, un po' sfocate. Le carte ancora da conquistare sono sagome con l'indizio. */
export default function CardCarousel({ cards, locked = [], onOpen }: { cards: ApiCard[]; locked?: Locked[]; onOpen: (c: ApiCard) => void }) {
  const { lang } = useApp();
  const [i, setI] = useState(0);
  const drag = useRef<{ x: number } | null>(null);
  const list: Item[] = useMemo(() => [...cards.map((c) => ({ key: "c" + c.id, card: c })), ...locked.map((l) => ({ key: "l" + l.goal, locked: l }))], [cards, locked]);
  useEffect(() => { if (i > list.length - 1) setI(Math.max(0, list.length - 1)); }, [list.length, i]);

  const go = (d: number) => setI((x) => Math.max(0, Math.min(list.length - 1, x + d)));
  const cur = list[i];
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowLeft") { e.preventDefault(); go(-1); }
    if (e.key === "ArrowRight") { e.preventDefault(); go(1); }
    if (e.key === "Enter" && cur?.card) onOpen(cur.card);
  };
  const down = (e: React.PointerEvent) => { drag.current = { x: e.clientX }; };
  const up = (e: React.PointerEvent) => {
    const d = drag.current; drag.current = null;
    if (d && Math.abs(e.clientX - d.x) > 40) go(e.clientX - d.x < 0 ? 1 : -1);
  };
  if (!list.length) return null;
  const t = cur.card ? goalCopy(cur.card.goal, lang, cur.card.data) : goalCopy(cur.locked!.goal, lang);
  return (
    <div className="car">
      <div className="car-stage" tabIndex={0} onKeyDown={onKey} onPointerDown={down} onPointerUp={up} onPointerCancel={() => { drag.current = null; }} aria-roledescription="carousel">
        {list.map((it, idx) => {
          const off = idx - i;
          if (Math.abs(off) > 2) return null;
          return (
            <div key={it.key} className={"car-slot o" + off} aria-hidden={off !== 0}
              onClick={() => { if (off !== 0) go(off); else if (it.card) onOpen(it.card); }}>
              {it.card ? <GameCard card={it.card} still={off !== 0} /> : (
                <div className="gc-locked" style={{ borderColor: rarityColor(it.locked!.rarity as any) }}>
                  <svg viewBox="0 0 24 24" width="44" height="44" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 018 0v3" /></svg>
                  <b>{goalCopy(it.locked!.goal, lang).title}</b>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="car-bar">
        <button className="car-btn" onClick={() => go(-1)} disabled={i === 0} aria-label={tc("carPrev", lang)}>‹</button>
        <div className="car-info">
          <b>{t.title}</b>
          <span className="muted small">{tc("carOf", lang, { a: i + 1, b: list.length })}{cur.locked ? " · " + tc("lockedTag", lang) : ""}</span>
        </div>
        <button className="car-btn" onClick={() => go(1)} disabled={i === list.length - 1} aria-label={tc("carNext", lang)}>›</button>
      </div>
      {cur.locked
        ? <p className="car-how"><b>{tc("howTo", lang)}</b><br />{t.sub.replace(/\{\w+\}/g, "…")}</p>
        : <p className="muted small" style={{ textAlign: "center", margin: ".3rem 0 0" }}>{tc("carOpen", lang)}</p>}
    </div>
  );
}
