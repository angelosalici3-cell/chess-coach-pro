import "./globals.css";
export const metadata = { title: "Chess Coach Pro", description: "AI Grandmaster" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (<html lang="it"><head><meta name="viewport" content="width=device-width, initial-scale=1" /></head><body>{children}</body></html>);
}
