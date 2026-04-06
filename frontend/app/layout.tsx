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
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,200..800;1,6..72,200..800&display=swap" rel="stylesheet" />
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet" />
      </head>
      <body className="bg-background text-on-background antialiased">
        <AuthBootstrap />
        {children}
      </body>
    </html>
  )
}
