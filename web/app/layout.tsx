import type { Metadata } from "next";
import "./globals.css";
import { DisableServiceWorkers } from "@/components/DisableServiceWorkers";

export const metadata: Metadata = {
  title: "Voice Assistant",
  description: "Local voice assistant powered by Pipecat",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen">
        <DisableServiceWorkers />
        {children}
      </body>
    </html>
  );
}
