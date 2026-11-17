"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Chess } from "chess.js";
import ChessBoard from "./ChessBoard";
import { useApp } from "./app";
import { K } from "../lib/i18n";
import { tc } from "../lib/train-copy";
import { H, VOL_COLOR, VolKey, W, currentName, layout, moveLabel, prepare, resolve, search } from "../lib/openings";

type Data = ReturnType<typeof prepare>;
const short = (name: string) => (name.includes(":") ? name.split(":").slice(1).join(":").trim() : name);
const pgnOf = (path: string[]) => path.map((s, i) => (i % 2 ? s : `${i / 2 + 1}. ${s}`)).join(" ");

export default function OpeningMap() {
  const { t, call, lang } = useApp();
  const [data, setData] = useState<Data | null>(null);
  const [failed, setFailed] = useState(false);
  const [path, setPath] = useState<string[]>([]);
  const [flip, setFlip] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [q, setQ] = useState("");
  const [copied, setCopied] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);
  const [games, setGames] = useState<any[] | null>(null);
  const [mineOn, setMineOn] = useState(true);
  const [colorF, setColorF] = useState<"all" | "w" | "b">("all");

  useEffect(() => { call("/openings/mine").then(setGames).catch(() => setGames([])); }, [call]);
  useEffect(() => {
    fetch("/openings.json").then((r) => r.json()).then((j) => setData(prepare(j.t))).catch(() => setFailed(true));
  }, []);

  const L = useMemo(() => (data ? layout(data.roots, path) : null), [data, path]);
  const nodes = useMemo(() => (data ? resolve(data.roots, path) : []), [data, path]);
  const here = nodes[nodes.length - 1];
  const kids = here ? here.kids : data?.roots || [];
  const info = currentName(nodes);

  const board = useMemo(() => {
    const c = new Chess();
    let last: string | null = null;
    for (const s of path) { try { const m = c.move(s); last = m.from + m.to; } catch { break; } }
    return { fen: c.fen(), last };
  }, [path]);

  // la mappa scorre da sola verso il ramo scelto
  useEffect(() => {
    const el = scroller.current;
    if (!el || !L) return;
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollTo({ left: Math.max(0, L.width - el.clientWidth), top: Math.max(0, (L.selY ?? 0) - el.clientHeight / 2), behavior: calm ? "auto" : "smooth" });
  }, [L]);

  // riproduzione automatica della linea principale (il ramo con più varianti)
  useEffect(() => {
    if (!playing || !data) return;
    const id = setTimeout(() => {
      const cur = resolve(data.roots, path);
      const next = (cur.length ? cur[cur.length - 1].kids : data.roots)[0];
      if (!next) setPlaying(false); else setPath([...path, next.san]);
    }, 780);
    return () => clearTimeout(id);
  }, [playing, path, data]);

  // le tue partite: conteggi per ogni linea (prefisso di mosse) e partite che passano dal nodo scelto
  const mine = useMemo(() => {
    const m = new Map<string, { n: number; w: number; d: number; l: number }>();
    for (const g of games || []) {
      if (colorF !== "all" && g.c !== colorF) continue;
      let id = "";
      for (let i = 0; i < g.m.length; i++) {
        id = i ? id + " " + g.m[i] : g.m[0];
        const e = m.get(id) || { n: 0, w: 0, d: 0, l: 0 };
        e.n++; (e as any)[g.r]++; m.set(id, e);
      }
    }
    return m;
  }, [games, colorF]);
  const topMine = useMemo(() => {
    if (!data) return [];
    return data.entries.map((e) => ({ e, s: mine.get(e.path.join(" ")) })).filter((x) => x.s).sort((a, b) => b.s!.n - a.s!.n).slice(0, 6);
  }, [data, mine]);
  const here_id = path.join(" ");
  const through = useMemo(() => (games || []).filter((g) => (colorF === "all" || g.c === colorF) && g.m.length >= path.length && g.m.slice(0, path.length).join(" ") === here_id), [games, colorF, path, here_id]);
  const leaving = useMemo(() => {
    const known = new Set((here ? here.kids : data?.roots || []).map((k) => k.san));
    const c: Record<string, number> = {};
    for (const g of through) { const nx = g.m[path.length]; if (nx && !known.has(nx)) c[nx] = (c[nx] || 0) + 1; }
    return Object.entries(c).sort((a, b) => b[1] - a[1]).slice(0, 4);
  }, [through, here, data, path]);

  const results = useMemo(() => (data ? search(data.entries, q) : []), [data, q]);
  const go = (p: string[]) => { setPlaying(false); setPath(p); };
  const forward = () => { if (kids[0]) go([...path, kids[0].san]); };
  const random = () => { if (data) go(data.entries[Math.floor(Math.random() * data.entries.length)].path); };
  const copy = () => { navigator.clipboard?.writeText(pgnOf(path)).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500); }).catch(() => {}); };

  const onKey = (e: React.KeyboardEvent) => {
    if ((e.target as HTMLElement).tagName === "INPUT") return;
    const sib = nodes.length > 1 ? nodes[nodes.length - 2].kids : data?.roots || [];
    const i = here ? sib.findIndex((s) => s.san === here.san) : -1;
    if (e.key === "ArrowLeft") { go(path.slice(0, -1)); e.preventDefault(); }
    else if (e.key === "ArrowRight") { forward(); e.preventDefault(); }
    else if ((e.key === "ArrowUp" || e.key === "ArrowDown") && i >= 0) {
      const nx = sib[i + (e.key === "ArrowDown" ? 1 : -1)];
      if (nx) go([...path.slice(0, -1), nx.san]);
      e.preventDefault();
    }
  };

  if (failed) return <div className="note err">{t("omLoadErr")}</div>;
  if (!data || !L) return <p className="muted">{t("loading")}</p>;

  return (
    <div className="om" onKeyDown={onKey}>
      <div className="om-main">
        <div className="om-search">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("omSearch")} aria-label={t("omSearch")} />
          {q.trim().length >= 2 && (
            <div className="om-results" role="listbox">
              {results.length === 0 && <div className="muted small" style={{ padding: ".6rem .8rem" }}>{t("omNoResult")}</div>}
              {results.map((r) => (
                <button key={r.path.join(" ")} role="option" onClick={() => { go(r.path); setQ(""); }}>
                  <i className="dotc" style={{ background: VOL_COLOR[(r.eco[0] || "A") as VolKey] }} /><span>{r.name}</span><em>{r.eco}</em>
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="om-mine-bar">
          <button className={"chip" + (mineOn ? " on" : "")} onClick={() => setMineOn((v) => !v)} aria-pressed={mineOn}>{tc("mineToggle", lang)}</button>
          {mineOn && (["all", "w", "b"] as const).map((k) => (
            <button key={k} className={"chip" + (colorF === k ? " on" : "")} onClick={() => setColorF(k)}>{tc(k === "all" ? "mineAll" : k === "w" ? "mineWhite" : "mineBlack", lang)}</button>
          ))}
        </div>
        <div className="om-legend" aria-label="ECO">
          {(["A", "B", "C", "D", "E"] as VolKey[]).map((v) => <span key={v}><i style={{ background: VOL_COLOR[v] }} />{t(("omVol" + v) as K)}</span>)}
        </div>
        <div className="om-scroll" ref={scroller} tabIndex={0} aria-label={t("omTitle")}>
          <div className="om-canvas" style={{ width: L.width, height: L.height }}>
            <svg className="om-edges" width={L.width} height={L.height} aria-hidden="true">
              {L.edges.map((e) => <path key={e.key} d={e.d} className={e.on ? "on" : ""} />)}
            </svg>
            {L.nodes.map((n) => {
              const below = n.node.n - (n.node.name ? 1 : 0);
              const mi = mineOn ? mine.get(n.id) : undefined;
              const wr = mi ? mi.w / mi.n : 0;
              return (
                <button key={n.id} className={"om-node" + (n.sel ? " sel" : "") + (mi ? " mine" : "")}
                  style={{ left: n.x, top: n.y, width: W, height: H, ["--v" as string]: VOL_COLOR[n.node.vol], ["--m" as string]: mi ? (wr >= 0.55 ? "#4ee3b0" : wr <= 0.4 ? "#ff5d6c" : "#ffb84d") : undefined }}
                  title={n.node.name ? `${n.node.name} (${n.node.eco})` : undefined} aria-pressed={n.sel}
                  onClick={() => go(n.sel ? n.path.slice(0, -1) : n.path)}>
                  <span className="om-san">{moveLabel(n.node.ply, n.node.san)}</span>
                  {n.node.name && <span className="om-name">{short(n.node.name)}</span>}
                  {mi && <span className="om-mine" title={tc("mineWinRate", lang, { n: Math.round(wr * 100) })}>{mi.n}× · {Math.round(wr * 100)}%</span>}
                  {below > 0 && <span className="om-n" aria-label={`${below} ${t("omLines")}`}>{below}</span>}
                </button>
              );
            })}
          </div>
        </div>
        <p className="muted small" style={{ margin: ".5rem 0 0" }}>{t("omNames")}</p>
      </div>

      <aside className="om-panel">
        <div className="om-title">
          <div>
            <div className="muted small">{info ? info.eco : "ECO"}</div>
            <h2>{info ? info.name : t("omStart")}</h2>
          </div>
          {here && <span className="om-count">{here.n} {t("omLines")}</span>}
        </div>
        <ChessBoard fen={board.fen} flip={flip} last={board.last} />
        <div className="ctrls">
          <button onClick={() => go([])} aria-label={t("omReset")} title={t("omReset")}>⏮</button>
          <button onClick={() => go(path.slice(0, -1))} disabled={!path.length} aria-label={t("omBack")}>◀</button>
          <button onClick={() => setPlaying((p) => !p)} disabled={!kids.length && !playing} aria-label={playing ? t("omPause") : t("omPlay")} title={playing ? t("omPause") : t("omPlay")}>{playing ? "❚❚" : "▶"}</button>
          <button onClick={forward} disabled={!kids.length} aria-label={t("omNext")}>⏭</button>
          <button onClick={() => setFlip((f) => !f)} aria-label={t("omFlip")} title={t("omFlip")}>⇅</button>
        </div>
        {path.length > 0 && (
          <div className="om-line">
            {path.map((s, i) => (
              <button key={i} className={"chip" + (i === path.length - 1 ? " on" : "")} onClick={() => go(path.slice(0, i + 1))}>{moveLabel(i + 1, s)}</button>
            ))}
          </div>
        )}
        {kids.length > 0 ? (
          <div className="om-next">
            {kids.slice(0, 6).map((k) => (
              <button key={k.id} onClick={() => go([...path, k.san])} style={{ ["--v" as string]: VOL_COLOR[k.vol] }}>
                <b>{moveLabel(k.ply, k.san)}</b><span>{k.name ? short(k.name) : `${k.n} ${t("omLines")}`}</span>
              </button>
            ))}
          </div>
        ) : path.length > 0 ? <p className="muted small">{t("omEnd")}</p> : null}
        {mineOn && games && games.length === 0 && <p className="muted small">{tc("mineNoGames", lang)}</p>}
        {mineOn && games && games.length > 0 && !path.length && topMine.length > 0 && (
          <div>
            <div className="muted small" style={{ marginBottom: ".4rem" }}>{tc("mineTop", lang)}</div>
            <div className="om-next">
              {topMine.map(({ e, s }) => (
                <button key={e.path.join(" ")} onClick={() => go(e.path)} style={{ ["--v" as string]: VOL_COLOR[(e.eco[0] || "A") as VolKey] }}>
                  <b>{s!.n}× · {Math.round((100 * s!.w) / s!.n)}%</b><span>{e.name}</span>
                </button>
              ))}
            </div>
          </div>
        )}
        {mineOn && games && games.length > 0 && path.length > 0 && (
          <div className="om-mycard">
            <div className="muted small" style={{ marginBottom: ".4rem" }}>{tc("mineHere", lang)}</div>
            {through.length === 0 ? <span className="small muted">{tc("mineNone", lang)}</span> : (() => {
              const w = through.filter((g) => g.r === "w").length, d = through.filter((g) => g.r === "d").length, l = through.length - w - d;
              return (
                <>
                  <div className="row small"><b>{tc("mineGames", lang, { n: through.length })}</b><span className="muted">{tc("mineW", lang)} {w} · {tc("mineD", lang)} {d} · {tc("mineL", lang)} {l}</span></div>
                  <div className="wdl"><div style={{ flex: w, background: "var(--mint)" }} /><div style={{ flex: d, background: "var(--mute)" }} /><div style={{ flex: l, background: "var(--bad)" }} /></div>
                  {leaving.length > 0 && (
                    <div style={{ marginTop: ".5rem" }}>
                      <div className="muted small" title={tc("mineLeaveHint", lang)}>{tc("mineLeave", lang)}</div>
                      <div className="chips">{leaving.map(([m, n]) => <span key={m} className="chip">{moveLabel(path.length + 1, m)} ×{n}</span>)}</div>
                    </div>
                  )}
                  <div className="muted small" style={{ marginTop: ".5rem" }}>{tc("mineRecent", lang)}</div>
                  <div className="om-games">
                    {through.slice(0, 4).map((g) => (
                      <Link key={g.id} href={`/dashboard/games/${g.id}`}><i className={"res " + g.r} />{g.d} · {g.o}</Link>
                    ))}
                  </div>
                </>
              );
            })()}
          </div>
        )}
        <div className="row" style={{ justifyContent: "flex-start" }}>
          <button className="btn btn-primary btn-sm" onClick={random}>{t("omRandom")}</button>
          <button className="btn btn-ghost btn-sm" onClick={copy} disabled={!path.length}>{copied ? t("omCopied") : t("omCopy")}</button>
        </div>
      </aside>
    </div>
  );
}
