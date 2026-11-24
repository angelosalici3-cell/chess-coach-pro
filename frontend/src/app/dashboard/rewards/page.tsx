"use client";
import { useCallback, useEffect, useState } from "react";
import { useApp } from "../../../components/app";
import Achievements from "../../../components/train/Achievements";
import Journey from "../../../components/train/Journey";
import Cards from "../../../components/train/Cards";
import { Seg } from "../../../components/ui/Seg";
import { tc } from "../../../lib/train-copy";
import { u } from "../../../lib/ui-copy";

type Tab = "path" | "cards" | "badges";

export default function RewardsPage() {
  const { call, lang } = useApp();
  const [tab, setTab] = useState<Tab>("path");
  const [, setOv] = useState<any>(null);
  useEffect(() => { if (new URLSearchParams(window.location.search).get("tab") === "badges") setTab("badges"); else if (new URLSearchParams(window.location.search).get("tab") === "cards") setTab("cards"); }, []);
  const refresh = useCallback(() => { call("/train/overview").then(setOv).catch(() => {}); }, [call]);
  const pick = (v: Tab) => { setTab(v); window.history.replaceState(null, "", `?tab=${v}`); };
  return (
    <>
      <div className="pagehead">
        <h1>{u("rwTitle", lang)}</h1>
        <Seg<Tab> value={tab} onChange={pick} items={[{ v: "path", label: { it: "Percorso", en: "Journey", es: "Camino" }[lang] }, { v: "cards", label: tc("tabCards", lang) }, { v: "badges", label: tc("tabBadges", lang) }]} />
      </div>
      {tab === "path" ? <Journey /> : tab === "cards" ? <Cards onProgress={refresh} /> : <Achievements onProgress={refresh} />}
    </>
  );
}
