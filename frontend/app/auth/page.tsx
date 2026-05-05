'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAppStore } from '@/lib/store'

export default function AuthPage() {
  const router = useRouter()
  const { isAuthenticated, login } = useAppStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
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
      await login(email, password)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'Authentication failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="va-landing min-h-screen flex flex-col selection:bg-cyan-200 selection:text-slate-950">
      <div className="va-grid-overlay" aria-hidden="true" />

      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="relative z-20 border-b border-slate-200/60 bg-white/75 backdrop-blur-xl transition-all duration-300">
        <nav className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-6 lg:px-10">
          <Link href="/" className="font-headline text-xl font-semibold tracking-tight text-slate-950 group hover:text-cyan-700 transition-colors duration-200">
            VibeAnalytix
          </Link>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-slate-500 sm:block">New to the platform?</span>
            <Link
              href="/sign-up"
              className="rounded-lg bg-gradient-to-r from-cyan-600 to-cyan-500 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-cyan-600/30 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-cyan-600/40 active:scale-95"
            >
              Create account
            </Link>
          </div>
        </nav>
      </header>

      {/* ── Main ───────────────────────────────────────────────── */}
      <main className="relative z-10 flex flex-grow items-center justify-center px-6 py-12">

        {/* Decorative orbs anchored to main */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute left-[-8%] top-[-5%] h-72 w-72 rounded-full blur-[90px]"
          style={{ background: 'rgba(34,211,238,0.18)' }}
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute right-[-8%] bottom-[-5%] h-64 w-64 rounded-full blur-[80px]"
          style={{ background: 'rgba(251,191,36,0.16)' }}
        />

        <div className="va-fade-in-up w-full max-w-md">

          {/* Badge + heading */}
          <div className="mb-10 text-center space-y-4">
            <p className="inline-flex rounded-full border border-cyan-400/60 bg-cyan-100/80 px-4 py-1 text-xs font-bold uppercase tracking-[0.2em] text-cyan-800 shadow-md shadow-cyan-300/20 hover:shadow-lg hover:shadow-cyan-400/30 transition-all duration-200">
              Welcome back
            </p>
            <h1 className="font-headline text-4xl leading-tight text-slate-950 md:text-5xl hover:text-transparent hover:bg-clip-text hover:bg-gradient-to-r hover:from-cyan-700 hover:to-cyan-600 transition-all duration-300">
              Access Neural Analytics
            </h1>
            <p className="mx-auto max-w-xs text-sm leading-relaxed text-slate-500 hover:text-slate-600 transition-colors duration-200">
              Continue your codebase exploration with deliberate intelligence.
            </p>
          </div>

          {/* Card */}
          <div className="light-card p-8 hover:shadow-lg hover:shadow-cyan-300/15 transition-all duration-300">

            {/* Error */}
            {error && (
              <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                <svg className="mt-0.5 h-5 w-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M12 3a9 9 0 110 18A9 9 0 0112 3z" />
                </svg>
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">

              {/* Email */}
              <div className="space-y-2">
                <label
                  className="ml-0.5 block text-[0.6875rem] font-bold uppercase tracking-widest text-slate-500"
                  htmlFor="auth-email"
                >
                  Email
                </label>
                <input
                  id="auth-email"
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  placeholder="architect@vibeanalytix.io"
                  className="light-input"
                />
              </div>

              {/* Password */}
              <div className="space-y-2">
                <div className="flex items-end justify-between">
                  <label
                    className="ml-0.5 block text-[0.6875rem] font-bold uppercase tracking-widest text-slate-500"
                    htmlFor="auth-password"
                  >
                    Password
                  </label>
                  <a
                    href="/forgot-password"
                    className="text-[0.6875rem] font-bold uppercase tracking-widest text-cyan-700 transition-colors hover:text-cyan-900"
                  >
                    Forgot Password
                  </a>
                </div>
                <div className="relative">
                  <input
                    id="auth-password"
                    type={showPass ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    minLength={8}
                    placeholder="••••••••"
                    className="light-input pr-12"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(!showPass)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 transition-colors hover:text-slate-700"
                    aria-label="Toggle password visibility"
                  >
                    <span className="material-symbols-outlined text-xl">
                      {showPass ? 'visibility' : 'visibility_off'}
                    </span>
                  </button>
                </div>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="light-btn-primary mt-2 bg-gradient-to-r from-slate-800 to-slate-700 hover:from-slate-700 hover:to-slate-600 shadow-lg shadow-slate-900/30 hover:shadow-xl hover:shadow-slate-900/40"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    Signing in…
                  </span>
                ) : 'Sign In'}
              </button>
            </form>

            {/* Toggle to sign-up */}
            <div className="mt-8 border-t border-slate-100 pt-8 text-center">
              <p className="text-sm text-slate-500">
                New to the platform?{' '}
                <button
                  onClick={() => router.push('/sign-up')}
                  className="font-semibold text-slate-900 underline-offset-4 transition-all hover:underline"
                >
                  Create Account
                </button>
              </p>
            </div>
          </div>


        </div>
      </main>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer className="relative z-10 border-t border-slate-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex w-full max-w-7xl flex-col items-start justify-between gap-4 px-6 py-7 md:flex-row md:items-center lg:px-10">
          <p className="font-headline font-semibold text-slate-700">VibeAnalytix</p>
          <p className="text-xs text-slate-400">© 2024 VibeAnalytix. Neural Precision Engineering.</p>
          <div className="flex gap-6">
            {['Security', 'SOC2', 'API Docs'].map(l => (
              <a key={l} href="#" className="text-[10px] font-bold uppercase tracking-widest text-slate-400 transition-colors hover:text-slate-700">
                {l}
              </a>
            ))}
          </div>
        </div>
      </footer>
    </div>
  )
}
