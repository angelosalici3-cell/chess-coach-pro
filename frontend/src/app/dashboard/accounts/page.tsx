"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "../../../components/app";

export default function AccountsPage() {
  const { call, t, me, refreshMe } = useApp();
  const [list, setList] = useState<any[]>([]);
  const [plat, setPlat] = useState("lichess");
  const [user, setUser] = useState("");
  const [err, setErr] = useState("");
  const [info, setInfo] = useState("");
  const load = () => call("/profiles").then(setList).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, [call]);

  const add = async () => {
    setErr("");
    try { await call("/profiles", { method: "POST", body: JSON.stringify({ piattaforma: plat, username: user }) }); setUser(""); setInfo(t("historyStarted").replace("{n}", String(me?.history_games ?? 50))); load(); refreshMe(); }
    catch (e: any) { setErr(e.message === "profile_limit" ? t("profileLimit") : e.message); }
  };
  const del = async (id: number) => { await call(`/profiles/${id}`, { method: "DELETE" }); load(); refreshMe(); };

  return (
    <>
      <div className="pagehead"><h1>{t("navAccounts")} {me && <span className="muted">{me.profiles.used}/{me.profiles.limit}</span>}</h1></div>
      {info && <div className="note">{info}</div>}
      {err && <div className="note err">{err} <Link href="/dashboard/plans" className="accent">{t("navPlans")}</Link></div>}
      {list.map((p) => (
        <div key={p.id} className="card row"><span>{p.piattaforma === "lichess" ? "Lichess" : "Chess.com"} <b>{p.username}</b></span><button onClick={() => del(p.id)}>{t("remove")}</button></div>
      ))}
      {list.length > 0 && <button className="btn btn-sm" onClick={async () => { await call("/sync/history", { method: "POST" }); setInfo(t("historyStarted").replace("{n}", String(me?.history_games ?? 50))); }}>{t("historyMore")}</button>}
      <div className="card askrow">
        <select value={plat} onChange={(e) => setPlat(e.target.value)}><option value="lichess">Lichess</option><option value="chesscom">Chess.com</option></select>
        <input placeholder={t("username")} value={user} onChange={(e) => setUser(e.target.value)} />
        <button className="btn btn-primary" onClick={add}>{t("add")}</button>
      </div>
    </>
  );
}
