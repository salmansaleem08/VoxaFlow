import type { Metadata } from "next"
import { Manrope, JetBrains_Mono } from "next/font/google"
import "./globals.css"

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
  display: "swap",
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
  display: "swap",
})

export const metadata: Metadata = {
  title: "VoxaFlow — AI Voice Call Automation",
  description:
    "VoxaFlow deploys intelligent AI voice agents for outbound appointment reminders, lead qualification, and customer outreach. Powered by Gemini AI, Whisper STT, and Google TTS.",
  keywords: ["voice AI", "outbound calls", "appointment reminder", "lead qualification", "AI agent"],
  openGraph: {
    title: "VoxaFlow — AI Voice Call Automation",
    description: "Automate every customer conversation with AI voice agents.",
    type: "website",
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${manrope.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen bg-background text-foreground font-sans antialiased">
        {children}
      </body>
    </html>
  )
}
