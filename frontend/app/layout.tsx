import type { Metadata } from 'next'
import './globals.css'
import AuthBootstrap from './AuthBootstrap'

export const metadata: Metadata = {
  title: 'VibeAnalytix | Neural Precision Engineering',
  description: 'Deliberate AI understanding that transforms complex repositories into clear, structured narratives.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="bg-background text-on-background antialiased">
        <AuthBootstrap />
        {children}
      </body>
    </html>
  )
}
