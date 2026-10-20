import type { Metadata } from "next";
import { Suspense } from "react";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "NetPulse AI",
  description: "Predictive network observability and root-cause intelligence",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex" style={{ background: "var(--page)" }}>
        <Suspense fallback={<div className="hidden md:block w-60 shrink-0" style={{ background: "var(--surface)" }} />}>
          <Sidebar />
        </Suspense>
        <div className="flex min-h-screen flex-1 flex-col overflow-x-hidden">{children}</div>
      </body>
    </html>
  );
}
