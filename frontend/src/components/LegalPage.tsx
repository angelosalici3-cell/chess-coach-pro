"use client";
import Link from "next/link";
import { LangSwitch, useLang } from "./lang";
import { Logo } from "./Logo";
import { ENTITY, LEGAL, isDraft } from "../lib/legal";

export default function LegalPage({ doc }: { doc: "privacy" | "terms" }) {
  const { lang, t } = useLang();
  const d = LEGAL[doc][lang];
  return (
    <div className="legal-wrap legal">
      <div className="legal-top"><Link href="/"><Logo size={34} /></Link><LangSwitch /></div>
      {isDraft() && <div className="note legal-draft">{t("legalDraft")}</div>}
      <h1>{d.title}</h1>
      <p className="muted">{t("updated")}: {ENTITY.updated}</p>
      <p>{d.intro}</p>
      {d.sections.map((s) => (
        <section key={s.h}>
          <h2>{s.h}</h2>
          {s.p?.map((x, i) => <p key={i}>{x}</p>)}
          {s.ul && <ul>{s.ul.map((x, i) => <li key={i}>{x}</li>)}</ul>}
        </section>
      ))}
    </div>
  );
}
