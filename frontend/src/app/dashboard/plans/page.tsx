"use client";
import { useEffect, useState } from "react";
import { useApp } from "../../../components/app";
import { supabase } from "../../../lib/supabase";

const PLANS = [
  { k: "Free", price: 0, year: 0, acc: 1, gm: "3", hist: 50, sync: false },
  { k: "Plus", price: 4.99, year: 49, acc: 2, gm: "20", hist: 200, sync: true },
  { k: "Pro", price: 8.99, year: 89, acc: 3, gm: "∞", hist: 500, sync: true },
  { k: "Elite", price: 14.99, year: 149, acc: 5, gm: "∞", hist: 1000, sync: true },
];

export default function PlansPage() {
  const { call, t, me, refreshMe, lang } = useApp();
  const promoTxt = { it: "Codice {c} attivo: -{p}% {m}", en: "Code {c} active: {p}% off {m}", es: "Código {c} activo: -{p}% {m}" } as const;
  const promoWhen = (m: number) => (m > 1 ? { it: `per i primi ${m} mesi`, en: `for the first ${m} months`, es: `los primeros ${m} meses` } : { it: "sul primo mese", en: "on the first month", es: "el primer mes" })[lang];
  const [yearly, setYearly] = useState(false);
  const tog = { it: ["Mensile", "Annuale", "2 mesi gratis"], en: ["Monthly", "Yearly", "2 months free"], es: ["Mensual", "Anual", "2 meses gratis"] }[lang];
  const per = { it: "/anno", en: "/year", es: "/año" }[lang];
  const [err, setErr] = useState("");
  const [flash, setFlash] = useState("");
  useEffect(() => {
    const c = new URLSearchParams(window.location.search).get("checkout");
    if (c === "success") { setFlash(t("checkoutOk")); setTimeout(refreshMe, 4000); }
    if (c === "cancel") setFlash(t("checkoutKo"));
  }, []); // eslint-disable-line
  const go = async (path: string, body?: any) => {
    try { const r = await call(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }); window.location.href = r.url; }
    catch (e: any) { setErr(e.message); }
  };
  const del = async () => {
    if (!confirm(t("deleteConfirm"))) return;
    try { await call("/me", { method: "DELETE" }); await supabase.auth.signOut(); window.location.href = "/"; } catch (e: any) { setErr(e.message); }
  };
  return (
    <>
      <div className="pagehead"><h1>{t("navPlans")}</h1></div>
      {flash && <div className="note">{flash}</div>}
      {me?.promo?.discount_pct > 0 && <div className="note">{promoTxt[lang].replace("{c}", me.promo.code).replace("{p}", String(me.promo.discount_pct)).replace("{m}", promoWhen(me.promo.months))}</div>}
      {err && <div className="note err">{err}</div>}
      <div className="seg" role="group" aria-label="Billing" style={{ display: "inline-flex", gap: 4, margin: "6px 0 14px" }}>
        <button className={"btn " + (!yearly ? "btn-primary" : "btn-out")} onClick={() => setYearly(false)}>{tog[0]}</button>
        <button className={"btn " + (yearly ? "btn-primary" : "btn-out")} onClick={() => setYearly(true)}>{tog[1]} · {tog[2]}</button>
      </div>
      <div className="plans">
        {PLANS.map((p) => (
          <div key={p.k} className={"card plan " + (me?.tier === p.k ? "cur" : "") + (p.k === "Pro" ? " rec" : "")}>
            {p.k === "Pro" && <span className="plan-tag">{({ it: "Consigliato", en: "Popular", es: "Recomendado" } as const)[lang]}</span>}
            <h3>{p.k}</h3>
            <div className="price">€{(yearly && p.year ? p.year : p.price).toFixed(2)}<span className="muted small">{yearly && p.year ? per : t("perMonth")}</span></div>
            <p className="small">{t("accounts")}: {p.acc}<br />{t("lessons")}: {p.gm}<br />{t("historyN")}: {p.hist}<br />{p.sync ? t("autoSync") : ""}</p>
            {me?.tier === p.k ? <span className="muted">{t("current")}</span> : p.price > 0 && <button className="btn btn-primary" onClick={() => go("/billing/checkout", { plan: p.k, lang, interval: yearly ? "year" : "month" })}>{t("choose")}</button>}
          </div>
        ))}
      </div>
      {me?.tier !== "Free" && <button onClick={() => go("/billing/portal")}>{t("manage")}</button>}
      {me?.is_admin && <p><a href="/dashboard/promo" className="small muted">Codici promo</a></p>}
      <details id="delete" className="danger-zone"><summary>{({ it: "Altre opzioni", en: "More options", es: "Más opciones" } as const)[lang]}</summary><button className="danger" onClick={del}>{t("deleteAcc")}</button></details>
    </>
  );
}
