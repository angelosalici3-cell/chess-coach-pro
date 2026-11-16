"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "../../components/app";

export default function GamesPage() {
  const { call, t } = useApp();
  const [games, setGames] = useState<any[] | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { call("/games").then(setGames).catch((e) => setErr(e.message)); }, [call]);
  return (
    <>
      <h2>{t("games")}</h2>
      {err && <div className="card err">⚠️ {err}</div>}
      {games?.length === 0 && <p className="muted">{t("empty")}</p>}
      {games?.map((g) => (
        <Link key={g.id} href={`/games/${g.id}`} className="card row link">
          <span>{g.white} vs {g.black} <span className="muted">· {g.opening_name || ""}</span></span>
          <span className="muted small">{g.result}{g.analyzed_at ? (g.accuracy_user ? ` · ${Math.round(g.accuracy_user)}%` : "") : ` · ${t("notAnalyzed")}`}</span>
        </Link>
      ))}
    </>
  );
}
