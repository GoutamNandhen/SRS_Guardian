import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

export const metadata: Metadata = {
  title: "SRS Guardian — AI Requirements Engineering Assistant",
  description:
    "AI-assisted Software Requirement Specification (SRS) quality review platform based on ISO/IEC/IEEE 29148 standards.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-surface text-on-surface antialiased font-sans">
        <Sidebar />
        <div className="pl-60">
          <Topbar />
          <main className="w-full pt-12 min-h-screen bg-surface px-8 py-6">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
