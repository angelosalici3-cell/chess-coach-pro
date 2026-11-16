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

## Atlante delle aperture (`/dashboard/openings`)
- I dati sono il database pubblico di Lichess (`lichess-org/chess-openings`, licenza CC0, circa 3.500 linee).
- `frontend/scripts/build-openings.mjs` lo scarica e genera `public/openings.json`; parte da solo prima di `next build` (script `prebuild`), quindi su Vercel i dati completi arrivano al deploy.
- Il file `public/openings.json` incluso nel repository è un **seed di 60 aperture** per far funzionare la pagina anche in locale (`npm run openings` per scaricare quello completo).
- Se il download fallisce durante la build, resta il file esistente.
