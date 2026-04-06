'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAppStore } from '@/lib/store'

export default function ForgotPasswordPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) { setError('Please enter your email address'); return }
    setLoading(true)
    setError('')
    // Simulate sending — backend endpoint can be wired later
    await new Promise(r => setTimeout(r, 1500))
    setLoading(false)
    setSent(true)
  }

  return (
    <div className="min-h-screen bg-surface text-on-surface flex flex-col">
      {/* Ambient glows */}
      <div className="fixed top-[-15%] left-[-10%] w-[600px] h-[600px] bg-primary/8 rounded-full blur-[140px] pointer-events-none" />
      <div className="fixed bottom-[-15%] right-[-10%] w-[500px] h-[500px] bg-tertiary/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Nav */}
      <header className="flex justify-between items-center px-8 py-6 z-10 relative">
        <button onClick={() => router.push('/')} className="text-2xl font-headline italic text-on-surface hover:text-primary transition-colors">
          VibeAnalytix
        </button>
        <span className="text-on-surface-variant text-xs uppercase tracking-widest hidden md:block">Neural Precision Engineering</span>
      </header>

      <main className="flex-grow flex items-center justify-center px-4 relative z-10">
        <div className="w-full max-w-md animate-fade-up">

          {!sent ? (
            <div className="glass-panel p-10 rounded-2xl border border-outline-variant/15 neural-glow">
              {/* Back link */}
              <button
                onClick={() => router.push('/auth')}
                className="flex items-center gap-2 text-on-surface-variant hover:text-primary transition-colors text-sm mb-8 group"
              >
                <span className="material-symbols-outlined text-lg group-hover:-translate-x-1 transition-transform">keyboard_backspace</span>
                Back to Sign In
              </button>

              <div className="mb-10">
                <div className="w-14 h-14 bg-primary/10 border border-primary/20 rounded-2xl flex items-center justify-center text-primary mb-6">
                  <span className="material-symbols-outlined text-3xl">lock_reset</span>
                </div>
                <h1 className="text-4xl font-headline text-on-surface mb-3">Recover Your Workspace.</h1>
                <p className="text-on-surface-variant leading-relaxed">Enter your email and we'll send a secure recovery link valid for 24 hours.</p>
              </div>

              {error && (
                <div className="alert-error mb-6">
                  <span className="material-symbols-outlined text-lg flex-shrink-0">error</span>
                  <span>{error}</span>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2">
                  <label className="section-label" htmlFor="email">Email Address</label>
                  <div className="relative group">
                    <input
                      id="email"
                      type="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      placeholder="name@company.com"
                      required
                      className="input-field pr-12"
                    />
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant/40 group-focus-within:text-primary transition-colors pointer-events-none">
                      <span className="material-symbols-outlined">mail</span>
                    </div>
                  </div>
                </div>

                <button type="submit" disabled={loading} className="btn-primary w-full py-4 text-base rounded-xl">
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="w-4 h-4 border-2 border-on-primary/30 border-t-on-primary rounded-full animate-spin" />
                      Sending Recovery Link...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      Send Recovery Link
                      <span className="material-symbols-outlined text-xl">arrow_forward</span>
                    </span>
                  )}
                </button>
              </form>

              <div className="mt-8 pt-6 border-t border-outline-variant/10 flex items-start gap-3">
                <span className="material-symbols-outlined text-primary/50 text-lg flex-shrink-0 mt-0.5">security</span>
                <p className="text-xs text-on-surface-variant leading-relaxed italic">
                  Security Notice: If an account exists for this email, you will receive instructions shortly. Check your spam folder if the email doesn't arrive within 5 minutes.
                </p>
              </div>
            </div>
          ) : (
            /* Success state */
            <div className="glass-panel p-10 rounded-2xl border border-outline-variant/15 neural-glow text-center animate-fade-up">
              <div className="w-20 h-20 bg-emerald-500/10 border border-emerald-500/20 rounded-full flex items-center justify-center text-emerald-400 mx-auto mb-6">
                <span className="material-symbols-outlined text-4xl" style={{ fontVariationSettings: "'FILL' 1" }}>mark_email_read</span>
              </div>
              <h2 className="text-3xl font-headline text-on-surface mb-3">Check Your Inbox.</h2>
              <p className="text-on-surface-variant leading-relaxed mb-8">
                We've sent a recovery link to <strong className="text-primary">{email}</strong>. It expires in 24 hours.
              </p>
              <div className="space-y-3">
                <button onClick={() => router.push('/auth')} className="btn-primary w-full py-4 rounded-xl">
                  Back to Sign In
                </button>
                <button onClick={() => { setSent(false); setEmail('') }} className="btn-ghost w-full py-3 text-sm">
                  Send to a different email
                </button>
              </div>
            </div>
          )}

        </div>
      </main>

      <footer className="w-full px-12 py-6 flex justify-between items-center z-10 relative">
        <p className="text-[10px] uppercase tracking-widest text-on-surface-variant">© 2024 VibeAnalytix. Neural Precision Engineering.</p>
        <div className="flex gap-6">
          <span className="text-[10px] uppercase tracking-widest text-on-surface-variant hover:text-primary cursor-pointer transition-colors">Security</span>
          <span className="text-[10px] uppercase tracking-widest text-on-surface-variant hover:text-primary cursor-pointer transition-colors">Docs</span>
        </div>
      </footer>
    </div>
  )
}
