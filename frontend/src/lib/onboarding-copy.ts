import { Lang } from "./i18n";

type L3<T> = Record<Lang, T>;
export type OStep = { id: string; href?: string; title: L3<string>; body: L3<string>; points: L3<string[]>; cta?: L3<string> };

/** Il minicorso: ogni passo spiega una funzione e porta alla pagina giusta ("Provalo ora"). */
export const STEPS: OStep[] = [
  { id: "welcome",
    title: { it: "Benvenuto in Chess Coach", en: "Welcome to Chess Coach", es: "Bienvenido a Chess Coach" },
    body: { it: "Un minuto per scoprire come trasformare le tue partite in allenamento. Puoi rivedere questa guida quando vuoi dal pulsante Guida.", en: "One minute to see how your games become training. You can reopen this guide any time from the Guide button.", es: "Un minuto para ver cómo tus partidas se convierten en entrenamiento. Puedes volver a abrir esta guía cuando quieras desde el botón Guía." },
    points: { it: ["Analizza le partite di Lichess e Chess.com", "Capisce dove perdi punti e te lo spiega", "Ti fa allenare proprio su quegli errori"], en: ["Analyzes your Lichess and Chess.com games", "Finds where you lose points and explains it", "Trains you on those exact mistakes"], es: ["Analiza tus partidas de Lichess y Chess.com", "Encuentra dónde pierdes puntos y te lo explica", "Te entrena justo en esos errores"] } },
  { id: "connect", href: "/dashboard/accounts",
    title: { it: "Collega il tuo account", en: "Link your account", es: "Vincula tu cuenta" },
    body: { it: "Scrivi il nome utente di Lichess o Chess.com: non serve nessuna password. Le tue partite recenti arrivano da sole.", en: "Type your Lichess or Chess.com username: no password needed. Your recent games arrive on their own.", es: "Escribe tu usuario de Lichess o Chess.com: no hace falta contraseña. Tus partidas recientes llegan solas." },
    points: { it: ["Importiamo anche lo storico, in base al tuo piano", "Puoi collegare più account e più ritmi di gioco", "I dati restano tuoi: puoi cancellarli quando vuoi"], en: ["We also import your history, depending on your plan", "Link several accounts and time controls", "Your data stays yours: delete it any time"], es: ["También importamos tu historial, según tu plan", "Vincula varias cuentas y ritmos de juego", "Tus datos son tuyos: bórralos cuando quieras"] },
    cta: { it: "Collega ora", en: "Link now", es: "Vincular ahora" } },
  { id: "home", href: "/dashboard",
    title: { it: "La tua dashboard", en: "Your dashboard", es: "Tu panel" },
    body: { it: "Un solo grafico del rating: scegli account e ritmo con i filtri e passa dalla vista generale al dettaglio.", en: "One rating chart: pick account and time control with the filters, from the big picture to the detail.", es: "Un solo gráfico de rating: elige cuenta y ritmo con los filtros, de la vista general al detalle." },
    points: { it: ["Il riquadro Oggi ti dice cosa fare adesso", "Statistiche su vittorie, precisione e aperture", "Analisi del tempo: dove sprechi o ti manca l'orologio"], en: ["The Today card tells you what to do now", "Stats on wins, accuracy and openings", "Time analysis: where you waste or run out of clock"], es: ["La tarjeta Hoy te dice qué hacer ahora", "Estadísticas de victorias, precisión y aperturas", "Análisis del tiempo: dónde lo gastas o te falta reloj"] } },
  { id: "game", href: "/dashboard/games",
    title: { it: "Rivedi le partite", en: "Review your games", es: "Revisa tus partidas" },
    body: { it: "Apri una partita: la scacchiera, il grafico della perdita di valutazione e l'elenco di svarioni, errori e imprecisioni.", en: "Open a game: board, evaluation-loss chart and a list of blunders, mistakes and inaccuracies.", es: "Abre una partida: tablero, gráfico de pérdida de evaluación y lista de errores graves, errores e imprecisiones." },
    points: { it: ["Clicca un punto del grafico per saltare a quella mossa", "Il grafico del tempo mostra dove hai esitato", "Ogni errore ha la mossa migliore"], en: ["Click a chart point to jump to that move", "The time chart shows where you hesitated", "Every mistake comes with the best move"], es: ["Haz clic en un punto del gráfico para ir a esa jugada", "El gráfico de tiempo muestra dónde dudaste", "Cada error trae la mejor jugada"] } },
  { id: "lessons", href: "/dashboard/lessons",
    title: { it: "Le lezioni del Gran Maestro", en: "Grandmaster lessons", es: "Lecciones del Gran Maestro" },
    body: { it: "Su ogni errore puoi chiedere una lezione breve: cosa è successo, l'idea giusta e una regola pratica da ricordare.", en: "On any mistake, ask for a short lesson: what happened, the right idea and a practical rule to remember.", es: "En cualquier error puedes pedir una lección breve: qué pasó, la idea correcta y una regla práctica." },
    points: { it: ["Le lezioni sono salvate: le ritrovi nella sezione Lezioni", "Ogni piano ha le sue lezioni al mese", "Se il GM non risponde, la lezione non viene scalata"], en: ["Lessons are saved in the Lessons section", "Each plan has monthly lessons", "If the GM fails to answer, nothing is deducted"], es: ["Las lecciones se guardan en la sección Lecciones", "Cada plan tiene sus lecciones al mes", "Si el GM no responde, no se descuenta"] } },
  { id: "train", href: "/dashboard/train",
    title: { it: "Allenati sui tuoi errori", en: "Train on your mistakes", es: "Entrena tus errores" },
    body: { it: "Le posizioni dove hai sbagliato tornano come esercizi, a intervalli sempre più lunghi finché le sai. In più, puzzle Lichess al tuo livello.", en: "Positions where you slipped come back as drills, spaced further apart until you know them. Plus Lichess puzzles at your level.", es: "Las posiciones donde fallaste vuelven como ejercicios, cada vez más espaciados hasta que las dominas. Además, puzles de Lichess a tu nivel." },
    points: { it: ["Muovi i pezzi direttamente sulla scacchiera", "Puzzle per tema: matto, forchette, finali…", "Il tuo rating puzzle cresce con te"], en: ["Move the pieces right on the board", "Puzzles by theme: mate, forks, endgames…", "Your puzzle rating grows with you"], es: ["Mueve las piezas directamente en el tablero", "Puzles por tema: mate, horquillas, finales…", "Tu rating de puzles crece contigo"] },
    cta: { it: "Allenati ora", en: "Train now", es: "Entrenar ahora" } },
  { id: "badges", href: "/dashboard/train?tab=badges",
    title: { it: "Scudi, livelli e premi", en: "Shields, levels and rewards", es: "Escudos, niveles y premios" },
    body: { it: "Ogni allenamento dà XP. Gli scudi (bronzo, argento, oro) premiano costanza e progressi, e i livelli sbloccano premi veri.", en: "Every workout gives XP. Shields (bronze, silver, gold) reward consistency and progress, and levels unlock real prizes.", es: "Cada entrenamiento da XP. Los escudos (bronce, plata, oro) premian constancia y progreso, y los niveles desbloquean premios reales." },
    points: { it: ["Lezioni GM extra e prove di piani superiori", "Mantieni la serie di giorni per non perderla", "Un livello alto può valere un mese di Elite"], en: ["Extra GM lessons and trials of higher plans", "Keep your daily streak alive", "A high level can be worth a month of Elite"], es: ["Lecciones GM extra y pruebas de planes superiores", "Mantén tu racha diaria", "Un nivel alto puede valer un mes de Elite"] } },
  { id: "atlas", href: "/dashboard/openings",
    title: { it: "L'Atlante delle aperture", en: "The Opening Atlas", es: "El Atlas de aperturas" },
    body: { it: "Una mappa da esplorare: ogni nodo è una linea di apertura. Attiva \"Le mie aperture\" per vedere dove hai giocato e come è andata.", en: "A map to explore: every node is an opening line. Turn on \"My openings\" to see where you played and how it went.", es: "Un mapa para explorar: cada nodo es una línea de apertura. Activa \"Mis aperturas\" para ver dónde jugaste y cómo te fue." },
    points: { it: ["Colore verde, ambra o rosso in base alle tue vittorie", "Scopri dove esci dalla teoria", "Apri le tue partite su quella linea"], en: ["Green, amber or red by your results", "See where you leave theory", "Open your games on that line"], es: ["Verde, ámbar o rojo según tus resultados", "Descubre dónde sales de la teoría", "Abre tus partidas en esa línea"] } },
  { id: "plans", href: "/dashboard/plans",
    title: { it: "Il tuo piano", en: "Your plan", es: "Tu plan" },
    body: { it: "Gratis per cominciare. Con un piano a pagamento ottieni più lezioni, più storico, più account e la sincronizzazione automatica.", en: "Free to start. A paid plan gives you more lessons, more history, more accounts and automatic sync.", es: "Gratis para empezar. Con un plan de pago tienes más lecciones, más historial, más cuentas y sincronización automática." },
    points: { it: ["Cambi o disdici quando vuoi dal portale", "Le ricompense contano anche sul piano gratuito", "Puoi riaprire questa guida con il pulsante Guida"], en: ["Change or cancel any time from the portal", "Rewards count on the free plan too", "Reopen this guide with the Guide button"], es: ["Cambia o cancela cuando quieras desde el portal", "Las recompensas cuentan también en el plan gratuito", "Reabre esta guía con el botón Guía"] },
    cta: { it: "Vedi i piani", en: "See plans", es: "Ver planes" } },
];

export const UI: L3<Record<string, string>> = {
  it: { guide: "Guida", next: "Avanti", back: "Indietro", skip: "Salta", done: "Inizia", close: "Chiudi guida", step: "Passo {a} di {b}", tryIt: "Provalo ora", linked: "Account collegato", notLinked: "Nessun account ancora", lessonsLeft: "Lezioni questo mese: {a}/{b}", unlimited: "illimitate", plan: "Piano attuale: {t}. Storico fino a {n} partite per account." },
  en: { guide: "Guide", next: "Next", back: "Back", skip: "Skip", done: "Get started", close: "Close guide", step: "Step {a} of {b}", tryIt: "Try it now", linked: "Account linked", notLinked: "No account yet", lessonsLeft: "Lessons this month: {a}/{b}", unlimited: "unlimited", plan: "Current plan: {t}. History up to {n} games per account." },
  es: { guide: "Guía", next: "Siguiente", back: "Atrás", skip: "Saltar", done: "Empezar", close: "Cerrar guía", step: "Paso {a} de {b}", tryIt: "Pruébalo ahora", linked: "Cuenta vinculada", notLinked: "Aún sin cuenta", lessonsLeft: "Lecciones este mes: {a}/{b}", unlimited: "ilimitadas", plan: "Plan actual: {t}. Historial hasta {n} partidas por cuenta." },
};
export const ui = (k: string, lang: Lang, v: Record<string, string | number> = {}) =>
  UI[lang][k].replace(/\{(\w+)\}/g, (_, x) => String(v[x] ?? ""));
