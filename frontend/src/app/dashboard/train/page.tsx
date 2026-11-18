"use client";
import { useCallback, useEffect, useState } from "react";
import { useApp } from "../../../components/app";
import MistakeDrill from "../../../components/train/MistakeDrill";
import PuzzleTrainer from "../../../components/train/PuzzleTrainer";
import Achievements from "../../../components/train/Achievements";
import Cards from "../../../components/train/Cards";
import { tc } from "../../../lib/train-copy";

type Tab = "mistakes" | "puzzles" | "badges" | "cards";

export default function TrainPage() {
  const { call, lang } = useApp();
  const [tab, setTab] = useState<Tab>("mistakes");
  const [ov, setOv] = useState<any>(null);

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("tab");
    if (q === "puzzles" || q === "badges" || q === "cards") setTab(q);
  }, []);
  const refresh = useCallback(() => { call("/train/overview").then(setOv).catch(() => {}); }, [call]);
  useEffect(() => { refresh(); }, [refresh]);

  const pick = (t: Tab) => { setTab(t); window.history.replaceState(null, "", `?tab=${t}`); };
  const st = ov?.stats;
  return (
    <>
      <div className="pagehead"><h1>{tc("trainTitle", lang)}</h1></div>
      {st && (
        <div className="trainbar">
          <div className="card"><div className="muted small">{st.current_streak > 0 ? tc("streak", lang, { n: st.current_streak }) : tc("streak0", lang)}</div><div className="big flame">{st.current_streak}</div></div>
          <div className="card"><div className="muted small">{tc("puzzleRatingLbl", lang)}</div><div className="big">{st.puzzle_rating}</div></div>
          <div className="card"><div className="muted small">{tc("dueLbl", lang)}</div><div className="big">{ov.mistakes_due}</div></div>
          <div className="card"><div className="muted small">{tc("newLbl", lang)}</div><div className="big">{ov.mistakes_new}</div></div>
        </div>
      )}
      <div className="tabs" role="tablist">
        {(["mistakes", "puzzles", "badges", "cards"] as Tab[]).map((k) => (
          <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => pick(k)}>
            {tc(k === "mistakes" ? "tabMistakes" : k === "puzzles" ? "tabPuzzles" : k === "badges" ? "tabBadges" : "tabCards", lang)}
          </button>
        ))}
      </div>
      {tab === "mistakes" && <MistakeDrill onProgress={refresh} />}
      {tab === "puzzles" && <PuzzleTrainer onProgress={refresh} />}
      {tab === "badges" && <Achievements onProgress={refresh} />}
      {tab === "cards" && <Cards onProgress={refresh} />}
    </>
  );
}
