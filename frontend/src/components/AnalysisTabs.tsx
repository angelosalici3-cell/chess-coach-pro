"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useApp } from "./app";
import { u } from "../lib/ui-copy";

/** Sezione "Analisi": Partite, Aperture e Lezioni AI sono tre viste dello stesso posto. */
export default function AnalysisTabs() {
  const { lang } = useApp();
  const path = usePathname();
  const items = [
    { href: "/dashboard/games", label: u("tabGames", lang), on: path.startsWith("/dashboard/games") },
    { href: "/dashboard/lessons", label: u("tabLessons", lang), on: path.startsWith("/dashboard/lessons") },
    { href: "/dashboard/openings", label: lang === "it" ? "Aperture" : lang === "es" ? "Aperturas" : "Openings", on: path.startsWith("/dashboard/openings") },
  ];
  return <div className="subtabs" role="tablist">{items.map((i) => <Link key={i.href} href={i.href} className={i.on ? "on" : ""}>{i.label}</Link>)}</div>;
}
