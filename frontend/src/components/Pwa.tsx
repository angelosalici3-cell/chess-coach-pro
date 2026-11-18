"use client";
import { useEffect, useState } from "react";

const TXT = {
  it: { title: "Installa Chess Coach", body: "Aprilo come un'app, a schermo intero.", install: "Installa", later: "Non ora", ios: "Su iPhone: tocca Condividi e poi “Aggiungi alla schermata Home”.", doneT: "App installata!", done: "La trovi già nel menu delle app del telefono e nella schermata Home, con l'icona di Chess Coach. Non cercarla tra i file scaricati: aprila da lì come qualsiasi altra app.", ok: "Ho capito", hint: "Dopo l'installazione la trovi nel menu delle app, non tra i download." },
  en: { title: "Install Chess Coach", body: "Open it like an app, full screen.", install: "Install", later: "Not now", ios: "On iPhone: tap Share, then “Add to Home Screen”.", doneT: "App installed!", done: "You'll find it in your phone's app menu and on the Home screen, with the Chess Coach icon. Don't look in your downloaded files: open it from there like any other app.", ok: "Got it", hint: "After installing, find it in your app menu, not in downloads." },
  es: { title: "Instala Chess Coach", body: "Ábrelo como una app, a pantalla completa.", install: "Instalar", later: "Ahora no", ios: "En iPhone: toca Compartir y luego “Añadir a pantalla de inicio”.", doneT: "¡App instalada!", done: "Ya la tienes en el menú de apps del teléfono y en la pantalla de inicio, con el icono de Chess Coach. No la busques en los archivos descargados: ábrela desde ahí como cualquier otra app.", ok: "Entendido", hint: "Tras instalarla, la encontrarás en el menú de apps, no en descargas." },
} as const;

/** Registra il service worker e propone l'installazione (Android/Chrome: pulsante; iPhone: istruzioni). */
export default function Pwa({ lang }: { lang: "it" | "en" | "es" }) {
  const [evt, setEvt] = useState<any>(null);
  const [ios, setIos] = useState(false);
  const [hide, setHide] = useState(true);
  const [done, setDone] = useState(false);
  const t = TXT[lang];

  useEffect(() => {
    if ("serviceWorker" in navigator && location.protocol === "https:") navigator.serviceWorker.register("/sw.js").catch(() => {});
    const standalone = window.matchMedia("(display-mode: standalone)").matches || (navigator as any).standalone;
    let dismissed = "";
    try { dismissed = localStorage.getItem("pwa-dismissed") || ""; } catch {}
    const on2 = () => { setEvt(null); setDone(true); setHide(false); try { localStorage.setItem("pwa-dismissed", "1"); } catch {} };
    window.addEventListener("appinstalled", on2);
    if (standalone || dismissed) return;
    const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent) && !(window as any).MSStream;
    if (isIos) { setIos(true); setHide(false); }
    const on = (e: Event) => { e.preventDefault(); setEvt(e); setHide(false); };
    window.addEventListener("beforeinstallprompt", on);
    return () => window.removeEventListener("beforeinstallprompt", on);
  }, []);

  const close = () => { setHide(true); try { localStorage.setItem("pwa-dismissed", "1"); } catch {} };
  const install = async () => { if (!evt) return; evt.prompt(); const r = await evt.userChoice.catch(() => null); setEvt(null); if (r && r.outcome === "accepted") { setDone(true); } else close(); };
  if (done) return (
    <div className="pwa" role="dialog" aria-label={t.doneT}>
      <img src="/icon-192.png" alt="" width="44" height="44" />
      <div><b>{t.doneT}</b><div className="small muted">{t.done}</div></div>
      <div className="row"><button className="btn btn-primary btn-sm" onClick={() => { setDone(false); setHide(true); }}>{t.ok}</button></div>
    </div>
  );
  if (hide || (!evt && !ios)) return null;
  return (
    <div className="pwa" role="dialog" aria-label={t.title}>
      <img src="/icon-192.png" alt="" width="44" height="44" />
      <div><b>{t.title}</b><div className="small muted">{evt ? t.body : t.ios} {t.hint}</div></div>
      <div className="row">{evt && <button className="btn btn-primary btn-sm" onClick={install}>{t.install}</button>}<button className="btn btn-sm" onClick={close}>{t.later}</button></div>
    </div>
  );
}
