import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'VibeAnalytix - AI Code Understanding',
  description: 'Understand any codebase with AI-powered analysis',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-slate-50">{children}</body>
    </html>
  )
}
