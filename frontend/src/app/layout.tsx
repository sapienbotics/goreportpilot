import type { Metadata } from "next";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import { Toaster } from "@/components/ui/sonner";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-plus-jakarta-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ReportPilot — AI-Powered Client Reports for Marketing Agencies",
  description:
    "Generate professional marketing reports with AI insights in 5 minutes. Connect Google Analytics & Meta Ads, get AI-written narratives, export to PowerPoint & PDF.",
  keywords: "marketing reports, client reporting, AI reports, agency reporting, Google Analytics reports, Meta Ads reports",
  openGraph: {
    title: "ReportPilot — AI-Powered Client Reports",
    description: "Generate professional marketing reports with AI insights in 5 minutes.",
    type: "website",
    url: "https://reportpilot.co",
    siteName: "ReportPilot",
  },
  twitter: {
    card: "summary_large_image",
    title: "ReportPilot — AI-Powered Client Reports",
    description: "Generate professional marketing reports with AI insights in 5 minutes.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={cn(inter.variable, plusJakartaSans.variable)}>
      <body className="font-sans antialiased bg-background text-foreground">
        {children}
        <Toaster />
      </body>
    </html>
  );
}
