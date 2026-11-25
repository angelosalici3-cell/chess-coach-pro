"use client";
import { useCallback, useEffect, useState } from "react";
import { useApp } from "../../../components/app";

const eur = (n: number) => (n || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: Math.abs(n || 0) % 1 ? 2 : 0 });
const pct = (a: number, b: number) => (b ? Math.round((100 * a) / b) : 0);
const MON = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];
const mlabel = (m: string) => MON[Number(m.slice(5, 7)) - 1];
const PROFILES: Record<string, { name: string; desc: string }> = {
  nano: { name: "Nano", desc: "Un premio fisso per ogni abbonato confermato (1,2 volte il primo canone mensile)." },
  standard: { name: "Standard", desc: "Premio per ogni abbonato confermato più il 10% di quanto incassiamo da lui nei primi 12 mesi." },
  partner: { name: "Partner", desc: "7% di quanto incassiamo, premi di fedeltà a 3, 6 e 12 mesi e un premio annuale di performance." },
  retention: { name: "Fedeltà", desc: "Guadagni quando gli abbonati restano: premi a 3, 6 e 12 mesi di abbonamento." },
};
const REGIMES: Record<string, string> = { forfettario: "Forfettario", ordinario: "Ordinario con P.IVA", occasionale: "Prestazione occasionale", estero: "Estero" };

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

/* ---------- creator ---------- */
function TaxForm({ d, onSaved }: { d: any; onSaved: () => void }) {
  const { call } = useApp();
  const [f, setF] = useState({ regime: d.regime || "", tax_id: "", country: d.country || "IT", iban: "", invoice_mode: d.invoice_mode || "" });
  const [err, setErr] = useState(""), [ok, setOk] = useState(false);
  const save = async (e: React.FormEvent) => {
    e.preventDefault(); setErr("");
    try { await call("/studio/creator/tax", { method: "POST", body: JSON.stringify(f) }); setOk(true); onSaved(); } catch (x: any) { setErr(x.message); }
  };
  return (
    <form className="card st-form st-tax" onSubmit={save}>
      <div className="st-row"><b>I tuoi dati per essere pagato</b><span className={"st-pill " + (d.tax_ok ? "ok" : "warn")}>{d.tax_ok ? "Completi" : "Da completare"}</span></div>
      <p className="muted small" style={{ margin: 0 }}>Servono per emettere il pagamento. Fino a quando mancano, i compensi maturano ma non possiamo versarli. Li vede solo chi gestisce EloRise.</p>
      <label className="st-lab">Come lavori<select value={f.regime} onChange={(e) => setF({ ...f, regime: e.target.value })} required>
        <option value="">Scegli…</option>{Object.entries(REGIMES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
      {(f.regime === "ordinario" || f.regime === "estero") && <p className="muted small" style={{ margin: 0 }}>Con questo regime il compenso è soggetto a IVA 22%: l'IVA è a carico di EloRise e rientra nel tetto dei compensi.</p>}
      <div className="st-3b">
        <label className="st-lab">Codice fiscale o P.IVA<input value={f.tax_id} onChange={(e) => setF({ ...f, tax_id: e.target.value })} placeholder={d.tax_ok ? "Già salvato, riscrivi per cambiare" : ""} required /></label>
        <label className="st-lab">Paese (2 lettere)<input maxLength={2} value={f.country} onChange={(e) => setF({ ...f, country: e.target.value.toUpperCase() })} /></label>
      </div>
      <label className="st-lab">IBAN<input value={f.iban} onChange={(e) => setF({ ...f, iban: e.target.value })} placeholder="IT00 X000 0000 0000 0000 0000 000" required /></label>
      <label className="st-lab">Documento che emetti<select value={f.invoice_mode} onChange={(e) => setF({ ...f, invoice_mode: e.target.value })}>
        <option value="">Non so ancora</option><option>Fattura elettronica</option><option>Ricevuta</option><option>Nota di debito estera</option></select></label>
      <button className="btn btn-primary">Salva dati</button>
      {ok && <div className="note ok">Dati salvati.</div>}{err && <div className="note err">{err}</div>}
    </form>
  );
}

function CreatorView({ code, who }: { code?: string; who?: string }) {
  const { call } = useApp();
  const [d, setD] = useState<any>(null), [err, setErr] = useState(""), [msg, setMsg] = useState("");
  const load = useCallback(() => { call(`/studio/creator${code ? `?code=${code}` : ""}`).then(setD).catch((e) => setErr(e.message)); }, [call, code]);
  useEffect(() => { load(); }, [load]);
  if (err) return <div className="note err">{err}</div>;
  if (!d) return <p className="muted">…</p>;
  const link = `${typeof window !== "undefined" ? window.location.origin : ""}/?ref=${d.code}`;
  const copy = async (t: string, m: string) => { try { await navigator.clipboard.writeText(t); setMsg(m); } catch { setMsg(t); } setTimeout(() => setMsg(""), 2500); };
  const caps = [
    `Sto usando EloRise: un coach di scacchi che analizza le tue partite di Chess.com e Lichess e ti spiega gli errori che ripeti. Con il mio link hai ${d.discount_pct}% di sconto: ${link}`,
    `Se vuoi migliorare a scacchi senza perdere ore a rivedere le partite, prova EloRise. Codice ${d.code}, link: ${link}`,
    `Il mio consiglio per salire di Elo: capire perché perdi. EloRise lo fa per te. Sconto per voi con ${d.code}: ${link}`,
  ];
  const P = PROFILES[d.profile] || PROFILES.nano;
  const rows: [string, number, string][] = [
    ["Premio per abbonato confermato", d.cpa, "una volta per ogni abbonato rimasto oltre 30 giorni"],
    ["Quota sugli incassi", d.share, "percentuale su quanto incassiamo dai tuoi abbonati"],
    ["Premi di fedeltà", d.retention, "a 3, 6 e 12 mesi di abbonamento"],
    ["Premio di performance", d.perf, d.perf_pending > 0 ? `${eur(d.perf_pending)} in maturazione, si sblocca dopo 12 mesi di collaborazione` : "annuale, sul totale dei tuoi abbonati"],
  ];
  const shown = rows.filter((r) => r[1] > 0 || (r[0].startsWith("Premio per") && d.profile !== "partner" && d.profile !== "retention") || (r[0].startsWith("Quota") && ["standard", "partner"].includes(d.profile)) || (r[0].startsWith("Premi di fedeltà") && ["partner", "retention"].includes(d.profile)) || (r[0].startsWith("Premio di perf") && d.profile === "partner"));
  return (
    <div className="st">
      <section className="card st-hero">
        <div className="muted small">{who || "Il tuo impatto"}</div>
        <h2>{d.signups > 0 ? <>Grazie a te <b>{d.signups}</b> {d.signups === 1 ? "persona ha iniziato" : "persone hanno iniziato"} a migliorare a scacchi con EloRise.</> : "Il tuo link è pronto: la prima persona che si iscrive apparirà qui."}</h2>
        <p className="muted" style={{ margin: 0 }}>{d.payers > 0 ? `${d.payers} di loro ${d.payers === 1 ? "ha scelto" : "hanno scelto"} un piano a pagamento.` : "Ogni iscritto che passa a un piano a pagamento ti fa guadagnare."}</p>
      </section>

      {!d.tax_ok && !code && <TaxForm d={d} onSaved={load} />}

      <section className="st-kpis">
        {[["Visite al link", d.clicks, ""], ["Iscritti", d.signups, `${pct(d.signups, d.clicks)}% delle visite`], ["Abbonati confermati", d.confirmed, `${d.payers} hanno pagato`], ["Maturato", eur(d.earned), `${eur(d.due)} da ricevere`]].map(([l, v, s]: any) => (
          <div key={l} className="card st-kpi"><div className="muted small">{l}</div><b className="jy-big">{v}</b><div className="muted small">{s}</div></div>
        ))}
      </section>

      <section className="card">
        <div className="st-row"><b>Iscritti per settimana</b><span className="muted small">ultime 12 settimane</span></div>
        <Bars s={d.series} />
      </section>

      <section className="card">
        <div className="st-row"><b>Come guadagni: profilo {P.name}</b></div>
        <p className="muted small" style={{ margin: ".2rem 0 .8rem" }}>{P.desc}</p>
        <div className="st-lines">
          {shown.map(([l, v, s]) => <div key={l} className="st-line"><div><span>{l}</span><span className="muted small">{s}</span></div><b>{eur(v)}</b></div>)}
          <div className="st-line tot"><div><span>Totale maturato</span>{d.capped && <span className="muted small">Hai raggiunto il tetto del {d.cap_pct}% del valore generato: il resto non matura.</span>}</div><b>{eur(d.earned)}</b></div>
        </div>
        <div className="st-split">
          <div><span className="muted small">Già pagato</span><b className="jy-big">{eur(d.paid)}</b></div>
          <div><span className="muted small">Da ricevere</span><b className="jy-big">{eur(d.due)}</b></div>
        </div>
        <p className="muted small" style={{ margin: ".8rem 0 0" }}>Un abbonato è confermato dopo {d.confirm_days} giorni dal primo pagamento, senza rimborso. Guadagni sui suoi primi {d.attr_months} mesi. Paghiamo da 50 € maturati, circa 45 giorni dopo la fine del mese.</p>
        {d.payouts.length > 0 && <div className="st-pay">{d.payouts.map((p: any, i: number) => <div key={i} className="muted small">{new Date(p.paid_at).toLocaleDateString("it-IT")} · {eur(Number(p.amount))}{p.doc_ref ? ` · ${p.doc_ref}` : ""}{p.note ? ` · ${p.note}` : ""}</div>)}</div>}
      </section>

      {d.tax_ok && !code && <details className="card"><summary><b>Modifica i tuoi dati fiscali</b></summary><div style={{ marginTop: ".8rem" }}><TaxForm d={d} onSaved={load} /></div></details>}

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

/* ---------- grafici admin ---------- */
function Money({ m }: { m: any[] }) {
  const W = 640, H = 240, L = 40, B = 24, T = 10;
  const cost = (x: any) => x.fees + x.variable + x.fixed + x.creators + x.tax + x.refunds + x.disputes;
  const top = Math.max(50, ...m.map((x) => Math.max(x.revenue + x.donations, cost(x))), ...m.map((x) => x.profit)) * 1.1;
  const low = Math.min(0, ...m.map((x) => x.profit)) * 1.1;
  const y = (v: number) => T + (H - T - B) * (1 - (v - low) / (top - low));
  const bw = (W - L) / m.length;
  const layers: [string, string][] = [["fixed", "var(--mute)"], ["variable", "#7a6a5a"], ["fees", "#b08968"], ["creators", "#8ecae6"], ["tax", "#6c7a89"], ["refunds", "#e5484d"]];
  const line = m.map((x, i) => `${i ? "L" : "M"}${L + bw * i + bw / 2},${y(x.profit)}`).join(" ");
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="st-svg" role="img" aria-label="Incassi, costi e utile per mese">
        {[0, 0.5, 1].map((p) => { const v = low + (top - low) * p; return <g key={p}><line x1={L} x2={W} y1={y(v)} y2={y(v)} className="st-grid" /><text x={L - 6} y={y(v) + 3} textAnchor="end" className="st-ax">{Math.round(v)}</text></g>; })}
        <line x1={L} x2={W} y1={y(0)} y2={y(0)} className="st-zero" />
        {m.map((x, i) => {
          const bx = L + bw * i + bw * 0.12, w = bw * 0.36;
          let acc = 0;
          return (
            <g key={x.m}>
              <title>{`${x.m}: incassi ${eur(x.revenue)}, donazioni ${eur(x.donations)}, costi ${eur(cost(x))}, utile ${eur(x.profit)}`}</title>
              <rect x={bx} y={y(x.revenue + x.donations)} width={w} height={Math.max(0, y(0) - y(x.revenue + x.donations))} fill="var(--ember)" rx="2" />
              {layers.map(([k, c]) => { const v = x[k] || 0; const r = <rect key={k} x={bx + w + 2} y={y(acc + v)} width={w} height={Math.max(0, y(acc) - y(acc + v))} fill={c} />; acc += v; return r; })}
              <text x={L + bw * i + bw / 2} y={H - 8} textAnchor="middle" className="st-ax">{mlabel(x.m)}</text>
            </g>
          );
        })}
        <path d={line} className="st-profit" />
        {m.map((x, i) => <circle key={x.m} cx={L + bw * i + bw / 2} cy={y(x.profit)} r="3" className="st-dot" />)}
      </svg>
      <div className="st-legend"><span><i style={{ background: "var(--ember)" }} />Incassi</span>{layers.map(([k, c]) => <span key={k}><i style={{ background: c }} />{({ fixed: "Costi fissi", variable: "Variabili", fees: "Commissioni Stripe", creators: "Creator (con IVA)", tax: "Tasse stimate", refunds: "Rimborsi" } as any)[k]}</span>)}<span><i className="ln" />Utile</span></div>
    </div>
  );
}

function Funnel({ steps }: { steps: [string, number][] }) {
  const max = Math.max(1, steps[0][1]);
  return <div className="st-fun">{steps.map(([l, v], i) => (
    <div key={l} className="st-fstep"><div className="st-row"><span>{l}</span><b>{v}</b></div><div className="bar"><div style={{ width: `${Math.max(2, (100 * v) / max)}%`, background: "var(--ember)" }} /></div>{i > 0 && <span className="muted small">{pct(v, steps[i - 1][1])}% del passo prima</span>}</div>
  ))}</div>;
}

function Overview() {
  const { call } = useApp();
  const [a, setA] = useState<any>(null), [d, setD] = useState<any>(null), [err, setErr] = useState("");
  useEffect(() => { call("/studio/admin/analytics").then(setA).catch((e) => setErr(e.message)); call("/studio/admin").then(setD).catch(() => {}); }, [call]);
  if (!a) return err ? <div className="note err">{err}</div> : <p className="muted">…</p>;
  const m = a.months, last = m[m.length - 1], s = a.subs, be = a.breakeven;
  const tot = (k: string) => m.reduce((n: number, x: any) => n + x[k], 0);
  const cost = (x: any) => x.fees + x.variable + x.fixed + x.creators + x.tax + x.refunds + x.disputes;
  const profit12 = tot("profit"), rev12 = tot("revenue") + tot("donations");
  const tiers = Object.entries(s.by_tier) as [string, number][];
  const maxT = Math.max(1, ...tiers.map(([, n]) => n));
  const progress = be.subs_needed ? Math.min(100, (100 * s.total) / be.subs_needed) : 0;
  const t = d?.totals;
  return (
    <div className="st">
      <section className="st-kpis">
        {[["Utile ultimi 12 mesi", eur(profit12), profit12 >= 0 ? "in positivo" : "in perdita"], ["Incassi 12 mesi", eur(rev12), `${eur(last.revenue + last.donations)} questo mese`], ["MRR", eur(s.mrr), `${s.total} abbonati, ARPU ${eur(s.arpu)}`], ["Abbandono 30 giorni", `${s.churn_30d}%`, `${s.canceled_30d} disdette`], ["Utenti gratuiti", s.free, `${pct(s.total, s.total + s.free)}% passa a pagamento`]].map(([l, v, sub]: any) => (
          <div key={l} className="card st-kpi"><div className="muted small">{l}</div><b className="jy-big">{v}</b><div className="muted small">{sub}</div></div>
        ))}
      </section>

      <section className="card">
        <div className="st-row"><b>Incassi, costi e utile</b><span className="muted small">ultimi 12 mesi, euro</span></div>
        <Money m={m} />
      </section>

      <section className="st-two">
        <div className="card">
          <b>Punto di pareggio</b>
          <p className="muted small" style={{ margin: ".3rem 0 .8rem" }}>Costi fissi {eur(be.fixed)} al mese, ogni abbonato lascia circa {eur(be.contribution)} dopo commissioni e costi variabili.</p>
          <div className="st-row"><span>{s.total} abbonati</span><b>{be.subs_needed ? `servono ${Math.ceil(be.subs_needed)}` : "da configurare"}</b></div>
          <div className="bar"><div style={{ width: `${progress}%`, background: progress >= 100 ? "var(--ok, #4ade80)" : "var(--ember)" }} /></div>
          <p className="muted small" style={{ margin: ".6rem 0 0" }}>{be.fixed === 0 ? "Inserisci i costi fissi nella scheda Costi per vedere il pareggio." : progress >= 100 ? "I costi fissi sono coperti." : `Ti mancano ${Math.max(0, Math.ceil(be.subs_needed - s.total))} abbonati.`}</p>
        </div>
        <div className="card">
          <b>Abbonati per piano</b>
          <div className="st-hb">{tiers.map(([k, n]) => <div key={k} className="st-hrow"><span>{k}</span><div className="bar"><div style={{ width: `${(100 * n) / maxT}%`, background: "var(--ember)" }} /></div><b>{n}</b></div>)}</div>
        </div>
      </section>

      <section className="st-two">
        <div className="card">
          <b>Dove vanno i soldi, ultimo mese</b>
          <div className="st-lines" style={{ marginTop: ".6rem" }}>
            {([["Commissioni Stripe", last.fees], ["Costi variabili", last.variable], ["Costi fissi", last.fixed], ["Creator", last.creators], ["Tasse stimate", last.tax], ["Rimborsi e contestazioni", last.refunds + last.disputes]] as [string, number][]).map(([l, v]) => <div key={l} className="st-line"><span>{l}</span><b>{eur(v)}</b></div>)}
            <div className="st-line tot"><span>Utile</span><b>{eur(last.profit)}</b></div>
          </div>
          <p className="muted small" style={{ margin: ".6rem 0 0" }}>Le tasse sono una stima (forfettario) da confermare con il commercialista.</p>
        </div>
        <div className="card">
          <b>Dai creator agli abbonati</b>
          {t ? <Funnel steps={[["Visite", t.clicks], ["Iscritti", t.signups], ["Abbonati", t.payers]]} /> : <p className="muted">…</p>}
          {t && <p className="muted small" style={{ margin: ".6rem 0 0" }}>Costo creator maturato {eur(a.creators_cost_accrued)} su un margine generato di {eur(t.margin)}.</p>}
        </div>
      </section>
    </div>
  );
}

function CostsTab() {
  const { call } = useApp();
  const [rows, setRows] = useState<any[]>([]), [err, setErr] = useState("");
  const thisMonth = new Date().toISOString().slice(0, 7);
  const [f, setF] = useState({ label: "", amount: "", recurring: true, month: thisMonth });
  const load = useCallback(() => { call("/studio/admin/costs").then((r: any) => setRows(r.costs)).catch((e) => setErr(e.message)); }, [call]);
  useEffect(() => { load(); }, [load]);
  const add = async (e: React.FormEvent) => { e.preventDefault(); setErr(""); try { await call("/studio/admin/costs", { method: "POST", body: JSON.stringify({ ...f, amount: Number(f.amount) }) }); setF({ ...f, label: "", amount: "" }); load(); } catch (x: any) { setErr(x.message); } };
  const end = async (id: number) => { try { await call(`/studio/admin/costs/${id}/end`, { method: "POST" }); load(); } catch (x: any) { setErr(x.message); } };
  const active = rows.filter((r) => r.recurring && !r.ended);
  const monthly = active.reduce((n, r) => n + Number(r.amount), 0);
  return (
    <div className="st">
      <section className="st-kpis"><div className="card st-kpi"><div className="muted small">Costi fissi mensili attivi</div><b className="jy-big">{eur(monthly)}</b><div className="muted small">{eur(monthly * 12)} all'anno</div></div></section>
      <section className="st-two">
        <form className="card st-form" onSubmit={add}>
          <b>Aggiungi un costo</b>
          <input placeholder="Voce (es. Render, commercialista)" value={f.label} onChange={(e) => setF({ ...f, label: e.target.value })} required />
          <div className="st-3b"><label className="st-lab">Importo €<input inputMode="decimal" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value.replace(",", ".") })} required /></label>
            <label className="st-lab">Dal mese<input type="month" value={f.month} onChange={(e) => setF({ ...f, month: e.target.value })} required /></label></div>
          <label className="st-check"><input type="checkbox" checked={f.recurring} onChange={(e) => setF({ ...f, recurring: e.target.checked })} /> Si ripete ogni mese</label>
          <button className="btn btn-primary">Aggiungi</button>{err && <div className="note err">{err}</div>}
        </form>
        <div className="card st-tablewrap">
          <table className="st-table"><thead><tr><th>Voce</th><th>Importo</th><th>Tipo</th><th>Da</th><th /></tr></thead>
            <tbody>{rows.map((r) => <tr key={r.id}><td>{r.label}</td><td>{eur(Number(r.amount))}</td><td>{r.recurring ? "mensile" : "una tantum"}</td><td>{String(r.month).slice(0, 7)}</td><td>{r.recurring && !r.ended ? <button className="btn btn-sm" onClick={() => end(r.id)}>Termina</button> : r.ended ? <span className="muted small">finito</span> : null}</td></tr>)}</tbody></table>
          {rows.length === 0 && <p className="muted" style={{ margin: ".6rem 0 0" }}>Nessun costo inserito. Parti da server, database, dominio e commercialista.</p>}
        </div>
      </section>
    </div>
  );
}

function CreatorsTab() {
  const { call } = useApp();
  const [d, setD] = useState<any>(null), [err, setErr] = useState(""), [msg, setMsg] = useState(""), [see, setSee] = useState<any>(null);
  const [f, setF] = useState({ email: "", name: "", code: "", profile: "nano", cap_pct: 20, discount_pct: 20, months: 1 });
  const [pay, setPay] = useState({ code: "", amount: "", note: "", doc_ref: "" });
  const load = useCallback(() => { call("/studio/admin").then(setD).catch((e) => setErr(e.message)); }, [call]);
  useEffect(() => { load(); }, [load]);
  const post = async (path: string, body: any, ok: string, reset?: () => void) => { setErr(""); setMsg(""); try { await call(path, { method: "POST", body: JSON.stringify(body) }); setMsg(ok); reset?.(); load(); } catch (x: any) { setErr(x.message); } };
  if (see) return <><button className="btn btn-sm" onClick={() => setSee(null)}>‹ Tutti i creator</button><CreatorView code={see.code} who={`Vista di ${see.name}`} /></>;
  if (!d) return err ? <div className="note err">{err}</div> : <p className="muted">…</p>;
  const t = d.totals;
  const sel = d.creators.find((c: any) => c.code === pay.code);
  return (
    <div className="st">
      <section className="st-kpis">
        {[["Visite", t.clicks], ["Iscritti", t.signups], ["Abbonati", t.payers], ["Incassi da codici", eur(t.revenue)], ["Margine generato", eur(t.margin)], ["Costo creator", eur(t.cost_total)], ["Da pagare", eur(t.due)]].map(([l, v]: any) => <div key={l} className="card st-kpi"><div className="muted small">{l}</div><b className="jy-big">{v}</b></div>)}
      </section>
      <section className="card st-tablewrap st-desk">
        <table className="st-table">
          <thead><tr><th>Creator</th><th>Profilo</th><th>Dati fiscali</th><th>Iscritti</th><th>Abbonati</th><th>Margine</th><th>Maturato</th><th>Tetto</th><th>Da pagare</th><th /></tr></thead>
          <tbody>{d.creators.map((c: any) => (
            <tr key={c.email} className={!c.active ? "off" : ""}>
              <td className="st-click" onClick={() => setSee(c)}><b>{c.name}</b><div className="muted small">{c.code}</div></td>
              <td><select value={c.profile} onChange={(e) => post(`/studio/admin/creators/${encodeURIComponent(c.email)}`, { profile: e.target.value }, "Profilo aggiornato")}>{Object.entries(PROFILES).map(([k, v]) => <option key={k} value={k}>{v.name}</option>)}</select></td>
              <td><span className={"st-pill " + (c.tax_ok ? "ok" : "warn")}>{c.tax_ok ? (REGIMES[c.regime] || "ok") : "mancanti"}</span></td>
              <td>{c.signups}</td><td>{c.payers}</td><td>{eur(c.margin)}</td>
              <td>{eur(c.earned)}{c.capped && <span className="st-pill warn" title="Compenso limitato dal tetto">tetto</span>}</td>
              <td><input className="st-mini" type="number" min={0} max={60} defaultValue={c.cap_pct} onBlur={(e) => Number(e.target.value) !== c.cap_pct && post(`/studio/admin/creators/${encodeURIComponent(c.email)}`, { cap_pct: Number(e.target.value) }, "Tetto aggiornato")} />%</td>
              <td><b>{eur(c.due)}</b></td>
              <td><button className="btn btn-sm" onClick={() => post(`/studio/admin/creators/${encodeURIComponent(c.email)}`, { active: !c.active }, c.active ? "Disattivato" : "Riattivato")}>{c.active ? "Disattiva" : "Attiva"}</button></td>
            </tr>
          ))}</tbody>
        </table>
        {d.creators.length === 0 && <p className="muted" style={{ margin: ".6rem 0 0" }}>Nessun creator ancora: abilitane uno qui sotto.</p>}
      </section>
      <section className="st-ccards">
        {d.creators.map((c: any) => (
          <article key={c.email} className={"card st-cc" + (!c.active ? " off" : "")}>
            <div className="st-row"><button className="st-cname" onClick={() => setSee(c)}><b>{c.name}</b><span className="muted small">{c.code}</span></button><span className={"st-pill " + (c.tax_ok ? "ok" : "warn")}>{c.tax_ok ? (REGIMES[c.regime] || "ok") : "dati mancanti"}</span></div>
            <div className="st-cstats">
              <div><span>Iscritti</span><b>{c.signups}</b></div><div><span>Abbonati</span><b>{c.payers}</b></div>
              <div><span>Maturato</span><b>{eur(c.earned)}</b></div><div><span>Da pagare</span><b>{eur(c.due)}</b></div>
            </div>
            {c.capped && <p className="muted small" style={{ margin: 0 }}>Compenso limitato dal tetto.</p>}
            <div className="st-cctl">
              <label className="st-lab">Profilo<select value={c.profile} onChange={(e) => post(`/studio/admin/creators/${encodeURIComponent(c.email)}`, { profile: e.target.value }, "Profilo aggiornato")}>{Object.entries(PROFILES).map(([k, v]) => <option key={k} value={k}>{v.name}</option>)}</select></label>
              <label className="st-lab">Tetto %<input type="number" min={0} max={60} defaultValue={c.cap_pct} onBlur={(e) => Number(e.target.value) !== c.cap_pct && post(`/studio/admin/creators/${encodeURIComponent(c.email)}`, { cap_pct: Number(e.target.value) }, "Tetto aggiornato")} /></label>
            </div>
            <div className="st-cbtn"><button className="btn btn-sm" onClick={() => setSee(c)}>Vedi dettaglio</button><button className="btn btn-sm" onClick={() => post(`/studio/admin/creators/${encodeURIComponent(c.email)}`, { active: !c.active }, c.active ? "Disattivato" : "Riattivato")}>{c.active ? "Disattiva" : "Attiva"}</button></div>
          </article>
        ))}
      </section>
      <section className="st-two">
        <form className="card st-form" onSubmit={(e) => { e.preventDefault(); post("/studio/admin/creators", { ...f, code: f.code.toUpperCase() }, "Creator abilitato.", () => setF({ ...f, email: "", name: "", code: "" })); }}>
          <b>Abilita un creator</b>
          <input placeholder="Email del creator" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} required />
          <input placeholder="Nome" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required />
          <input placeholder="Codice (es. MARCO20)" value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} required />
          <label className="st-lab">Profilo<select value={f.profile} onChange={(e) => setF({ ...f, profile: e.target.value })}>{Object.entries(PROFILES).map(([k, v]) => <option key={k} value={k}>{v.name}</option>)}</select></label>
          <p className="muted small" style={{ margin: 0 }}>{PROFILES[f.profile].desc}</p>
          <div className="st-3"><label>Sconto %<input type="number" value={f.discount_pct} onChange={(e) => setF({ ...f, discount_pct: Number(e.target.value) })} /></label><label>Mesi<input type="number" value={f.months} onChange={(e) => setF({ ...f, months: Number(e.target.value) })} /></label><label>Tetto % margine<input type="number" value={f.cap_pct} onChange={(e) => setF({ ...f, cap_pct: Number(e.target.value) })} /></label></div>
          <button className="btn btn-primary">Abilita</button>
        </form>
        <form className="card st-form" onSubmit={(e) => { e.preventDefault(); post("/studio/admin/payouts", { code: pay.code, amount: Number(pay.amount), note: pay.note, doc_ref: pay.doc_ref }, "Pagamento registrato.", () => setPay({ code: "", amount: "", note: "", doc_ref: "" })); }}>
          <b>Registra un pagamento</b>
          <select value={pay.code} onChange={(e) => setPay({ ...pay, code: e.target.value })} required><option value="">Creator…</option>{d.creators.map((c: any) => <option key={c.code} value={c.code}>{c.name} · da pagare {eur(c.due)}</option>)}</select>
          <input placeholder="Importo netto €" inputMode="decimal" value={pay.amount} onChange={(e) => setPay({ ...pay, amount: e.target.value.replace(",", ".") })} required />
          {sel && (sel.regime === "ordinario" || sel.regime === "estero") && Number(pay.amount) > 0 && <p className="muted small" style={{ margin: 0 }}>Regime con IVA: sul documento aggiungi IVA 22% ({eur(Number(pay.amount) * 0.22)}), totale {eur(Number(pay.amount) * 1.22)}.</p>}
          {sel && !sel.tax_ok && <p className="note err" style={{ margin: 0 }}>Il creator non ha ancora inserito i dati fiscali: non puoi pagarlo.</p>}
          <input placeholder="Numero fattura o ricevuta" value={pay.doc_ref} onChange={(e) => setPay({ ...pay, doc_ref: e.target.value })} />
          <input placeholder="Nota (bonifico, mese…)" value={pay.note} onChange={(e) => setPay({ ...pay, note: e.target.value })} />
          <button className="btn btn-primary">Registra</button>
        </form>
      </section>
      {msg && <div className="note ok">{msg}</div>}{err && <div className="note err">{err}</div>}
    </div>
  );
}

function AdminView() {
  const [tab, setTab] = useState<"over" | "cr" | "cost">("over");
  return (
    <>
      <div className="st-tabs" role="tablist">
        {([["over", "Panoramica"], ["cr", "Creator"], ["cost", "Costi"]] as const).map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} className={"st-tab" + (tab === k ? " on" : "")} onClick={() => setTab(k)}>{l}</button>)}
      </div>
      {tab === "over" ? <Overview /> : tab === "cr" ? <CreatorsTab /> : <CostsTab />}
    </>
  );
}

export default function StudioPage() {
  const { me } = useApp();
  if (me && !me.studio) return <div className="note">Pagina riservata ai creator di EloRise.</div>;
  if (!me) return <p className="muted">…</p>;
  const isAdmin = me.studio === "admin";
  return (
    <>
      <div className="pagehead"><h1>Studio</h1>{isAdmin && <span className="muted small">Vista amministratore</span>}</div>
      {isAdmin ? <AdminView /> : <CreatorView />}
    </>
  );
}
