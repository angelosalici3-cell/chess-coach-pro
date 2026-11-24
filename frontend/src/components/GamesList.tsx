"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useApp } from "./app";
import { Seg } from "./ui/Seg";
import { K, tr } from "../lib/i18n";
import { u } from "../lib/ui-copy";

type G = any;
const SPEEDS = ["bullet", "blitz", "rapid", "classical", "daily"];

export default function GamesList() {
  const { call, t, lang } = useApp();
  const [games, setGames] = useState<G[] | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [err, setErr] = useState("");
  const [res, setRes] = useState<"all" | "w" | "d" | "l">("all");
  const [col, setCol] = useState<"all" | "white" | "black">("all");
  const [speed, setSpeed] = useState("all");
  const [q, setQ] = useState("");
  const [shown, setShown] = useState(30);
  const [more, setMore] = useState(false);   // filtri secondari (colore, ritmo)
  useEffect(() => { call("/games").then(setGames).catch((e) => setErr(e.message)); call("/stats").then(setStats).catch(() => {}); }, [call]);

  const list = useMemo(() => (games || []).filter((g) =>
    (res === "all" || g.outcome === res) && (col === "all" || g.user_color === col) && (speed === "all" || g.speed === speed) &&
    (!q.trim() || `${g.opp} ${g.opening_name || ""}`.toLowerCase().includes(q.trim().toLowerCase()))), [games, res, col, speed, q]);
  useEffect(() => { setShown(30); }, [res, col, speed, q]);

  const sum = useMemo(() => {
    const a = games || [], dec = a.filter((g) => g.outcome), w = dec.filter((g) => g.outcome === "w").length;
    const acc = a.filter((g) => g.accuracy_user != null);
    return { n: a.length, win: dec.length ? Math.round((100 * w) / dec.length) : null, acc: acc.length ? Math.round(acc.reduce((s, g) => s + Number(g.accuracy_user), 0) / acc.length) : null, done: a.filter((g) => g.analyzed_at).length };
  }, [games]);
  const speeds = useMemo(() => SPEEDS.filter((s) => (games || []).some((g) => g.speed === s)), [games]);
  const cnt = (o: string) => (games || []).filter((g) => g.outcome === o).length;

  const day = (iso: string) => {
    const d = new Date(iso), t0 = new Date(); t0.setHours(0, 0, 0, 0);
    const diff = Math.round((t0.getTime() - new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()) / 86400000);
    return diff === 0 ? u("gToday", lang) : diff === 1 ? u("gYesterday", lang) : d.toLocaleDateString(lang, { weekday: "short", day: "numeric", month: "short", year: d.getFullYear() === t0.getFullYear() ? undefined : "numeric" });
  };
  const groups: { label: string; rows: G[] }[] = [];
  list.slice(0, shown).forEach((g) => {
    const l = g.played_at ? day(g.played_at) : "—";
    const last = groups[groups.length - 1];
    if (last && last.label === l) last.rows.push(g); else groups.push({ label: l, rows: [g] });
  });

  return (
    <>
      {err && <div className="note err">{err}</div>}
      {games && games.length > 0 && (
        <>
          <div className="gsum">
            <span><b>{sum.n}</b> {u("gGames", lang).toLowerCase()}</span>
            <span><b>{sum.win ?? "—"}{sum.win != null && "%"}</b> {u("gWin", lang).toLowerCase()}</span>
            <span><b>{sum.acc ?? "—"}{sum.acc != null && "%"}</b> {u("gAcc", lang).toLowerCase()}</span>
            <span className={sum.done < sum.n ? "warn" : ""}><b>{sum.done}/{sum.n}</b> {u("gAnalyzed", lang).toLowerCase()}</span>
          </div>
          <div className="gfilters">
            <input className="search" placeholder={u("fSearch", lang)} value={q} onChange={(e) => setQ(e.target.value)} aria-label={u("fSearch", lang)} />
            <Seg<"all" | "w" | "d" | "l"> value={res} onChange={setRes} label={u("fResult", lang)} items={[{ v: "all", label: u("fAll", lang) }, { v: "w", label: u("fWin", lang), n: cnt("w") }, { v: "d", label: u("fDraw", lang), n: cnt("d") }, { v: "l", label: u("fLoss", lang), n: cnt("l") }]} />
            <button className={"chip fmore" + (more || col !== "all" || speed !== "all" ? " on" : "")} onClick={() => setMore((m) => !m)} aria-expanded={more}>{lang === "it" ? "Filtri" : lang === "es" ? "Filtros" : "Filters"}{col !== "all" || speed !== "all" ? " •" : ""}</button>
            {(more || col !== "all" || speed !== "all") && <div className="fscroll">
              <Seg<"all" | "white" | "black"> value={col} onChange={setCol} label={u("fColor", lang)} items={[{ v: "all", label: u("fAll", lang) }, { v: "white", label: u("fWhite", lang) }, { v: "black", label: u("fBlack", lang) }]} />
              {speeds.length > 1 && <Seg<string> value={speed} onChange={setSpeed} label={u("fSpeed", lang)} items={[{ v: "all", label: u("fAll", lang) }, ...speeds.map((s) => ({ v: s, label: tr(("speed" + s[0].toUpperCase() + s.slice(1)) as K, lang) }))]} />}
            </div>}
          </div>
        </>
      )}
      {games?.length === 0 && <div className="card muted">{t("empty")}</div>}
      {games && games.length > 0 && list.length === 0 && <div className="card muted">{u("gNoMatch", lang)}</div>}
      {groups.map((gr) => (
        <section key={gr.label} className="dgroup">
          <h3 className="dhead">{gr.label}<span>{gr.rows.length}</span></h3>
          {gr.rows.map((g) => (
            <Link key={g.id} href={`/dashboard/games/${g.id}`} className={"grow " + (g.outcome || "x")}>
              <span className="gres" aria-label={g.outcome === "w" ? u("fWin", lang) : g.outcome === "l" ? u("fLoss", lang) : g.outcome === "d" ? u("fDraw", lang) : ""}>{g.outcome === "w" ? "W" : g.outcome === "l" ? "L" : g.outcome === "d" ? "D" : "·"}</span>
              <span className="gmain">
                <b className="ellip"><i className={"pc " + g.user_color} aria-hidden="true" />{g.opp || `${g.white} - ${g.black}`}</b>
                <span className="muted small ellip">{g.opening_name || "—"}{g.speed && g.speed !== "other" ? ` · ${tr(("speed" + g.speed[0].toUpperCase() + g.speed.slice(1)) as K, lang)}` : ""}</span>
              </span>
              <span className="gside">
                {g.analyzed_at ? (
                  <>
                    <b>{g.accuracy_user != null ? Math.round(g.accuracy_user) : "—"}{g.accuracy_user != null && <small>%</small>}</b>
                    <span className="small">{(() => {
                      const parts: [number, string, string, string, string][] = [[g.blunders, "bad", "gSevere1", "gSevere", ""], [g.mistakes, "warn", "gErr1", "gMistakes", ""], [g.inaccuracies || 0, "muted", "gInacc1", "gInacc", ""]];
                      const shown = parts.filter((p) => p[0] > 0);
                      if (!shown.length) return <span className="ok">{u("gClean", lang)}</span>;
                      return shown.map((p, k) => <span key={p[2]} className={p[1]}>{k ? " · " : ""}{p[0] === 1 ? u(p[2] as any, lang) : u(p[3] as any, lang, { n: p[0] })}</span>);
                    })()}</span>
                  </>
                ) : <span className="tag muted">{t("notAnalyzed")}</span>}
              </span>
            </Link>
          ))}
        </section>
      ))}
      {list.length > shown && <button className="btn btn-ghost" style={{ width: "100%" }} onClick={() => setShown((n) => n + 30)}>{u("gMore", lang)} ({list.length - shown})</button>}
    </>
  );
}
