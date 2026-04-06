import type { Metadata } from "next";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import { Toaster } from "@/components/ui/sonner";
import { Providers } from "@/components/providers";

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
  title: "GoReportPilot — AI-Powered Client Reports",
  description:
    "Generate branded PowerPoint reports with AI narrative insights. Connect GA4, Meta Ads, Google Ads — reports ready in minutes.",
  keywords: "marketing reports, client reporting, AI reports, agency reporting, Google Analytics reports, Meta Ads reports",
  icons: {
    icon: "/favicon.svg",
  },
  openGraph: {
    title: "GoReportPilot — AI-Powered Client Reports",
    description: "Generate branded PowerPoint reports with AI narrative insights. Connect GA4, Meta Ads, Google Ads — reports ready in minutes.",
    type: "website",
    url: "https://goreportpilot.com",
    siteName: "GoReportPilot",
  },
  twitter: {
    card: "summary_large_image",
    title: "GoReportPilot — AI-Powered Client Reports",
    description: "Generate branded PowerPoint reports with AI narrative insights. Connect GA4, Meta Ads, Google Ads — reports ready in minutes.",
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
        <Providers>
          {children}
        </Providers>
        <Toaster />
      </body>
    </html>
  );
}
