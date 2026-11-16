import { Lang } from "./i18n";

type PlanKey = "Free" | "Plus" | "Pro" | "Elite";
export type Copy = {
  nav: { features: string; how: string; pricing: string; faq: string; login: string };
  hero: { title: string; sub: string; cta: string; cta2: string; note: string; cardTitle: string; cardText: string; example: string };
  marquee: string[];
  how: { title: string; sub: string; steps: { title: string; text: string }[] };
  vis: { accounts: string; add: string; accuracy: string; blunder: string; mistake: string; inaccuracy: string; best: string };
  features: { title: string; items: { title: string; text: string }[] };
  demo: { title: string; sub: string; example: string; heads: [string, string, string]; items: { label: string; error: string; idea: string; rule: string }[] };
  pricing: { title: string; sub: string; month: string; popular: string; start: string; plans: Record<PlanKey, { blurb: string; items: string[] }> };
  faq: { title: string; items: { q: string; a: string }[] };
  final: { title: string; sub: string; cta: string };
  footer: { text: string; support: string; terms: string };
};

export const COPY: Record<Lang, Copy> = {
  it: {
    nav: { features: "Funzioni", how: "Come funziona", pricing: "Prezzi", faq: "Domande", login: "Accedi" },
    hero: {
      title: "Un Gran Maestro che studia le tue partite.",
      sub: "Collega Lichess o Chess.com. L'app analizza ogni partita, trova gli errori che continui a ripetere e te li spiega come farebbe un allenatore.",
      cta: "Inizia gratis", cta2: "Guarda come funziona", note: "Nessuna carta per cominciare.",
      cardTitle: "Lezione del GM", cardText: "Hai mosso un pezzo senza controllare se era difeso.", example: "esempio",
    },
    marquee: ["Lichess", "Chess.com", "Motore Stockfish", "Gran Maestro AI", "Italiano, English, Español", "Sincronizzazione notturna", "Statistiche per apertura"],
    how: {
      title: "Dalla partita alla lezione in tre passi",
      sub: "Non devi caricare nulla a mano.",
      steps: [
        { title: "Collega i tuoi account", text: "Scrivi il tuo nome utente su Lichess o Chess.com. Le tue ultime partite arrivano da sole." },
        { title: "Il motore trova gli errori", text: "Stockfish valuta ogni mossa e segna imprecisioni, errori ed errori gravi, con la mossa migliore accanto." },
        { title: "Il GM ti spiega perché", text: "Tocca un errore e ricevi una lezione breve: cosa è successo, l'idea giusta e una regola da ricordare." },
      ],
    },
    vis: { accounts: "Account collegati", add: "Aggiungi", accuracy: "Precisione", blunder: "Errore grave", mistake: "Errore", inaccuracy: "Imprecisione", best: "Migliore" },
    features: {
      title: "Tutto quello che serve per smettere di ripetere gli stessi errori",
      items: [
        { title: "Lezioni del Gran Maestro AI", text: "Una spiegazione chiara per ogni errore, nella tua lingua. Le trovi tutte salvate e filtrabili in un'unica pagina." },
        { title: "Chiedi quello che vuoi", text: "Fai una domanda libera su qualsiasi posizione della tua partita e ricevi una risposta subito." },
        { title: "Statistiche per apertura", text: "Scopri con quali aperture vinci e con quali perdi, e dove sbagli di più." },
        { title: "Partite che arrivano da sole", text: "Con un abbonamento le nuove partite si scaricano e si analizzano ogni notte." },
        { title: "Il tuo rating nel tempo", text: "Segui la crescita su Lichess e Chess.com in un grafico solo." },
        { title: "In italiano, inglese e spagnolo", text: "L'app e il Gran Maestro parlano la tua lingua." },
      ],
    },
    demo: {
      title: "Prova una lezione del GM",
      sub: "Scegli un errore tipico e guarda come te lo spiega.",
      example: "Esempio di lezione",
      heads: ["Errore", "Idea corretta", "Regola pratica"],
      items: [
        { label: "Pezzo lasciato indifeso", error: "Hai mosso il cavallo senza controllare chi lo difendeva, e l'avversario l'ha preso gratis.", idea: "Prima di muovere, controlla che tutti i tuoi pezzi siano difesi o al sicuro.", rule: "Un pezzo indifeso è un regalo." },
        { label: "Re ancora al centro", error: "Hai lasciato il re al centro mentre le colonne si aprivano, e l'attacco è arrivato subito.", idea: "Arrocca presto, prima di iniziare qualsiasi attacco.", rule: "Prima il re al sicuro, poi si attacca." },
        { label: "Stesso pezzo mosso due volte", error: "In apertura hai mosso due volte lo stesso pezzo, e l'avversario ha guadagnato un tempo.", idea: "A ogni mossa porta in gioco un pezzo nuovo.", rule: "Prima sviluppa i pezzi, poi fai i piani." },
      ],
    },
    pricing: {
      title: "Scegli quanto vuoi allenarti", sub: "Parti gratis. Cambi piano o disdici quando vuoi.", month: "/mese", popular: "Il più scelto", start: "Inizia",
      plans: {
        Free: { blurb: "Per provare", items: ["1 account collegato", "5 lezioni del GM al mese", "Sincronizzazione manuale"] },
        Plus: { blurb: "Per iniziare sul serio", items: ["2 account collegati", "20 lezioni del GM al mese", "Sincronizzazione automatica ogni notte"] },
        Pro: { blurb: "Per migliorare ogni settimana", items: ["3 account collegati", "Lezioni del GM illimitate", "Sincronizzazione automatica ogni notte"] },
        Elite: { blurb: "Per chi gioca su più account", items: ["5 account collegati", "Lezioni del GM illimitate", "Sincronizzazione automatica ogni notte"] },
      },
    },
    faq: {
      title: "Domande frequenti",
      items: [
        { q: "Quali piattaforme posso collegare?", a: "Lichess e Chess.com. Puoi collegare più account, in base al tuo piano." },
        { q: "Come vengono analizzate le partite?", a: "Il motore Stockfish valuta ogni mossa. Poi un modello di intelligenza artificiale scrive la lezione sugli errori che scegli tu." },
        { q: "Posso disdire quando voglio?", a: "Sì. Dalla pagina Piani gestisci o disdici l'abbonamento. Puoi anche eliminare il tuo account e tutti i dati." },
        { q: "E se il GM non risponde?", a: "In quel caso la lezione non viene conteggiata nel tuo limite mensile. Riprova quando vuoi." },
        { q: "Le mie partite sono private?", a: "Sì. Le tue partite e le tue lezioni sono visibili solo a te." },
      ],
    },
    final: { title: "La prossima partita può andare diversamente.", sub: "Collega il tuo account e ricevi la prima lezione oggi.", cta: "Crea il tuo account gratis" },
    footer: { text: "Allenatore di scacchi con intelligenza artificiale.", support: "Assistenza", terms: "Termini" },
  },

  en: {
    nav: { features: "Features", how: "How it works", pricing: "Pricing", faq: "FAQ", login: "Log in" },
    hero: {
      title: "A grandmaster that studies your games.",
      sub: "Connect Lichess or Chess.com. The app analyzes every game, finds the mistakes you keep repeating and explains them the way a coach would.",
      cta: "Start free", cta2: "See how it works", note: "No card needed to start.",
      cardTitle: "GM lesson", cardText: "You moved a piece without checking if it was defended.", example: "example",
    },
    marquee: ["Lichess", "Chess.com", "Stockfish engine", "AI Grandmaster", "Italiano, English, Español", "Nightly sync", "Opening statistics"],
    how: {
      title: "From game to lesson in three steps",
      sub: "You never upload anything by hand.",
      steps: [
        { title: "Connect your accounts", text: "Enter your username on Lichess or Chess.com. Your latest games arrive on their own." },
        { title: "The engine finds the mistakes", text: "Stockfish rates every move and flags inaccuracies, mistakes and blunders, with the best move next to each." },
        { title: "The GM explains why", text: "Tap a mistake and get a short lesson: what happened, the right idea and a rule to remember." },
      ],
    },
    vis: { accounts: "Linked accounts", add: "Add", accuracy: "Accuracy", blunder: "Blunder", mistake: "Mistake", inaccuracy: "Inaccuracy", best: "Best" },
    features: {
      title: "Everything you need to stop repeating the same mistakes",
      items: [
        { title: "AI Grandmaster lessons", text: "A clear explanation for every mistake, in your language. All of them saved and filterable on one page." },
        { title: "Ask anything", text: "Ask a free question about any position in your game and get an answer right away." },
        { title: "Opening statistics", text: "See which openings you win with, which ones you lose with, and where you slip most." },
        { title: "Games that arrive on their own", text: "With a subscription, new games are downloaded and analyzed every night." },
        { title: "Your rating over time", text: "Follow your progress on Lichess and Chess.com in a single chart." },
        { title: "In English, Italian and Spanish", text: "The app and the Grandmaster speak your language." },
      ],
    },
    demo: {
      title: "Try a GM lesson",
      sub: "Pick a typical mistake and see how it gets explained.",
      example: "Sample lesson",
      heads: ["Mistake", "Right idea", "Rule of thumb"],
      items: [
        { label: "Undefended piece", error: "You moved the knight without checking who defended it, and your opponent took it for free.", idea: "Before moving, check that all your pieces are defended or safe.", rule: "An undefended piece is a gift." },
        { label: "King still in the center", error: "You left the king in the center while the files opened, and the attack came straight away.", idea: "Castle early, before starting any attack.", rule: "King safe first, then attack." },
        { label: "Same piece moved twice", error: "In the opening you moved the same piece twice, and your opponent gained a tempo.", idea: "Bring a new piece into the game on every move.", rule: "Develop your pieces first, make plans later." },
      ],
    },
    pricing: {
      title: "Choose how much you want to train", sub: "Start free. Change plan or cancel whenever you want.", month: "/month", popular: "Most chosen", start: "Start",
      plans: {
        Free: { blurb: "To try it out", items: ["1 linked account", "5 GM lessons per month", "Manual sync"] },
        Plus: { blurb: "To get started for real", items: ["2 linked accounts", "20 GM lessons per month", "Automatic sync every night"] },
        Pro: { blurb: "To improve every week", items: ["3 linked accounts", "Unlimited GM lessons", "Automatic sync every night"] },
        Elite: { blurb: "For players with several accounts", items: ["5 linked accounts", "Unlimited GM lessons", "Automatic sync every night"] },
      },
    },
    faq: {
      title: "Frequently asked questions",
      items: [
        { q: "Which platforms can I connect?", a: "Lichess and Chess.com. You can link several accounts, depending on your plan." },
        { q: "How are games analyzed?", a: "The Stockfish engine rates every move. Then an AI model writes the lesson for the mistakes you pick." },
        { q: "Can I cancel anytime?", a: "Yes. Manage or cancel your subscription from the Plans page. You can also delete your account and all your data." },
        { q: "What if the GM doesn't answer?", a: "Then that lesson isn't counted against your monthly limit. Try again whenever you like." },
        { q: "Are my games private?", a: "Yes. Your games and lessons are visible only to you." },
      ],
    },
    final: { title: "Your next game can go differently.", sub: "Connect your account and get your first lesson today.", cta: "Create your free account" },
    footer: { text: "An AI chess coach.", support: "Support", terms: "Terms" },
  },

  es: {
    nav: { features: "Funciones", how: "Cómo funciona", pricing: "Precios", faq: "Preguntas", login: "Entrar" },
    hero: {
      title: "Un gran maestro que estudia tus partidas.",
      sub: "Conecta Lichess o Chess.com. La app analiza cada partida, encuentra los errores que repites y te los explica como lo haría un entrenador.",
      cta: "Empieza gratis", cta2: "Mira cómo funciona", note: "No hace falta tarjeta para empezar.",
      cardTitle: "Lección del GM", cardText: "Moviste una pieza sin comprobar si estaba defendida.", example: "ejemplo",
    },
    marquee: ["Lichess", "Chess.com", "Motor Stockfish", "Gran Maestro IA", "Italiano, English, Español", "Sincronización nocturna", "Estadísticas por apertura"],
    how: {
      title: "De la partida a la lección en tres pasos",
      sub: "No tienes que subir nada a mano.",
      steps: [
        { title: "Conecta tus cuentas", text: "Escribe tu usuario de Lichess o Chess.com. Tus últimas partidas llegan solas." },
        { title: "El motor encuentra los errores", text: "Stockfish evalúa cada jugada y marca imprecisiones, errores y errores graves, con la mejor jugada al lado." },
        { title: "El GM te explica por qué", text: "Toca un error y recibe una lección breve: qué pasó, la idea correcta y una regla para recordar." },
      ],
    },
    vis: { accounts: "Cuentas vinculadas", add: "Añadir", accuracy: "Precisión", blunder: "Error grave", mistake: "Error", inaccuracy: "Imprecisión", best: "Mejor" },
    features: {
      title: "Todo lo que necesitas para dejar de repetir los mismos errores",
      items: [
        { title: "Lecciones del Gran Maestro IA", text: "Una explicación clara para cada error, en tu idioma. Todas guardadas y filtrables en una sola página." },
        { title: "Pregunta lo que quieras", text: "Haz una pregunta libre sobre cualquier posición de tu partida y recibe la respuesta al instante." },
        { title: "Estadísticas por apertura", text: "Descubre con qué aperturas ganas, con cuáles pierdes y dónde fallas más." },
        { title: "Partidas que llegan solas", text: "Con una suscripción, las partidas nuevas se descargan y se analizan cada noche." },
        { title: "Tu rating en el tiempo", text: "Sigue tu progreso en Lichess y Chess.com en un solo gráfico." },
        { title: "En español, inglés e italiano", text: "La app y el Gran Maestro hablan tu idioma." },
      ],
    },
    demo: {
      title: "Prueba una lección del GM",
      sub: "Elige un error típico y mira cómo te lo explica.",
      example: "Lección de ejemplo",
      heads: ["Error", "Idea correcta", "Regla práctica"],
      items: [
        { label: "Pieza sin defender", error: "Moviste el caballo sin comprobar quién lo defendía, y el rival lo capturó gratis.", idea: "Antes de mover, comprueba que todas tus piezas estén defendidas o a salvo.", rule: "Una pieza sin defender es un regalo." },
        { label: "Rey aún en el centro", error: "Dejaste el rey en el centro mientras se abrían las columnas, y el ataque llegó enseguida.", idea: "Enroca pronto, antes de empezar cualquier ataque.", rule: "Primero el rey a salvo, luego se ataca." },
        { label: "La misma pieza dos veces", error: "En la apertura moviste dos veces la misma pieza, y el rival ganó un tiempo.", idea: "En cada jugada, saca una pieza nueva al juego.", rule: "Primero desarrolla las piezas, después haz planes." },
      ],
    },
    pricing: {
      title: "Elige cuánto quieres entrenar", sub: "Empieza gratis. Cambia de plan o cancela cuando quieras.", month: "/mes", popular: "El más elegido", start: "Empezar",
      plans: {
        Free: { blurb: "Para probar", items: ["1 cuenta vinculada", "5 lecciones del GM al mes", "Sincronización manual"] },
        Plus: { blurb: "Para empezar en serio", items: ["2 cuentas vinculadas", "20 lecciones del GM al mes", "Sincronización automática cada noche"] },
        Pro: { blurb: "Para mejorar cada semana", items: ["3 cuentas vinculadas", "Lecciones del GM ilimitadas", "Sincronización automática cada noche"] },
        Elite: { blurb: "Para quien juega en varias cuentas", items: ["5 cuentas vinculadas", "Lecciones del GM ilimitadas", "Sincronización automática cada noche"] },
      },
    },
    faq: {
      title: "Preguntas frecuentes",
      items: [
        { q: "¿Qué plataformas puedo conectar?", a: "Lichess y Chess.com. Puedes vincular varias cuentas, según tu plan." },
        { q: "¿Cómo se analizan las partidas?", a: "El motor Stockfish evalúa cada jugada. Después un modelo de inteligencia artificial escribe la lección de los errores que tú elijas." },
        { q: "¿Puedo cancelar cuando quiera?", a: "Sí. Desde la página Planes gestionas o cancelas la suscripción. También puedes eliminar tu cuenta y todos tus datos." },
        { q: "¿Y si el GM no responde?", a: "En ese caso la lección no cuenta para tu límite mensual. Inténtalo de nuevo cuando quieras." },
        { q: "¿Mis partidas son privadas?", a: "Sí. Tus partidas y tus lecciones solo las ves tú." },
      ],
    },
    final: { title: "Tu próxima partida puede ser distinta.", sub: "Conecta tu cuenta y recibe tu primera lección hoy.", cta: "Crea tu cuenta gratis" },
    footer: { text: "Entrenador de ajedrez con inteligencia artificial.", support: "Soporte", terms: "Términos" },
  },
};
