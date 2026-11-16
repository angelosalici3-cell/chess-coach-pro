"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "../../../components/app";

export default function GamesPage() {
  const { call, t } = useApp();
  const [games, setGames] = useState<any[] | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { call("/games").then(setGames).catch((e) => setErr(e.message)); }, [call]);
  return (
    <>
      <div className="pagehead"><h1>{t("games")}</h1></div>
      {err && <div className="note err">{err}</div>}
      {games?.length === 0 && <p className="muted">{t("empty")}</p>}
      {games?.map((g) => (
        <Link key={g.id} href={`/dashboard/games/${g.id}`} className="card row link">
          <span><b>{g.white}</b> vs <b>{g.black}</b> <span className="muted small">{g.opening_name || ""}</span></span>
          <span className="muted small">{g.result}{g.analyzed_at ? (g.accuracy_user ? `  ${Math.round(g.accuracy_user)}%` : "") : `  ${t("notAnalyzed")}`}</span>
        </Link>
      ))}
    </>
  );
}
