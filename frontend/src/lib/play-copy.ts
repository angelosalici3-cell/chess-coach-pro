import { Lang } from "./i18n";

// Testi del Coach nella scacchiera giocabile della home. Pochi, brevi e con un po' di ironia.
type Pool = string[];
export type PlayCopy = {
  hint: string; again: string; coach: string; elo: string; demo: string; start: string;
  mate: Pool; mated: Pool; draw: Pool; check: Pool; castle: Pool; center: Pool;
  win: Pool; hang: Pool; bad: Pool; ok: Pool; cap: Pool;
};

export const PLAY: Record<Lang, PlayCopy> = {
  it: {
    hint: "Prova tu: muovi un pezzo bianco. Il Coach commenta ogni mossa.",
    again: "Ricomincia", coach: "Il Coach", elo: "Elo demo", demo: "Punteggio dimostrativo, non è il tuo Elo.", start: "Tocca a te: giochi con il Bianco.",
    mate: ["Scacco matto! Senza neanche sudare.", "Matto. Il Coach si inchina."],
    mated: ["Scacco matto per te. Succede: ora lo analizziamo insieme.", "Matto subìto. Il tuo diario degli errori ringrazia."],
    draw: ["Patta. Un punto è un punto.", "Partita pari: nessuno vince, nessuno piange."],
    check: ["Scacco! Il Re avversario trema.", "Scacco. Ora vediamo come si difende."],
    castle: ["Arrocco: Re al sicuro e torre in gioco.", "Arrocco. Il Re ti ringrazia."],
    center: ["Centro conquistato: ottimo inizio.", "Il centro prima di tutto. Ben fatto."],
    win: ["Pezzo catturato e nessun rischio. Pulito.", "Preso! E nessuno può riprenderselo."],
    hang: ["Occhio: quel pezzo ora è in presa e nessuno lo difende.", "Pezzo lasciato lì da solo. Il Coach l'avrebbe notato."],
    bad: ["Scambio che ti costa materiale: prima di muovere, chiediti chi attacca la casa.", "Si può fare, ma ci rimetti un pezzo."],
    ok: ["Mossa solida.", "Sviluppo ordinato, bene.", "Niente da dire. Continua così.", "Tranquilla e utile."],
    cap: ["Catturato. Ora guarda cosa può rispondere l'avversario.", "Un pezzo in meno per lui."],
  },
  en: {
    hint: "Try it: move a white piece. The Coach comments on every move.",
    again: "Restart", coach: "The Coach", elo: "Demo Elo", demo: "Demo score, not your real Elo.", start: "Your turn: you play White.",
    mate: ["Checkmate! Not even a drop of sweat.", "Mate. The Coach bows."],
    mated: ["You got mated. It happens: we'll go over it together.", "Checkmated. Your mistake diary says thanks."],
    draw: ["Draw. A point is a point.", "Even game: nobody wins, nobody cries."],
    check: ["Check! Their King is shaking.", "Check. Let's see how they defend."],
    castle: ["Castled: King safe, rook in play.", "Castling. The King is grateful."],
    center: ["Center taken: great start.", "Center first. Well done."],
    win: ["Piece won with no risk. Clean.", "Captured! And nobody can take it back."],
    hang: ["Careful: that piece is now hanging, nobody defends it.", "You left that piece alone. The Coach would have spotted it."],
    bad: ["That trade costs you material: ask who attacks the square before you move.", "Playable, but you lose a piece."],
    ok: ["Solid move.", "Tidy development, nice.", "Nothing to add. Keep going.", "Quiet and useful."],
    cap: ["Captured. Now see what they can answer.", "One piece fewer for them."],
  },
  es: {
    hint: "Pruébalo: mueve una pieza blanca. El Coach comenta cada jugada.",
    again: "Reiniciar", coach: "El Coach", elo: "Elo demo", demo: "Puntuación de demostración, no es tu Elo real.", start: "Te toca: juegas con blancas.",
    mate: ["¡Jaque mate! Ni sudaste.", "Mate. El Coach se inclina."],
    mated: ["Te dieron mate. Pasa: lo analizamos juntos.", "Mate recibido. Tu diario de errores lo agradece."],
    draw: ["Tablas. Un punto es un punto.", "Partida igualada: nadie gana, nadie llora."],
    check: ["¡Jaque! Su Rey tiembla.", "Jaque. Veamos cómo se defiende."],
    castle: ["Enroque: Rey a salvo y torre en juego.", "Enroque. El Rey te lo agradece."],
    center: ["Centro conquistado: gran comienzo.", "El centro primero. Bien hecho."],
    win: ["Pieza ganada sin riesgo. Limpio.", "¡Capturada! Y nadie puede recuperarla."],
    hang: ["Ojo: esa pieza queda en prise y nadie la defiende.", "Dejaste esa pieza sola. El Coach lo habría visto."],
    bad: ["Ese cambio te cuesta material: antes de mover, mira quién ataca la casilla.", "Se puede, pero pierdes una pieza."],
    ok: ["Jugada sólida.", "Desarrollo ordenado, bien.", "Nada que decir. Sigue así.", "Tranquila y útil."],
    cap: ["Capturada. Ahora mira qué puede responder.", "Una pieza menos para él."],
  },
};
