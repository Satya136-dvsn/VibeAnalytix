'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAppStore } from '@/lib/store'

export default function AuthPage() {
  const router = useRouter()
  const { isAuthenticated, login, register } = useAppStore()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isAuthenticated) router.push('/dashboard')
  }, [isAuthenticated, router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      if (mode === 'login') {
        await login(email, password)
      } else {
        await register(email, password)
      }
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen flex flex-col overflow-hidden bg-background">

      {/* ── Ambient glows ─────────────────────────────────────── */}
      <div className="fixed top-[-10%] left-[-10%] w-[500px] h-[500px] bg-primary/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="fixed bottom-[-10%] right-[-10%] w-[600px] h-[600px] bg-primary-dim/5 rounded-full blur-[150px] pointer-events-none" />

      {/* ── Top bar ───────────────────────────────────────────── */}
      <header className="flex justify-between items-center px-8 py-6 z-10">
        <span className="text-2xl font-headline italic text-on-surface">VibeAnalytix</span>
        <a href="#" className="text-on-surface-variant text-sm hover:text-primary transition-colors">Support</a>
      </header>

      {/* ── Main ──────────────────────────────────────────────── */}
      <main className="flex-grow flex items-center justify-center px-6 z-10">
        <div className="w-full max-w-md animate-fade-up">

          {/* Heading */}
          <div className="text-center mb-10 space-y-3">
            <h1 className="text-4xl md:text-5xl font-headline text-on-surface leading-tight">
              {mode === 'login' ? 'Access Neural Analytics' : 'Engineer Your Understanding.'}
            </h1>
            <p className="text-on-surface-variant text-sm max-w-xs mx-auto leading-relaxed">
              {mode === 'login'
                ? 'Continue your codebase exploration with deliberate intelligence.'
                : 'Join developers transforming repositories into insights.'}
            </p>
          </div>

          {/* Card */}
          <div className="glass-panel rounded-2xl p-8 neural-glow border border-outline-variant/15">

            {/* Error */}
            {error && (
              <div className="alert-error mb-6">
                <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M12 3a9 9 0 110 18A9 9 0 0112 3z" />
                </svg>
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">

              {/* Full name — register only */}
              {mode === 'register' && (
                <div className="space-y-2">
                  <label className="block text-[0.6875rem] uppercase tracking-widest text-on-surface-variant ml-1" htmlFor="name">
                    Full Name
                  </label>
                  <input
                    id="name"
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="Nikola Tesla"
                    className="input-field"
                  />
                </div>
              )}

              {/* Email */}
              <div className="space-y-2">
                <label className="block text-[0.6875rem] uppercase tracking-widest text-on-surface-variant ml-1" htmlFor="email">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  placeholder={mode === 'login' ? 'architect@vibeanalytix.io' : 'name@company.com'}
                  className="input-field"
                />
              </div>

              {/* Password */}
              <div className="space-y-2">
                <div className="flex justify-between items-end">
                  <label className="block text-[0.6875rem] uppercase tracking-widest text-on-surface-variant ml-1" htmlFor="password">
                    Password
                  </label>
                  {mode === 'login' && (
                    <a href="/forgot-password" className="text-[0.6875rem] text-primary hover:text-primary-fixed transition-colors uppercase tracking-widest">
                      Forgot Password
                    </a>
                  )}
                </div>
                <div className="relative">
                  <input
                    id="password"
                    type={showPass ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    minLength={8}
                    placeholder="••••••••"
                    className="input-field pr-12"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(!showPass)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface transition-colors"
                    aria-label="Toggle password visibility"
                  >
                    <span className="material-symbols-outlined text-xl">
                      {showPass ? 'visibility' : 'visibility_off'}
                    </span>
                  </button>
                </div>
              </div>

              {/* Submit */}
              <button type="submit" disabled={loading} className="btn-primary w-full py-4 rounded-xl mt-2">
                {loading
                  ? 'Processing…'
                  : mode === 'login' ? 'Sign In' : 'Create Architect Account'}
              </button>
            </form>

            {/* Toggle */}
            <div className="mt-8 pt-8 border-t border-outline-variant/10 text-center">
              <p className="text-on-surface-variant text-sm">
                  {mode === 'login' ? 'New to the platform?' : 'Already have an account?'}
                  {mode === 'login' ? (
                    <button
                      onClick={() => router.push('/sign-up')}
                      className="text-primary font-semibold hover:underline decoration-primary/30 underline-offset-4 ml-1 transition-all"
                    >
                      Create Account
                    </button>
                  ) : (
                    <button
                      onClick={() => { setMode('login'); setError('') }}
                      className="text-primary font-semibold hover:underline decoration-primary/30 underline-offset-4 ml-1 transition-all"
                    >
                      Sign In
                    </button>
                  )}
              </p>
            </div>
          </div>

          {/* Trust badges */}
          <div className="mt-10 flex justify-center items-center gap-8 opacity-40">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-lg">security</span>
              <span className="text-[0.6875rem] uppercase tracking-widest font-label">SOC2 TYPE II</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-lg">lock</span>
              <span className="text-[0.6875rem] uppercase tracking-widest font-label">AES-256</span>
            </div>
          </div>
        </div>

        {/* Decorative rings */}
        <div className="absolute right-[-5%] top-[20%] opacity-15 pointer-events-none hidden lg:block">
          <div className="w-80 h-80 rounded-full border border-primary/20 flex items-center justify-center">
            <div className="w-60 h-60 rounded-full border border-primary/40 flex items-center justify-center">
              <div className="w-40 h-40 rounded-full border border-primary/60 flex items-center justify-center">
                <span className="material-symbols-outlined text-7xl text-primary/80">psychology</span>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* ── Footer ────────────────────────────────────────────── */}
      <footer className="w-full border-t border-outline-variant/10 bg-surface-container-lowest/60 flex flex-col md:flex-row justify-between items-center px-12 py-6 z-10 gap-4">
        <div>
          <span className="text-lg font-headline text-on-surface">VibeAnalytix</span>
          <p className="text-xs uppercase tracking-widest text-on-surface-variant mt-0.5">© 2024 VibeAnalytix. Neural Precision Engineering.</p>
        </div>
        <div className="flex gap-6">
          {['Security Architecture', 'SOC2 Compliance', 'API Docs'].map(l => (
            <a key={l} href="#" className="text-[10px] uppercase tracking-widest text-on-surface-variant hover:text-primary transition-colors">{l}</a>
          ))}
        </div>
      </footer>
    </div>
  )
}
