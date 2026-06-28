import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/next";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "VERIDIS",
    template: "%s | VERIDIS",
  },
  description: "La conformite CSRD, enfin claire.",
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL ?? "https://veridis-beta.vercel.app"),
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="fr">
      <body>
        {children}
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
