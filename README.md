# Chess Coach Pro
- `backend/`  FastAPI (Render/Railway). Root directory: `backend`. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- `frontend/` Next.js (Vercel). Root directory: `frontend`
- `supabase/` migrazioni SQL da eseguire in ordine nel SQL Editor (001, poi 002)
- `.github/workflows/sync.yml` sincronizzazione notturna

Rotte del sito: `/` landing, `/login`, `/dashboard/*` app.
Il nome del prodotto si cambia in `frontend/src/lib/brand.ts`.

## Modello AI
Il modello Gemini in uso è `gemini-3.5-flash` (variabile `GEMINI_MODEL` su Render). Il piano Free usa `GEMINI_MODEL_FREE` (default `gemini-3.5-flash-lite`, più economico; se il nome non esiste o fallisce si usa `GEMINI_MODEL`).

## Login social, reset password, legale
- Login con Google e Discord (Supabase Auth): vedi la guida di setup nella chat/documentazione; callback `https://<progetto>.supabase.co/auth/v1/callback`.
- Reset password: `/login` → "Password dimenticata?" → email → `/reset-password`.
- Pagine legali `/privacy` e `/terms`: completa `frontend/src/lib/legal.ts` e segui `LEGAL-CHECKLIST.md`.

## Atlante delle aperture (`/dashboard/openings`)
- I dati sono il database pubblico di Lichess (`lichess-org/chess-openings`, licenza CC0, circa 3.500 linee).
- `frontend/scripts/build-openings.mjs` lo scarica e genera `public/openings.json`; parte da solo prima di `next build` (script `prebuild`), quindi su Vercel i dati completi arrivano al deploy.
- Il file `public/openings.json` incluso nel repository è un **seed di 60 aperture** per far funzionare la pagina anche in locale (`npm run openings` per scaricare quello completo).
- Se il download fallisce durante la build, resta il file esistente.

## Allenamento, puzzle, scudi e analisi del tempo

1. Supabase → SQL editor: esegui `supabase/003_training.sql` (dopo 001 e 002).
2. GitHub → Settings → Secrets → Actions: aggiungi `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` e (facoltativo) `HF_TOKEN`.
3. GitHub → Actions → **import-puzzles** → Run workflow (scarica il database ufficiale Lichess, CC0, e importa ~5.000 puzzle; HF_TOKEN non serve più).
4. Per l'analisi del tempo servono i clock: in Impostazioni premi "Risincronizza 100 partite".
5. Atlante: "Le mie aperture" usa le ultime 400 partite sincronizzate.

## Prezzi e piani (v2)
Free 3 lezioni/mese · Plus €3,99 · Pro €6,99 · Elite €12,99. Esegui `supabase/004_free_3_lessons.sql`.
In Stripe crea **nuovi Price** (3,99 / 6,99 / 12,99 mensili) e aggiorna `STRIPE_PRICE_PLUS/PRO/ELITE` su Render. Gli abbonati esistenti restano sul prezzo vecchio finché non li migri.

## Storico per piano
Esegui `supabase/005_history.sql`. Free 50 partite, Plus 200, Pro 500, Elite 1000 per account collegato: l'import parte da solo al collegamento e si amplia dopo un upgrade (pulsante "Importa lo storico del tuo piano"). Le partite storiche alimentano grafico rating, atlante e statistiche; l'analisi con motore resta in coda.

## Guida / onboarding
Al primo accesso (una volta per utente, in /dashboard) si apre da sola una guida di 9 passi; si riapre sempre dal pulsante "Guida" (menu laterale e barra in alto su mobile). Testi in `frontend/src/lib/onboarding-copy.ts`.

## App installabile (PWA)
`public/manifest.webmanifest`, `public/sw.js`, `public/offline.html` e le icone (`icon-192/512`, `maskable-512`, `apple-touch-icon`). Il service worker non mette in cache API, login o dati personali: serve solo per l'installazione e per la pagina offline. Su Android/Chrome compare un banner "Installa"; su iPhone le istruzioni "Condividi → Aggiungi alla schermata Home". Serve HTTPS (su Vercel c'è già). Test: Chrome → DevTools → Application → Manifest / Lighthouse "PWA". Per gli store: PWA impacchettata con Bubblewrap/PWABuilder (Google Play).

## Carte collezionabili e scudi delle aperture
1. Esegui `supabase/006_cards.sql`.
2. Le carte si assegnano da sole quando apri Allenamento → Carte (obiettivi in `backend/app/cardlogic.py`): prima vittoria con 10+ mosse a testa, prima partita con precisione ≥95%, matto lampo, senza macchia, da maestro, ammazzagiganti, capolavoro e una carta per ogni scudo di apertura (bronzo/argento/oro). Servono partite già analizzate.
3. La partita si rigioca dentro la carta (canvas). Da "Condividi" si crea GIF animata, video (MP4/WebM) o immagine; sul telefono si apre il foglio di condivisione, sul computer il file viene scaricato.
4. Scudi delle aperture: 12 linee di massimo 10 semimosse (5 mosse per lato), 3 / 10 / 25 vittorie. Le linee sono in `cardlogic.py`: aggiungine altre nella lista `OPENINGS` e i nomi in `train-copy.ts` (`OPEN_NAMES`).
5. Ogni scudo conquistato ha il pulsante Condividi (immagine 4:5 per storie e post).

### Carte senza attese
Le carte vengono assegnate dal backend subito dopo l'analisi di una partita. L'app controlla `/me` (campo `new_cards`) all'apertura e ogni minuto: se c'è una carta nuova mostra la celebrazione con la preview statica e prepara in sottofondo GIF e immagine (cache nel browser), così "Condividi" è immediato. Il video si crea al momento perché si registra in tempo reale.

## Nuovi obiettivi delle carte (rimonta, mossa brillante, serie, ore)
- Esegui in Supabase `supabase/007_highlights.sql` (dopo la 006): aggiunge `games.highlights`.
- Nuove carte: serie di vittorie (totali, Bianco, Nero), prima vittoria con una nuova apertura, vittoria lampo precisa (<20 mosse, precisione >90% / >96%), vittoria all'ultimo secondo (usa gli orologi), rivincita contro lo stesso avversario, rimonta (da -3 / -6 pedoni), mossa brillante (badge "!!" sulla scacchiera e pausa nella GIF), traguardi di ore giocate per ritmo (2/10/40 ore, uguali per ogni ritmo).
- Rimonta e mossa brillante usano le valutazioni già salvate in `moves.eval_cp`: nessun costo motore in più. Per le vecchie partite i dati vengono calcolati 15 partite per volta a ogni apertura dell'album. La mossa brillante è un'euristica (sacrificio di materiale che l'engine conferma valido).
- Per partite senza orologi la durata è stimata (60% del tempo a disposizione); la vittoria all'ultimo secondo richiede gli orologi (risincronizza le partite vecchie).

## Codici promo per creatori e community (con tracciamento)
1. Esegui in Supabase `supabase/008_promo.sql` (dopo la 007).
2. Su Render aggiungi la variabile `ADMIN_EMAILS` con la tua email (più indirizzi separati da virgola). Solo loro vedono "Codici promo" nel menu.
3. Dal pannello **Codici promo** crei un codice per ogni creatore o gruppo: nome, canale, sconto %, mesi di sconto e percentuale concordata. Lo sconto viene creato su Stripe in automatico (con sconto 0 il codice serve solo a tracciare).
4. Mandi al creatore il link `https://tuosito/?ref=CODICE` (pulsante "Copia link"). Chi lo apre: il clic viene contato; dopo la registrazione il codice si lega all'account; al pagamento lo sconto è già applicato.
5. Il pannello mostra per codice: clic, iscritti, paganti, incassi (primo pagamento più rinnovi) e importo da riconoscere. Chi scrive il codice a mano nella pagina di pagamento Stripe viene tracciato lo stesso.
- Il primo link aperto vale per l'iscrizione (prima attribuzione) e dura 30 giorni nel browser.
- I dati sono al lordo di IVA e commissioni Stripe: verifica gli importi prima di pagare un creatore.
- Alla cancellazione dell'account l'email viene tolta dagli eventi promo; restano solo i conteggi.

## Menu laterale e lezioni sulle imprecisioni
- Il menu a scomparsa (hamburger, in alto a sinistra; su desktop il pulsante "Menu" nella barra laterale) raccoglie consumi AI, scadenza, dati e gestione account, manuale e lingua. La barra in basso resta solo con le funzioni (Home, Partite, Lezioni, Aperture, Allenamento).
- Nessun SQL da eseguire. Backend: nuovo endpoint `POST /games/{id}/moves/{ply}/lesson` (lezione GM anche per le imprecisioni), `/me` restituisce `renews` e `member_since`.

## Velocità di apertura
- Backend: `/me` esegue le query in parallelo; token verificato e `/me`/`/stats` messi in cache per pochi secondi (`app/cache.py`, si svuota dopo sync, lezioni, piano, profili).
- Frontend: all'apertura mostra subito gli ultimi dati salvati (localStorage `c:*`) e li aggiorna appena arrivano.
- Su Render **Free** il server si addormenta dopo ~15 minuti e la prima richiesta impiega 30–60 secondi: tieni sveglio `/health` con un ping ogni 5–10 minuti (UptimeRobot/cron-job.org) oppure passa a un piano a pagamento. Metti Render e Supabase nella stessa regione.
