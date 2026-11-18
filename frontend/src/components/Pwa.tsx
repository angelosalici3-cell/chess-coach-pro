"use client";
import { useEffect, useState } from "react";

const TXT = {
  it: { title: "Installa Chess Coach", body: "Aprilo come un'app, a schermo intero.", install: "Installa", later: "Non ora", ios: "Su iPhone: tocca Condividi e poi “Aggiungi alla schermata Home”." },
  en: { title: "Install Chess Coach", body: "Open it like an app, full screen.", install: "Install", later: "Not now", ios: "On iPhone: tap Share, then “Add to Home Screen”." },
  es: { title: "Instala Chess Coach", body: "Ábrelo como una app, a pantalla completa.", install: "Instalar", later: "Ahora no", ios: "En iPhone: toca Compartir y luego “Añadir a pantalla de inicio”." },
} as const;

/** Registra il service worker e propone l'installazione (Android/Chrome: pulsante; iPhone: istruzioni). */
export default function Pwa({ lang }: { lang: "it" | "en" | "es" }) {
  const [evt, setEvt] = useState<any>(null);
  const [ios, setIos] = useState(false);
  const [hide, setHide] = useState(true);
  const t = TXT[lang];

  useEffect(() => {
    if ("serviceWorker" in navigator && location.protocol === "https:") navigator.serviceWorker.register("/sw.js").catch(() => {});
    const standalone = window.matchMedia("(display-mode: standalone)").matches || (navigator as any).standalone;
    let dismissed = "";
    try { dismissed = localStorage.getItem("pwa-dismissed") || ""; } catch {}
    if (standalone || dismissed) return;
    const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent) && !(window as any).MSStream;
    if (isIos) { setIos(true); setHide(false); }
    const on = (e: Event) => { e.preventDefault(); setEvt(e); setHide(false); };
    window.addEventListener("beforeinstallprompt", on);
    window.addEventListener("appinstalled", () => setHide(true));
    return () => window.removeEventListener("beforeinstallprompt", on);
  }, []);

  const close = () => { setHide(true); try { localStorage.setItem("pwa-dismissed", "1"); } catch {} };
  const install = async () => { if (!evt) return; evt.prompt(); await evt.userChoice.catch(() => {}); setEvt(null); close(); };
  if (hide || (!evt && !ios)) return null;
  return (
    <div className="pwa" role="dialog" aria-label={t.title}>
      <img src="/icon-192.png" alt="" width="44" height="44" />
      <div><b>{t.title}</b><div className="small muted">{evt ? t.body : t.ios}</div></div>
      <div className="row">{evt && <button className="btn btn-primary btn-sm" onClick={install}>{t.install}</button>}<button className="btn btn-sm" onClick={close}>{t.later}</button></div>
    </div>
  );
}
