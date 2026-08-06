import "./css/style.css";

import localFont from "next/font/local";
import type { Metadata } from "next";
import { ClientErrorReporter } from "@/components/client-error-reporter";

const nacelle = localFont({
  src: [
    {
      path: "../public/fonts/nacelle-regular.woff2",
      weight: "400",
      style: "normal",
    },
    {
      path: "../public/fonts/nacelle-italic.woff2",
      weight: "400",
      style: "italic",
    },
    {
      path: "../public/fonts/nacelle-semibold.woff2",
      weight: "600",
      style: "normal",
    },
    {
      path: "../public/fonts/nacelle-semibolditalic.woff2",
      weight: "600",
      style: "italic",
    },
  ],
  variable: "--font-nacelle",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Сводка — аналитика маркетплейсов",
    template: "%s — Сводка",
  },
  description: "Внутренняя аналитика Wildberries, Ozon и Яндекс Маркета",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body
        className={`${nacelle.variable} bg-[#f4f5f3] font-sans text-sm text-[#20231f] antialiased`}
      >
        <ClientErrorReporter />
        {children}
      </body>
    </html>
  );
}
