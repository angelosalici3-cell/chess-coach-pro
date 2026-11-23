"use client";
import { useApp } from "../../../components/app";
import OpeningMap from "../../../components/OpeningMap";
import AnalysisTabs from "../../../components/AnalysisTabs";

export default function OpeningsPage() {
  const { t } = useApp();
  return (
    <>
      <AnalysisTabs />
      <div className="pagehead"><h1>{t("omTitle")}</h1></div>
      <p className="muted" style={{ marginTop: 0 }}>{t("omSub")}</p>
      <OpeningMap />
    </>
  );
}
