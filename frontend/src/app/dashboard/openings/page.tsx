"use client";
import { useApp } from "../../../components/app";
import OpeningMap from "../../../components/OpeningMap";

export default function OpeningsPage() {
  const { t } = useApp();
  return (
    <>
      <div className="pagehead"><h1>{t("omTitle")}</h1></div>
      <p className="muted" style={{ marginTop: 0 }}>{t("omSub")}</p>
      <OpeningMap />
    </>
  );
}
