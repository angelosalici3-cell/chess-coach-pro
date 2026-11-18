"use client";
import { useEffect } from "react";

/** Se l'indirizzo contiene ?ref=CODICE (link di un creatore o di una community), lo ricorda per 30 giorni
 *  e conta il clic. Il codice viene collegato all'account dopo l'accesso (vedi app.tsx). */
export default function RefCapture() {
  useEffect(() => {
    const code = (new URLSearchParams(window.location.search).get("ref") || "").trim().toUpperCase();
    if (!/^[A-Z0-9_-]{3,24}$/.test(code)) return;
    try {
      localStorage.setItem("ref", JSON.stringify({ code, t: Date.now() }));
      if (localStorage.getItem("ref-clicked") !== code) {
        localStorage.setItem("ref-clicked", code);
        fetch(process.env.NEXT_PUBLIC_API_URL + "/promo/click", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code }), keepalive: true }).catch(() => {});
      }
    } catch {}
  }, []);
  return null;
}
