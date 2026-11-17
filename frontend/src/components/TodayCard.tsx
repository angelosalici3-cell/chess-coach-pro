"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "./app";
import { tc } from "../lib/train-copy";

export default function TodayCard() {
  const { call, lang } = useApp();
  const [o, setO] = useState<any>(null);
  useEffect(() => { call("/train/overview").then(setO).catch(() => {}); }, [call]);
  if (!o) return null;
  const st = o.stats;
  return (
    <div className="card today">
      <div style={{ display: "flex", alignItems: "center", gap: ".9rem" }}>
        <span className="flame" aria-hidden="true">●</span>
        <div>
          <b>{tc("todayTitle", lang)}</b>
          <div className="muted small">
            {st.current_streak > 0 ? tc("streak", lang, { n: st.current_streak }) + " · " : ""}
            {o.done_today ? tc("todayDone", lang) : o.mistakes_due + o.mistakes_new > 0 ? tc("todayDue", lang, { n: o.mistakes_due + o.mistakes_new }) : tc("todayNone", lang)}
          </div>
        </div>
      </div>
      <Link href="/dashboard/train" className="btn btn-primary btn-sm">{tc("todayCta", lang)}</Link>
    </div>
  );
}
