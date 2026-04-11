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

const SITE_TITLE = "GoReportPilot — AI Client Reporting for Marketing Agencies";
const SITE_DESCRIPTION =
  "Generate branded PowerPoint and PDF client reports in 5 minutes. AI writes narrative insights from GA4, Meta Ads, Google Ads, and Search Console. From $19/mo — 14-day free trial, no credit card required.";

export const metadata: Metadata = {
  metadataBase: new URL("https://goreportpilot.com"),
  title: SITE_TITLE,
  description: SITE_DESCRIPTION,
  keywords:
    "AI client reporting tool, agency reporting software, PowerPoint client reports, automated marketing reports, white-label marketing reports, GA4 reporting tool, Meta Ads reporting, Google Ads reporting, SEO reporting tool, multi-language marketing reports",
  alternates: { canonical: "/" },
  icons: { icon: "/favicon.svg" },
  openGraph: {
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    type: "website",
    url: "https://goreportpilot.com",
    siteName: "GoReportPilot",
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
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
