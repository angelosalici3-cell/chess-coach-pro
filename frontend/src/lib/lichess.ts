// Gioco su Lichess dall'app: accesso OAuth (PKCE, senza segreti) e Board API. Il token resta nel browser dell'utente.
const BASE = "https://lichess.org";
const CLIENT_ID = "elorise-app";
const TOK = "li:tok";
const VER = "li:ver";

export const redirectUri = () => `${location.origin}/dashboard/play`;

const b64 = (buf: ArrayBuffer) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const rand = () => b64(crypto.getRandomValues(new Uint8Array(32)).buffer);

export function getToken(): string | null { try { return localStorage.getItem(TOK); } catch { return null; } }
export function clearToken() { try { localStorage.removeItem(TOK); } catch {} }

/** Apre la pagina di Lichess dove l'utente autorizza "giocare partite con la Board API". */
export async function startAuth() {
  const verifier = rand(), state = rand();
  try { sessionStorage.setItem(VER, JSON.stringify({ verifier, state })); } catch {}
  const challenge = b64(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)));
  const q = new URLSearchParams({ response_type: "code", client_id: CLIENT_ID, redirect_uri: redirectUri(), scope: "board:play", code_challenge_method: "S256", code_challenge: challenge, state });
  location.href = `${BASE}/oauth?${q}`;
}

/** Al ritorno da Lichess: scambia il codice con il token. */
export async function finishAuth(code: string, state: string): Promise<boolean> {
  let saved: any = null;
  try { saved = JSON.parse(sessionStorage.getItem(VER) || "null"); sessionStorage.removeItem(VER); } catch {}
  if (!saved || saved.state !== state) return false;
  const r = await fetch(`${BASE}/api/token`, {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ grant_type: "authorization_code", code, code_verifier: saved.verifier, redirect_uri: redirectUri(), client_id: CLIENT_ID }),
  });
  if (!r.ok) return false;
  const d = await r.json();
  try { localStorage.setItem(TOK, d.access_token); } catch { return false; }
  return true;
}

export async function revoke() {
  const t = getToken();
  if (t) { try { await fetch(`${BASE}/api/token`, { method: "DELETE", headers: { Authorization: `Bearer ${t}` } }); } catch {} }
  clearToken();
}

const auth = (t: string) => ({ Authorization: `Bearer ${t}` });
export const account = async (t: string) => { const r = await fetch(`${BASE}/api/account`, { headers: auth(t) }); if (!r.ok) throw new Error(String(r.status)); return r.json(); };

/** Legge una risposta a righe JSON (NDJSON) man mano che arriva. */
export async function* ndjson(res: Response): AsyncGenerator<any> {
  if (!res.body) return;
  const rd = res.body.getReader(), dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await rd.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i: number;
    while ((i = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
      if (line) { try { yield JSON.parse(line); } catch {} }
    }
  }
}

export const openEvents = (t: string, signal: AbortSignal) => fetch(`${BASE}/api/stream/event`, { headers: auth(t), signal });
export const openGame = (t: string, id: string, signal: AbortSignal) => fetch(`${BASE}/api/board/game/stream/${id}`, { headers: auth(t), signal });

/** Cerca un avversario: la richiesta resta aperta finché Lichess ne trova uno (la partita arriva dal flusso eventi). Solo ritmi rapid/classical. */
export const seek = (t: string, o: { time: number; inc: number; rated: boolean; ratingRange?: string }, signal: AbortSignal) => {
  const body = new URLSearchParams({ rated: String(o.rated), time: String(o.time), increment: String(o.inc), variant: "standard", color: "random" });
  if (o.ratingRange) body.set("ratingRange", o.ratingRange);
  return fetch(`${BASE}/api/board/seek`, { method: "POST", signal, headers: { ...auth(t), "Content-Type": "application/x-www-form-urlencoded" }, body });
};

/** Testo dell'errore restituito da Lichess (corpo JSON {error: ...}), se c'è. */
export async function errText(r: Response): Promise<string> {
  try { const d = await r.clone().json(); const e = d?.error; return typeof e === "string" ? e : e ? Object.values(e).flat().join(" ") : ""; } catch { return ""; }
}

const act = (t: string, path: string) => fetch(`${BASE}/api/board/game/${path}`, { method: "POST", headers: auth(t) });
export const sendMove = (t: string, id: string, uci: string) => act(t, `${id}/move/${uci}`);
export const resign = (t: string, id: string) => act(t, `${id}/resign`);
export const abort = (t: string, id: string) => act(t, `${id}/abort`);
export const draw = (t: string, id: string, yes: boolean) => act(t, `${id}/draw/${yes ? "yes" : "no"}`);
