"use client";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "../../../components/app";
import MistakeDrill from "../../../components/train/MistakeDrill";
import PuzzleTrainer from "../../../components/train/PuzzleTrainer";
import { Seg } from "../../../components/ui/Seg";
import { tc } from "../../../lib/train-copy";

type Tab = "mistakes" | "puzzles";

export default function TrainPage() {
  const { call, lang } = useApp();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("mistakes");
  const [ov, setOv] = useState<any>(null);

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("tab");
    if (q === "puzzles") setTab("puzzles");
    if (q === "badges" || q === "cards") router.replace(`/dashboard/rewards?tab=${q}`);   // vecchi collegamenti: premi e carte ora hanno la loro scheda
  }, [router]);
  const refresh = useCallback(() => { call("/train/overview").then(setOv).catch(() => {}); }, [call]);
  useEffect(() => { refresh(); }, [refresh]);

  const pick = (t: Tab) => { setTab(t); window.history.replaceState(null, "", `?tab=${t}`); };
  const st = ov?.stats;
  return (
    <>
      <div className="pagehead">
        <h1>{tc("trainTitle", lang)}</h1>
        <Seg<Tab> value={tab} onChange={pick} items={[{ v: "mistakes", label: tc("tabMistakes", lang), n: ov?.mistakes_due }, { v: "puzzles", label: tc("tabPuzzles", lang) }]} />
      </div>
      {st && (
        <div className="trainstrip" aria-label="stats">
          <span title={tc("streak0", lang)}><i className="flame" aria-hidden="true">●</i><b>{st.current_streak}</b>{tc("streakShort", lang)}</span>
          <span><b>{st.puzzle_rating}</b>{tc("puzzleRatingLbl", lang)}</span>
          <span><b>{ov.mistakes_due}</b>{tc("dueLbl", lang)}</span>
          <span><b>{ov.mistakes_new}</b>{tc("newLbl", lang)}</span>
        </div>
      )}
      {tab === "mistakes" ? <MistakeDrill onProgress={refresh} /> : <PuzzleTrainer onProgress={refresh} />}
    </>
  );
}
