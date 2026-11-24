"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "../../../components/app";

const eur = (n: number) => n.toLocaleString("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: n % 1 ? 2 : 0 });
const pct = (a: number, b: number) => (b ? Math.round((100 * a) / b) : 0);

function Bars({ s }: { s: { w: string; clicks: number; signups: number }[] }) {
  const max = Math.max(1, ...s.map((x) => x.signups));
  return (
    <div className="st-bars" role="img" aria-label="Iscritti per settimana">
      {s.map((x) => (
        <div key={x.w} className="st-bar" title={`${new Date(x.w).toLocaleDateString("it-IT", { day: "numeric", month: "short" })}: ${x.signups} iscritti, ${x.clicks} visite`}>
          <i style={{ height: `${Math.max(x.signups ? 8 : 3, (100 * x.signups) / max)}%` }} />
          <span>{new Date(x.w).getDate()}</span>
        </div>
      ))}
    </div>
  );
}

function CreatorView({ code, who }: { code?: string; who?: string }) {
  const { call } = useApp();
  const [d, setD] = useState<any>(null), [err, setErr] = useState(""), [msg, setMsg] = useState("");
  useEffect(() => { call(`/studio/creator${code ? `?code=${code}` : ""}`).then(setD).catch((e) => setErr(e.message)); }, [call, code]);
  if (err) return <div className="note err">{err}</div>;
  if (!d) return <p className="muted">…</p>;
  const link = `${typeof window !== "undefined" ? window.location.origin : ""}/?ref=${d.code}`;
  const copy = async (t: string, m: string) => { try { await navigator.clipboard.writeText(t); setMsg(m); } catch { setMsg(t); } setTimeout(() => setMsg(""), 2500); };
  const caps = [
    `Sto usando EloRise: un coach di scacchi che analizza le tue partite di Chess.com e Lichess e ti spiega gli errori che ripeti. Con il mio link hai ${d.discount_pct}% di sconto: ${link}`,
    `Se vuoi migliorare a scacchi senza perdere ore a rivedere le partite, prova EloRise. Codice ${d.code}, link: ${link}`,
    `Il mio consiglio per salire di Elo: capire perché perdi. EloRise lo fa per te. Sconto per voi con ${d.code}: ${link}`,
  ];
  const nx = d.next, left = nx ? nx.n - d.confirmed : 0;
  return (
    <div className="st">
      <section className="card st-hero">
        <div className="muted small">{who || "Il tuo impatto"}</div>
        <h2>{d.signups > 0 ? <>Grazie a te <b>{d.signups}</b> {d.signups === 1 ? "persona ha iniziato" : "persone hanno iniziato"} a migliorare a scacchi con EloRise.</> : "Il tuo link è pronto: la prima persona che si iscrive apparirà qui."}</h2>
        <p className="muted" style={{ margin: 0 }}>{d.payers > 0 ? `${d.payers} di loro ${d.payers === 1 ? "ha scelto" : "hanno scelto"} un piano a pagamento.` : "Ogni iscritto che passa a un piano a pagamento ti fa guadagnare."}</p>
      </section>

      <section className="st-kpis">
        {[["Visite al link", d.clicks, ""], ["Iscritti", d.signups, `${pct(d.signups, d.clicks)}% delle visite`], ["Abbonati", d.payers, `${pct(d.payers, d.signups)}% degli iscritti`], ["Guadagno maturato", eur(d.earned), `${eur(d.due)} da ricevere`]].map(([l, v, s]: any) => (
          <div key={l} className="card st-kpi"><div className="muted small">{l}</div><b className="jy-big">{v}</b><div className="muted small">{s}</div></div>
        ))}
      </section>

      <section className="card">
        <div className="st-row"><b>Iscritti per settimana</b><span className="muted small">ultime 12 settimane</span></div>
        <Bars s={d.series} />
      </section>

      <section className="card">
        <div className="st-row"><b>I tuoi traguardi</b><span className="muted small">abbonati confermati: {d.confirmed}</span></div>
        <p className="muted small" style={{ margin: ".2rem 0 .8rem" }}>
          {nx ? `Ti ${left === 1 ? "manca 1 abbonato" : `mancano ${left} abbonati`} per sbloccare ${eur(nx.bonus)}.` : "Hai sbloccato tutti i traguardi. Grazie: parliamo di come lavorare insieme più a lungo."}
        </p>
        <div className="st-lad">
          {d.milestones.map((m: any) => (
            <div key={m.n} className={"st-step" + (m.reached ? " on" : "")}>
              <b>{eur(m.bonus)}</b><span className="muted small">{m.n} abbonati</span>
              <div className="bar"><div style={{ width: `${Math.min(100, (100 * d.confirmed) / m.n)}%`, background: "var(--ember)" }} /></div>
            </div>
          ))}
        </div>
        <p className="muted small" style={{ margin: ".8rem 0 0" }}>Un abbonato è confermato dopo {d.confirm_days} giorni dal primo pagamento. Il bonus si sblocca una volta sola per traguardo.</p>
      </section>

      <section className="card">
        <div className="st-row"><b>I tuoi guadagni</b></div>
        <div className="st-split">
          <div><span className="muted small">Commissione {d.commission_pct}% su {eur(d.revenue)} incassati</span><b className="jy-big">{eur(d.commission)}</b></div>
          <div><span className="muted small">Bonus traguardi</span><b className="jy-big">{eur(d.bonus)}</b></div>
          <div><span className="muted small">Già pagato</span><b className="jy-big">{eur(d.paid)}</b></div>
        </div>
        {d.payouts.length > 0 && <div className="st-pay">{d.payouts.map((p: any, i: number) => <div key={i} className="muted small">{new Date(p.paid_at).toLocaleDateString("it-IT")} · {eur(Number(p.amount))}{p.note ? ` · ${p.note}` : ""}</div>)}</div>}
      </section>

      <section className="card">
        <div className="st-row"><b>Il tuo kit</b><span className="muted small">sconto {d.discount_pct}%{d.months > 1 ? ` per ${d.months} mesi` : " sul primo pagamento"}</span></div>
        <div className="st-link"><code>{link}</code><button className="btn btn-sm" onClick={() => copy(link, "Link copiato")}>Copia link</button></div>
        <div className="st-caps">
          {caps.map((c, i) => <div key={i} className="st-cap"><p>{c}</p><button className="btn btn-sm" onClick={() => copy(c, "Testo copiato")}>Copia testo</button></div>)}
        </div>
        {msg && <div className="note ok">{msg}</div>}
      </section>
    </div>
  );
}

function AdminView() {
  const { call } = useApp();
  const [d, setD] = useState<any>(null), [err, setErr] = useState(""), [msg, setMsg] = useState(""), [see, setSee] = useState<any>(null);
  const [f, setF] = useState({ email: "", name: "", code: "", discount_pct: 20, months: 1, commission_pct: 20 });
  const [pay, setPay] = useState({ code: "", amount: "", note: "" });
  const load = useCallback(() => { call("/studio/admin").then(setD).catch((e) => setErr(e.message)); }, [call]);
  useEffect(() => { load(); }, [load]);
  const add = async (e: React.FormEvent) => { e.preventDefault(); setErr(""); try { await call("/studio/admin/creators", { method: "POST", body: JSON.stringify({ ...f, code: f.code.toUpperCase() }) }); setMsg("Creator abilitato."); setF({ ...f, email: "", name: "", code: "" }); load(); } catch (x: any) { setErr(x.message); } };
  const payout = async (e: React.FormEvent) => { e.preventDefault(); setErr(""); try { await call("/studio/admin/payouts", { method: "POST", body: JSON.stringify({ code: pay.code, amount: Number(pay.amount), note: pay.note }) }); setMsg("Pagamento registrato."); setPay({ code: "", amount: "", note: "" }); load(); } catch (x: any) { setErr(x.message); } };
  if (see) return <><button className="btn btn-sm" onClick={() => setSee(null)}>‹ Tutti i creator</button><CreatorView code={see.code} who={`Vista di ${see.name}`} /></>;
  if (!d) return err ? <div className="note err">{err}</div> : <p className="muted">…</p>;
  const t = d.totals;
  return (
    <div className="st">
      <section className="st-kpis">
        {[["Visite", t.clicks], ["Iscritti", t.signups], ["Abbonati", t.payers], ["Incassi da codici", eur(t.revenue)], ["Da pagare", eur(t.due)]].map(([l, v]: any) => <div key={l} className="card st-kpi"><div className="muted small">{l}</div><b className="jy-big">{v}</b></div>)}
      </section>
      <section className="card st-tablewrap">
        <table className="st-table">
          <thead><tr><th>Creator</th><th>Codice</th><th>Visite</th><th>Iscritti</th><th>Abbonati</th><th>Incassi</th><th>Maturato</th><th>Da pagare</th></tr></thead>
          <tbody>{d.creators.map((c: any) => (
            <tr key={c.email} onClick={() => setSee(c)} className="st-click"><td><b>{c.name}</b></td><td>{c.code}</td><td>{c.clicks}</td><td>{c.signups}</td><td>{c.payers}</td><td>{eur(c.revenue)}</td><td>{eur(c.earned)}</td><td><b>{eur(c.due)}</b></td></tr>
          ))}</tbody>
        </table>
        {d.creators.length === 0 && <p className="muted" style={{ margin: ".6rem 0 0" }}>Nessun creator ancora: abilitane uno qui sotto.</p>}
      </section>
      <section className="st-two">
        <form className="card st-form" onSubmit={add}>
          <b>Abilita un creator</b>
          <input placeholder="Email del creator" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} required />
          <input placeholder="Nome" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required />
          <input placeholder="Codice (es. MARCO20)" value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} required />
          <div className="st-3"><label>Sconto %<input type="number" value={f.discount_pct} onChange={(e) => setF({ ...f, discount_pct: Number(e.target.value) })} /></label><label>Mesi<input type="number" value={f.months} onChange={(e) => setF({ ...f, months: Number(e.target.value) })} /></label><label>Commissione %<input type="number" value={f.commission_pct} onChange={(e) => setF({ ...f, commission_pct: Number(e.target.value) })} /></label></div>
          <button className="btn btn-primary">Abilita</button>
        </form>
        <form className="card st-form" onSubmit={payout}>
          <b>Registra un pagamento</b>
          <select value={pay.code} onChange={(e) => setPay({ ...pay, code: e.target.value })} required><option value="">Creator…</option>{d.creators.map((c: any) => <option key={c.code} value={c.code}>{c.name} · da pagare {eur(c.due)}</option>)}</select>
          <input placeholder="Importo €" inputMode="decimal" value={pay.amount} onChange={(e) => setPay({ ...pay, amount: e.target.value.replace(",", ".") })} required />
          <input placeholder="Nota (bonifico, mese…)" value={pay.note} onChange={(e) => setPay({ ...pay, note: e.target.value })} />
          <button className="btn btn-primary">Registra</button>
          <Link href="/dashboard/promo" className="small accent">Gestione codici</Link>
        </form>
      </section>
      {msg && <div className="note ok">{msg}</div>}{err && <div className="note err">{err}</div>}
    </div>
  );
}

export default function StudioPage() {
  const { me } = useApp();
  if (me && !me.studio) return <div className="note">Pagina riservata ai creator di EloRise.</div>;
  if (!me) return <p className="muted">…</p>;
  const isAdmin = me.studio === "admin";
  return (
    <>
      <div className="pagehead"><h1>Studio</h1>{isAdmin && me && <span className="muted small">Vista amministratore</span>}</div>
      {isAdmin ? <AdminView /> : <CreatorView />}
    </>
  );
}
