"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Chess } from "chess.js";
import { useApp } from "../../../components/app";
import ChessBoard from "../../../components/ChessBoard";
import * as LI from "../../../lib/lichess";
import type { Lang } from "../../../lib/i18n";

const T = {
  it: {
    title: "Gioca su Lichess", intro: "Collega il tuo account Lichess e gioca da qui, con la tua interfaccia. Le partite sono vere: contano per il tuo rating e dopo la fine EloRise le analizza.",
    connect: "Collega Lichess", why: "Si apre Lichess per darmi il permesso di giocare per te. Non vedo la tua password.", as: "Collegato come", off: "Scollega",
    rules: "Qui si gioca senza aiuti: niente motore e nessun suggerimento durante la partita (regola di Lichess).",
    time: "Ritmo", rated: "Valida per il rating", casual: "Amichevole", search: "Cerca avversario", searching: "Cerco un avversario…", cancel: "Annulla",
    you: "Tu", resign: "Abbandona", draw: "Proponi patta", accept: "Accetta patta", abort: "Annulla partita", yourTurn: "Tocca a te", theirTurn: "Tocca all'avversario…",
    won: "Hai vinto!", lost: "Hai perso", drawn: "Patta", aborted: "Partita annullata",
    why_: { mate: "scacco matto", resign: "abbandono", outoftime: "tempo scaduto", timeout: "avversario assente", stalemate: "stallo", draw: "accordo o regola", cheat: "violazione", noStart: "non iniziata", aborted: "annullata" } as Record<string, string>,
    analyze: "Analizza con EloRise", analyzing: "Preparo l'analisi…", again: "Nuova partita", notLinked: "Questo account Lichess non è ancora tra i tuoi account in EloRise: aggiungilo per far analizzare le partite.", link: "Aggiungi account", err: "Qualcosa non ha funzionato",
  },
  en: {
    title: "Play on Lichess", intro: "Connect your Lichess account and play from here, with your own interface. Games are real: they count for your rating, and EloRise analyzes them when they end.",
    connect: "Connect Lichess", why: "Lichess opens to give me permission to play for you. I never see your password.", as: "Connected as", off: "Disconnect",
    rules: "No help while playing: no engine and no hints during the game (Lichess rule).",
    time: "Time control", rated: "Rated", casual: "Casual", search: "Find an opponent", searching: "Looking for an opponent…", cancel: "Cancel",
    you: "You", resign: "Resign", draw: "Offer draw", accept: "Accept draw", abort: "Abort game", yourTurn: "Your turn", theirTurn: "Opponent's turn…",
    won: "You won!", lost: "You lost", drawn: "Draw", aborted: "Game aborted",
    why_: { mate: "checkmate", resign: "resignation", outoftime: "out of time", timeout: "opponent left", stalemate: "stalemate", draw: "agreement or rule", cheat: "violation", noStart: "not started", aborted: "aborted" } as Record<string, string>,
    analyze: "Analyze with EloRise", analyzing: "Preparing the analysis…", again: "New game", notLinked: "This Lichess account isn't among your EloRise accounts yet: add it so your games get analyzed.", link: "Add account", err: "Something went wrong",
  },
  es: {
    title: "Juega en Lichess", intro: "Conecta tu cuenta de Lichess y juega desde aquí, con tu propia interfaz. Las partidas son reales: cuentan para tu rating y EloRise las analiza al terminar.",
    connect: "Conectar Lichess", why: "Se abre Lichess para darme permiso de jugar por ti. Nunca veo tu contraseña.", as: "Conectado como", off: "Desconectar",
    rules: "Aquí se juega sin ayudas: sin motor ni pistas durante la partida (regla de Lichess).",
    time: "Ritmo", rated: "Con rating", casual: "Amistosa", search: "Buscar rival", searching: "Buscando rival…", cancel: "Cancelar",
    you: "Tú", resign: "Rendirse", draw: "Ofrecer tablas", accept: "Aceptar tablas", abort: "Anular partida", yourTurn: "Te toca", theirTurn: "Turno del rival…",
    won: "¡Ganaste!", lost: "Perdiste", drawn: "Tablas", aborted: "Partida anulada",
    why_: { mate: "jaque mate", resign: "abandono", outoftime: "tiempo agotado", timeout: "rival ausente", stalemate: "ahogado", draw: "acuerdo o regla", cheat: "infracción", noStart: "no iniciada", aborted: "anulada" } as Record<string, string>,
    analyze: "Analizar con EloRise", analyzing: "Preparando el análisis…", again: "Nueva partida", notLinked: "Esta cuenta de Lichess aún no está entre tus cuentas de EloRise: añádela para que se analicen las partidas.", link: "Añadir cuenta", err: "Algo salió mal",
  },
} as const;

// Solo ritmi rapid e classical: sono quelli che Lichess consente alle app esterne per cercare un avversario.
const MODES = [{ time: 10, inc: 0, label: "10+0" }, { time: 15, inc: 10, label: "15+10" }, { time: 30, inc: 0, label: "30+0" }];

type GameState = { moves: string[]; wtime: number; btime: number; at: number; status: string; winner?: string; wdraw?: boolean; bdraw?: boolean };
type Meta = { id: string; color: "white" | "black"; white: any; black: any; clock: boolean };

const fmt = (ms: number) => {
  const s = Math.max(0, Math.ceil(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};
const nm = (p: any) => (p?.aiLevel ? `Stockfish ${p.aiLevel}` : p?.name || p?.id || "?");

export default function PlayPage() {
  const { call, lang } = useApp();
  const L = T[lang as Lang] || T.it;
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [acct, setAcct] = useState<any>(null);
  const [linked, setLinked] = useState(true);
  const [mode, setMode] = useState(0);
  const [rated, setRated] = useState(false);
  const [phase, setPhase] = useState<"lobby" | "seeking" | "game">("lobby");
  const [gameId, setGameId] = useState<string | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [st, setSt] = useState<GameState | null>(null);
  const [moves, setMoves] = useState<string[]>([]);
  const [now, setNow] = useState(Date.now());
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const seekAbort = useRef<AbortController | null>(null);
  const serverMoves = useRef<string[]>([]);

  // Ritorno da Lichess (?code=...) oppure token già salvato
  useEffect(() => {
    (async () => {
      const q = new URLSearchParams(location.search);
      const code = q.get("code"), state = q.get("state");
      if (code && state) {
        const ok = await LI.finishAuth(code, state);
        history.replaceState(null, "", location.pathname);
        if (!ok) setErr(L.err);
      }
      setToken(LI.getToken());
    })();
  }, []); // eslint-disable-line

  useEffect(() => {
    if (!token) { setAcct(null); return; }
    LI.account(token).then(setAcct).catch(() => { LI.clearToken(); setToken(null); });
  }, [token]);

  useEffect(() => {
    if (!acct) return;
    call("/profiles").then((l: any[]) => setLinked(l.some((p) => p.piattaforma === "lichess" && String(p.username).toLowerCase() === String(acct.username).toLowerCase()))).catch(() => {});
  }, [acct, call]);

  // Flusso eventi: avvisa quando comincia una partita (anche una già in corso se si ricarica la pagina)
  useEffect(() => {
    if (!token) return;
    let stop = false;
    const ac = new AbortController();
    (async () => {
      while (!stop) {
        try {
          const r = await LI.openEvents(token, ac.signal);
          for await (const ev of LI.ndjson(r)) {
            if (ev.type === "gameStart" && ev.game && (!ev.game.variant || ev.game.variant.key === "standard")) { setGameId(ev.game.gameId || ev.game.id); setPhase("game"); }
          }
        } catch { if (stop) return; }
        if (!stop) await new Promise((res) => setTimeout(res, 3000));
      }
    })();
    return () => { stop = true; ac.abort(); };
  }, [token]);

  // Flusso della partita: mosse e orologi arrivano da Lichess
  useEffect(() => {
    if (!token || !gameId) return;
    const ac = new AbortController();
    const apply = (s: any) => {
      const mv: string[] = s.moves ? String(s.moves).split(" ").filter(Boolean) : [];
      serverMoves.current = mv;
      setMoves(mv);
      setSt({ moves: mv, wtime: s.wtime, btime: s.btime, at: Date.now(), status: s.status, winner: s.winner, wdraw: s.wdraw, bdraw: s.bdraw });
    };
    (async () => {
      try {
        const r = await LI.openGame(token, gameId, ac.signal);
        for await (const ev of LI.ndjson(r)) {
          if (ev.type === "gameFull") {
            const mine = String(ev.white?.id || "").toLowerCase() === String(acct?.id || "").toLowerCase() ? "white" : "black";
            setMeta({ id: gameId, color: mine, white: ev.white, black: ev.black, clock: !!ev.clock });
            apply(ev.state);
          } else if (ev.type === "gameState") apply(ev);
        }
      } catch {}
    })();
    return () => ac.abort();
  }, [token, gameId, acct?.id]);

  const over = !!st && !["created", "started"].includes(st.status);
  useEffect(() => {
    if (phase !== "game" || over) return;
    const t = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(t);
  }, [phase, over]);

  const board = useMemo(() => {
    const c = new Chess();
    for (const u of moves) { try { c.move({ from: u.slice(0, 2), to: u.slice(2, 4), promotion: u[4] }); } catch { break; } }
    return c;
  }, [moves]);
  const mine = meta?.color === "white" ? "w" : "b";
  const myTurn = !!st && !over && board.turn() === mine;
  const last = moves.length ? moves[moves.length - 1].slice(0, 4) : null;

  const onDrop = (from: string, to: string): boolean => {
    if (!token || !meta || !myTurn) return false;
    const p = board.get(from as any);
    if (!p || p.color !== mine) return false;
    const trial = new Chess(board.fen());
    let uci = from + to;
    try {
      const promo = p.type === "p" && (to[1] === "8" || to[1] === "1");
      trial.move({ from, to, promotion: promo ? "q" : undefined });
      if (promo) uci += "q";
    } catch { return false; }
    setMoves([...serverMoves.current, uci]);       // la mossa compare subito; Lichess poi conferma
    LI.sendMove(token, meta.id, uci).then((r) => { if (!r.ok) { setMoves(serverMoves.current); setErr(L.err); } }).catch(() => setMoves(serverMoves.current));
    return true;
  };

  const search = async () => {
    if (!token) return;
    setErr(""); setPhase("seeking");
    const ac = new AbortController(); seekAbort.current = ac;
    try {
      const m = MODES[mode];
      const r = await LI.seek(token, { time: m.time, inc: m.inc, rated }, ac.signal);
      if (!r.ok) { setErr(`${L.err} (${r.status})`); setPhase("lobby"); return; }
      for await (const _ of LI.ndjson(r)) { /* resta aperta finché Lichess trova un avversario */ }
    } catch { /* annullata dall'utente */ }
  };
  const cancel = () => { seekAbort.current?.abort(); setPhase("lobby"); };

  const reset = () => { setGameId(null); setMeta(null); setSt(null); setMoves([]); serverMoves.current = []; setPhase("lobby"); setBusy(false); };
  const analyze = async () => {
    setBusy(true);
    await new Promise((r) => setTimeout(r, 3000));       // Lichess ha bisogno di qualche secondo per pubblicare la partita
    try { await call("/sync", { method: "POST" }); router.push("/dashboard"); } catch (e: any) { setErr(e.message); setBusy(false); }
  };

  const disconnect = async () => { await LI.revoke(); setToken(null); setAcct(null); reset(); };

  // ---- Orologi
  const mt = (side: "white" | "black") => {
    if (!st) return "";
    const base = side === "white" ? st.wtime : st.btime;
    if (base == null) return "";
    const running = !over && st.moves.length >= 2 && ((board.turn() === "w") === (side === "white"));
    return fmt(base - (running ? now - st.at : 0));
  };
  const resultText = () => {
    if (!st || !meta) return "";
    const why = L.why_[st.status] || st.status;
    if (st.status === "aborted" || st.status === "noStart") return `${L.aborted}`;
    if (!st.winner) return `${L.drawn} · ${why}`;
    return `${st.winner === meta.color ? L.won : L.lost} · ${why}`;
  };

  // ---- Interfaccia
  if (!token) {
    return (
      <>
        <div className="pagehead"><h1>{L.title}</h1></div>
        <div className="card">
          <p style={{ marginTop: 0 }}>{L.intro}</p>
          <button className="btn btn-primary" onClick={() => LI.startAuth()}>{L.connect}</button>
          <p className="muted small" style={{ marginBottom: 0 }}>{L.why}</p>
          <p className="muted small" style={{ marginBottom: 0 }}>{L.rules}</p>
        </div>
        {err && <div className="note err">{err}</div>}
      </>
    );
  }

  if (phase === "game" && meta && st) {
    const opp = meta.color === "white" ? meta.black : meta.white;
    const oppSide = meta.color === "white" ? "black" : "white";
    const iOffered = meta.color === "white" ? st.wdraw : st.bdraw;
    const theyOffered = meta.color === "white" ? st.bdraw : st.wdraw;
    return (
      <>
        <div className="pagehead"><h1>{L.title}</h1></div>
        <div className="play-wrap">
          <div className="play-side">
            <div className={"play-player" + (!over && !myTurn ? " on" : "")}><b>{nm(opp)}</b>{opp?.rating ? <span className="muted"> {opp.rating}</span> : null}<span className="play-clock">{meta.clock ? mt(oppSide) : ""}</span></div>
            <ChessBoard fen={board.fen()} flip={meta.color === "black"} last={last} onDrop={onDrop} />
            <div className={"play-player" + (!over && myTurn ? " on" : "")}><b>{L.you}</b>{acct ? <span className="muted"> {acct.username}</span> : null}<span className="play-clock">{meta.clock ? mt(meta.color) : ""}</span></div>
          </div>
          <div className="play-panel card">
            {!over ? <p className="play-turn">{myTurn ? L.yourTurn : L.theirTurn}</p> : <p className="play-turn res">{resultText()}</p>}
            {!over && (
              <div className="play-btns">
                {st.moves.length < 2 ? <button className="btn btn-sm" onClick={() => LI.abort(token, meta.id)}>{L.abort}</button>
                  : <>
                    <button className="btn btn-sm" disabled={!!iOffered} onClick={() => LI.draw(token, meta.id, true)}>{theyOffered ? L.accept : L.draw}</button>
                    <button className="btn btn-sm" onClick={() => LI.resign(token, meta.id)}>{L.resign}</button>
                  </>}
              </div>
            )}
            {over && (
              <div className="play-btns">
                <button className="btn btn-primary" onClick={analyze} disabled={busy}>{busy ? L.analyzing : L.analyze}</button>
                <button className="btn btn-sm" onClick={reset}>{L.again}</button>
              </div>
            )}
            <p className="muted small" style={{ marginBottom: 0 }}>{L.rules}</p>
          </div>
        </div>
        {err && <div className="note err">{err}</div>}
      </>
    );
  }

  return (
    <>
      <div className="pagehead"><h1>{L.title}</h1></div>
      <div className="card">
        <p className="muted small" style={{ marginTop: 0 }}>{L.as} <b>{acct?.username || "…"}</b> · <button className="linklike" onClick={disconnect}>{L.off}</button></p>
        {!linked && <div className="note">{L.notLinked} <Link href="/dashboard/accounts" className="accent">{L.link}</Link></div>}
        <b>{L.time}</b>
        <div className="play-modes">
          {MODES.map((m, i) => <button key={m.label} className={"chip" + (mode === i ? " on" : "")} onClick={() => setMode(i)} disabled={phase === "seeking"}>{m.label}</button>)}
        </div>
        <div className="play-modes">
          <button className={"chip" + (!rated ? " on" : "")} onClick={() => setRated(false)} disabled={phase === "seeking"}>{L.casual}</button>
          <button className={"chip" + (rated ? " on" : "")} onClick={() => setRated(true)} disabled={phase === "seeking"}>{L.rated}</button>
        </div>
        {phase === "seeking"
          ? <div className="play-seek"><span className="spinner" aria-hidden="true" /> {L.searching} <button className="btn btn-sm" onClick={cancel}>{L.cancel}</button></div>
          : <button className="btn btn-primary" onClick={search}>{L.search}</button>}
        <p className="muted small" style={{ marginBottom: 0 }}>{L.rules}</p>
      </div>
      {err && <div className="note err">{err}</div>}
    </>
  );
}
