"use client";
import { useState } from "react";
import { supabase, useApp } from "../../components/app";

const PLANS = [
  { k: "Free", price: 0, acc: 1, gm: "5", sync: false },
  { k: "Plus", price: 2.99, acc: 2, gm: "20", sync: true },
  { k: "Pro", price: 4.99, acc: 3, gm: "∞", sync: true },
  { k: "Elite", price: 9.99, acc: 5, gm: "∞", sync: true },
];

export default function PlansPage() {
  const { call, t, me } = useApp();
  const [err, setErr] = useState("");
  const go = async (path: string, body?: any) => {
    try { const r = await call(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }); window.location.href = r.url; }
    catch (e: any) { setErr(e.message); }
  };
  const del = async () => {
    if (!confirm(t("deleteConfirm"))) return;
    try { await call("/me", { method: "DELETE" }); await supabase.auth.signOut(); } catch (e: any) { setErr(e.message); }
  };
  return (
    <>
      <h2>{t("navPlans")}</h2>
      {err && <div className="card err">⚠️ {err}</div>}
      <div className="plans">
        {PLANS.map((p) => (
          <div key={p.k} className={"card " + (me?.tier === p.k ? "cur" : "")}>
            <h3>{p.k}</h3>
            <div className="price">€{p.price.toFixed(2)}<span className="muted small">{t("perMonth")}</span></div>
            <p className="small">{t("accounts")}: {p.acc}<br />{t("lessons")}: {p.gm}<br />{p.sync ? "✓ " + t("autoSync") : ""}</p>
            {me?.tier === p.k ? <span className="muted">{t("current")}</span> : p.price > 0 && <button className="primary" onClick={() => go("/billing/checkout", { plan: p.k })}>{t("choose")}</button>}
          </div>
        ))}
      </div>
      {me?.tier !== "Free" && <button onClick={() => go("/billing/portal")}>{t("manage")}</button>}
      <hr style={{ margin: "2rem 0", opacity: 0.15 }} />
      <button onClick={del} style={{ color: "#ff6b6b", borderColor: "#ff6b6b55" }}>{t("deleteAcc")}</button>
    </>
  );
}
