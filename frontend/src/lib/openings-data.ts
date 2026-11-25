// Percorsi di apertura e trappole. Le mosse sono in notazione SAN (con + e #) e sono verificate:
// ogni linea è legale e i matti indicati sono veri. Per aggiungere contenuti basta aggiungere una voce a OPENINGS.
// ES usa l'inglese finché non viene tradotto.

export type T2 = { it: string; en: string };
export type Side = "w" | "b";

export type OpLine = {
  id: string;                 // univoco; per le trappole le due modalità salvano "id" (tendi) e "id:a" (evita)
  kind: "main" | "trap";
  title: T2;
  moves: string;              // SAN separate da spazio, senza numeri
  side: Side;                 // linea: il lato che alleni · trappola: chi tende la trappola
  idea: T2;                   // linea: i piani · trappola: perché funziona
  // solo trappole
  blunderAt?: number;         // indice (0 = prima mossa del Bianco) della mossa con cui cade chi subisce la trappola
  safe?: string[];            // mosse che evitano la trappola
  avoid?: T2;                 // come evitarla
  result?: T2;                // cosa succede se si cade
  springOnly?: boolean;       // niente modalità «evita» (finché non c'è una risposta sicura verificata)
};

export type Opening = { id: string; name: T2; eco: string; side: Side; blurb: T2; lines: OpLine[] };

export const OPENINGS: Opening[] = [
  {
    id: "italiana", name: { it: "Partita Italiana", en: "Italian Game" }, eco: "C50", side: "w",
    blurb: { it: "Sviluppo rapido e mira su f7: la porta d'ingresso al gioco aperto.", en: "Fast development with an eye on f7: the gateway to open play." },
    lines: [
      {
        id: "it-pianissimo", kind: "main", side: "w", title: { it: "Giuoco Pianissimo", en: "Giuoco Pianissimo" },
        moves: "e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d6 O-O O-O Re1 a6",
        idea: {
          it: "Piano solido: c3 e d3 preparano il centro senza fretta, poi la torre in e1 e il ritiro dell'alfiere in b3. Il Nero risponde con a6 per tenere l'alfiere. Piano tipico: Nbd2-f1-g3, poi d4 al momento giusto.",
          en: "A solid plan: c3 and d3 prepare the centre without hurry, then Re1 and the bishop retreat to b3. Black answers with ...a6 to keep the bishop. Typical plan: Nbd2-f1-g3, then d4 at the right moment.",
        },
      },
      {
        id: "it-legal", kind: "trap", side: "w", title: { it: "Matto di Légal", en: "Légal's Mate" },
        moves: "e4 e5 Nf3 d6 Bc4 Bg4 Nc3 g6 Nxe5 Bxd1 Bxf7+ Ke7 Nd5#", blunderAt: 9, safe: ["dxe5"],
        idea: {
          it: "L'alfiere in g4 inchioda il cavallo in f3 alla donna. Se il Nero prende la donna con Bxd1, il Bianco sacrifica la donna ma costruisce un matto con soli pezzi minori.",
          en: "The bishop on g4 pins the f3 knight to the queen. If Black grabs the queen with ...Bxd1, White gives the queen away but mates with minor pieces only.",
        },
        avoid: { it: "Dopo Nxe5 riprendi semplicemente con dxe5: dopo Qxg4 hai pareggiato il materiale. Non prendere la donna.", en: "After Nxe5 simply recapture with ...dxe5: after Qxg4 material is level. Don't take the queen." },
        result: { it: "Matto in 3 mosse, in cambio della donna.", en: "Mate in three, for the price of the queen." },
      },
      {
        id: "it-friedliver", kind: "trap", side: "w", title: { it: "Attacco del Fegato Fritto", en: "Fried Liver Attack" },
        moves: "e4 e5 Nf3 Nc6 Bc4 Nf6 Ng5 d5 exd5 Nxd5 Nxf7 Kxf7 Qf3+ Ke6 Nc3", blunderAt: 9, safe: ["Na5"],
        idea: {
          it: "Il Nero riprende d5 con il cavallo e il Bianco sacrifica il cavallo in f7: il re nero viene trascinato in mezzo alla scacchiera, sotto attacco di donna, cavallo e alfiere.",
          en: "Black recaptures on d5 with the knight, and White sacrifices the knight on f7: the black king is dragged into the open, facing queen, knight and bishop.",
        },
        avoid: { it: "Dopo Ng5 d5 exd5, gioca Na5! cacciando l'alfiere: dopo Bb5+ c6 dxc6 bxc6 il Nero è a posto.", en: "After Ng5 d5 exd5, play ...Na5! to kick the bishop: after Bb5+ c6 dxc6 bxc6 Black is fine." },
        result: { it: "Re nero esposto, attacco vincente per il Bianco.", en: "Exposed black king and a strong attack for White." },
      },
      {
        id: "it-blackburne", kind: "trap", side: "b", title: { it: "Gambetto Blackburne-Shilling", en: "Blackburne Shilling Gambit" },
        moves: "e4 e5 Nf3 Nc6 Bc4 Nd4 Nxe5 Qg5 Nxf7 Qxg2 Rf1 Qxe4+ Be2 Nf3#", blunderAt: 6, safe: ["Nxd4"],
        idea: {
          it: "Il Nero offre un pedone con Nd4. Chi prende in e5 si ritrova con Qg5 che attacca g2 e il cavallo: dopo Nxf7 Qxg2 il Bianco non ha tempo di difendersi e finisce in matto.",
          en: "Black offers a pawn with ...Nd4. White grabs on e5, and ...Qg5 hits g2 and the knight: after Nxf7 Qxg2 White has no time to defend and gets mated.",
        },
        avoid: { it: "Contro Nd4 prendi il cavallo: Nxd4 exd4 e il Bianco è solo in vantaggio di sviluppo.", en: "Against ...Nd4 take the knight: Nxd4 exd4 and White simply keeps a development edge." },
        result: { it: "Matto di cavallo in f3 dopo la cattura avvelenata.", en: "Smothered knight mate on f3 after the poisoned capture." },
      },
    ],
  },
  {
    id: "spagnola", name: { it: "Partita Spagnola", en: "Ruy Lopez" }, eco: "C60", side: "w",
    blurb: { it: "La regina delle aperture: pressione costante sul cavallo c6 e sul centro nero.", en: "The queen of openings: steady pressure on the c6 knight and Black's centre." },
    lines: [
      {
        id: "ruy-closed", kind: "main", side: "w", title: { it: "Spagnola chiusa", en: "Closed Ruy Lopez" },
        moves: "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5 Bb3 d6 c3 O-O h3",
        idea: {
          it: "Il Bianco tiene l'alfiere in b3 e prepara d4. Con h3 si toglie al Nero l'inchiodatura Bg4. Piani tipici: d4, poi Nbd2-f1-g3 o la spinta in centro.",
          en: "White keeps the bishop on b3 and prepares d4. h3 takes away the ...Bg4 pin. Typical plans: d4, then Nbd2-f1-g3 or a central break.",
        },
      },
      {
        id: "ruy-exchange-pawn", kind: "trap", side: "b", title: { it: "Il pedone avvelenato in e5", en: "The poisoned e5 pawn" },
        moves: "e4 e5 Nf3 Nc6 Bb5 a6 Bxc6 dxc6 Nxe5 Qd4 Nf3 Qxe4+ Qe2 Qxe2+ Kxe2", blunderAt: 8, safe: ["O-O", "d4", "Nc3"],
        idea: {
          it: "Dopo la Variante di Cambio il pedone e5 sembra regalato. Ma Qd4 attacca insieme il cavallo e il pedone e4: il Bianco non vince niente e rimane con la struttura peggiore.",
          en: "After the Exchange Variation the e5 pawn looks free. But ...Qd4 hits both the knight and the e4 pawn: White wins nothing and is left with the worse structure.",
        },
        avoid: { it: "Non prendere subito in e5: gioca O-O, d4 oppure Nc3 e tieni il vantaggio strutturale.", en: "Don't grab on e5 at once: play O-O, d4 or Nc3 and keep the structural edge." },
        result: { it: "Il Nero riprende il pedone e pareggia.", en: "Black regains the pawn and equalises." },
      },
    ],
  },
  {
    id: "petrov", name: { it: "Difesa Russa (Petrov)", en: "Petrov's Defence" }, eco: "C42", side: "b",
    blurb: { it: "Risposta simmetrica e molto solida: contrattacchi subito, niente piani passivi.", en: "A symmetrical and very solid reply: you counterattack at once, no passive play." },
    lines: [
      {
        id: "petrov-main", kind: "main", side: "b", title: { it: "Linea principale", en: "Main line" },
        moves: "e4 e5 Nf3 Nf6 Nxe5 d6 Nf3 Nxe4 d4 d5 Bd3 Nc6 O-O Be7 c4 Nb4 Be2 O-O Nc3 Bf5",
        idea: {
          it: "Non prendere mai e4 subito: prima scaccia il cavallo con d6. Poi riprendi e4 e costruisci un centro con d5. Il cavallo in b4 mette pressione, e Bf5 sviluppa con tempo.",
          en: "Never take e4 right away: first kick the knight with ...d6. Then retake e4 and build a centre with ...d5. The knight on b4 adds pressure and ...Bf5 develops with tempo.",
        },
      },
      {
        id: "petrov-qe2", kind: "trap", side: "w", title: { it: "Scacco di scoperta in e-colonna", en: "Discovered check on the e-file" },
        moves: "e4 e5 Nf3 Nf6 Nxe5 Nxe4 Qe2 Nf6 Nc6+ Qe7 Nxe7 Bxe7", blunderAt: 7, safe: ["Qe7"],
        idea: {
          it: "Se il Nero prende e4 senza aver cacciato il cavallo, Qe2 inchioda il cavallo in e4. Muovendolo (Nf6?) la colonna si apre: Nc6+ è scacco di scoperta e il cavallo attacca anche la donna.",
          en: "If Black takes on e4 without kicking the knight first, Qe2 pins the e4 knight. Moving it (...Nf6?) opens the file: Nc6+ is a discovered check and the knight also hits the queen.",
        },
        avoid: { it: "Contro Qe2 gioca Qe7! e dopo Qxe4 d6 riprendi il pedone. Meglio ancora: evita Nxe4 e gioca prima d6.", en: "Against Qe2 play ...Qe7! and after Qxe4 d6 you win the pawn back. Better still: skip ...Nxe4 and play ...d6 first." },
        result: { it: "Il Bianco vince la donna per un cavallo.", en: "White wins the queen for a knight." },
      },
    ],
  },
  {
    id: "siciliana", name: { it: "Difesa Siciliana (Najdorf)", en: "Sicilian Defence (Najdorf)" }, eco: "B90", side: "b",
    blurb: { it: "La risposta più ambiziosa a 1.e4: sbilanciare subito la partita.", en: "The most ambitious answer to 1.e4: unbalance the game from move one." },
    lines: [
      {
        id: "sic-najdorf", kind: "main", side: "b", title: { it: "Najdorf, Attacco Inglese", en: "Najdorf, English Attack" },
        moves: "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6 Be3 e5 Nb3 Be6 f3 Be7 Qd2 O-O O-O-O Nbd7",
        idea: {
          it: "a6 toglie b5 al Bianco e prepara ...b5. Dopo e5 il Nero controlla d4 e il Bianco attacca con g4-h4, il Nero risponde con ...b5 e ...Rc8: gioco di contrattacco sui lati opposti.",
          en: "...a6 takes b5 away from White and prepares ...b5. After ...e5 Black holds d4 while White attacks with g4-h4; Black answers with ...b5 and ...Rc8: opposite-side counterplay.",
        },
      },
    ],
  },
  {
    id: "caro-kann", name: { it: "Difesa Caro-Kann", en: "Caro-Kann Defence" }, eco: "B12", side: "b",
    blurb: { it: "Struttura solida e alfiere buono fuori dalla catena di pedoni.", en: "Solid structure with the good bishop outside the pawn chain." },
    lines: [
      {
        id: "ck-classic", kind: "main", side: "b", title: { it: "Variante Classica", en: "Classical Variation" },
        moves: "e4 c6 d4 d5 Nc3 dxe4 Nxe4 Bf5 Ng3 Bg6 h4 h6 Nf3 Nd7 h5 Bh7 Bd3 Bxd3 Qxd3 e6",
        idea: {
          it: "L'alfiere esce prima di e6. Dopo h4 h6 e h5, si ritira in h7 e si scambia: il Nero ha una struttura solida e il pedone d5 libero. Poi Ngf6 e ...Be7 con ...Qc7.",
          en: "The bishop comes out before ...e6. After h4 h6 and h5, it retreats to h7 and gets traded: Black has a solid structure. Then ...Ngf6, ...Be7 and ...Qc7.",
        },
      },
      {
        id: "ck-nd6", kind: "trap", side: "w", title: { it: "Matto del cavallo in d6", en: "Nd6 smothered mate" },
        moves: "e4 c6 d4 d5 Nc3 dxe4 Nxe4 Nd7 Qe2 Ngf6 Nd6#", blunderAt: 9, safe: ["e6", "Nb6"],
        idea: {
          it: "Il cavallo in d7 chiude la fuga del re: dopo Qe2 il cavallo in g8 non deve andare in f6. Nd6 è matto, perché il re non ha caselle e il pedone e7 è inchiodato sul re.",
          en: "The knight on d7 blocks the king's escape: after Qe2 the g8 knight must not go to f6. Nd6 is mate because the king has no squares and the e7 pawn can't help.",
        },
        avoid: { it: "Dopo Qe2 gioca ...e6 oppure ...Nb6 e il cavallo non è più in pericolo. Mai ...Ngf6?? con il cavallo già in d7.", en: "After Qe2 play ...e6 or ...Nb6 and the knight is out of danger. Never ...Ngf6?? with the other knight on d7." },
        result: { it: "Matto in 6 mosse.", en: "Mate in six moves." },
      },
    ],
  },
  {
    id: "francese", name: { it: "Difesa Francese", en: "French Defence" }, eco: "C11", side: "b",
    blurb: { it: "Centro solido con d5, contrattacco sulla catena di pedoni con c5 e f6.", en: "A solid centre with ...d5 and counterplay against the pawn chain with ...c5 and ...f6." },
    lines: [
      {
        id: "fr-tarrasch", kind: "main", side: "b", title: { it: "Variante Tarrasch", en: "Tarrasch Variation" },
        moves: "e4 e6 d4 d5 Nd2 Nf6 e5 Nfd7 Bd3 c5 c3 Nc6 Ne2 cxd4 cxd4 f6 exf6 Nxf6 O-O Bd6",
        idea: {
          it: "Il Nero attacca la base della catena con c5 e poi mina e5 con f6. Dopo exf6 Nxf6 i pezzi neri sono attivi e l'alfiere in d6 punta al lato di re.",
          en: "Black attacks the base of the chain with ...c5 and undermines e5 with ...f6. After exf6 Nxf6 the black pieces are active and the d6 bishop eyes the kingside.",
        },
      },
    ],
  },
  {
    id: "gambetto-donna", name: { it: "Gambetto di Donna", en: "Queen's Gambit" }, eco: "D30", side: "w",
    blurb: { it: "Pressione sul centro nero e iniziativa: l'apertura posizionale per eccellenza.", en: "Pressure on Black's centre and the initiative: the positional opening par excellence." },
    lines: [
      {
        id: "qgd-main", kind: "main", side: "w", title: { it: "Rifiutato, Variante Ortodossa", en: "Declined, Orthodox Variation" },
        moves: "d4 d5 c4 e6 Nc3 Nf6 Bg5 Be7 e3 O-O Nf3 h6 Bh4 b6 cxd5 Nxd5 Bxe7 Qxe7 Nxd5 exd5 Rc1 Be6",
        idea: {
          it: "Il Nero cerca di scambiare i pezzi per liberarsi. Il Bianco mantiene la maggioranza in e3 e prepara Qa4 o Qb3 contro il centro nero. La torre in c1 occupa la colonna aperta.",
          en: "Black tries to trade pieces to free the position. White keeps solid pressure and prepares Qa4 or Qb3 against Black's centre. The rook on c1 takes the open file.",
        },
      },
      {
        id: "qgd-elephant", kind: "trap", side: "b", title: { it: "Trappola dell'Elefante", en: "Elephant Trap" },
        moves: "d4 d5 c4 e6 Nc3 Nf6 Bg5 Nbd7 cxd5 exd5 Nxd5 Nxd5 Bxd8 Bb4+ Qd2 Bxd2+ Kxd2 Kxd8", blunderAt: 10, safe: ["Bxf6"],
        idea: {
          it: "Il pedone d5 sembra indifeso, ma se il Bianco lo prende con il cavallo, Nxd5 libera la linea: la donna è attaccata e l'alfiere cattura Bxd8, ma dopo Bb4+ Qd2 Bxd2+ il Nero riprende l'alfiere e ha un pezzo in più.",
          en: "The d5 pawn looks loose, but if White takes it with the knight, ...Nxd5 opens the file: White grabs the queen with Bxd8, but after ...Bb4+ Qd2 Bxd2+ Black retakes and is a piece up.",
        },
        avoid: { it: "Prima di prendere in d5 gioca Bxf6: elimina il difensore e mantieni la pressione senza rischi.", en: "Before grabbing d5 play Bxf6: it removes the defender and keeps the pressure without risk." },
        result: { it: "Il Nero vince un pezzo.", en: "Black wins a piece." },
      },
    ],
  },
  {
    id: "londra", name: { it: "Sistema Londra", en: "London System" }, eco: "D02", side: "w",
    blurb: { it: "Una struttura sola da imparare e usare contro quasi tutto: pochi piani, tanta solidità.", en: "One setup to learn and use against almost everything: few plans, lots of solidity." },
    lines: [
      {
        id: "lon-main", kind: "main", side: "w", title: { it: "Schema classico", en: "Classical setup" },
        moves: "d4 d5 Bf4 Nf6 e3 e6 Nf3 Bd6 Bg3 O-O Nbd2 c5 c3 Nc6 Bd3 b6",
        idea: {
          it: "L'alfiere esce prima di e3, poi cavallo, e il Bianco costruisce con Nbd2, c3, Bd3. Piano: scambia l'alfiere nero con Bxd6 o ritirati in g3, poi Ne5 e attacco sul lato di re.",
          en: "The bishop comes out before e3, then the knights, and White builds with Nbd2, c3, Bd3. Plan: trade the black bishop on d6 or retreat to g3, then Ne5 and a kingside attack.",
        },
      },
    ],
  },
  {
    id: "indiana-re", name: { it: "Indiana di Re", en: "King's Indian Defence" }, eco: "E90", side: "b",
    blurb: { it: "Lasci il centro al Bianco e poi lo attacchi: attacco sul lato di re con f5.", en: "You let White build the centre, then attack it: a kingside attack with ...f5." },
    lines: [
      {
        id: "kid-main", kind: "main", side: "b", title: { it: "Linea classica", en: "Classical line" },
        moves: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Ne1 Nd7 Be3 f5",
        idea: {
          it: "Dopo d5 il centro si chiude: il Bianco gioca sull'ala di donna con c5, il Nero attacca sul lato di re con f5 e g5. Chi è più veloce, vince.",
          en: "After d5 the centre closes: White plays on the queenside with c5, Black attacks on the kingside with ...f5 and ...g5. Whoever is faster wins.",
        },
      },
    ],
  },
  {
    id: "inglese", name: { it: "Apertura Inglese", en: "English Opening" }, eco: "A20", side: "w",
    blurb: { it: "Flessibile e posizionale: controlla il centro dai lati e decidi dopo cosa fare.", en: "Flexible and positional: control the centre from the wings and decide later." },
    lines: [
      {
        id: "eng-main", kind: "main", side: "w", title: { it: "Siciliana invertita", en: "Reversed Sicilian" },
        moves: "c4 e5 Nc3 Nf6 Nf3 Nc6 g3 d5 cxd5 Nxd5 Bg2 Nb6 O-O Be7 d3 O-O",
        idea: {
          it: "Una Siciliana con un tempo in più. L'alfiere in g2 controlla la lunga diagonale; il Bianco punta a Be3, Qd2 e al gioco sul lato di donna con a3 e b4.",
          en: "A Sicilian with an extra tempo. The g2 bishop controls the long diagonal; White aims for Be3, Qd2 and queenside play with a3 and b4.",
        },
      },
    ],
  },
  {
    id: "olandese", name: { it: "Difesa Olandese", en: "Dutch Defence" }, eco: "A80", side: "b",
    blurb: { it: "Combatti per e4 con f5: aggressiva ma con qualche insidia sul re.", en: "Fight for e4 with ...f5: aggressive, with some danger around the king." },
    lines: [
      {
        id: "dutch-classic", kind: "main", side: "b", title: { it: "Olandese classica", en: "Classical Dutch" },
        moves: "d4 f5 g3 Nf6 Bg2 e6 Nf3 Be7 O-O O-O c4 d6 Nc3 Qe8",
        idea: {
          it: "Struttura Stonewall/classica: il Nero controlla e4 e prepara ...Qh5 e ...Ne4. Il punto debole è la diagonale a7-g1 e la casella e6.",
          en: "Stonewall/classical structure: Black controls e4 and prepares ...Qh5 and ...Ne4. The weak points are the a7-g1 diagonal and the e6 square.",
        },
      },
      {
        id: "dutch-qh5", kind: "trap", side: "w", title: { it: "Matto in h5", en: "Qh5 mate" },
        moves: "d4 f5 Bg5 h6 Bh4 g5 Bg3 f4 e3 fxg3 Qh5#", blunderAt: 7, springOnly: true,
        idea: {
          it: "Dopo ...g5 il re nero perde la copertura sulla diagonale h5-e8. Se il Nero attacca l'alfiere con ...f4? e prende con fxg3, la donna arriva in h5 con matto.",
          en: "After ...g5 the black king loses cover on the h5-e8 diagonal. If Black attacks the bishop with ...f4? and takes with ...fxg3, the queen lands on h5 with mate.",
        },
        result: { it: "Matto in 6 mosse.", en: "Mate in six moves." },
      },
    ],
  },
  {
    id: "budapest", name: { it: "Gambetto Budapest", en: "Budapest Gambit" }, eco: "A52", side: "b",
    blurb: { it: "Sacrifichi un pedone per sviluppo e iniziativa: tante trappole se il Bianco sbaglia.", en: "Sacrifice a pawn for development and initiative: plenty of traps if White slips." },
    lines: [
      {
        id: "bud-nd3", kind: "trap", side: "b", title: { it: "Matto di cavallo in d3", en: "Knight mate on d3" },
        moves: "d4 Nf6 c4 e5 dxe5 Ng4 Bf4 Nc6 Nf3 Bb4+ Nbd2 Qe7 a3 Ngxe5 axb4 Nd3#", blunderAt: 14, safe: ["Nxe5"],
        idea: {
          it: "Nbd2 blocca la donna e l'alfiere f1 è chiuso dal pedone e2: il re bianco non ha vie. Se il Bianco prende l'alfiere con axb4, Nd3 è matto.",
          en: "Nbd2 blocks the queen and the f1 bishop is hemmed in by the e2 pawn: the white king has no way out. If White grabs the bishop with axb4, ...Nd3 is mate.",
        },
        avoid: { it: "Dopo Ngxe5 non prendere l'alfiere: gioca Nxe5 e cambia i cavalli. Il re deve prima respirare.", en: "After ...Ngxe5 don't take the bishop: play Nxe5 and trade knights. The king needs room to breathe first." },
        result: { it: "Matto in 1 mossa.", en: "Mate in one." },
      },
    ],
  },
  {
    id: "barbiere", name: { it: "Matto del Barbiere", en: "Scholar's Mate" }, eco: "C20", side: "w",
    blurb: { it: "Il matto in 4 mosse che tutti hanno visto: impara a tenderlo e, soprattutto, a pararlo.", en: "The four-move mate everyone has seen: learn to play it and, above all, to stop it." },
    lines: [
      {
        id: "scholar", kind: "trap", side: "w", title: { it: "Donna e alfiere su f7", en: "Queen and bishop on f7" },
        moves: "e4 e5 Bc4 Nc6 Qh5 Nf6 Qxf7#", blunderAt: 5, safe: ["g6", "Qe7", "Nh6"],
        idea: {
          it: "Alfiere e donna puntano entrambi f7, difeso solo dal re. Se il Nero ignora la minaccia, la donna prende in f7 con matto.",
          en: "Bishop and queen both aim at f7, defended only by the king. If Black ignores the threat, the queen takes on f7 with mate.",
        },
        avoid: { it: "Difendi f7 con ...g6 (cacciando la donna), ...Qe7 oppure ...Nh6. Con ...g6 la donna è costretta a ritirarsi.", en: "Defend f7 with ...g6 (kicking the queen), ...Qe7 or ...Nh6. With ...g6 the queen has to retreat." },
        result: { it: "Matto in 4 mosse.", en: "Mate in four." },
      },
    ],
  },
];

export const ALL_LINES: OpLine[] = OPENINGS.flatMap((o) => o.lines);
export const lineKey = (l: OpLine, mode: "learn" | "spring" | "avoid") => (mode === "avoid" ? `${l.id}:a` : l.id);
/** Tutti gli esercizi disponibili: per le trappole due (tendi / evita), per le linee uno. */
export type Drill = { key: string; line: OpLine; mode: "learn" | "spring" | "avoid"; opening: Opening };
export const ALL_DRILLS: Drill[] = OPENINGS.flatMap((o) =>
  o.lines.flatMap((l): Drill[] =>
    l.kind === "main" ? [{ key: l.id, line: l, mode: "learn", opening: o }]
      : [{ key: l.id, line: l, mode: "spring", opening: o }, ...(l.springOnly || !l.safe?.length ? [] : [{ key: l.id + ":a", line: l, mode: "avoid" as const, opening: o }])]));
