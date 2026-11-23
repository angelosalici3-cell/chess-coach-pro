"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { Chess } from "chess.js";
import ChessBoard from "./ChessBoard";
import { LogoMark } from "./Logo";
import { PLAY, PlayCopy } from "../lib/play-copy";
import { Lang } from "../lib/i18n";

const VAL: Record<string, number> = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 };
const pick = (a: string[]) => a[Math.floor(Math.random() * a.length)];

/** Quanto rischia il pezzo appena arrivato in `to`: 0 se sicuro, altrimenti il materiale che si perde. */
function risk(g: Chess, to: string, victim: number): number {
  const caps = g.moves({ verbose: true }).filter((m) => m.to === to && m.captured);
  if (!caps.length) return 0;
  caps.sort((a, b) => VAL[a.piece] - VAL[b.piece]);
  const low = caps[0];
  g.move(low.san);
  const defended = g.moves({ verbose: true }).some((m) => m.to === to && m.captured);
  g.undo();
  if (!defended) return victim;
  return Math.max(0, victim - VAL[low.piece]);
}

/** Risposta del Nero: golosa ma non sciocca. Cattura se conviene, evita di lasciare pezzi in presa. */
function blackReply(g: Chess) {
  let best: { san: string; s: number } | null = null;
  for (const m of g.moves({ verbose: true })) {
    g.move(m.san);
    let s = (m.captured ? VAL[m.captured] * 10 : 0) + Math.random() * 2.4;
    if (g.isCheckmate()) s += 1000;
    else if (g.isCheck()) s += 3;
    if (!g.isGameOver()) s -= risk(g, m.to, VAL[m.piece]) * 8;
    if (["n", "b"].includes(m.piece) && m.from[1] === "8") s += 1.5;
    if (["d", "e"].includes(m.to[0]) && m.piece === "p") s += 1;
    g.undo();
    if (!best || s > best.s) best = { san: m.san, s };
  }
  return best?.san || null;
}

type Say = { text: string; kind: "good" | "bad" | "info"; d: number; n: number };

export default function PlayBoard({ lang }: { lang: Lang }) {
  const T: PlayCopy = PLAY[lang];
  const game = useRef(new Chess());
  const busy = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [fen, setFen] = useState(game.current.fen());
  const [last, setLast] = useState<string | null>(null);
  const [marks, setMarks] = useState<Record<string, string>>({});
  const [shake, setShake] = useState(false);
  const [elo, setElo] = useState(1200);
  const [say, setSay] = useState<Say>({ text: "", kind: "info", d: 0, n: 0 });
  const [over, setOver] = useState(false);
  const touched = useRef(false);

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  const talk = (text: string, kind: Say["kind"], d = 0) => {
    setSay((p) => ({ text, kind, d, n: p.n + 1 }));
    if (d) setElo((e) => Math.max(0, e + d));
  };

  const finish = (g: Chess, userMoved: boolean) => {
    if (!g.isGameOver()) return false;
    setOver(true);
    if (g.isCheckmate()) talk(pick(userMoved ? T.mate : T.mated), userMoved ? "good" : "bad", userMoved ? 25 : -10);
    else talk(pick(T.draw), "info");
    return true;
  };

  const onDrop = (from: string, to: string): boolean => {
    const g = game.current;
    if (busy.current || over || g.turn() !== "w") return false;
    let m;
    try { m = g.move({ from, to, promotion: "q" }); } catch { return false; }
    if (!m) return false;
    touched.current = true;
    busy.current = true;
    setFen(g.fen()); setLast(m.from + m.to);

    // Giudizio del Coach sulla mossa appena fatta
    const got = m.captured ? VAL[m.captured] : 0;
    const lost = g.isGameOver() ? 0 : risk(g, m.to, VAL[m.piece]);
    const ply = g.history().length;
    if (g.isCheckmate()) { setMarks({}); finish(g, true); busy.current = false; return true; }
    if (lost >= 3 || (lost > 0 && lost > got)) {
      setMarks({ [m.to]: "rgba(255, 61, 90, .5)" });
      setShake(true); setTimeout(() => setShake(false), 650);
      talk(pick(m.captured ? T.bad : T.hang), "bad", -(8 + lost * 3));
    } else if (g.isCheck()) { setMarks({ [m.to]: "rgba(61, 220, 151, .45)" }); talk(pick(T.check), "good", 8); }
    else if (m.flags.includes("k") || m.flags.includes("q")) { setMarks({ [m.to]: "rgba(61, 220, 151, .4)" }); talk(pick(T.castle), "good", 9); }
    else if (m.captured && lost === 0) { setMarks({ [m.to]: "rgba(61, 220, 151, .45)" }); talk(pick(T.win), "good", 6 + got * 2); }
    else if (m.captured) { setMarks({}); talk(pick(T.cap), "info", 3); }
    else if (ply <= 3 && m.piece === "p" && ["d", "e"].includes(m.to[0])) { setMarks({ [m.to]: "rgba(61, 220, 151, .4)" }); talk(pick(T.center), "good", 7); }
    else { setMarks({}); talk(pick(T.ok), "info", 4); }

    // Risposta del Nero dopo un attimo, così sembra che pensi
    timer.current = setTimeout(() => {
      const san = blackReply(g);
      if (san) {
        const r = g.move(san);
        setFen(g.fen()); setLast(r.from + r.to);
        if (!finish(g, false) && r.captured && VAL[r.captured] >= 3) {
          setMarks({ [r.to]: "rgba(255, 61, 90, .5)" });
          talk(pick(T.bad), "bad", -(5 + VAL[r.captured] * 2));
        }
      }
      busy.current = false;
    }, 750);
    return true;
  };

  const restart = () => {
    if (timer.current) clearTimeout(timer.current);
    game.current = new Chess(); busy.current = false; touched.current = false;
    setFen(game.current.fen()); setLast(null); setMarks({}); setOver(false); setElo(1200);
    setSay({ text: "", kind: "info", d: 0, n: 0 });
  };

  const shown = useMemo(() => (say.text ? say : { text: T.start, kind: "info" as const, d: 0, n: 0 }), [say, T]);
  const sq = !touched.current && !over ? { e2: "rgba(255, 107, 61, .35)" } : marks;

  return (
    <div className="pb">
      <ChessBoard fen={fen} last={last} notation={false} onDrop={onDrop} marks={sq} shake={shake} />
      <div className="pb-elo" title={T.demo}>
        <span>{T.elo}</span><b>{elo}</b>
        {say.d !== 0 && <i key={say.n} className={say.d > 0 ? "up" : "down"}>{say.d > 0 ? "+" : ""}{say.d}</i>}
      </div>
      <div className={"pb-coach " + shown.kind} key={shown.n} aria-live="polite">
        <span className="pb-av"><LogoMark size={30} /></span>
        <div><em>{T.coach}</em><p>{shown.text}</p></div>
      </div>
      {(over || touched.current) && <button type="button" className="pb-again" onClick={restart}>{T.again}</button>}
      {!touched.current && <p className="pb-hint">{T.hint}</p>}
    </div>
  );
}
