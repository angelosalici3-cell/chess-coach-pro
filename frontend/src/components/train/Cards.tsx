"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "../app";
import GameCard, { ApiCard } from "../GameCard";
import CardCarousel from "./CardCarousel";
import { rarityColor } from "../../lib/cardArt";
import { Seg } from "../ui/Seg";
import { goalCopy, rarityName, speedName, tc } from "../../lib/train-copy";

const ORDER = ["common", "rare", "epic", "legendary"] as const;
type Cat = { goal: string; rarity: string; group: string; owned: boolean };

export default function Cards({ onProgress }: { onProgress: () => void }) {
  const { call, lang, refreshMe } = useApp();
  const [data, setData] = useState<{ cards: ApiCard[]; catalog: Cat[]; new: number; progress: any; hour_steps: number[] } | null>(null);
  const [err, setErr] = useState("");
  const [open, setOpen] = useState<ApiCard | null>(null);
  const [sub, setSub] = useState<"album" | "progress">("album");
  const [rar, setRar] = useState<string | null>(null);

  const load = () => call("/cards").then(setData).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, [call]); // eslint-disable-line
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(null); };
    window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k);
  }, [open]);

  // il NEW sparisce solo quando apri quella rarità
  const pickRarity = async (r: string) => {
    setRar(r);
    if (data?.cards.some((c) => c.rarity === r && c.new)) {
      setData({ ...data, cards: data.cards.map((c) => (c.rarity === r ? { ...c, new: c.new } : c)) });
      call("/cards/seen", { method: "POST", body: JSON.stringify({ rarity: r }) }).then(() => { refreshMe(); onProgress(); }).catch(() => {});
    }
  };
  const closeRarity = () => { setRar(null); load(); };

  if (err) return <div className="note err">{err}</div>;
  if (!data) return <p className="muted">…</p>;
  const { cards, catalog, progress: pr, hour_steps: steps } = data;
  const SUB = { it: ["Album", "Progressi"], en: ["Album", "Progress"], es: ["Álbum", "Progreso"] }[lang];
  const total = (r: string) => catalog.filter((c) => c.rarity === r).length;
  const owned = (r: string) => cards.filter((c) => c.rarity === r && catalog.some((k) => k.goal === c.goal)).length;
  const monthCards = (r: string) => cards.filter((c) => c.rarity === r && c.goal.startsWith("month_"));
  const rarCards = (r: string) => cards.filter((c) => c.rarity === r);
  const lockedOf = (r: string) => catalog.filter((c) => c.rarity === r && !c.owned).map((c) => ({ goal: c.goal, rarity: c.rarity }));
  const newIn = (r: string) => cards.filter((c) => c.rarity === r && c.new).length;

  return (
    <div>
      <Seg<"album" | "progress"> value={sub} onChange={(v) => { setSub(v); setRar(null); }} items={[{ v: "album", label: SUB[0], n: cards.length }, { v: "progress", label: SUB[1] }]} />

      {sub === "album" && !rar && (
        <>
          <p className="muted" style={{ marginTop: ".6rem" }}>{tc("albumHint", lang)}</p>
          <div className="rar-grid">
            {ORDER.map((r) => {
              const n = newIn(r), got = owned(r) + (r === "rare" ? monthCards(r).length : 0), tot = total(r) + (r === "rare" ? monthCards(r).length : 0);
              return (
                <button key={r} className={"rar-box" + (got === 0 ? " empty" : "")} style={{ ["--rc" as any]: rarityColor(r as any) }} onClick={() => pickRarity(r)}>
                  {n > 0 && <span className="new-pill">{tc("newFlag", lang)} · {n}</span>}
                  <span className="rar-gem" aria-hidden="true" />
                  <b>{rarityName(r, lang)}</b>
                  <span className="rar-count">{tc("albumOwned", lang, { a: got, b: tot })}</span>
                  <span className="bar"><i style={{ width: `${tot ? (100 * got) / tot : 0}%` }} /></span>
                </button>
              );
            })}
          </div>
          {cards.length === 0 && <div className="card" style={{ marginTop: ".8rem" }}><p style={{ margin: 0 }}>{tc("cardsEmpty", lang)}</p></div>}
          <p className="muted small" style={{ textAlign: "center" }}>{tc("monthNote", lang)}</p>
        </>
      )}

      {sub === "album" && rar && (
        <>
          <button className="btn btn-sm rar-back" onClick={closeRarity}>‹ {tc("albumBack", lang)}</button>
          <h2 className="rar-h" style={{ color: rarityColor(rar as any) }}>{rarityName(rar, lang)}</h2>
          <CardCarousel cards={rarCards(rar)} locked={lockedOf(rar)} onOpen={setOpen} />
        </>
      )}

      {sub === "progress" && <div className="card prog" style={{ marginTop: ".6rem" }}>
        <div className="muted small">{tc("hoursTitle", lang)}</div>
        <div className="prog-grid">
          {(["bullet", "blitz", "rapid", "classical"] as const).map((sp) => {
            const h = pr.hours[sp], next = steps.find((s) => s > h);
            return (
              <div key={sp}>
                <b>{speedName(sp, lang)}</b>
                <div className="muted small">{tc("hoursOf", lang, { h, g: pr.games[sp] })}</div>
                <div className="bar"><div style={{ width: `${next ? Math.min(100, (100 * h) / next) : 100}%`, background: "var(--ember)" }} /></div>
                <div className="muted small">{next ? tc("hoursNext", lang, { n: next }) : "✓"}</div>
              </div>
            );
          })}
        </div>
        <div className="chips" style={{ marginTop: ".7rem" }}>
          <span className="chip">{tc("streakAll", lang)}: {tc("streakNow", lang, { n: pr.runs.all, b: pr.best_runs.all })}</span>
          {pr.rating_next && <span className="chip">{tc("nextRating", lang, { n: pr.rating_next })}</span>}
        </div>
      </div>}

      {open && (
        <div className="ob-back" onMouseDown={(e) => { if (e.target === e.currentTarget) setOpen(null); }}>
          <div className="viewer" role="dialog" aria-modal="true">
            <button className="ob-x" onClick={() => setOpen(null)} aria-label={tc("cardClose", lang)}>×</button>
            <GameCard card={{ ...open, new: false }} showTools />
            <Link href={`/dashboard/games/${open.game.id}`} className="small accent">{tc("cardOpenGame", lang)}</Link>
          </div>
        </div>
      )}
    </div>
  );
}
