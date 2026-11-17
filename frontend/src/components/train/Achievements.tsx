"use client";
import { useEffect, useState } from "react";
import { useApp } from "../app";
import Shield from "../Shield";
import { TK, tc } from "../../lib/train-copy";

const CONFETTI = ["#ff6b3d", "#ffd56a", "#4ee3b0", "#5aa9ff", "#ff5d8f"];

export default function Achievements({ onProgress }: { onProgress: () => void }) {
  const { call, lang, refreshMe } = useApp();
  const [a, setA] = useState<any>(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [burst, setBurst] = useState<{ dx: number; dy: number; rot: number; c: string }[]>([]);
  const load = () => call("/achievements").then(setA).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, [call]);

  const claim = async (lvl: number) => {
    setErr(""); setMsg("");
    try {
      const r = await call("/rewards/claim", { method: "POST", body: JSON.stringify({ lvl }) });
      const g = r.granted;
      setMsg(g.kind === "trial" ? tc("claimTrialOk", lang, { tier: g.tier, when: new Date(g.until).toLocaleDateString(lang) }) : g.converted ? tc("claimConvOk", lang, { n: g.amount }) : tc("claimLessonsOk", lang, { n: g.amount }));
      setBurst(Array.from({ length: 36 }, (_, i) => ({ dx: (Math.random() - 0.5) * 900, dy: -250 + Math.random() * 600, rot: Math.random() * 720, c: CONFETTI[i % CONFETTI.length] })));
      setTimeout(() => setBurst([]), 1700);
      load(); refreshMe(); onProgress();
    } catch (e: any) { setErr(e.message); }
  };

  if (err && !a) return <div className="note err">{err}</div>;
  if (!a) return <p className="muted">…</p>;
  const span = a.next_xp - a.level_xp, pct = Math.min(1, (a.xp - a.level_xp) / span), R = 46, C = 2 * Math.PI * R;
  const tierName = (n: number) => tc((["tierBronze", "tierSilver", "tierGold"] as TK[])[n - 1], lang);
  return (
    <div>
      {burst.length > 0 && <div className="burst" aria-hidden="true">{burst.map((b, i) => <i key={i} style={{ background: b.c, ["--dx" as string]: `${b.dx}px`, ["--dy" as string]: `${b.dy}px`, ["--rot" as string]: `${b.rot}deg` }} />)}</div>}
      <div className="card hero-level">
        <div className="lvl-ring">
          <svg viewBox="0 0 108 108" aria-hidden="true">
            <circle cx="54" cy="54" r={R} fill="none" stroke="var(--line-2)" strokeWidth="8" />
            <circle cx="54" cy="54" r={R} fill="none" stroke="var(--ember)" strokeWidth="8" strokeLinecap="round" strokeDasharray={C} strokeDashoffset={C * (1 - pct)} />
          </svg>
          <b>{a.level}</b><small>{tc("levelWord", lang).toUpperCase()}</small>
        </div>
        <div>
          <div className="big" style={{ fontSize: "1.8rem" }}>{a.xp} XP</div>
          <p className="muted" style={{ margin: ".2rem 0 .6rem" }}>{tc("toNext", lang, { n: a.next_xp - a.xp, l: a.level + 1 })}</p>
          <div className="chips" style={{ margin: 0 }}>
            <span className="chip"><span className="flame">●</span>&nbsp;{a.streak > 0 ? tc("streak", lang, { n: a.streak }) : tc("streak0", lang)}</span>
            {a.bonus_lessons > 0 && <span className="chip on">{tc("bonusLeft", lang, { n: a.bonus_lessons })}</span>}
          </div>
        </div>
      </div>

      <h2>{tc("shieldsTitle", lang)}</h2>
      <div className="shields">
        {a.shields.map((s: any) => {
          const next = s.tier < 3 ? s.tiers[s.tier] : null;
          const prev = s.tier > 0 ? s.tiers[s.tier - 1] : 0;
          return (
            <div key={s.id} className={"card shield-card t" + s.tier}>
              <Shield id={s.id} tier={s.tier} />
              <div className="nm">{tc(("sh_" + s.id) as TK, lang)}</div>
              <div className="pips" aria-label={s.tier ? tierName(s.tier) : tc("locked", lang)}>{[0, 1, 2].map((i) => <i key={i} className={i < s.tier ? "on" + i : ""} />)}</div>
              <div className="muted small">{next != null ? `${s.value} / ${next} ${tc(("un_" + s.id) as TK, lang)}` : tc("maxed", lang)}</div>
              {next != null && <div className="bar" style={{ width: "100%" }}><div style={{ width: `${Math.min(100, (100 * (s.value - prev)) / (next - prev))}%`, background: "var(--ember)" }} /></div>}
            </div>
          );
        })}
      </div>

      <h2>{tc("rewardsTitle", lang)}</h2>
      <p className="muted" style={{ marginTop: 0 }}>{tc("rewardsSub", lang)}</p>
      {msg && <div className="note ok">{msg}</div>}
      {err && <div className="note err">{err}</div>}
      <div className="ladder">
        {a.rewards.map((r: any) => (
          <div key={r.lvl} className={"card rung" + (r.claimable ? " can" : "") + (r.claimed ? " done" : "")}>
            <div className="lv">{tc("lockedAt", lang, { l: r.lvl })}</div>
            <div>
              <div className="gift">{r.kind === "trial" ? tc("rewardTrial", lang, { d: r.days, tier: r.tier }) : tc("rewardLessons", lang, { n: r.amount })}</div>
            </div>
            {r.claimed ? <span className="muted small">{tc("claimed", lang)}</span> : r.claimable ? <button className="btn btn-primary btn-sm" onClick={() => claim(r.lvl)}>{tc("claim", lang)}</button> : <span className="muted small">{a.level} / {r.lvl}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
