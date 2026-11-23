"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import AnalysisTabs from "../../../components/AnalysisTabs";
import GamesList from "../../../components/GamesList";

export default function GamesPage() {
  const router = useRouter();
  // vecchio collegamento ?tab=lessons: le lezioni ora hanno la loro voce
  useEffect(() => { if (new URLSearchParams(window.location.search).get("tab") === "lessons") router.replace("/dashboard/lessons"); }, [router]);
  return (
    <>
      <AnalysisTabs />
      <GamesList />
    </>
  );
}
