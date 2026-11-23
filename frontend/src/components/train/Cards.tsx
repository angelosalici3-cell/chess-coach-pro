"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "../app";
import GameCard, { ApiCard } from "../GameCard";
import CardCarousel from "./CardCarousel";
import { rarityColor } from "../../lib/cardArt";
import { Seg } from "../ui/Seg";
import { goalCopy, rarityName, speedName, tc } from "../../lib/train-copy";

export default function Cards({ onProgress }: { onProgress: () => void }) {
  const { call, lang } = useApp();
  const [data, setData] = useState<{ cards: ApiCard[]; goals: any[]; new: number; progress: any; hour_steps: number[] } | null>(null);
  const [err, setErr] = useState("");
  const [open, setOpen] = useState<ApiCard | null>(null);
  const [sub, setSub] = useState<"album" | "progress" | "goals">("album");

  useEffect(() => {
    call("/cards").then((d) => { setData(d); if (d.cards.some((c: ApiCard) => c.new)) call("/cards/seen", { method: "POST" }).then(onProgress).catch(() => {}); }).catch((e) => setErr(e.message));
  }, [call]); // eslint-disable-line
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(null); };
    window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k);
  }, [open]);

  if (err) return <div className="note err">{err}</div>;
  if (!data) return <p className="muted">…</p>;
  const { cards, goals, progress: pr, hour_steps: steps } = data;
  const singles = goals.filter((g) => g.group === "single");
  const SUB = { it: ["Album", "Progressi", "Obiettivi"], en: ["Album", "Progress", "Goals"], es: ["Álbum", "Progreso", "Objetivos"] }[lang];
  return (
    <div>
      <Seg<"album" | "progress" | "goals"> value={sub} onChange={setSub} items={[{ v: "album", label: SUB[0], n: cards.length }, { v: "progress", label: SUB[1] }, { v: "goals", label: SUB[2] }]} />
      {sub === "album" && <p className="muted" style={{ marginTop: ".6rem" }}>{tc("cardsSub", lang)}</p>}
      {sub === "album" && data.new > 0 && <div className="note ok">{tc("cardsNew", lang, { n: data.new })}</div>}
      {sub === "album" && (cards.length === 0 ? <div className="card"><p style={{ margin: 0 }}>{tc("cardsEmpty", lang)}</p></div> : (
        <CardCarousel cards={cards} onOpen={setOpen} />
      ))}
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
        <p className="muted small" style={{ margin: ".6rem 0 0" }}>{tc("hoursNote", lang)}</p>
        {pr.vs && Object.keys(pr.vs).length > 0 && (
          <div style={{ marginTop: ".8rem" }}>
            <div className="muted small">{tc("vsGroup", lang)}</div>
            <div className="chips" style={{ marginTop: ".3rem" }}>
              {Object.entries(pr.vs).map(([sp, v]: any) => <span key={sp} className="chip">{tc("vsNext", lang, { sp: speedName(sp, lang), n: v.next })}</span>)}
            </div>
            <p className="muted small" style={{ margin: ".4rem 0 0" }}>{tc("vsNote", lang)}</p>
          </div>
        )}
        <div className="chips" style={{ marginTop: ".7rem" }}>
          {(["all", "w", "b"] as const).map((k) => <span key={k} className="chip">{tc(k === "all" ? "streakAll" : k === "w" ? "streakW" : "streakB", lang)}: {tc("streakNow", lang, { n: pr.runs[k], b: pr.best_runs[k] })}</span>)}
        </div>
      </div>}
      {sub === "goals" && <div className="goal-list" style={{ marginTop: ".6rem" }}>
        {singles.map((g) => {
          const t = goalCopy(g.goal, lang);
          return (
            <div key={g.goal} className={"card goal" + (g.owned ? " got" : "")}>
              <i className="goal-dot" style={{ background: rarityColor(g.rarity) }} aria-hidden="true" />
              <div><b>{t.title}</b> <span className="muted small">{rarityName(g.rarity, lang)}</span><div className="muted small">{t.sub.replace(/\{\w+\}/g, "…")}</div></div>
              <span className="muted small">{tc("cardOwned", lang, { a: g.owned, b: g.max })}</span>
            </div>
          );
        })}
        {([["streak_all", "streakAll"], ["streak_w", "streakW"], ["streak_b", "streakB"], ["hours", "hoursTitle"], ["vs", "vsGroup"]] as const).filter(([grp]) => grp !== "vs" || goals.some((g) => g.group === "vs")).map(([grp, label]) => (
          <div key={grp} className="card goal grp">
            <div style={{ flex: 1 }}>
              <b>{tc(label, lang)}</b>
              <div className="chips" style={{ margin: ".4rem 0 0" }}>
                {goals.filter((g) => g.group === grp).map((g) => (
                  <span key={g.goal} className={"chip" + (g.owned ? " on" : "")} title={goalCopy(g.goal, lang).sub} style={{ borderColor: rarityColor(g.rarity) }}>{g.owned ? "✓ " : ""}{goalCopy(g.goal, lang).title}</span>
                ))}
              </div>
            </div>
          </div>
        ))}
        <div className="card goal"><i className="goal-dot" style={{ background: rarityColor("rare") }} aria-hidden="true" /><div><b>{tc("openShieldsTitle", lang)}</b><div className="muted small">{tc("openShieldsSub", lang)}</div></div></div>
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
