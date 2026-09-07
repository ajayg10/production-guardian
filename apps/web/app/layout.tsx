import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { Sidebar } from "@/components/sidebar"
import { HydrationSuppressor } from "@/components/hydration-suppressor"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Production Guardian",
  description: "Autonomous operations for film and media production",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        <HydrationSuppressor />
        <div className="flex h-screen bg-background text-foreground overflow-hidden" suppressHydrationWarning>
          <Sidebar />
          <main className="flex-1 overflow-y-auto" suppressHydrationWarning>
            <div className="mx-auto max-w-6xl p-8" suppressHydrationWarning>
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  )
}
