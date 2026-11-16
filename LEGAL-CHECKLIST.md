# Checklist legale prima di incassare

I testi in `frontend/src/lib/legal.ts` sono bozze complete ma **non sono una consulenza legale**: fatti rivedere da un avvocato o da un consulente privacy almeno una volta.

## 1. Dati da completare (obbligatorio)
In `frontend/src/lib/legal.ts`, oggetto `ENTITY`: nome/ragione sociale, indirizzo, P.IVA o codice fiscale. Finché c'è "DA COMPLETARE" le pagine /privacy e /terms mostrano l'avviso di bozza. Aggiorna anche `SUPPORT` in `src/lib/brand.ts` con una email vera.

## 2. Stripe (Dashboard)
- Settings → Business → Public details: inserisci URL Termini `https://TUO-SITO/terms` e Privacy `https://TUO-SITO/privacy`.
- Attiva la casella obbligatoria "accetto i Termini" nel checkout: variabile Render `STRIPE_TERMS_CHECKBOX=1` (richiede l'URL dei Termini nelle impostazioni Stripe).
- Settings → Tax: configura IVA (Stripe Tax o manuale) con il tuo commercialista.
- Billing → Customer portal: attiva disdetta abbonamento e aggiornamento metodo di pagamento.

## 3. Fornitori (DPA)
Accetta/archivia i Data Processing Agreement di Supabase, Vercel, Render, Stripe, Google (Gemini). Sono nei rispettivi pannelli/pagine legali, di solito si accettano con un click.
Controlla la regione: Supabase e Render in UE (Francoforte) se possibile.
Verifica sui termini di Gemini API che il piano in uso non usi i tuoi dati per addestrare i modelli (il piano a pagamento di solito non lo fa).

## 4. Registro dei trattamenti
Un documento interno (anche un foglio) con: dati trattati, finalità, fornitori, tempi di conservazione. Puoi ricavarlo dalla sezione 2–7 della privacy.

## 5. Aspetti fiscali
Partita IVA o forma giuridica adeguata, fatturazione/ricevute per gli abbonamenti, regime IVA OSS per vendite a consumatori UE: parlane con un commercialista prima del primo incasso.

## 6. Decisioni da prendere
- Età minima: ora 14 anni (Italia/Spagna). Alzala a 16 in `ENTITY.minAge` per stare tranquillo in tutta l'UE.
- Se aggiungi analytics o pixel pubblicitari: serve un banner di consenso e va aggiornata la privacy.
- Il foro: i termini scelgono la legge italiana; i consumatori mantengono sempre il foro del loro paese.

## 7. Account OAuth (Google/Discord)
Google Cloud → Schermata consenso OAuth: imposta "In produzione" e inserisci link a privacy e termini (stessi URL), altrimenti gli utenti vedono "app non verificata" e ci sono limiti di 100 utenti di prova.
