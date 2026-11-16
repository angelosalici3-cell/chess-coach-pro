"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { Chess } from "chess.js";
import ChessBoard from "./ChessBoard";
import { useApp } from "./app";
import { K } from "../lib/i18n";
import { H, VOL_COLOR, VolKey, W, currentName, layout, moveLabel, prepare, resolve, search } from "../lib/openings";

type Data = ReturnType<typeof prepare>;
const short = (name: string) => (name.includes(":") ? name.split(":").slice(1).join(":").trim() : name);
const pgnOf = (path: string[]) => path.map((s, i) => (i % 2 ? s : `${i / 2 + 1}. ${s}`)).join(" ");

export default function OpeningMap() {
  const { t } = useApp();
  const [data, setData] = useState<Data | null>(null);
  const [failed, setFailed] = useState(false);
  const [path, setPath] = useState<string[]>([]);
  const [flip, setFlip] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [q, setQ] = useState("");
  const [copied, setCopied] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);

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
              return (
                <button key={n.id} className={"om-node" + (n.sel ? " sel" : "")} style={{ left: n.x, top: n.y, width: W, height: H, ["--v" as string]: VOL_COLOR[n.node.vol] }}
                  title={n.node.name ? `${n.node.name} (${n.node.eco})` : undefined} aria-pressed={n.sel}
                  onClick={() => go(n.sel ? n.path.slice(0, -1) : n.path)}>
                  <span className="om-san">{moveLabel(n.node.ply, n.node.san)}</span>
                  {n.node.name && <span className="om-name">{short(n.node.name)}</span>}
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
        <div className="row" style={{ justifyContent: "flex-start" }}>
          <button className="btn btn-primary btn-sm" onClick={random}>{t("omRandom")}</button>
          <button className="btn btn-ghost btn-sm" onClick={copy} disabled={!path.length}>{copied ? t("omCopied") : t("omCopy")}</button>
        </div>
      </aside>
    </div>
  );
}
