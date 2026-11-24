import type { Lang } from "./i18n";
const x = (it: string, en: string, es: string) => ({ it, en, es });
const U = {
  navRewards: x("Profilo", "Profile", "Perfil"),
  tabGames: x("Partite", "Games", "Partidas"), tabLessons: x("Lezioni GM", "GM lessons", "Lecciones GM"),
  gTitle: x("Le tue partite", "Your games", "Tus partidas"),
  gGames: x("Partite", "Games", "Partidas"), gWin: x("Vittorie", "Wins", "Victorias"), gAcc: x("Precisione", "Accuracy", "Precisión"), gAnalyzed: x("Analizzate", "Analyzed", "Analizadas"),
  fAll: x("Tutte", "All", "Todas"), fWin: x("Vinte", "Won", "Ganadas"), fDraw: x("Patte", "Draws", "Tablas"), fLoss: x("Perse", "Lost", "Perdidas"),
  fWhite: x("Bianco", "White", "Blancas"), fBlack: x("Nero", "Black", "Negras"), fSearch: x("Cerca avversario o apertura", "Search opponent or opening", "Buscar rival o apertura"),
  fResult: x("Risultato", "Result", "Resultado"), fColor: x("Colore", "Color", "Color"), fSpeed: x("Ritmo", "Pace", "Ritmo"),
  gToday: x("Oggi", "Today", "Hoy"), gYesterday: x("Ieri", "Yesterday", "Ayer"),
  gNoMatch: x("Nessuna partita con questi filtri.", "No games match these filters.", "Ninguna partida con estos filtros."),
  gMore: x("Mostra altre", "Show more", "Mostrar más"), gBlunders: x("{n} errori gravi", "{n} blunders", "{n} errores graves"), gMistakes: x("{n} errori", "{n} mistakes", "{n} errores"), gErr1: x("1 errore", "1 mistake", "1 error"), gSevere: x("{n} gravi", "{n} blunders", "{n} graves"), gSevere1: x("1 grave", "1 blunder", "1 grave"), gInacc: x("{n} imprecisioni", "{n} inaccuracies", "{n} imprecisiones"), gInacc1: x("1 imprecisione", "1 inaccuracy", "1 imprecisión"),
  gClean: x("Nessun errore", "No mistakes", "Sin errores"), gWeak: x("I tuoi punti deboli", "Your weak spots", "Tus puntos débiles"),
  critTitle: x("Mossa critica", "Critical move", "Jugada crítica"),
  critText: x("{m}: la valutazione passa da {a} a {b}. La migliore era {best}.", "{m}: the evaluation goes from {a} to {b}. The best was {best}.", "{m}: la evaluación pasa de {a} a {b}. La mejor era {best}."),
  critShow: x("Mostrala sulla scacchiera", "Show it on the board", "Muéstrala en el tablero"),
  critNone: x("Nessuna mossa decisiva: partita equilibrata.", "No decisive move: a balanced game.", "Ninguna jugada decisiva: partida equilibrada."),
  evalTitle: x("Chi sta meglio", "Who is better", "Quién está mejor"), evalNote: x("Sopra lo zero sei in vantaggio, sotto lo zero è in vantaggio l'avversario. Tocca il grafico per saltare alla mossa.", "Above zero you are ahead, below zero your opponent is. Tap the chart to jump to that move.", "Sobre cero vas por delante, bajo cero va tu rival. Toca el gráfico para saltar a esa jugada."),
  you: x("Tu", "You", "Tú"), opp: x("Avversario", "Opponent", "Rival"),
  lqTitle: x("Lezioni del GM", "GM lessons", "Lecciones del GM"), lqLeft: x("{n} rimaste su {m} questo mese", "{n} left of {m} this month", "{n} restantes de {m} este mes"),
  lqUnlimited: x("Illimitate con il tuo piano", "Unlimited with your plan", "Ilimitadas con tu plan"), lqBonus: x("+{n} bonus", "+{n} bonus", "+{n} extra"), lqUpgrade: x("Più lezioni", "Get more", "Más lecciones"),
  lessonsEmpty: x("Nessuna lezione ancora: apri una partita e tocca «Chiedi al GM» su un errore.", "No lessons yet: open a game and tap “Ask the GM” on a mistake.", "Aún no hay lecciones: abre una partida y toca «Pregunta al GM» en un error."),
  lessonOpen: x("Apri la partita", "Open the game", "Abrir la partida"),
  rwTitle: x("Premi", "Rewards", "Premios"),
  homeToday: x("Oggi", "Today", "Hoy"),
  seeAll: x("Vedi tutto", "See all", "Ver todo"),
  themeLbl: x("Tema", "Theme", "Tema"),
  on: x("Attivo", "On", "Activo"), off: x("Spento", "Off", "Apagado"),
  rangeLbl: x("Periodo", "Period", "Periodo"),
};
export type UK = keyof typeof U;
export const u = (k: UK, lang: Lang, v?: Record<string, string | number>) =>
  Object.entries(v || {}).reduce((s, [a, b]) => s.replace(`{${a}}`, String(b)), U[k][lang]);
