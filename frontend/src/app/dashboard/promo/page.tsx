"use client";
import { useCallback, useEffect, useState } from "react";
import { useApp } from "../../../components/app";

type Row = { code: string; creator: string; channel: string | null; discount_pct: number; months: number; commission_pct: number; active: boolean; clicks: number; signups: number; payers: number; revenue: number; commission: number };
const EMPTY = { code: "", creator: "", channel: "", discount_pct: 20, months: 1, commission_pct: 20 };

/** Pannello per chi gestisce l'app (email in ADMIN_EMAILS): crea codici e guarda i risultati per creatore. */
export default function PromoPage() {
  const { call, me } = useApp();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [f, setF] = useState(EMPTY);
  const [err, setErr] = useState(""), [msg, setMsg] = useState(""), [busy, setBusy] = useState(false);
  const load = useCallback(() => { call("/admin/promo").then((d) => setRows(d.codes)).catch((e) => setErr(e.message)); }, [call]);
  useEffect(() => { if (me?.is_admin) load(); }, [me?.is_admin, load]);
  if (me && !me.is_admin) return <div className="note">Pagina riservata a chi gestisce l&apos;app.</div>;

  const link = (c: string) => `${window.location.origin}/?ref=${c}`;
  const copy = async (c: string) => { try { await navigator.clipboard.writeText(link(c)); setMsg(`Link copiato: ${link(c)}`); } catch { setMsg(link(c)); } };
  const create = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(""); setMsg(""); setBusy(true);
    try { await call("/admin/promo", { method: "POST", body: JSON.stringify({ ...f, code: f.code.trim().toUpperCase() }) }); setF(EMPTY); setMsg("Codice creato."); load(); }
    catch (e: any) { setErr(e.message); }
    setBusy(false);
  };
  const toggle = async (r: Row) => { try { await call(`/admin/promo/${r.code}/active`, { method: "POST", body: JSON.stringify({ active: !r.active }) }); load(); } catch (e: any) { setErr(e.message); } };
  const num = (k: keyof typeof EMPTY, min: number, max: number) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: Math.max(min, Math.min(max, Number(e.target.value) || 0)) });

  return (
    <>
      <div className="pagehead"><h1>Codici promo</h1></div>
      <p className="muted">Un codice per ogni creatore o gruppo. Il link <b>tuosito/?ref=CODICE</b> applica lo sconto in automatico e traccia clic, iscrizioni e pagamenti.</p>
      {err && <div className="note err">{err}</div>}
      {msg && <div className="note">{msg}</div>}
      <form className="card promo-form" onSubmit={create}>
        <label>Codice<input id="pc-code" required minLength={3} maxLength={24} placeholder="ES. MARCO20" value={f.code} onChange={(e) => setF({ ...f, code: e.target.value.toUpperCase() })} /></label>
        <label>Creatore o gruppo<input id="pc-creator" required placeholder="Nome" value={f.creator} onChange={(e) => setF({ ...f, creator: e.target.value })} /></label>
        <label>Canale<input id="pc-channel" placeholder="Twitch, TikTok, Discord…" value={f.channel} onChange={(e) => setF({ ...f, channel: e.target.value })} /></label>
        <label>Sconto %<input id="pc-disc" type="number" inputMode="numeric" value={f.discount_pct} onChange={num("discount_pct", 0, 100)} /></label>
        <label>Mesi di sconto<input id="pc-months" type="number" inputMode="numeric" value={f.months} onChange={num("months", 1, 12)} /></label>
        <label>Percentuale al creatore<input id="pc-comm" type="number" inputMode="numeric" value={f.commission_pct} onChange={num("commission_pct", 0, 100)} /></label>
        <button className="btn btn-primary" disabled={busy}>Crea codice</button>
      </form>
      <div className="promo-wrap">
        <table className="promo-tbl">
          <thead><tr><th>Codice</th><th>Creatore</th><th>Sconto</th><th>Clic</th><th>Iscritti</th><th>Paganti</th><th>Incassi €</th><th>Da pagare €</th><th></th></tr></thead>
          <tbody>
            {rows?.map((r) => (
              <tr key={r.code} className={r.active ? "" : "off"}>
                <td><b>{r.code}</b><div className="muted small">{r.channel || ""}</div></td>
                <td>{r.creator}<div className="muted small">{r.commission_pct}% al creatore</div></td>
                <td>{r.discount_pct ? `-${r.discount_pct}% · ${r.months} ${r.months > 1 ? "mesi" : "mese"}` : "nessuno"}</td>
                <td>{r.clicks}</td><td>{r.signups}</td><td>{r.payers}</td><td>{r.revenue.toFixed(2)}</td><td>{r.commission.toFixed(2)}</td>
                <td className="promo-act"><button className="btn btn-sm" onClick={() => copy(r.code)}>Copia link</button><button className="btn btn-sm" onClick={() => toggle(r)}>{r.active ? "Disattiva" : "Attiva"}</button></td>
              </tr>
            ))}
            {rows && !rows.length && <tr><td colSpan={9} className="muted">Nessun codice ancora: creane uno qui sopra.</td></tr>}
          </tbody>
        </table>
      </div>
      <p className="muted small">Gli incassi sommano il primo pagamento e i rinnovi degli utenti arrivati con quel codice, al lordo delle commissioni Stripe e dell&apos;IVA. La colonna &quot;Da pagare&quot; applica la percentuale concordata: va verificata prima di ogni pagamento.</p>
    </>
  );
}
