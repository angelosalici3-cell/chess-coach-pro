"use client";
import { useEffect, useRef, useState } from "react";

const TXT = {
  it: { title: "Installa EloRise", body: "Aprilo come un'app, a schermo intero.", install: "Installa", later: "Non ora", ios: "Su iPhone: tocca Condividi e poi “Aggiungi alla schermata Home”.", generic: "Dal menu del browser (⋮) scegli “Installa app” o “Aggiungi a schermata Home”.", doneT: "App installata!", done: "La trovi nel menu delle app del telefono, con l'icona di EloRise. Aprila da lì come qualsiasi altra app.", ok: "Ho capito", hint: "Dopo l'installazione la trovi nel menu delle app, non tra i download.", upT: "Nuova versione pronta", upB: "Aggiorna", reinstall: "Già installata con la vecchia icona? Disinstallala e reinstallala per vedere quella nuova." },
  en: { title: "Install EloRise", body: "Open it like an app, full screen.", install: "Install", later: "Not now", ios: "On iPhone: tap Share, then “Add to Home Screen”.", generic: "From the browser menu (⋮) choose “Install app” or “Add to Home screen”.", doneT: "App installed!", done: "You'll find it in your phone's app menu with the EloRise icon. Open it from there like any other app.", ok: "Got it", hint: "After installing, find it in your app menu, not in downloads.", upT: "New version ready", upB: "Update", reinstall: "Installed with the old icon? Uninstall and reinstall to see the new one." },
  es: { title: "Instala EloRise", body: "Ábrelo como una app, a pantalla completa.", install: "Instalar", later: "Ahora no", ios: "En iPhone: toca Compartir y luego “Añadir a pantalla de inicio”.", generic: "En el menú del navegador (⋮) elige “Instalar app” o “Añadir a pantalla de inicio”.", doneT: "¡App instalada!", done: "La tienes en el menú de apps del teléfono, con el icono de EloRise. Ábrela desde ahí como cualquier otra app.", ok: "Entendido", hint: "Tras instalarla, la encontrarás en el menú de apps, no en descargas.", upT: "Nueva versión lista", upB: "Actualizar", reinstall: "¿Instalada con el icono antiguo? Desinstálala y vuelve a instalarla para ver el nuevo." },
} as const;
const SNOOZE = 3 * 864e5;

/** Service worker + installazione (Android/Chrome: pulsante; iPhone: istruzioni) + avviso di nuova versione.
 *  Il banner torna dopo 3 giorni e si può riaprire sempre dal menu ("Installa l'app"). */
export default function Pwa({ lang }: { lang: "it" | "en" | "es" }) {
  const [evt, setEvt] = useState<any>(null);
  const [ios, setIos] = useState(false);
  const [hide, setHide] = useState(true);
  const [done, setDone] = useState(false);
  const [standalone, setStandalone] = useState(false);
  const [update, setUpdate] = useState<ServiceWorker | null>(null);
  const evtRef = useRef<any>(null);
  const t = TXT[lang];

  useEffect(() => {
    const sa = window.matchMedia("(display-mode: standalone)").matches || !!(navigator as any).standalone;
    setStandalone(sa);
    if ("serviceWorker" in navigator && location.protocol === "https:") {
      navigator.serviceWorker.register("/sw.js").then((reg) => {
        const watch = (w: ServiceWorker | null) => w && w.addEventListener("statechange", () => { if (w.state === "installed" && navigator.serviceWorker.controller) setUpdate(w); });
        if (reg.waiting && navigator.serviceWorker.controller) setUpdate(reg.waiting);
        reg.addEventListener("updatefound", () => watch(reg.installing));
        reg.update().catch(() => {});
        const id = setInterval(() => reg.update().catch(() => {}), 30 * 60000);
        window.addEventListener("pagehide", () => clearInterval(id), { once: true });
      }).catch(() => {});
      let reloaded = false;
      navigator.serviceWorker.addEventListener("controllerchange", () => { if (reloaded) return; reloaded = true; location.reload(); });
    }
    let snoozed = 0;
    try { snoozed = Number(localStorage.getItem("pwa-snooze") || 0); } catch {}
    const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent) && !(window as any).MSStream;
    setIos(isIos);
    const on2 = () => { setEvt(null); evtRef.current = null; setDone(true); setHide(false); };
    const on = (e: Event) => { e.preventDefault(); evtRef.current = e; setEvt(e); if (!sa && Date.now() - snoozed > SNOOZE) setHide(false); };
    const open = () => { setDone(false); setHide(false); };   // dal menu: riapre sempre il banner
    window.addEventListener("appinstalled", on2);
    window.addEventListener("beforeinstallprompt", on);
    window.addEventListener("pwa-open", open);
    if (!sa && isIos && Date.now() - snoozed > SNOOZE) setHide(false);
    return () => { window.removeEventListener("appinstalled", on2); window.removeEventListener("beforeinstallprompt", on); window.removeEventListener("pwa-open", open); };
  }, []);

  const close = () => { setHide(true); try { localStorage.setItem("pwa-snooze", String(Date.now())); } catch {} };
  const install = async () => { const e = evtRef.current; if (!e) return; e.prompt(); const r = await e.userChoice.catch(() => null); setEvt(null); evtRef.current = null; if (r && r.outcome === "accepted") setDone(true); else close(); };
  const applyUpdate = () => { if (update) update.postMessage("SKIP_WAITING"); else location.reload(); };

  return (
    <>
      {update && (
        <div className="pwa-up" role="status">
          <img src="/icon-192.png" alt="" width="36" height="36" />
          <b>{t.upT}</b>
          <button className="btn btn-primary btn-sm" onClick={applyUpdate}>{t.upB}</button>
        </div>
      )}
      {done ? (
        <div className="pwa" role="dialog" aria-label={t.doneT}>
          <img src="/icon-192.png" alt="" width="44" height="44" />
          <div><b>{t.doneT}</b><div className="small muted">{t.done}</div></div>
          <div className="row"><button className="btn btn-primary btn-sm" onClick={() => { setDone(false); setHide(true); }}>{t.ok}</button></div>
        </div>
      ) : !hide && (
        <div className="pwa" role="dialog" aria-label={t.title}>
          <img src="/icon-192.png" alt="" width="44" height="44" />
          <div><b>{t.title}</b><div className="small muted">{evt ? t.body : ios ? t.ios : t.generic} {standalone ? "" : t.hint}<br />{t.reinstall}</div></div>
          <div className="row">{evt && <button className="btn btn-primary btn-sm" onClick={install}>{t.install}</button>}<button className="btn btn-sm" onClick={close}>{t.later}</button></div>
        </div>
      )}
    </>
  );
}
