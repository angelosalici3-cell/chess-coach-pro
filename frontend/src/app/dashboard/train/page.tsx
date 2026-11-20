"use client";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "../../../components/app";
import MistakeDrill from "../../../components/train/MistakeDrill";
import PuzzleTrainer from "../../../components/train/PuzzleTrainer";
import { Seg } from "../../../components/ui/Seg";
import { tc } from "../../../lib/train-copy";
import { patternTitle, pc } from "../../../lib/pattern-copy";

type Tab = "mistakes" | "puzzles";

export default function TrainPage() {
  const { call, lang } = useApp();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("mistakes");
  const [ov, setOv] = useState<any>(null);
  const [tag, setTag] = useState("");
  const [ready, setReady] = useState(false);   // si legge prima il parametro ?tag=, poi parte l'esercizio

  useEffect(() => {
    const sp = new URLSearchParams(window.location.search);
    const q = sp.get("tab");
    setTag(sp.get("tag") || "");
    setReady(true);
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
      {tab === "mistakes" && tag && (
        <div className="note drillnote">
          <span>{pc("drillOn", lang, { t: patternTitle(tag, lang) })}</span>
          <button className="btn btn-ghost btn-sm" onClick={() => { setTag(""); window.history.replaceState(null, "", "?tab=mistakes"); }}>{pc("drillAll", lang)}</button>
        </div>
      )}
      {!ready ? null : tab === "mistakes" ? <MistakeDrill onProgress={refresh} tag={tag || undefined} /> : <PuzzleTrainer onProgress={refresh} />}
    </>
  );
}
