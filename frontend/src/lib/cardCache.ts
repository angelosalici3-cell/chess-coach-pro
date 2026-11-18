/** Cache dei file già pronti (GIF e immagine di ogni carta): così il pulsante Condividi risponde subito.
 *  Sta in IndexedDB e, se il browser non la concede, almeno in memoria per la sessione. */
const mem = new Map<string, Blob>();
const DB = "cc-cards", ST = "files", MAX = 60;

function open(): Promise<IDBDatabase | null> {
  return new Promise((res) => {
    try {
      const r = indexedDB.open(DB, 1);
      r.onupgradeneeded = () => { const s = r.result.createObjectStore(ST, { keyPath: "key" }); s.createIndex("t", "t"); };
      r.onsuccess = () => res(r.result);
      r.onerror = () => res(null);
    } catch { res(null); }
  });
}

export async function getFile(key: string): Promise<Blob | null> {
  if (mem.has(key)) return mem.get(key)!;
  const db = await open(); if (!db) return null;
  return new Promise((res) => {
    try {
      const q = db.transaction(ST).objectStore(ST).get(key);
      q.onsuccess = () => { const b = q.result?.blob as Blob | undefined; if (b) mem.set(key, b); res(b || null); };
      q.onerror = () => res(null);
    } catch { res(null); }
  });
}

export async function putFile(key: string, blob: Blob): Promise<void> {
  mem.set(key, blob);
  const db = await open(); if (!db) return;
  try {
    const tx = db.transaction(ST, "readwrite"), st = tx.objectStore(ST);
    st.put({ key, blob, t: Date.now() });
    const cnt = st.count();
    cnt.onsuccess = () => {                       // tiene solo i file più recenti
      let extra = cnt.result - MAX;
      if (extra <= 0) return;
      st.index("t").openCursor().onsuccess = (e) => {
        const c = (e.target as IDBRequest<IDBCursorWithValue | null>).result;
        if (c && extra-- > 0) { c.delete(); c.continue(); }
      };
    };
  } catch { /* nessun problema: resta la copia in memoria */ }
}
