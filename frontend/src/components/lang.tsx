"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { K, LANGS, Lang, tr } from "../lib/i18n";

type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (k: K) => string };
const C = createContext<Ctx>({ lang: "it", setLang: () => {}, t: (k) => tr(k, "it") });
export const useLang = () => useContext(C);

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setL] = useState<Lang>("it");
  useEffect(() => {
    let saved: Lang | null = null;
    try { saved = localStorage.getItem("lang") as Lang | null; } catch {}
    const nav = navigator.language.slice(0, 2) as Lang;
    setL(saved && LANGS.includes(saved) ? saved : LANGS.includes(nav) ? nav : "en");
  }, []);
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  const setLang = (l: Lang) => { setL(l); try { localStorage.setItem("lang", l); } catch {} };
  return <C.Provider value={{ lang, setLang, t: (k) => tr(k, lang) }}>{children}</C.Provider>;
}

export function LangSwitch() {
  const { lang, setLang } = useLang();
  return (
    <div className="lang" role="group" aria-label="Language">
      {LANGS.map((l) => (
        <button key={l} className={l === lang ? "on" : ""} onClick={() => setLang(l)} aria-pressed={l === lang}>{l.toUpperCase()}</button>
      ))}
    </div>
  );
}

const LANG_NAME: Record<Lang, string> = { it: "Italiano", en: "English", es: "Español" };
/** Selettore lingua a tendina: occupa poco spazio nella barra in alto. */
export function LangSelect({ full = false }: { full?: boolean }) {
  const { lang, setLang } = useLang();
  return (
    <select className={"lang-sel" + (full ? " full" : "")} value={lang} onChange={(e) => setLang(e.target.value as Lang)} aria-label="Language">
      {LANGS.map((l) => <option key={l} value={l}>{full ? LANG_NAME[l] : l.toUpperCase()}</option>)}
    </select>
  );
}
