export async function api<T = any>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(process.env.NEXT_PUBLIC_API_URL + path, {
    ...init,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init.headers || {}) },
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || String(r.status));
  return r.json();
}
