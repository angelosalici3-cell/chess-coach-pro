"use client";
import { useEffect, useState } from "react";
import { useApp } from "../../../components/app";
import GamesList from "../../../components/GamesList";
import Lessons from "../../../components/Lessons";
import { Seg } from "../../../components/ui/Seg";
import { u } from "../../../lib/ui-copy";

export default function GamesPage() {
  const { lang } = useApp();
  const [tab, setTab] = useState<"games" | "lessons">("games");
  useEffect(() => { if (new URLSearchParams(window.location.search).get("tab") === "lessons") setTab("lessons"); }, []);
  const pick = (v: "games" | "lessons") => { setTab(v); window.history.replaceState(null, "", v === "games" ? "?" : `?tab=${v}`); };
  return (
    <>
      <div className="pagehead">
        <h1>{tab === "games" ? u("gTitle", lang) : u("tabLessons", lang)}</h1>
        <Seg<"games" | "lessons"> value={tab} onChange={pick} items={[{ v: "games", label: u("tabGames", lang) }, { v: "lessons", label: u("tabLessons", lang) }]} />
      </div>
      {tab === "games" ? <GamesList /> : <Lessons />}
    </>
  );
}
