import type { Metadata } from "next";
import { Archivo, PT_Serif, Roboto } from "next/font/google";
import "./globals.css";

// Archivo (900 for display caps, 600–700 for UI caps): hero statements, big numbers,
// buttons, tags, timecodes, tiny labels.
const sans = Archivo({
  subsets: ["latin"],
  weight: ["400", "600", "700", "900"],
  variable: "--font-sans",
  display: "swap",
});

// PT Serif: page H1s, scene and card titles, soft italic asides.
const serif = PT_Serif({
  subsets: ["latin"],
  weight: ["400", "700"],
  style: ["normal", "italic"],
  variable: "--font-serif",
  display: "swap",
});

// Roboto: body copy and everything else.
const body = Roboto({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  variable: "--font-body",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Klarblick",
  description: "Render a narrated maths micro-lesson, or hand in an assignment and be marked on it.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${sans.variable} ${serif.variable} ${body.variable}`}>
      <body>{children}</body>
    </html>
  );
}
