# Chess Coach Pro
- `backend/`  FastAPI (Render/Railway). Root directory: `backend`. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- `frontend/` Next.js (Vercel). Root directory: `frontend`
- `supabase/` migrazioni SQL da eseguire in ordine nel SQL Editor (001, poi 002)
- `.github/workflows/sync.yml` sincronizzazione notturna

Rotte del sito: `/` landing, `/login`, `/dashboard/*` app.
Il nome del prodotto si cambia in `frontend/src/lib/brand.ts`.

## Modello AI
Il modello Gemini in uso è `gemini-3.5-flash` (variabile `GEMINI_MODEL` su Render; default nel codice già aggiornato).

## Login social, reset password, legale
- Login con Google e Discord (Supabase Auth): vedi la guida di setup nella chat/documentazione; callback `https://<progetto>.supabase.co/auth/v1/callback`.
- Reset password: `/login` → "Password dimenticata?" → email → `/reset-password`.
- Pagine legali `/privacy` e `/terms`: completa `frontend/src/lib/legal.ts` e segui `LEGAL-CHECKLIST.md`.
