"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useApp } from "../app";
import GameCard, { ApiCard } from "../GameCard";
import { rarityColor } from "../../lib/cardArt";
import { goalCopy, rarityName, tc } from "../../lib/train-copy";

const ORDER = ["legendary", "epic", "rare", "common"] as const;

/** Carosello: la carta scelta al centro, la precedente e la successiva ai lati, un po' sfocate. */
export default function CardCarousel({ cards, onOpen }: { cards: ApiCard[]; onOpen: (c: ApiCard) => void }) {
  const { lang } = useApp();
  const [filter, setFilter] = useState<string>("all");
  const [i, setI] = useState(0);
  const drag = useRef<{ x: number; moved: boolean } | null>(null);

  const counts = useMemo(() => Object.fromEntries(ORDER.map((r) => [r, cards.filter((c) => c.rarity === r).length])) as Record<string, number>, [cards]);
  const list = useMemo(() => (filter === "all" ? cards : cards.filter((c) => c.rarity === filter)), [cards, filter]);
  useEffect(() => { setI(0); }, [filter]);
  useEffect(() => { if (i > list.length - 1) setI(Math.max(0, list.length - 1)); }, [list.length, i]);

  const go = (d: number) => setI((x) => Math.max(0, Math.min(list.length - 1, x + d)));
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowLeft") { e.preventDefault(); go(-1); }
    if (e.key === "ArrowRight") { e.preventDefault(); go(1); }
    if (e.key === "Enter" && list[i]) onOpen(list[i]);
  };
  const down = (e: React.PointerEvent) => { drag.current = { x: e.clientX, moved: false }; };
  const up = (e: React.PointerEvent) => {
    const d = drag.current; drag.current = null;
    if (!d) return;
    const dx = e.clientX - d.x;
    if (Math.abs(dx) > 40) { go(dx < 0 ? 1 : -1); d.moved = true; }
  };

  return (
    <div className="car">
      <div className="chips car-filter" role="tablist" aria-label="Rarity">
        <button className={"chip" + (filter === "all" ? " on" : "")} onClick={() => setFilter("all")}>{tc("carAll", lang)} · {cards.length}</button>
        {ORDER.filter((r) => counts[r] > 0).map((r) => (
          <button key={r} className={"chip" + (filter === r ? " on" : "")} style={{ borderColor: rarityColor(r) }} onClick={() => setFilter(r)}>
            <i className="goal-dot" style={{ background: rarityColor(r), width: 8, height: 8, display: "inline-block", marginRight: 6 }} aria-hidden="true" />
            {rarityName(r, lang)} · {counts[r]}
          </button>
        ))}
      </div>

      {list.length > 0 && (
        <>
          <div className="car-stage" tabIndex={0} onKeyDown={onKey} onPointerDown={down} onPointerUp={up} onPointerCancel={() => { drag.current = null; }} aria-roledescription="carousel">
            {list.map((c, idx) => {
              const off = idx - i;
              if (Math.abs(off) > 2) return null;
              return (
                <div key={c.id} className={"car-slot o" + off} aria-hidden={off !== 0}
                  onClick={() => { if (off === 0) onOpen(c); else go(off); }}>
                  <GameCard card={c} still={off !== 0} />
                </div>
              );
            })}
          </div>
          <div className="car-bar">
            <button className="car-btn" onClick={() => go(-1)} disabled={i === 0} aria-label={tc("carPrev", lang)}>‹</button>
            <div className="car-info">
              <b>{goalCopy(list[i].goal, lang, list[i].data).title}</b>
              <span className="muted small">{tc("carOf", lang, { a: i + 1, b: list.length })}</span>
            </div>
            <button className="car-btn" onClick={() => go(1)} disabled={i === list.length - 1} aria-label={tc("carNext", lang)}>›</button>
          </div>
          <p className="muted small" style={{ textAlign: "center", margin: ".3rem 0 0" }}>{tc("carOpen", lang)}</p>
        </>
      )}
    </div>
  );
}
