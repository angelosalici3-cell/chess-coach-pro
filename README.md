# EloRise
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
Free 3 lezioni/mese · Plus €4,99 · Pro €8,99 · Elite €14,99 (annuali 49 / 89 / 149). Esegui `supabase/004_free_3_lessons.sql`.
In Stripe crea i **Price** con `python -m scripts.create_stripe_prices` (vedi sotto) e imposta `STRIPE_PRICE_PLUS/PRO/ELITE` e le versioni `_YEAR` su Render. Gli abbonati esistenti restano sul prezzo vecchio finché non li migri.

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

## Aggiornamento: lezioni, carte, analisi iniziale, intro
- **Lezioni GM:** la lezione si genera prima e la quota si scala solo a lezione salvata. Se Gemini è sovraccarico (429/503) l'app lo dice e non conta nulla. Gli errori veri si leggono nei log di Render (cerca "GM"). Le lezioni sono nella tabella `errori_utenti` (colonne `gm_lesson`, `gm_lesson_at`).
- **Carte:** carosello con filtro per rarità. Nuove carte "Vittoria contro un X+" per ritmo, da 100 a 100 punti, a partire dal rating della prima partita di quel ritmo (nessun SQL da eseguire).
- **Analisi iniziale:** dopo il collegamento di un account (e dopo un upgrade) si scaricano le partite e si analizzano le più recenti garantite dal piano (`initial_games` in `backend/core/plans.py`: Free 20, Plus 50, Pro 100, Elite 150). Il banner in Home mostra avanzamento e tempo stimato (`/onboarding/status`).
- **Intro:** cerchio attorno al logo e portone che si apre quando i dati sono pronti (`components/Intro.tsx`).

## Email (verifica, benvenuto, grazie abbonamento)
1. **Resend** (resend.com, piano gratuito 3.000 mail/mese): aggiungi il tuo dominio, inserisci i record DNS che ti mostra, crea una API key.
2. **Render**: `RESEND_API_KEY`, `MAIL_FROM` (es. `EloRise <ciao@tuodominio.it>`), `EMAIL_VIDEO_URL` (link YouTube del video, anche "non in elenco"). Opzionale `EMAIL_VIDEO_THUMB` per un'immagine di anteprima tua.
3. **Supabase SQL**: esegui `supabase/010_email_log.sql`.
4. **Verifica account**: Supabase > Authentication > Providers > Email: attiva "Confirm email". Authentication > Emails > SMTP Settings: host `smtp.resend.com`, porta 465, utente `resend`, password = la API key, mittente = `MAIL_FROM`. Poi Templates > "Confirm signup": incolla `supabase/email-templates/confirm-signup.html`.
5. **Benvenuto con piani e video**: parte da sola, una volta, al primo accesso dopo l'attivazione (anche per chi entra con Google). **Grazie per l'abbonamento**: parte dal webhook Stripe a ogni nuovo abbonamento.
6. Anteprima senza inviare: da `backend/` `python -m scripts.preview_emails` crea i file HTML in `email-preview/`.

## Stripe in modalità test
1. dashboard.stripe.com: interruttore **Modalità test** in alto a destra.
2. Developers > API keys: copia la **Secret key** `sk_test_...` in `STRIPE_SECRET_KEY` su Render.
3. Crea i prezzi: da `backend/` `STRIPE_SECRET_KEY=sk_test_... python -m scripts.create_stripe_prices` e copia le 6 righe `STRIPE_PRICE_*` su Render.
4. Developers > Webhooks > Add endpoint: URL `https://TUO-BACKEND.onrender.com/billing/webhook`, eventi `checkout.session.completed`, `invoice.paid`, `customer.subscription.deleted`. Copia il **Signing secret** `whsec_...` in `STRIPE_WEBHOOK_SECRET`.
5. Settings > Billing > Customer portal: attiva e salva (serve per "Gestisci abbonamento").
6. Redeploy di Render, poi paga con la carta di prova `4242 4242 4242 4242`, scadenza futura, CVC qualsiasi.
7. Controlli: tabella `config_utenti` (tier cambiato), `storico_abbonamenti`, `email_log` (riga `sub:...`) e l'email ricevuta. Rinnovo: nel dettaglio dell'abbonamento in Stripe usa i test clock oppure "Run simulation".
8. Per passare al reale: chiave `sk_live_`, ripeti i punti 3 e 4 in modalità live e sostituisci le variabili.

## Sincronizzazione notturna in due fasi
- **Fase 1, download** (`sync.yml`, 02:00 UTC): chiama `/cron/sync` su Render. Scarica fino a 200 partite nuove per account (prima erano 15), solo download, veloce.
- **Fase 2, analisi** (`analyze.yml`, 02:30 UTC): gira su GitHub Actions, non su Render, quindi non si interrompe quando il server si addormenta. Analizza **tutte** le partite in attesa degli abbonati, a giri equi tra utenti (Elite e Pro per primi, le partite più recenti prima), con 3 analisi in parallelo e un massimo di 5 ore. Quello che resta si riprende la notte dopo.
- Secrets GitHub richiesti: `API_URL`, `CRON_SECRET` (fase 1), `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (fase 2). Per provare subito: Actions > nightly-analysis > Run workflow.
- Il pulsante "Sincronizza partite" resta per chi vuole subito le partite appena giocate.

## Revisione dell'interfaccia (v3)
- **Menù a 5 voci**: Home, Partite (con le Lezioni GM come seconda scheda), Aperture, Allenamento, Premi (Carte e Traguardi). I vecchi indirizzi `/dashboard/lessons` e `/dashboard/train?tab=cards|badges` reindirizzano alla scheda nuova.
- **Grafici**: si disegnano alla larghezza reale dello schermo, con assi a 13 px, anche su telefono. Nuovo grafico "Chi sta meglio" nella partita, con la **mossa critica** segnata e un riquadro che la spiega (la tua mossa che ha fatto perdere più valutazione, se supera 1 pedone).
- **Partite**: riepilogo, punti deboli, filtri (risultato, colore, ritmo, ricerca), raggruppamento per giorno, errori per partita. `/games` ora restituisce esito, ritmo ed errori già calcolati (fino a 300 partite).
- **Account duplicato in Home**: i nomi utente ora si raggruppano senza distinguere maiuscole. Se vedi ancora due account, esiste davvero un profilo Chess.com con quel nome: toglilo da Account scacchi (o con l'SQL qui sotto).
```sql
select id, piattaforma, username from profili_scacchi where user_email = 'TUA_EMAIL';
-- elimina il profilo sbagliato e le sue partite
delete from games where user_email = 'TUA_EMAIL' and source = 'chesscom';
delete from profili_scacchi where user_email = 'TUA_EMAIL' and piattaforma = 'chesscom';
```

## Partite "senza errori" analizzate male (v3.1)

Se il motore non rispondeva (limite di richieste), la mossa contava come perfetta e la partita risultava al 100% senza errori. Ora una partita con troppe valutazioni mancanti non viene salvata e resta "da analizzare" per il giro successivo.
Per rianalizzare quelle già salvate male, in Supabase (SQL editor):

```sql
update games set analyzed_at = null, accuracy_user = null
where user_email = 'TUA_EMAIL' and analyzed_at is not null and accuracy_user >= 99;
```

## Schemi di errore personali (v3.2)

Home mostra la scheda "Il tuo schema di errore": dalle partite analizzate (almeno 30) l'app cerca dove l'utente sbaglia più del suo normale
(vantaggio, poco tempo, fase, colore, ritmo, pezzo mosso, apertura, subito dopo una sconfitta). Un errore è una perdita di almeno 15 punti di
probabilità di vittoria, e non conta se la mossa giocata è uguale alla migliore. Il calcolo è in `backend/app/patterns.py` (nessuna IA, nessuna
nuova tabella); il risultato resta in memoria 10 minuti per utente. "Allenati su questo" apre il ripasso solo con gli errori di quello schema
(`/train/mistakes/next?tag=...`). Per vedere cosa emerge su un account senza aprire l'app: workflow `pattern-probe`.

## Memoria condivisa delle valutazioni (v3.3)

`eval_cache` (SQL `supabase/011_eval_cache.sql`) tiene una riga per posizione (4 campi del FEN) con valutazione e miglior mossa.
`engine.analyze_game` la legge prima di chiamare il motore e vi salva le valutazioni nuove (senza sovrascrivere quelle già presenti,
anche se arrivano da una fonte più profonda). Così le aperture comuni, le partite di giocatori già aggiunti da altri utenti e le partite
tra due utenti dell'app si analizzano una volta sola. Nel log dell'analisi ogni partita riporta "posizioni N, dalla memoria M, dal motore K".
Finché la tabella non esiste, l'analisi funziona come prima.
Sonda sul dataset Lichess/chess-position-evaluations: workflow `lichess-eval-probe` (copertura, segno delle valutazioni, ordinamento).

## Stockfish in locale nell'analisi notturna (v3.4)

`engine.py` usa il Stockfish installato (`STOCKFISH_PATH` o nel PATH) invece di chess-api.com: nessun limite di richieste, profondità 16 invece di 12
(`LOCAL_DEPTH`, tetto `LOCAL_TIME` secondi per posizione). Se il motore non c'è (come sul server Render) o fallisce, si usa il servizio esterno come prima.
`analyze.yml` lo installa con apt. In `eval_cache` ogni posizione ha la sua profondità: con il motore locale si riusano solo valutazioni da almeno
`LOCAL_DEPTH − 2` e quelle più profonde sostituiscono le superficiali (funzione SQL `eval_cache_put`, in `supabase/011_eval_cache.sql`: rieseguilo).
Le analisi fatte sul server (primo caricamento di un utente) restano a profondità 12.

## v3.7 – Nuovo nome: EloRise
- Il nome è in un solo posto: `frontend/src/lib/brand.ts` (`BRAND`, `SUPPORT`). Il logo scrive "Elo" in bianco e "Rise" in arancio (`Wordmark` in `Logo.tsx`).
- Sostituito "EloRise" in app, PWA (manifest, offline), email (`mailer.py`), titolo API, User-Agent, template Supabase, nomi file e hashtag di condivisione.
- Da fare a mano: acquistare `elorise.app`, impostare `FRONTEND_URL`, `MAIL_FROM` ("EloRise <noreply@elorise.app>") e `MAIL_REPLY_TO` (Vercel/Render), verificare il dominio su Resend, creare la casella `support@elorise.app` (compare nello User-Agent verso Lichess/Chess.com) e rinominare il template email su Supabase (Auth > Email Templates, incolla `supabase/email-templates/confirm-signup.html`).
- Stripe: i prodotti già creati si rinominano dalla dashboard (lo script cambia solo i nuovi).
- Home: scacchiera giocabile (`PlayBoard.tsx`, testi in `lib/play-copy.ts`). Il Coach commenta ogni mossa del Bianco; il Nero risponde con una euristica semplice. Il punteggio mostrato è dimostrativo.

## v3.8 – Sincronizza che analizza + nuovo logo
- **Sincronizza** ora scarica, mostra "Scaricate N nuove partite" e le analizza subito con un contatore reale ("Analizzo 3 di 8"). Endpoint `GET /sync/status`. Free: 3 partite per clic, piani a pagamento: fino a 40.
- **Contatore fermo (43/50):** le partite non analizzate venivano ritentate all'infinito se il motore online falliva. Ora ogni partita fallita si riprova una volta, poi si ferma per 30 minuti e l'app dice quante sono e perché (testo dell'errore). Un nuovo clic su Sincronizza le riprova tutte.
- **Motore sul server (consigliato):** `backend/scripts/get_stockfish.sh` scarica Stockfish durante la build su Render. Build Command: `pip install -r requirements.txt && bash scripts/get_stockfish.sh`; variabile `STOCKFISH_PATH` = percorso stampato nell'ultima riga del log (`.../backend/bin/stockfish`). Script non provato qui: controlla il log di build.
- **Logo nuovo:** un pedone che sale una scalinata di case della scacchiera. Cartella `brand/`: icona, marchio a colori, in nero, in bianco, a due colori, e lockup con "EloRise" già trasformato in tracciati. File dell'app (icon, apple-touch, maskable, og) rigenerati.

## v3.9 – Home in diretta, gioco su Lichess, analisi sul server
- **Home:** partita automatica dell'Opera di Parigi con il commento del Gran Maestro "in diretta" mossa per mossa (`LiveBoard.tsx`, testi IT/EN/ES in `lib/live-copy.ts`): chat che si scrive da sola, emoji, etichette (Sacrificio!, Brillante!!, Matto!), barra della tensione, pausa/ripeti. Con "riduci animazioni" resta fissa.
- **Gioca su Lichess** (`/dashboard/play`, voce "Gioca" nel menu): accesso OAuth con PKCE (nessun segreto, nessuna registrazione: `client_id` = `elorise-app`), ricerca avversario con la Board API di Lichess, partita giocabile con orologi, abbandono/patta/annulla. Solo rapid e classical (10+0, 15+10, 30+0): sono i ritmi consentiti da Lichess alle app esterne. Il token resta nel browser. A fine partita "Analizza con EloRise" scarica e analizza. Durante la partita nessun aiuto del motore (regola Lichess). Redirect: `<tuo dominio>/dashboard/play` (nessuna configurazione su Lichess).
- **Analisi delle partite appena caricate:** la causa più probabile è il servizio online di analisi che rifiuta le richieste dal server (limiti). Il messaggio d'errore ora lo dice. Soluzione: Stockfish sul server.
  - Render Python: Build Command `pip install -r requirements.txt && bash scripts/get_stockfish.sh`, variabili `LOCAL_DEPTH=12`, `LOCAL_TIME=0.8`, `LOCAL_HASH=32` (il percorso `backend/bin/stockfish` si trova da solo).
  - In alternativa: `backend/Dockerfile` (Render > Web Service > Docker, Root Directory `backend`), Stockfish incluso.

## v3.10 — menu nuovo, home, installazione, diagnostica

**Cosa cambia**
- Menu a 5 voci: Home · Analisi (Partite + Aperture) · **Gioca** (pulsante centrale in evidenza) · Allenati · Premi.
- Home: "Missione di oggi" in 3 passi (gioca, ripassa gli errori, studia una lezione) con serie di giorni.
- Scacchiera della home più piccola, 3 partite commentate in rotazione (Opera di Parigi, matto di Légal, matto del barbiere), emoji di reazione sulla casa di arrivo, badge "!!" ingrandito.
- Logo allineato alle voci del menu.
- Installazione: voce "Installa l'app" nel menu, banner che ritorna dopo 3 giorni, avviso "Nuova versione pronta" con pulsante Aggiorna (service worker v2).
- Pagina **/dashboard/diag** (menu → Stato analisi): controlla colonne, motore, servizi.
- Dopo la sincronizzazione compare l'errore di download, se c'è.

**Da fare tu**
1. Supabase → SQL Editor: esegui `supabase/012_analysis_depth.sql` (e 011 se non l'hai fatto). È la causa più probabile delle analisi ferme.
2. Rilancia backend e frontend. Su Render imposta Build Command `pip install -r requirements.txt && bash scripts/get_stockfish.sh` e variabili `LOCAL_DEPTH=12 LOCAL_TIME=0.8 LOCAL_HASH=32`.
3. Apri Menu → Stato analisi e controlla che tutte le righe siano verdi.
4. Icona nuova: chi ha già installato l'app deve disinstallarla e reinstallarla.
