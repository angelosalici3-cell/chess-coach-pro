# Chess Coach Pro
- `backend/`  FastAPI (Render/Railway) — root directory: `backend`, start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- `frontend/` Next.js (Vercel) — root directory: `frontend`
- `supabase/` migrazioni SQL da eseguire nel SQL Editor
Sviluppo locale: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload` e `cd frontend && npm install && npm run dev`.
