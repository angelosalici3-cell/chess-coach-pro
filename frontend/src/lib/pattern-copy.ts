import type { Lang } from "./i18n";
import { speedName } from "./train-copy";

const x = (it: string, en: string, es: string) => ({ it, en, es });
const T = {
  cardTitle: x("Il tuo schema di errore", "Your error pattern", "Tu patrón de error"),
  cta: x("Allenati su questo", "Train on this", "Entrena esto"),
  examples: x("Dove succede", "Where it happens", "Dónde ocurre"),
  more: x("Altre tendenze", "Other tendencies", "Otras tendencias"),
  needMore: x("Servono ancora {n} partite analizzate per scoprire i tuoi schemi di errore.", "{n} more analyzed games are needed to find your error patterns.", "Faltan {n} partidas analizadas para descubrir tus patrones de error."),
  none: x("Nessuno schema marcato: i tuoi errori sono ben distribuiti. Continua così!", "No clear pattern: your mistakes are well spread out. Keep it up!", "Ningún patrón marcado: tus errores están bien repartidos. ¡Sigue así!"),
  body: x("{e} errori su {m} mosse ({r}%), contro il {b}% del tuo solito, in {g} partite.", "{e} mistakes in {m} moves ({r}%), against your usual {b}%, across {g} games.", "{e} errores en {m} jugadas ({r}%), frente a tu {b}% habitual, en {g} partidas."),
  trend: x("Ultime {n} partite: {a}% di errori (prima {b}%).", "Last {n} games: {a}% mistakes (before: {b}%).", "Últimas {n} partidas: {a}% de errores (antes {b}%)."),
  conv: x("Hai raggiunto almeno +3 in {n} partite e non ne hai vinte {k}.", "You reached at least +3 in {n} games and did not win {k} of them.", "Llegaste al menos a +3 en {n} partidas y no ganaste {k}."),
  move: x("mossa {n}", "move {n}", "jugada {n}"),
  drillOn: x("Esercizio su: {t}", "Practicing: {t}", "Practicando: {t}"),
  drillAll: x("Tutti gli errori", "All mistakes", "Todos los errores"),
};
export type PK = keyof typeof T;
export const pc = (k: PK, lang: Lang, v?: Record<string, string | number>) =>
  Object.entries(v || {}).reduce((s, [a, b]) => s.replace(`{${a}}`, String(b)), T[k][lang]);

const TITLE: Record<string, ReturnType<typeof x>> = {
  st_adv: x("Quando sei in vantaggio, ti distrai", "You lose focus when you're ahead", "Pierdes la concentración cuando vas ganando"),
  st_slight_adv: x("Quando sei un po' meglio, perdi precisione", "You get less precise when slightly better", "Pierdes precisión cuando estás algo mejor"),
  st_won: x("Nelle posizioni già vinte sbagli di più", "You err more in already-won positions", "Fallas más en posiciones ya ganadas"),
  st_even: x("Nelle posizioni equilibrate sbagli di più", "You err more in balanced positions", "Fallas más en posiciones igualadas"),
  st_slight_behind: x("In leggero svantaggio sbagli di più", "You err more when slightly worse", "Fallas más con ligera desventaja"),
  st_behind: x("Quando sei in svantaggio sbagli di più", "You err more when behind", "Fallas más cuando vas perdiendo"),
  st_lost: x("Nelle posizioni già perse sbagli di più", "You err more in already-lost positions", "Fallas más en posiciones ya perdidas"),
  t_low: x("Con poco tempo sbagli di più", "You err more when short on time", "Fallas más con poco tiempo"),
  t_fast: x("Le mosse veloci ti tradiscono", "Fast moves let you down", "Las jugadas rápidas te traicionan"),
  ph_opening: x("Nell'apertura sbagli di più", "You err more in the opening", "Fallas más en la apertura"),
  ph_middle: x("Nel mediogioco sbagli di più", "You err more in the middlegame", "Fallas más en el medio juego"),
  ph_end: x("Nei finali sbagli di più", "You err more in endgames", "Fallas más en los finales"),
  after_loss: x("Dopo una sconfitta giochi peggio", "You play worse right after a loss", "Juegas peor justo después de perder"),
  c_white: x("Con il Bianco sbagli di più", "You err more as White", "Fallas más con blancas"),
  c_black: x("Con il Nero sbagli di più", "You err more as Black", "Fallas más con negras"),
};
const TIP: Record<string, ReturnType<typeof x>> = {
  st_adv: x("Prima di ogni mossa in vantaggio chiediti: cosa può prendere o dare scacco l'avversario?", "Before every move when you're ahead, ask: what can my opponent capture or check?", "Antes de cada jugada con ventaja, pregúntate: ¿qué puede capturar o dar jaque el rival?"),
  st_slight_adv: x("Prima di ogni mossa chiediti: cosa può prendere o dare scacco l'avversario?", "Before every move, ask: what can my opponent capture or check?", "Antes de cada jugada, pregúntate: ¿qué puede capturar o dar jaque el rival?"),
  t_low: x("Gioca più in fretta le prime mosse, che conosci bene, per arrivare al finale con più tempo.", "Play the first moves faster, you know them well, to reach the endgame with more time.", "Juega más rápido las primeras jugadas, que conoces bien, para llegar al final con más tiempo."),
  after_loss: x("Dopo una sconfitta fai qualche minuto di pausa prima della partita successiva.", "After a loss, take a few minutes' break before the next game.", "Tras una derrota, haz unos minutos de pausa antes de la siguiente partida."),
};
const PIECE: Record<string, ReturnType<typeof x>> = {
  K: x("re", "king", "rey"), Q: x("donna", "queen", "dama"), R: x("torre", "rook", "torre"),
  B: x("alfiere", "bishop", "alfil"), N: x("cavallo", "knight", "caballo"), P: x("pedone", "pawn", "peón"),
};

export function patternTitle(id: string, lang: Lang): string {
  if (TITLE[id]) return TITLE[id][lang];
  if (id.startsWith("sp_")) { const s = speedName(id.slice(3), lang); return ({ it: `Nel ${s} sbagli di più`, en: `You err more in ${s}`, es: `Fallas más en ${s}` })[lang]; }
  if (id.startsWith("pc_")) { const p = (PIECE[id.slice(3)] || PIECE.P)[lang]; return ({ it: `Sbagli di più con le mosse di ${p}`, en: `You err more with ${p} moves`, es: `Fallas más con jugadas de ${p}` })[lang]; }
  if (id.startsWith("op:")) { const o = id.slice(3); return ({ it: `In ${o} sbagli di più`, en: `You err more in the ${o}`, es: `Fallas más en la ${o}` })[lang]; }
  return id;
}
export const patternTip = (id: string, lang: Lang): string | null => (TIP[id] ? TIP[id][lang] : null);
