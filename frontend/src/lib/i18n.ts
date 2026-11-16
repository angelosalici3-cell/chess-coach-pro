export type Lang = "it" | "en" | "es";
export const LANGS: Lang[] = ["it", "en", "es"];
const S = {
  tagline: { it: "Il tuo Gran Maestro AI, sempre con te", en: "Your AI Grandmaster, always by your side", es: "Tu Gran Maestro IA, siempre contigo" },
  login: { it: "Accedi", en: "Log in", es: "Iniciar sesión" },
  signup: { it: "Crea account", en: "Sign up", es: "Crear cuenta" },
  logout: { it: "Esci", en: "Log out", es: "Cerrar sesión" },
  password: { it: "Password", en: "Password", es: "Contraseña" },
  accounts: { it: "Account collegati", en: "Linked accounts", es: "Cuentas vinculadas" },
  lessons: { it: "Lezioni GM questo mese", en: "GM lessons this month", es: "Lecciones GM este mes" },
  unlimited: { it: "illimitate", en: "unlimited", es: "ilimitadas" },
  games: { it: "Le mie partite", en: "My games", es: "Mis partidas" },
  empty: { it: "Nessuna partita ancora.", en: "No games yet.", es: "Aún no hay partidas." },
  checkConfirm: { it: "Controlla la mail per confermare l'account.", en: "Check your email to confirm your account.", es: "Revisa tu correo para confirmar la cuenta." },
} as const;
export const tr = (k: keyof typeof S, l: Lang) => S[k][l];
