import "./globals.css";
import type { Metadata, Viewport } from "next";
import { Bricolage_Grotesque, DM_Sans } from "next/font/google";
import { LangProvider } from "../components/lang";
import RefCapture from "../components/RefCapture";
import { BRAND } from "../lib/brand";

const display = Bricolage_Grotesque({ subsets: ["latin"], variable: "--font-display", display: "swap" });
const body = DM_Sans({ subsets: ["latin"], variable: "--font-body", display: "swap" });

export const metadata: Metadata = {
  title: { default: `${BRAND}: il tuo Gran Maestro AI`, template: `%s | ${BRAND}` },
  description: "Analizza le tue partite di Lichess e Chess.com, scopri gli errori che ripeti e ricevi lezioni da un Gran Maestro AI.",
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, title: "Chess Coach", statusBarStyle: "black-translucent" },
  icons: { icon: [{ url: "/icon-192.png", sizes: "192x192" }, { url: "/icon-512.png", sizes: "512x512" }], apple: "/apple-touch-icon.png" },
  openGraph: { title: BRAND, description: "Il tuo Gran Maestro AI, sempre con te.", images: ["/og.png"], type: "website" },
};
export const viewport: Viewport = { themeColor: "#0b0f1e", width: "device-width", initialScale: 1, viewportFit: "cover" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it" className={`${display.variable} ${body.variable}`}>
      <body><RefCapture /><LangProvider>{children}</LangProvider></body>
    </html>
  );
}
