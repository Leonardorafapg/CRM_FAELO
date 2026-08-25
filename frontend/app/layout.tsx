import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import { AuthProvider } from "@/contexts/AuthContext";
import "./globals.css";

// Fonte proxima da referencia de dashboard (geometrica, arredondada) —
// substitui a Inter como fonte padrao do app inteiro.
const plusJakartaSans = Plus_Jakarta_Sans({
  variable: "--font-app",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Faelo",
  description: "CRM com atendimento por IA e humano.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${plusJakartaSans.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-page-bg text-text-dark font-sans">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
