import { BRAND, SUPPORT } from "./brand";
import type { Lang } from "./i18n";

/** ⚠️ COMPLETA QUESTI DATI prima di pubblicare. Finché c'è "DA COMPLETARE" le pagine mostrano un avviso di bozza. */
export const ENTITY = {
  name: "DA COMPLETARE (nome e cognome o ragione sociale)",
  address: "DA COMPLETARE (indirizzo completo)",
  taxId: "DA COMPLETARE (P.IVA / codice fiscale)",
  email: SUPPORT,
  country: "Italia",
  updated: "2026-11-16",
  minAge: 14, // 14 in Italia/Spagna; porta a 16 se vuoi essere cautelativo in tutta l'UE
};
export const isDraft = () => Object.values(ENTITY).some((v) => typeof v === "string" && v.includes("DA COMPLETARE"));

export type Section = { h: string; p?: string[]; ul?: string[] };
export type Doc = { title: string; intro: string; sections: Section[] };
const E = ENTITY;

const privacyIt: Doc = {
  title: "Informativa sulla privacy",
  intro: `Questa informativa spiega come ${BRAND} tratta i tuoi dati personali ai sensi del Regolamento (UE) 2016/679 (GDPR).`,
  sections: [
    { h: "1. Titolare del trattamento", p: [`${E.name}, ${E.address}, ${E.taxId}. Contatto privacy: ${E.email}.`] },
    { h: "2. Quali dati trattiamo", ul: [
      "Dati dell'account: email, password (conservata in forma cifrata dal nostro fornitore di autenticazione) e, se accedi con Google o Discord, nome e email forniti da quel servizio.",
      "Dati di gioco: i nomi utente che colleghi su Lichess e Chess.com e le tue partite pubbliche su quelle piattaforme (mosse, risultati, rating, aperture).",
      "Dati generati dal servizio: analisi del motore, errori rilevati, lezioni e risposte dell'AI, statistiche, utilizzo delle quote mensili.",
      "Dati di abbonamento: piano, stato, identificativo cliente Stripe. Non vediamo né conserviamo i dati della tua carta, che sono gestiti da Stripe.",
      "Dati tecnici: indirizzo IP e log di sicurezza presso i nostri fornitori di hosting.",
    ] },
    { h: "3. Perché li trattiamo e su quale base", ul: [
      "Fornirti il servizio (account, collegamento account scacchistici, analisi, lezioni AI): esecuzione del contratto.",
      "Gestire pagamenti e abbonamenti e adempiere agli obblighi fiscali e contabili: contratto e obbligo di legge.",
      "Sicurezza, prevenzione degli abusi e rispetto dei limiti d'uso: legittimo interesse.",
      "Comunicazioni di servizio (conferma email, reimpostazione password, avvisi sull'abbonamento): contratto.",
    ], p: ["Non usiamo i tuoi dati per pubblicità né li vendiamo. Non prendiamo decisioni automatizzate che producano effetti giuridici su di te."] },
    { h: "4. Intelligenza artificiale e servizi di terze parti", p: [
      "Per generare le lezioni, le posizioni delle tue partite (FEN e mosse giocate) vengono inviate a Google (Gemini API). Per la valutazione delle mosse, le posizioni vengono inviate al servizio chess-api.com (motore Stockfish). Non inviamo a questi servizi il tuo nome né la tua email.",
      "Le lezioni sono generate da un modello di intelligenza artificiale e possono contenere errori: sono uno strumento di studio, non una consulenza professionale.",
    ] },
    { h: "5. Con chi condividiamo i dati (responsabili del trattamento)", ul: [
      "Supabase (database e autenticazione)", "Vercel (hosting del sito)", "Render (hosting dei server)", "Stripe (pagamenti)", "Google (Gemini API; login con Google)", "Discord (solo se scegli di accedere con Discord)", "chess-api.com (analisi delle posizioni)", "GitHub (esecuzione dell'aggiornamento notturno delle partite, senza dati personali)",
    ], p: ["Con questi fornitori abbiamo o accettiamo i relativi accordi sul trattamento dei dati (DPA). Le partite pubbliche sono lette dalle API di Lichess e Chess.com."] },
    { h: "6. Trasferimenti fuori dallo Spazio Economico Europeo", p: ["Alcuni fornitori hanno sede o server negli Stati Uniti. I trasferimenti avvengono sulla base della decisione di adeguatezza UE-USA (Data Privacy Framework) o delle Clausole Contrattuali Standard della Commissione europea."] },
    { h: "7. Per quanto tempo conserviamo i dati", ul: [
      "Dati dell'account e di gioco: finché mantieni l'account. Se lo elimini dalla pagina Piani, li cancelliamo.",
      "Documenti contabili e fiscali: 10 anni, come previsto dalla legge.",
      "Log di sicurezza: per il tempo strettamente necessario, normalmente non oltre 90 giorni.",
    ] },
    { h: "8. I tuoi diritti", p: [`Puoi chiedere accesso, rettifica, cancellazione, limitazione, portabilità e opporti al trattamento scrivendo a ${E.email}. Puoi eliminare l'account in autonomia dalla sezione Piani. Hai diritto di proporre reclamo al Garante per la protezione dei dati personali (www.garanteprivacy.it) o all'autorità del tuo paese.`] },
    { h: "9. Cookie e archiviazione locale", p: ["Usiamo solo strumenti tecnici strettamente necessari: la sessione di accesso e la lingua scelta, salvate nel tuo browser. Non usiamo cookie di profilazione né di marketing, quindi non serve il banner di consenso. Se in futuro aggiungeremo strumenti di analisi, aggiorneremo questa pagina e chiederemo il consenso."] },
    { h: "10. Minori", p: [`Il servizio è riservato a chi ha almeno ${E.minAge} anni. Sotto questa età non puoi creare un account. Se scopriamo che un account appartiene a un minore sotto la soglia, lo eliminiamo.`] },
    { h: "11. Sicurezza", p: ["Usiamo connessioni cifrate (HTTPS), controllo degli accessi a livello di database e chiavi segrete conservate lato server. Nessun sistema è sicuro al 100%: se avviene una violazione che ti riguarda, ti avvisiamo come richiesto dalla legge."] },
    { h: "12. Modifiche", p: ["Se cambiamo questa informativa aggiorniamo la data in alto e, per le modifiche rilevanti, ti avvisiamo via email o nell'app."] },
  ],
};

const privacyEn: Doc = {
  title: "Privacy Policy",
  intro: `This policy explains how ${BRAND} processes your personal data under Regulation (EU) 2016/679 (GDPR).`,
  sections: [
    { h: "1. Data controller", p: [`${E.name}, ${E.address}, ${E.taxId}. Privacy contact: ${E.email}.`] },
    { h: "2. Data we process", ul: [
      "Account data: email, password (stored encrypted by our authentication provider) and, if you sign in with Google or Discord, the name and email that service provides.",
      "Game data: the usernames you link on Lichess and Chess.com and your public games on those platforms (moves, results, ratings, openings).",
      "Data generated by the service: engine analysis, detected mistakes, AI lessons and answers, statistics, monthly quota usage.",
      "Subscription data: plan, status, Stripe customer ID. We never see or store your card details; Stripe handles them.",
      "Technical data: IP address and security logs at our hosting providers.",
    ] },
    { h: "3. Why we process it and on what legal basis", ul: [
      "To provide the service (account, linking chess accounts, analysis, AI lessons): performance of a contract.",
      "To handle payments and subscriptions and meet tax and accounting duties: contract and legal obligation.",
      "Security, abuse prevention and enforcing usage limits: legitimate interest.",
      "Service messages (email confirmation, password reset, subscription notices): contract.",
    ], p: ["We do not use your data for advertising and we do not sell it. We do not make automated decisions that produce legal effects on you."] },
    { h: "4. Artificial intelligence and third-party services", p: [
      "To generate lessons, positions from your games (FEN and moves played) are sent to Google (Gemini API). To evaluate moves, positions are sent to chess-api.com (Stockfish engine). We do not send your name or email to these services.",
      "Lessons are produced by an AI model and may contain mistakes: they are a study aid, not professional advice.",
    ] },
    { h: "5. Who we share data with (processors)", ul: [
      "Supabase (database and authentication)", "Vercel (website hosting)", "Render (server hosting)", "Stripe (payments)", "Google (Gemini API; Google sign-in)", "Discord (only if you choose Discord sign-in)", "chess-api.com (position analysis)", "GitHub (runs the nightly game update, no personal data)",
    ], p: ["We have, or accept, data processing agreements (DPAs) with these providers. Public games are read from the Lichess and Chess.com APIs."] },
    { h: "6. Transfers outside the European Economic Area", p: ["Some providers are based or host data in the United States. Transfers rely on the EU-US adequacy decision (Data Privacy Framework) or the European Commission's Standard Contractual Clauses."] },
    { h: "7. How long we keep data", ul: [
      "Account and game data: while you keep your account. If you delete it from the Plans page, we erase it.",
      "Accounting and tax records: 10 years, as required by law.",
      "Security logs: only as long as strictly necessary, normally no more than 90 days.",
    ] },
    { h: "8. Your rights", p: [`You can request access, rectification, erasure, restriction, portability and object to processing by writing to ${E.email}. You can delete your account yourself from the Plans section. You may lodge a complaint with the Italian data protection authority (www.garanteprivacy.it) or the authority in your country.`] },
    { h: "9. Cookies and local storage", p: ["We only use strictly necessary technical storage: your sign-in session and your chosen language, saved in your browser. We use no profiling or marketing cookies, so no consent banner is needed. If we add analytics later, we will update this page and ask for consent."] },
    { h: "10. Children", p: [`The service is for people aged ${E.minAge} or older. Below that age you cannot create an account. If we learn an account belongs to someone under the threshold, we delete it.`] },
    { h: "11. Security", p: ["We use encrypted connections (HTTPS), database-level access control and secret keys kept server-side. No system is 100% secure: if a breach affects you, we will notify you as the law requires."] },
    { h: "12. Changes", p: ["If we change this policy we update the date above and, for significant changes, notify you by email or in the app."] },
  ],
};

const privacyEs: Doc = {
  title: "Política de privacidad",
  intro: `Esta política explica cómo ${BRAND} trata tus datos personales conforme al Reglamento (UE) 2016/679 (RGPD).`,
  sections: [
    { h: "1. Responsable del tratamiento", p: [`${E.name}, ${E.address}, ${E.taxId}. Contacto de privacidad: ${E.email}.`] },
    { h: "2. Qué datos tratamos", ul: [
      "Datos de la cuenta: email, contraseña (almacenada cifrada por nuestro proveedor de autenticación) y, si accedes con Google o Discord, el nombre y el email que facilita ese servicio.",
      "Datos de juego: los nombres de usuario que vinculas en Lichess y Chess.com y tus partidas públicas en esas plataformas (jugadas, resultados, ratings, aperturas).",
      "Datos generados por el servicio: análisis del motor, errores detectados, lecciones y respuestas de la IA, estadísticas, uso de las cuotas mensuales.",
      "Datos de suscripción: plan, estado, identificador de cliente de Stripe. Nunca vemos ni guardamos los datos de tu tarjeta; los gestiona Stripe.",
      "Datos técnicos: dirección IP y registros de seguridad en nuestros proveedores de alojamiento.",
    ] },
    { h: "3. Para qué los tratamos y con qué base legal", ul: [
      "Prestarte el servicio (cuenta, vincular cuentas de ajedrez, análisis, lecciones con IA): ejecución del contrato.",
      "Gestionar pagos y suscripciones y cumplir obligaciones fiscales y contables: contrato y obligación legal.",
      "Seguridad, prevención de abusos y control de los límites de uso: interés legítimo.",
      "Mensajes del servicio (confirmación de email, restablecer contraseña, avisos de suscripción): contrato.",
    ], p: ["No usamos tus datos para publicidad ni los vendemos. No tomamos decisiones automatizadas que produzcan efectos jurídicos sobre ti."] },
    { h: "4. Inteligencia artificial y servicios de terceros", p: [
      "Para generar las lecciones, las posiciones de tus partidas (FEN y jugadas) se envían a Google (API de Gemini). Para evaluar las jugadas, las posiciones se envían a chess-api.com (motor Stockfish). No enviamos tu nombre ni tu email a estos servicios.",
      "Las lecciones las produce un modelo de inteligencia artificial y pueden contener errores: son una ayuda de estudio, no asesoramiento profesional.",
    ] },
    { h: "5. Con quién compartimos los datos (encargados del tratamiento)", ul: [
      "Supabase (base de datos y autenticación)", "Vercel (alojamiento del sitio)", "Render (alojamiento de servidores)", "Stripe (pagos)", "Google (API de Gemini; acceso con Google)", "Discord (solo si eliges acceder con Discord)", "chess-api.com (análisis de posiciones)", "GitHub (ejecuta la actualización nocturna de partidas, sin datos personales)",
    ], p: ["Con estos proveedores tenemos, o aceptamos, los correspondientes contratos de encargado del tratamiento. Las partidas públicas se leen de las API de Lichess y Chess.com."] },
    { h: "6. Transferencias fuera del Espacio Económico Europeo", p: ["Algunos proveedores tienen sede o servidores en Estados Unidos. Las transferencias se basan en la decisión de adecuación UE-EE. UU. (Marco de Privacidad de Datos) o en las Cláusulas Contractuales Tipo de la Comisión Europea."] },
    { h: "7. Cuánto tiempo conservamos los datos", ul: [
      "Datos de cuenta y de juego: mientras mantengas la cuenta. Si la eliminas desde la página Planes, los borramos.",
      "Documentos contables y fiscales: 10 años, según exige la ley.",
      "Registros de seguridad: solo el tiempo estrictamente necesario, normalmente no más de 90 días.",
    ] },
    { h: "8. Tus derechos", p: [`Puedes solicitar acceso, rectificación, supresión, limitación, portabilidad y oponerte al tratamiento escribiendo a ${E.email}. Puedes eliminar tu cuenta tú mismo desde la sección Planes. Tienes derecho a presentar una reclamación ante la Agencia Española de Protección de Datos (www.aepd.es) o ante la autoridad de tu país.`] },
    { h: "9. Cookies y almacenamiento local", p: ["Solo usamos almacenamiento técnico estrictamente necesario: tu sesión de acceso y el idioma elegido, guardados en tu navegador. No usamos cookies de perfilado ni de marketing, por lo que no hace falta banner de consentimiento. Si en el futuro añadimos analítica, actualizaremos esta página y pediremos consentimiento."] },
    { h: "10. Menores", p: [`El servicio es para personas de ${E.minAge} años o más. Por debajo de esa edad no puedes crear una cuenta. Si descubrimos que una cuenta pertenece a alguien por debajo del umbral, la eliminamos.`] },
    { h: "11. Seguridad", p: ["Usamos conexiones cifradas (HTTPS), control de acceso a nivel de base de datos y claves secretas guardadas en el servidor. Ningún sistema es 100 % seguro: si una brecha te afecta, te avisaremos como exige la ley."] },
    { h: "12. Cambios", p: ["Si cambiamos esta política actualizamos la fecha de arriba y, en cambios relevantes, te avisamos por email o en la app."] },
  ],
};

const termsIt: Doc = {
  title: "Termini di servizio",
  intro: `Questi termini regolano l'uso di ${BRAND}. Creando un account li accetti.`,
  sections: [
    { h: "1. Chi siamo e cos'è il servizio", p: [`${BRAND} è un servizio online di ${E.name}, ${E.address}, ${E.taxId}, contatto ${E.email}. Collega i tuoi account Lichess e Chess.com, analizza le tue partite con un motore scacchistico e genera lezioni con un'intelligenza artificiale.`] },
    { h: "2. Account", ul: [
      `Devi avere almeno ${E.minAge} anni.`,
      "Le informazioni che fornisci devono essere vere. Sei responsabile di custodire le tue credenziali e di ciò che avviene nel tuo account.",
      "Puoi collegare solo account scacchistici tuoi.",
    ] },
    { h: "3. Natura delle lezioni AI", p: ["Le analisi del motore e le lezioni dell'AI sono strumenti di studio. L'AI può sbagliare, e non garantiamo che usarle migliori il tuo rating o i tuoi risultati."] },
    { h: "4. Uso corretto", p: ["Non puoi:"], ul: [
      "usare il servizio per barare in partite in corso o in violazione delle regole di Lichess, Chess.com o di un torneo;",
      "aggirare i limiti dei piani, rivendere l'accesso o condividere l'account;",
      "sovraccaricare il servizio con richieste automatizzate o tentare di accedere a dati di altri utenti;",
      "usare il servizio in modo illecito.",
    ] },
    { h: "5. Piani e prezzi", p: ["Esiste un piano gratuito e piani a pagamento (Plus, Pro, Elite) con prezzi e limiti indicati nella pagina Piani. I prezzi sono in euro e includono le imposte dove richiesto. Possiamo modificare prezzi e funzionalità: per gli abbonati vale la modifica solo dal rinnovo successivo e dopo preavviso."] },
    { h: "6. Abbonamento, rinnovo e disdetta", p: ["Gli abbonamenti si rinnovano automaticamente ogni mese fino alla disdetta. Puoi disdire in ogni momento dal portale di fatturazione nella pagina Piani: l'abbonamento resta attivo fino alla fine del periodo già pagato. I pagamenti sono gestiti da Stripe."] },
    { h: "7. Diritto di recesso (consumatori UE)", p: [
      "Se sei un consumatore hai 14 giorni dall'acquisto per recedere senza dare spiegazioni, scrivendo a " + E.email + ".",
      "Se chiedi di iniziare subito il servizio digitale, in caso di recesso ti rimborsiamo l'importo pagato meno la parte proporzionale al servizio già fruito. Se il servizio è stato completamente eseguito e hai espressamente accettato di perdere il recesso, questo non si applica. Non ti verranno comunque addebitate somme per il periodo successivo alla disdetta.",
    ] },
    { h: "8. Proprietà intellettuale", p: [`Software, design e marchio ${BRAND} appartengono a noi. Le tue partite restano tue. Le lezioni generate per te puoi usarle liberamente per il tuo studio personale. Lichess, Chess.com, Stockfish e gli altri marchi citati appartengono ai rispettivi titolari; non siamo affiliati a loro.`] },
    { h: "9. Disponibilità del servizio", p: ["Facciamo il possibile perché il servizio funzioni sempre, ma può essere interrotto per manutenzione, guasti o per cause dei servizi esterni da cui dipendiamo (ad esempio Lichess, Chess.com, Stripe, i fornitori di hosting e di AI)."] },
    { h: "10. Responsabilità", p: ["Il servizio è fornito \"così com'è\". Nei limiti consentiti dalla legge non rispondiamo di danni indiretti o di perdita di profitti. Resta ferma la nostra responsabilità per dolo o colpa grave e ogni altra responsabilità che la legge non permette di escludere, compresi i diritti inderogabili dei consumatori."] },
    { h: "11. Sospensione e chiusura", p: ["Possiamo sospendere o chiudere un account che violi questi termini, con preavviso quando possibile. Puoi eliminare il tuo account in qualsiasi momento dalla pagina Piani."] },
    { h: "12. Modifiche ai termini", p: ["Possiamo aggiornare questi termini. Per le modifiche rilevanti ti avvisiamo con ragionevole anticipo; se continui a usare il servizio dopo la data indicata, li accetti."] },
    { h: "13. Legge applicabile e foro", p: ["Si applica la legge italiana. Se sei un consumatore, restano salvi i diritti inderogabili previsti dalla legge del tuo paese di residenza e puoi rivolgerti al giudice del luogo in cui risiedi."] },
    { h: "14. Contatti", p: [`Per qualsiasi domanda scrivi a ${E.email}.`] },
  ],
};

const termsEn: Doc = {
  title: "Terms of Service",
  intro: `These terms govern your use of ${BRAND}. By creating an account you accept them.`,
  sections: [
    { h: "1. Who we are and what the service is", p: [`${BRAND} is an online service by ${E.name}, ${E.address}, ${E.taxId}, contact ${E.email}. It links your Lichess and Chess.com accounts, analyzes your games with a chess engine and generates lessons with artificial intelligence.`] },
    { h: "2. Accounts", ul: [
      `You must be at least ${E.minAge} years old.`,
      "The information you give must be true. You are responsible for keeping your credentials safe and for what happens in your account.",
      "You may only link chess accounts that are yours.",
    ] },
    { h: "3. Nature of AI lessons", p: ["Engine analysis and AI lessons are study tools. The AI can be wrong, and we do not guarantee that using them will improve your rating or results."] },
    { h: "4. Acceptable use", p: ["You may not:"], ul: [
      "use the service to cheat in live games or in breach of the rules of Lichess, Chess.com or a tournament;",
      "get around plan limits, resell access or share your account;",
      "overload the service with automated requests or try to access other users' data;",
      "use the service unlawfully.",
    ] },
    { h: "5. Plans and prices", p: ["There is a free plan and paid plans (Plus, Pro, Elite) with prices and limits shown on the Plans page. Prices are in euros and include taxes where required. We may change prices and features: for subscribers a change applies only from the next renewal and after notice."] },
    { h: "6. Subscription, renewal and cancellation", p: ["Subscriptions renew automatically every month until canceled. You can cancel at any time from the billing portal on the Plans page: the subscription stays active until the end of the period already paid. Payments are handled by Stripe."] },
    { h: "7. Right of withdrawal (EU consumers)", p: [
      "If you are a consumer you have 14 days from purchase to withdraw without giving a reason, by writing to " + E.email + ".",
      "If you asked to start the digital service immediately and then withdraw, we refund what you paid minus a proportionate amount for the service already used. If the service has been fully performed and you expressly agreed to lose the right of withdrawal, it does not apply. You will not be charged for any period after cancellation.",
    ] },
    { h: "8. Intellectual property", p: [`The software, design and ${BRAND} brand belong to us. Your games remain yours. You may freely use lessons generated for you for your personal study. Lichess, Chess.com, Stockfish and other marks mentioned belong to their owners; we are not affiliated with them.`] },
    { h: "9. Availability", p: ["We do our best to keep the service running, but it may be interrupted for maintenance, faults or because of external services we depend on (such as Lichess, Chess.com, Stripe, hosting and AI providers)."] },
    { h: "10. Liability", p: ["The service is provided \"as is\". To the extent permitted by law we are not liable for indirect damages or loss of profits. Our liability for intent or gross negligence, and any liability the law does not allow us to exclude, including mandatory consumer rights, remains unaffected."] },
    { h: "11. Suspension and termination", p: ["We may suspend or close an account that breaks these terms, with notice where possible. You can delete your account at any time from the Plans page."] },
    { h: "12. Changes to the terms", p: ["We may update these terms. For significant changes we give reasonable notice; if you keep using the service after the stated date, you accept them."] },
    { h: "13. Governing law and courts", p: ["Italian law applies. If you are a consumer, the mandatory rights under the law of your country of residence are preserved and you may bring claims before the courts where you live."] },
    { h: "14. Contact", p: [`For any question write to ${E.email}.`] },
  ],
};

const termsEs: Doc = {
  title: "Términos del servicio",
  intro: `Estos términos regulan el uso de ${BRAND}. Al crear una cuenta los aceptas.`,
  sections: [
    { h: "1. Quiénes somos y qué es el servicio", p: [`${BRAND} es un servicio en línea de ${E.name}, ${E.address}, ${E.taxId}, contacto ${E.email}. Vincula tus cuentas de Lichess y Chess.com, analiza tus partidas con un motor de ajedrez y genera lecciones con inteligencia artificial.`] },
    { h: "2. Cuentas", ul: [
      `Debes tener al menos ${E.minAge} años.`,
      "La información que facilites debe ser veraz. Eres responsable de custodiar tus credenciales y de lo que ocurra en tu cuenta.",
      "Solo puedes vincular cuentas de ajedrez que sean tuyas.",
    ] },
    { h: "3. Naturaleza de las lecciones con IA", p: ["Los análisis del motor y las lecciones de la IA son herramientas de estudio. La IA puede equivocarse y no garantizamos que usarlas mejore tu rating o tus resultados."] },
    { h: "4. Uso adecuado", p: ["No puedes:"], ul: [
      "usar el servicio para hacer trampas en partidas en curso o incumpliendo las normas de Lichess, Chess.com o de un torneo;",
      "eludir los límites de los planes, revender el acceso o compartir la cuenta;",
      "sobrecargar el servicio con solicitudes automatizadas o intentar acceder a datos de otros usuarios;",
      "usar el servicio de forma ilícita.",
    ] },
    { h: "5. Planes y precios", p: ["Hay un plan gratuito y planes de pago (Plus, Pro, Elite) con los precios y límites de la página Planes. Los precios son en euros e incluyen impuestos cuando corresponda. Podemos cambiar precios y funciones: para los suscriptores el cambio se aplica solo desde la siguiente renovación y con previo aviso."] },
    { h: "6. Suscripción, renovación y cancelación", p: ["Las suscripciones se renuevan automáticamente cada mes hasta que se cancelen. Puedes cancelar en cualquier momento desde el portal de facturación de la página Planes: la suscripción sigue activa hasta el final del periodo ya pagado. Los pagos los gestiona Stripe."] },
    { h: "7. Derecho de desistimiento (consumidores de la UE)", p: [
      "Si eres consumidor tienes 14 días desde la compra para desistir sin dar motivo, escribiendo a " + E.email + ".",
      "Si pediste empezar el servicio digital de inmediato y luego desistes, te reembolsamos lo pagado menos un importe proporcional al servicio ya utilizado. Si el servicio se ha ejecutado por completo y aceptaste expresamente perder el desistimiento, no se aplica. No se te cobrará ningún periodo posterior a la cancelación.",
    ] },
    { h: "8. Propiedad intelectual", p: [`El software, el diseño y la marca ${BRAND} nos pertenecen. Tus partidas siguen siendo tuyas. Puedes usar libremente las lecciones generadas para ti en tu estudio personal. Lichess, Chess.com, Stockfish y las demás marcas mencionadas pertenecen a sus titulares; no estamos afiliados a ellos.`] },
    { h: "9. Disponibilidad", p: ["Hacemos lo posible por mantener el servicio en marcha, pero puede interrumpirse por mantenimiento, fallos o por servicios externos de los que dependemos (como Lichess, Chess.com, Stripe, proveedores de alojamiento y de IA)."] },
    { h: "10. Responsabilidad", p: ["El servicio se presta \"tal cual\". En la medida permitida por la ley no respondemos de daños indirectos ni de lucro cesante. Se mantiene nuestra responsabilidad por dolo o negligencia grave y cualquier otra que la ley no permita excluir, incluidos los derechos irrenunciables de los consumidores."] },
    { h: "11. Suspensión y cierre", p: ["Podemos suspender o cerrar una cuenta que incumpla estos términos, con aviso cuando sea posible. Puedes eliminar tu cuenta en cualquier momento desde la página Planes."] },
    { h: "12. Cambios en los términos", p: ["Podemos actualizar estos términos. En cambios relevantes avisamos con antelación razonable; si sigues usando el servicio después de la fecha indicada, los aceptas."] },
    { h: "13. Ley aplicable y tribunales", p: ["Se aplica la ley italiana. Si eres consumidor, se mantienen los derechos irrenunciables de la ley de tu país de residencia y puedes acudir a los tribunales de tu domicilio."] },
    { h: "14. Contacto", p: [`Para cualquier duda escribe a ${E.email}.`] },
  ],
};

export const LEGAL: Record<"privacy" | "terms", Record<Lang, Doc>> = {
  privacy: { it: privacyIt, en: privacyEn, es: privacyEs },
  terms: { it: termsIt, en: termsEn, es: termsEs },
};
