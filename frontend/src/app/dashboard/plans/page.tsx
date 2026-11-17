"use client";
import { useEffect, useState } from "react";
import { useApp } from "../../../components/app";
import { supabase } from "../../../lib/supabase";

const PLANS = [
  { k: "Free", price: 0, acc: 1, gm: "3", hist: 50, sync: false },
  { k: "Plus", price: 3.99, acc: 2, gm: "20", hist: 200, sync: true },
  { k: "Pro", price: 6.99, acc: 3, gm: "∞", hist: 500, sync: true },
  { k: "Elite", price: 12.99, acc: 5, gm: "∞", hist: 1000, sync: true },
];

export default function PlansPage() {
  const { call, t, me, refreshMe, lang } = useApp();
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
      {err && <div className="note err">{err}</div>}
      <div className="plans">
        {PLANS.map((p) => (
          <div key={p.k} className={"card " + (me?.tier === p.k ? "cur" : "")}>
            <h3>{p.k}</h3>
            <div className="price">€{p.price.toFixed(2)}<span className="muted small">{t("perMonth")}</span></div>
            <p className="small">{t("accounts")}: {p.acc}<br />{t("lessons")}: {p.gm}<br />{t("historyN")}: {p.hist}<br />{p.sync ? t("autoSync") : ""}</p>
            {me?.tier === p.k ? <span className="muted">{t("current")}</span> : p.price > 0 && <button className="btn btn-primary" onClick={() => go("/billing/checkout", { plan: p.k, lang })}>{t("choose")}</button>}
          </div>
        ))}
      </div>
      {me?.tier !== "Free" && <button onClick={() => go("/billing/portal")}>{t("manage")}</button>}
      <hr className="sep" />
      <button className="danger" onClick={del}>{t("deleteAcc")}</button>
    </>
  );
}
