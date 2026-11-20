import type { Lang } from "./i18n";

type L3 = { it: string; en: string; es: string };
const x = (it: string, en: string, es: string): L3 => ({ it, en, es });

/** Testi di allenamento, traguardi, analisi del tempo e aperture personali. {n}, {a}, {b}, {d}, {l}, {tier}, {when} sono segnaposto. */
const C = {
  navTrain: x("Allenamento", "Training", "Entrenamiento"),
  trainTitle: x("Allenamento", "Training", "Entrenamiento"),
  tabMistakes: x("I tuoi errori", "Your mistakes", "Tus errores"),
  tabPuzzles: x("Puzzle", "Puzzles", "Puzzles"),
  tabBadges: x("Traguardi", "Achievements", "Logros"),
  streak: x("{n} giorni di fila", "{n}-day streak", "{n} días seguidos"),
  streakShort: x("giorni", "days", "días"),
  streak0: x("Nessuna serie attiva", "No active streak", "Sin racha activa"),
  puzzleRatingLbl: x("Rating puzzle", "Puzzle rating", "Rating de puzzles"),
  dueLbl: x("Da ripassare", "To review", "Por repasar"),
  newLbl: x("Nuovi", "New", "Nuevos"),
  // ripasso errori
  drillAsk: x("Trova la mossa migliore", "Find the best move", "Encuentra la mejor jugada"),
  drillPlayed: x("Nella partita hai giocato {a}", "In the game you played {a}", "En la partida jugaste {a}"),
  drillCost: x("ti è costata {n} pedoni", "it cost you {n} pawns", "te costó {n} peones"),
  drillTurnW: x("Muove il Bianco", "White to move", "Juegan las blancas"),
  drillTurnB: x("Muove il Nero", "Black to move", "Juegan las negras"),
  wrongTry: x("Non è questa. Riprova.", "Not that one. Try again.", "Esa no es. Inténtalo de nuevo."),
  hint: x("Suggerimento", "Hint", "Pista"),
  showSolution: x("Mostra la soluzione", "Show solution", "Mostrar solución"),
  rightFirst: x("Esatto!", "Correct!", "¡Exacto!"),
  rightLate: x("Trovata, ma non al primo colpo: te la riproponiamo presto.", "Found it, but not on the first try: we'll show it again soon.", "La encontraste, pero no a la primera: te la volveremos a mostrar pronto."),
  solutionWas: x("La mossa migliore era {a}", "The best move was {a}", "La mejor jugada era {a}"),
  nextCard: x("Prossimo", "Next", "Siguiente"),
  seeGame: x("Vedi la partita", "See the game", "Ver la partida"),
  comesBack: x("Tornerà tra {d}", "Comes back in {d}", "Volverá en {d}"),
  inMinutes: x("10 minuti", "10 minutes", "10 minutos"),
  inDays: x("{n} giorni", "{n} days", "{n} días"),
  inOneDay: x("1 giorno", "1 day", "1 día"),
  emptyNoErrors: x("Non ci sono errori da ripassare. Sincronizza e analizza qualche partita, poi torna qui.", "No mistakes to review yet. Sync and analyze a few games, then come back.", "Aún no hay errores que repasar. Sincroniza y analiza algunas partidas y vuelve."),
  emptyAllDone: x("Hai ripassato tutto. Il prossimo ripasso è previsto {when}.", "You've reviewed everything. Next review is due {when}.", "Lo has repasado todo. El próximo repaso será {when}."),
  cardNew: x("Nuovo errore", "New mistake", "Error nuevo"),
  cardReview: x("Ripasso", "Review", "Repaso"),
  // puzzle
  puzzleTurnW: x("Trova la mossa migliore per il Bianco", "Find the best move for White", "Encuentra la mejor jugada de las blancas"),
  puzzleTurnB: x("Trova la mossa migliore per il Nero", "Find the best move for Black", "Encuentra la mejor jugada de las negras"),
  puzzleSolved: x("Risolto!", "Solved!", "¡Resuelto!"),
  puzzleSolvedHelp: x("Risolto, ma con un aiuto o un errore: nessun punto rating.", "Solved, but with a hint or a miss: no rating points.", "Resuelto, pero con ayuda o un fallo: sin puntos de rating."),
  puzzleWrong: x("Non è la mossa giusta.", "Not the right move.", "No es la jugada correcta."),
  puzzleSkip: x("Salta", "Skip", "Saltar"),
  puzzleNext: x("Prossimo puzzle", "Next puzzle", "Siguiente puzzle"),
  puzzleLevel: x("Difficoltà {n}", "Difficulty {n}", "Dificultad {n}"),
  yourRating: x("Il tuo rating", "Your rating", "Tu rating"),
  themeAll: x("Tutti i temi", "All themes", "Todos los temas"),
  noPuzzles: x("I puzzle stanno arrivando: torna a trovarci presto.", "Puzzles are on their way: check back soon.", "Los puzzles están en camino: vuelve pronto."),
  noMatch: x("Nessun puzzle di questo tema al tuo livello: prova un altro tema.", "No puzzles of this theme at your level: try another theme.", "No hay puzzles de este tema a tu nivel: prueba otro tema."),
  themesLbl: x("Temi", "Themes", "Temas"),
  puzzleCredit: x("Puzzle del database Lichess (CC0).", "Puzzles from the Lichess database (CC0).", "Puzzles de la base de datos de Lichess (CC0)."),
  // traguardi
  levelWord: x("Livello", "Level", "Nivel"),
  toNext: x("{n} XP al livello {l}", "{n} XP to level {l}", "{n} XP para el nivel {l}"),
  shieldsTitle: x("I tuoi scudi", "Your shields", "Tus escudos"),
  rewardsTitle: x("Ricompense", "Rewards", "Recompensas"),
  rewardsSub: x("Sali di livello per sbloccare lezioni extra e prove gratuite dei piani superiori.", "Level up to unlock extra lessons and free trials of higher plans.", "Sube de nivel para desbloquear lecciones extra y pruebas gratuitas de planes superiores."),
  claim: x("Riscatta", "Claim", "Reclamar"),
  claimed: x("Riscattata", "Claimed", "Reclamada"),
  lockedAt: x("Livello {l}", "Level {l}", "Nivel {l}"),
  rewardLessons: x("+{n} lezioni del Gran Maestro", "+{n} Grandmaster lessons", "+{n} lecciones del Gran Maestro"),
  rewardTrial: x("{d} giorni di piano {tier}", "{d} days of {tier} plan", "{d} días del plan {tier}"),
  claimLessonsOk: x("Aggiunte {n} lezioni bonus: le userai quando finisci quelle del mese.", "{n} bonus lessons added: they kick in when your monthly ones run out.", "Se añadieron {n} lecciones extra: se usan cuando se acaban las del mes."),
  claimConvOk: x("Hai già un piano: la prova diventa {n} lezioni bonus.", "You already have a plan: the trial becomes {n} bonus lessons.", "Ya tienes un plan: la prueba se convierte en {n} lecciones extra."),
  claimTrialOk: x("Piano {tier} attivo fino al {when}. Buon allenamento!", "{tier} plan active until {when}. Enjoy!", "Plan {tier} activo hasta el {when}. ¡A entrenar!"),
  bonusLeft: x("Lezioni bonus: {n}", "Bonus lessons: {n}", "Lecciones extra: {n}"),
  tierBronze: x("Bronzo", "Bronze", "Bronce"),
  tierSilver: x("Argento", "Silver", "Plata"),
  tierGold: x("Oro", "Gold", "Oro"),
  locked: x("Da sbloccare", "Locked", "Bloqueado"),
  maxed: x("Completato", "Completed", "Completado"),
  sh_games: x("Veterano", "Veteran", "Veterano"), un_games: x("partite importate", "games imported", "partidas importadas"),
  sh_analyzed: x("Analista", "Analyst", "Analista"), un_analyzed: x("partite analizzate", "games analyzed", "partidas analizadas"),
  sh_puzzles: x("Tattico", "Tactician", "Táctico"), un_puzzles: x("puzzle risolti", "puzzles solved", "puzzles resueltos"),
  sh_streak: x("Costante", "Consistent", "Constante"), un_streak: x("giorni di fila (record)", "days in a row (best)", "días seguidos (récord)"),
  sh_fixed: x("Rimediatore", "Fixer", "Reparador"), un_fixed: x("errori corretti", "mistakes fixed", "errores corregidos"),
  sh_lessons: x("Allievo del GM", "GM's pupil", "Alumno del GM"), un_lessons: x("lezioni lette", "lessons read", "lecciones leídas"),
  sh_accuracy: x("Precisione", "Precision", "Precisión"), un_accuracy: x("% di precisione in una partita", "% accuracy in one game", "% de precisión en una partida"),
  sh_openings: x("Esploratore", "Explorer", "Explorador"), un_openings: x("aperture diverse giocate", "different openings played", "aperturas distintas jugadas"),
  sh_puzzle_rating: x("Mente tattica", "Tactical mind", "Mente táctica"), un_puzzle_rating: x("rating puzzle", "puzzle rating", "rating de puzzles"),
  sh_clean: x("Partita pulita", "Clean game", "Partida limpia"), un_clean: x("partite senza errori", "games without mistakes", "partidas sin errores"),
  // home
  todayTitle: x("Allenamento di oggi", "Today's training", "Entrenamiento de hoy"),
  todayDone: x("Allenamento di oggi completato. Torna domani per non perdere la serie.", "Today's training is done. Come back tomorrow to keep your streak.", "Entrenamiento de hoy completado. Vuelve mañana para no perder la racha."),
  todayCta: x("Allenati ora", "Train now", "Entrenar ahora"),
  todayDue: x("{n} errori da ripassare", "{n} mistakes to review", "{n} errores por repasar"),
  todayNone: x("Fai un puzzle per tenere viva la serie.", "Solve a puzzle to keep your streak alive.", "Resuelve un puzzle para mantener la racha."),
  // tempo
  timeTitle: x("Gestione del tempo", "Time management", "Gestión del tiempo"),
  timeChartTitle: x("Tempo per mossa", "Time per move", "Tiempo por jugada"),
  timeChartNote: x("Le barre sono i secondi spesi su ogni mossa. La linea è il tempo che ti resta. Il punto rosso segna un errore.", "Bars are seconds spent on each move. The line is your remaining time. A red dot marks a mistake.", "Las barras son los segundos gastados en cada jugada. La línea es tu tiempo restante. El punto rojo marca un error."),
  avgMove: x("Media per mossa", "Average per move", "Media por jugada"),
  slowest: x("Mossa più lunga", "Longest think", "Jugada más larga"),
  troubleMoves: x("Mosse in zeitnot", "Moves in time trouble", "Jugadas con poco tiempo"),
  fastMistakes: x("Errori in fretta", "Hasty mistakes", "Errores con prisa"),
  lostOnTime: x("Partite perse a tempo", "Games lost on time", "Partidas perdidas por tiempo"),
  insightTrouble: x("Con poco tempo perdi in media {a} centesimi di pedone a mossa, contro {b} nelle altre.", "Low on time you lose {a} hundredths of a pawn per move on average, versus {b} otherwise.", "Con poco tiempo pierdes de media {a} centésimas de peón por jugada, frente a {b} en las demás."),
  insightFast: x("{n} errori giocati in meno di 3 secondi: rallenta nelle posizioni critiche.", "{n} mistakes played in under 3 seconds: slow down in critical positions.", "{n} errores jugados en menos de 3 segundos: reduce el ritmo en posiciones críticas."),
  insightFlag: x("{n} partite perse perché è scaduto il tempo.", "{n} games lost because time ran out.", "{n} partidas perdidas porque se acabó el tiempo."),
  insightOk: x("Gestisci bene il tempo: nessun problema evidente nelle ultime partite.", "You manage time well: no obvious issues in your recent games.", "Gestionas bien el tiempo: ningún problema evidente en tus últimas partidas."),
  noClock: x("Questa partita non ha dati sul tempo.", "This game has no clock data.", "Esta partida no tiene datos de tiempo."),
  noClockHome: x("Servono partite analizzate con l'orologio. Risincronizza le ultime 100 per recuperare i tempi.", "Analyzed games with clock data are needed. Resync your last 100 to recover the times.", "Hacen falta partidas analizadas con reloj. Resincroniza las últimas 100 para recuperar los tiempos."),
  resync: x("Risincronizza 100 partite", "Resync 100 games", "Resincronizar 100 partidas"),
  basedOn: x("Su {n} partite recenti", "Across {n} recent games", "En {n} partidas recientes"),
  secShort: x("s", "s", "s"),
  clockLeft: x("Tempo residuo", "Time left", "Tiempo restante"),
  // atlante personale
  mineToggle: x("Le mie aperture", "My openings", "Mis aperturas"),
  mineAll: x("Tutti i colori", "Both colors", "Ambos colores"),
  mineWhite: x("Con il Bianco", "As White", "Con blancas"),
  mineBlack: x("Con il Nero", "As Black", "Con negras"),
  mineHere: x("Le tue partite su questa linea", "Your games on this line", "Tus partidas en esta línea"),
  mineNone: x("Non hai ancora giocato questa linea.", "You haven't played this line yet.", "Aún no has jugado esta línea."),
  mineGames: x("{n} partite", "{n} games", "{n} partidas"),
  mineWinRate: x("{n}% di vittorie", "{n}% wins", "{n}% de victorias"),
  mineTop: x("Le tue aperture più giocate", "Your most played openings", "Tus aperturas más jugadas"),
  mineLeave: x("Dove esci dalla teoria", "Where you leave theory", "Dónde sales de la teoría"),
  mineLeaveHint: x("Mosse che hai giocato da qui e che non sono nell'enciclopedia", "Moves you played from here that aren't in the encyclopedia", "Jugadas que hiciste desde aquí y no están en la enciclopedia"),
  mineRecent: x("Ultime partite", "Recent games", "Últimas partidas"),
  mineNoGames: x("Collega un account e sincronizza le partite per vedere qui le tue aperture.", "Link an account and sync games to see your openings here.", "Vincula una cuenta y sincroniza partidas para ver aquí tus aperturas."),
  mineW: x("V", "W", "G"), mineD: x("P", "D", "E"), mineL: x("S", "L", "P"),
  // carte collezionabili
  tabCards: x("Carte", "Cards", "Cartas"),
  cardsTitle: x("Le tue carte", "Your cards", "Tus cartas"),
  vsGroup: x("Vittorie contro avversari forti", "Wins against strong opponents", "Victorias contra rivales fuertes"),
  vsNext: x("Prossimo traguardo {sp}: vincere contro un {n}+", "Next {sp} target: beat a {n}+", "Próximo objetivo {sp}: ganar a un {n}+"),
  vsNote: x("Partono dal tuo livello di quando ti sei iscritto: niente carte per avversari più deboli di te.", "They start from your level when you joined: no cards for opponents weaker than you.", "Parten de tu nivel al registrarte: no hay cartas por rivales más débiles que tú."),
  carAll: x("Tutte", "All", "Todas"),
  carOf: x("{a} di {b}", "{a} of {b}", "{a} de {b}"),
  carPrev: x("Carta precedente", "Previous card", "Carta anterior"),
  carNext: x("Carta successiva", "Next card", "Carta siguiente"),
  carOpen: x("Tocca la carta per aprirla e condividerla", "Tap the card to open and share it", "Toca la carta para abrirla y compartirla"),
  cardsSub: x("Ogni carta racconta una tua partita speciale. Rigiocala e condividila.", "Every card tells one of your special games. Replay it and share it.", "Cada carta cuenta una de tus partidas especiales. Reprodúcela y compártela."),
  cardsEmpty: x("Ancora nessuna carta. Sincronizza le partite e fai analizzare le più belle: la prima carta arriva con la tua prima vittoria di almeno 10 mosse a testa.", "No cards yet. Sync your games and get your best ones analyzed: your first card comes with your first win of at least 10 moves each.", "Aún no hay cartas. Sincroniza tus partidas y analiza las mejores: tu primera carta llega con tu primera victoria de al menos 10 jugadas por bando."),
  cardsNew: x("{n} carte nuove!", "{n} new cards!", "¡{n} cartas nuevas!"),
  cardNewTag: x("NUOVA", "NEW", "NUEVA"),
  cardsGoals: x("Obiettivi delle carte", "Card goals", "Objetivos de cartas"),
  cardOwned: x("{a} di {b}", "{a} of {b}", "{a} de {b}"),
  cardGif: x("Condividi GIF", "Share GIF", "Compartir GIF"),
  cardVideo: x("Video", "Video", "Vídeo"),
  cardPng: x("Immagine", "Image", "Imagen"),
  cardMaking: x("Preparo la carta…", "Preparing your card…", "Preparando tu carta…"),
  cardSaved: x("Salvata sul dispositivo.", "Saved to your device.", "Guardada en tu dispositivo."),
  cardShared: x("Pronta da pubblicare!", "Ready to post!", "¡Lista para publicar!"),
  cardFail: x("Non sono riuscito a creare il file. Riprova.", "Couldn't create the file. Try again.", "No pude crear el archivo. Inténtalo de nuevo."),
  cardClose: x("Chiudi", "Close", "Cerrar"),
  cardOpenGame: x("Apri la partita", "Open the game", "Abrir la partida"),
  cardShareText: x("Ho battuto {opp} in {n} mosse. La mia carta su Chess Coach #ChessCoach #scacchi", "I beat {opp} in {n} moves. My card on Chess Coach #ChessCoach #chess", "Vencí a {opp} en {n} jugadas. Mi carta en Chess Coach #ChessCoach #ajedrez"),
  cardShareTextNoWin: x("La mia carta su Chess Coach #ChessCoach #scacchi", "My card on Chess Coach #ChessCoach #chess", "Mi carta en Chess Coach #ChessCoach #ajedrez"),
  rarCommon: x("COMUNE", "COMMON", "COMÚN"), rarRare: x("RARA", "RARE", "RARA"), rarEpic: x("EPICA", "EPIC", "ÉPICA"), rarLegendary: x("LEGGENDARIA", "LEGENDARY", "LEGENDARIA"),
  cWin: x("Vittoria", "Win", "Victoria"), cLoss: x("Sconfitta", "Loss", "Derrota"), cDraw: x("Patta", "Draw", "Tablas"),
  cMe: x("TU", "YOU", "TÚ"), cOpp: x("VS", "VS", "VS"), cMoves: x("mosse", "moves", "jugadas"), cAcc: x("PREC.", "ACC.", "PREC."),
  celebTitle: x("Nuova carta {rarity}!", "New {rarity} card!", "¡Nueva carta {rarity}!"),
  celebSub: x("Hai sbloccato: {title}", "You unlocked: {title}", "Has desbloqueado: {title}"),
  celebShare: x("Condividi", "Share", "Compartir"),
  celebView: x("Vedi le mie carte", "See my cards", "Ver mis cartas"),
  celebLater: x("Più tardi", "Later", "Más tarde"),
  celebMore: x("e altre {n} carte nuove", "and {n} more new cards", "y {n} cartas nuevas más"),
  cardsProgress: x("I tuoi progressi", "Your progress", "Tu progreso"),
  streakNow: x("Serie attuale: {n} (record {b})", "Current streak: {n} (best {b})", "Racha actual: {n} (récord {b})"),
  streakAll: x("Vittorie di fila", "Wins in a row", "Victorias seguidas"), streakW: x("Col Bianco", "As White", "Con Blancas"), streakB: x("Col Nero", "As Black", "Con Negras"),
  hoursTitle: x("Ore giocate per ritmo", "Hours played by time control", "Horas jugadas por ritmo"),
  hoursOf: x("{h} ore · {g} partite", "{h} h · {g} games", "{h} h · {g} partidas"),
  hoursNext: x("prossima carta a {n} ore", "next card at {n} h", "próxima carta a las {n} h"),
  hoursNote: x("Le ore contano il tempo reale sulla scacchiera di entrambi i giocatori. Stesse soglie per ogni ritmo, così 1 ora di bullet vale quanto 1 ora di classica.", "Hours count real time on the board for both players. Same thresholds for every time control, so 1 hour of bullet counts like 1 hour of classical.", "Las horas cuentan el tiempo real en el tablero de ambos jugadores. Mismos umbrales para cada ritmo, así 1 hora de bullet vale lo mismo que 1 de clásicas."),
  // scudi delle aperture
  openShieldsTitle: x("Scudi delle aperture", "Opening shields", "Escudos de aperturas"),
  openShieldsSub: x("Vinci partite giocando la linea indicata (al massimo 5 mosse per lato). Bronzo a 3 vittorie, argento a 10, oro a 25.", "Win games playing the given line (5 moves per side at most). Bronze at 3 wins, silver at 10, gold at 25.", "Gana partidas jugando la línea indicada (máximo 5 jugadas por bando). Bronce a 3 victorias, plata a 10, oro a 25."),
  openAsWhite: x("col Bianco", "as White", "con Blancas"), openAsBlack: x("col Nero", "as Black", "con Negras"),
  openWins: x("vittorie", "wins", "victorias"),
  shieldShare: x("Condividi", "Share", "Compartir"),
  shieldShareText: x("Ho conquistato lo scudo {name} ({tier}) su Chess Coach #ChessCoach #scacchi", "I earned the {name} shield ({tier}) on Chess Coach #ChessCoach #chess", "Conseguí el escudo {name} ({tier}) en Chess Coach #ChessCoach #ajedrez"),
} as const;

export type TK = keyof typeof C;
export function tc(k: TK, lang: Lang, v?: Record<string, string | number>): string {
  let s: string = C[k][lang];
  if (v) for (const key of Object.keys(v)) s = s.split(`{${key}}`).join(String(v[key]));
  return s;
}

export const THEMES = ["mateIn1", "mateIn2", "mateIn3", "fork", "pin", "skewer", "hangingPiece", "discoveredAttack", "backRankMate", "sacrifice", "deflection", "trappedPiece", "endgame", "middlegame", "opening"] as const;
const TH: Record<string, L3> = {
  mateIn1: x("Matto in 1", "Mate in 1", "Mate en 1"), mateIn2: x("Matto in 2", "Mate in 2", "Mate en 2"), mateIn3: x("Matto in 3", "Mate in 3", "Mate en 3"),
  fork: x("Forchetta", "Fork", "Horquilla"), pin: x("Inchiodatura", "Pin", "Clavada"), skewer: x("Infilata", "Skewer", "Rayos X"),
  hangingPiece: x("Pezzo indifeso", "Hanging piece", "Pieza colgada"), discoveredAttack: x("Attacco di scoperta", "Discovered attack", "Ataque descubierto"),
  backRankMate: x("Matto di corridoio", "Back rank mate", "Mate de pasillo"), sacrifice: x("Sacrificio", "Sacrifice", "Sacrificio"),
  deflection: x("Deviazione", "Deflection", "Desviación"), trappedPiece: x("Pezzo intrappolato", "Trapped piece", "Pieza atrapada"),
  endgame: x("Finale", "Endgame", "Final"), middlegame: x("Mediogioco", "Middlegame", "Medio juego"), opening: x("Apertura", "Opening", "Apertura"),
  mate: x("Matto", "Mate", "Mate"), advantage: x("Vantaggio", "Advantage", "Ventaja"), crushing: x("Schiacciante", "Crushing", "Aplastante"),
  short: x("Breve", "Short", "Corto"), long: x("Lunga", "Long", "Largo"), quietMove: x("Mossa tranquilla", "Quiet move", "Jugada tranquila"),
};
export const themeName = (k: string, lang: Lang) => (TH[k] ? TH[k][lang] : k);

// ---- aperture degli scudi
const OPEN_NAMES: Record<string, L3> = {
  italiana: x("Italiana", "Italian Game", "Italiana"), ruy: x("Spagnola", "Ruy Lopez", "Española"), scozzese: x("Scozzese", "Scotch Game", "Escocesa"),
  londra: x("Sistema Londra", "London System", "Sistema Londres"), gambetto: x("Gambetto di Donna", "Queen's Gambit", "Gambito de Dama"), inglese: x("Inglese", "English Opening", "Inglesa"),
  siciliana: x("Siciliana", "Sicilian Defense", "Siciliana"), francese: x("Francese", "French Defense", "Francesa"), caro: x("Caro-Kann", "Caro-Kann", "Caro-Kann"),
  scandinava: x("Scandinava", "Scandinavian", "Escandinava"), indiana: x("Indiana di Re", "King's Indian", "India de Rey"), nimzo: x("Nimzo-Indiana", "Nimzo-Indian", "Nimzo-India"),
};
export const openingName = (id: string, lang: Lang) => (OPEN_NAMES[id] ? OPEN_NAMES[id][lang] : id);
/** Nome dello scudo: per le aperture "op_italiana", per gli altri la chiave sh_*. */
export const shieldTitle = (id: string, lang: Lang) => (id.startsWith("op_") ? openingName(id.slice(3), lang) : tc(("sh_" + id) as TK, lang));
export const shieldUnit = (id: string, lang: Lang) => (id.startsWith("op_") ? tc("openWins", lang) : tc(("un_" + id) as TK, lang));

// ---- obiettivi delle carte
const GOAL: Record<string, { t: L3; s: L3 }> = {
  first_win: { t: x("Prima vittoria", "First win", "Primera victoria"), s: x("La tua prima vittoria con almeno 10 mosse a testa", "Your first win with at least 10 moves each", "Tu primera victoria con al menos 10 jugadas por bando") },
  first_95: { t: x("Prima perla", "First gem", "Primera joya"), s: x("Prima partita da 10+ mosse a testa con precisione sopra il 95%", "First game of 10+ moves each with accuracy above 95%", "Primera partida de 10+ jugadas por bando con precisión superior al 95%") },
  lightning: { t: x("Matto lampo", "Lightning mate", "Mate relámpago"), s: x("Vittoria con scacco matto in 10 mosse o meno", "Win by checkmate in 10 moves or fewer", "Victoria por jaque mate en 10 jugadas o menos") },
  flawless: { t: x("Senza macchia", "Flawless", "Impecable"), s: x("Vittoria senza un solo errore in 15+ mosse a testa", "A win without a single mistake in 15+ moves each", "Victoria sin un solo error en 15+ jugadas por bando") },
  master: { t: x("Da maestro", "Master class", "De maestro"), s: x("Precisione del 98% o più in oltre 20 mosse a testa", "98%+ accuracy over 20+ moves each", "Precisión del 98% o más en más de 20 jugadas por bando") },
  giant: { t: x("Ammazzagiganti", "Giant slayer", "Mata gigantes"), s: x("Battuto un avversario con 150+ punti più di te", "Beat an opponent rated 150+ above you", "Venciste a un rival con 150+ puntos más que tú") },
  giant_big: { t: x("Re dei giganti", "King of giants", "Rey de gigantes"), s: x("Battuto un avversario con 300+ punti più di te", "Beat an opponent rated 300+ above you", "Venciste a un rival con 300+ puntos más que tú") },
  masterpiece: { t: x("Capolavoro", "Masterpiece", "Obra maestra"), s: x("Vittoria con 97%+ di precisione in oltre 25 mosse a testa", "A win with 97%+ accuracy over 25+ moves each", "Victoria con 97%+ de precisión en más de 25 jugadas por bando") },
};
const SPEED: Record<string, L3> = { bullet: x("Bullet", "Bullet", "Bullet"), blitz: x("Blitz", "Blitz", "Blitz"), rapid: x("Rapid", "Rapid", "Rápidas"), classical: x("Classiche", "Classical", "Clásicas") };
export const speedName = (k: string, lang: Lang) => (SPEED[k] ? SPEED[k][lang] : k);
const GOAL2: Record<string, { t: L3; s: L3 }> = {
  new_opening: { t: x("Nuova apertura", "New opening", "Nueva apertura"), s: x("Prima vittoria con {name}", "First win with {name}", "Primera victoria con {name}") },
  short_win: { t: x("Lampo preciso", "Precise lightning", "Relámpago preciso"), s: x("Vittoria in meno di 20 mosse con precisione sopra il 90%", "Win in under 20 moves with accuracy above 90%", "Victoria en menos de 20 jugadas con precisión superior al 90%") },
  short_win_pro: { t: x("Lampo da maestro", "Master lightning", "Relámpago de maestro"), s: x("Vittoria in meno di 20 mosse con precisione sopra il 96%", "Win in under 20 moves with accuracy above 96%", "Victoria en menos de 20 jugadas con precisión superior al 96%") },
  photo_finish: { t: x("All'ultimo secondo", "Photo finish", "Por un suspiro"), s: x("Vittoria con quasi niente tempo sull'orologio ({left} secondi)", "A win with almost no time left ({left} seconds)", "Victoria con casi nada de tiempo en el reloj ({left} segundos)") },
  revenge: { t: x("Rivincita", "Revenge", "Revancha"), s: x("Battuto {opp} dopo aver perso con lui", "Beat {opp} after losing to them", "Venciste a {opp} tras perder con él") },
  comeback: { t: x("Rimonta", "Comeback", "Remontada"), s: x("Vittoria partendo da {low} pedoni sotto", "Won from {low} pawns down", "Victoria desde {low} peones por debajo") },
  comeback_big: { t: x("Rimonta leggendaria", "Legendary comeback", "Remontada legendaria"), s: x("Vittoria partendo da {low} pedoni sotto", "Won from {low} pawns down", "Victoria desde {low} peones por debajo") },
  brilliant: { t: x("Mossa brillante", "Brilliant move", "Jugada brillante"), s: x("Un sacrificio che ha deciso la partita", "A sacrifice that decided the game", "Un sacrificio que decidió la partida") },
};
const fill = (s: string, d: Record<string, any>) => s.replace(/\{(\w+)\}/g, (_, k) => (d[k] != null ? String(d[k]) : "").trim());
export function goalCopy(goal: string, lang: Lang, data: Record<string, any> = {}): { title: string; sub: string } {
  const st = goal.match(/^streak_(all|w|b)_(\d+)$/);
  if (st) {
    const n = st[2], who = st[1];
    const t = { it: who === "all" ? `Serie di ${n}` : `Serie di ${n} col ${who === "w" ? "Bianco" : "Nero"}`, en: who === "all" ? `${n}-win streak` : `${n}-win streak as ${who === "w" ? "White" : "Black"}`, es: who === "all" ? `Racha de ${n}` : `Racha de ${n} con ${who === "w" ? "Blancas" : "Negras"}` };
    const s = { it: `${n} vittorie di fila${who === "all" ? "" : who === "w" ? " giocando col Bianco" : " giocando col Nero"}`, en: `${n} wins in a row${who === "all" ? "" : who === "w" ? " playing White" : " playing Black"}`, es: `${n} victorias seguidas${who === "all" ? "" : who === "w" ? " con Blancas" : " con Negras"}` };
    return { title: t[lang], sub: s[lang] };
  }
  const vs = goal.match(/^vs_(\w+)_(\d+)$/);
  if (vs) {
    const sp = speedName(vs[1], lang), n = vs[2];
    const t = { it: `Vittoria contro un ${n}+`, en: `Win against a ${n}+`, es: `Victoria contra un ${n}+` };
    const s = { it: `Prima vittoria a ${sp} contro un giocatore di ${n} punti o più`, en: `First ${sp} win against a player rated ${n} or higher`, es: `Primera victoria en ${sp} contra un jugador de ${n} puntos o más` };
    return { title: t[lang], sub: s[lang] };
  }
  const hr = goal.match(/^hours_(\w+)_(\d)$/);
  if (hr) {
    const h = [2, 10, 40][Number(hr[2]) - 1], sp = speedName(hr[1], lang);
    const t = { it: `${sp}: ${h} ore`, en: `${sp}: ${h} hours`, es: `${sp}: ${h} horas` };
    const s = { it: `${h} ore giocate a ${sp}${data.games ? ` in ${data.games} partite` : ""}`, en: `${h} hours played in ${sp}${data.games ? ` over ${data.games} games` : ""}`, es: `${h} horas jugadas en ${sp}${data.games ? ` en ${data.games} partidas` : ""}` };
    return { title: t[lang], sub: s[lang] };
  }
  if (GOAL2[goal]) return { title: GOAL2[goal].t[lang], sub: fill(GOAL2[goal].s[lang], { ...data, name: data.opening_name, low: data.low, left: data.left }) };
  const m = goal.match(/^op_(\w+)_(\d)$/);
  if (m) {
    const tier = [tc("tierBronze", lang), tc("tierSilver", lang), tc("tierGold", lang)][Number(m[2]) - 1];
    return { title: openingName(m[1], lang), sub: `${tc("openShieldsTitle", lang)} · ${tier}` };
  }
  const g = GOAL[goal];
  return g ? { title: g.t[lang], sub: g.s[lang] } : { title: goal, sub: "" };
}
export const rarityName = (r: string, lang: Lang) => tc((r === "common" ? "rarCommon" : r === "rare" ? "rarRare" : r === "epic" ? "rarEpic" : "rarLegendary") as TK, lang);
export const GOAL_CODES = Object.keys(GOAL);
