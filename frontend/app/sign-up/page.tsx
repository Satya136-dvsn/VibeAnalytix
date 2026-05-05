'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAppStore } from '@/lib/store'

export default function SignUpPage() {
  const router = useRouter()
  const { register } = useAppStore()
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const strengthen = (p: string) => {
    let score = 0
    if (p.length >= 8) score++
    if (/[A-Z]/.test(p)) score++
    if (/[0-9]/.test(p)) score++
    if (/[^A-Za-z0-9]/.test(p)) score++
    return score
  }

  const strength = strengthen(form.password)
  const strengthLabels = ['', 'Weak', 'Fair', 'Good', 'Strong']
  const strengthColors = ['', 'bg-red-400', 'bg-amber-400', 'bg-cyan-500', 'bg-emerald-500']

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.password.length < 8) { setError('Password must be at least 8 characters'); return }
    setLoading(true)
    setError('')
    try {
      await register(form.email, form.password)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const features = [
    {
      icon: 'verified_user',
      title: 'SOC2 Compliant',
      desc: 'Enterprise-grade security protocols ensuring your code is strictly audited and protected at every layer.',
    },
    {
      icon: 'security',
      title: 'Sandboxed Ingestion',
      desc: 'Repositories are analyzed in isolated environments. No code ever leaves the secure perimeter.',
    },
    {
      icon: 'psychology',
      title: 'Neural Multi-Pass',
      desc: 'AI passes map every dependency chain and logical flow before synthesizing final intelligence.',
    },
  ]

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
            <span className="hidden text-sm text-slate-500 sm:block">Already an architect?</span>
            <Link
              href="/auth"
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition-all duration-200 hover:bg-slate-50 hover:border-slate-400 hover:shadow-md hover:shadow-slate-300/20 active:scale-95"
            >
              Sign In
            </Link>
          </div>
        </nav>
      </header>

      {/* ── Main ───────────────────────────────────────────────── */}
      <main className="relative z-10 flex flex-grow items-start justify-center px-6 py-12">

        {/* Decorative orbs */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute left-[-6%] top-[-4%] h-80 w-80 rounded-full blur-[100px]"
          style={{ background: 'rgba(34,211,238,0.16)' }}
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute right-[-6%] bottom-[-4%] h-72 w-72 rounded-full blur-[90px]"
          style={{ background: 'rgba(251,191,36,0.14)' }}
        />

        <div className="mx-auto grid w-full max-w-6xl grid-cols-1 items-start gap-12 lg:grid-cols-2 lg:gap-16">

          {/* ── Left: Form ─────────────────────────────────────── */}
          <div className="va-fade-in-up space-y-8">
            <div className="space-y-4">
              <p className="inline-flex rounded-full border border-cyan-400/60 bg-cyan-100/80 px-4 py-1 text-xs font-bold uppercase tracking-[0.2em] text-cyan-800 shadow-md shadow-cyan-300/20 hover:shadow-lg hover:shadow-cyan-400/30 transition-all duration-200">
                Free Forever Plan
              </p>
              <h1 className="font-headline text-5xl leading-tight text-slate-950 hover:text-transparent hover:bg-clip-text hover:bg-gradient-to-r hover:from-cyan-700 hover:to-cyan-600 transition-all duration-300">
                Engineer Your{' '}
                <span className="italic text-cyan-700">Understanding.</span>
              </h1>
              <p className="max-w-md leading-relaxed text-slate-500 hover:text-slate-600 transition-colors duration-200">
                Join developers who transform complex repositories into clear, structured narratives with neural precision.
              </p>
            </div>

            {/* Form card */}
            <div className="light-card p-8 hover:shadow-lg hover:shadow-cyan-300/15 transition-all duration-300">

              {error && (
                <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                  <span className="material-symbols-outlined flex-shrink-0 text-lg">error</span>
                  <span>{error}</span>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">

                {/* Full name */}
                <div className="space-y-2">
                  <label className="ml-0.5 block text-[0.6875rem] font-bold uppercase tracking-widest text-slate-500">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="Nikola Tesla"
                    className="light-input"
                  />
                </div>

                {/* Work email */}
                <div className="space-y-2">
                  <label className="ml-0.5 block text-[0.6875rem] font-bold uppercase tracking-widest text-slate-500">
                    Work Email
                  </label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                    placeholder="nikola@wardenclyffe.io"
                    required
                    className="light-input"
                  />
                </div>

                {/* Password */}
                <div className="space-y-2">
                  <label className="ml-0.5 block text-[0.6875rem] font-bold uppercase tracking-widest text-slate-500">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPass ? 'text' : 'password'}
                      value={form.password}
                      onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                      placeholder="Min. 8 characters"
                      required
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

                  {/* Password strength */}
                  {form.password && (
                    <div className="space-y-1.5 pt-1">
                      <div className="flex gap-1">
                        {[1, 2, 3, 4].map(i => (
                          <div
                            key={i}
                            className={`h-1.5 flex-1 rounded-full transition-all duration-300 shadow-sm ${
                              i <= strength ? strengthColors[strength] + ' shadow-md' : 'bg-slate-200'
                            }`}
                          />
                        ))}
                      </div>
                      <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
                        {strengthLabels[strength]}
                      </p>
                    </div>
                  )}
                </div>

                {/* Submit */}
                <div className="pt-2">
                  <button type="submit" disabled={loading} className="light-btn-primary">
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <span className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                        Creating Your Workspace…
                      </span>
                    ) : 'Create Architect Account'}
                  </button>
                </div>

                <p className="text-center text-[11px] leading-relaxed text-slate-400">
                  By creating an account, you agree to our{' '}
                  <span className="cursor-pointer text-slate-600 hover:underline">Terms of Service</span>{' '}
                  and{' '}
                  <span className="cursor-pointer text-slate-600 hover:underline">Privacy Policy</span>.
                </p>
              </form>
            </div>
          </div>

          {/* ── Right: Trust panel ─────────────────────────────── */}
          <div
            className="hidden flex-col gap-6 lg:flex va-fade-in-up-delay"
          >
            {/* Feature list */}
            <div className="light-card p-8 space-y-8">
              <h2 className="font-headline text-2xl italic text-slate-950">
                Precision Architecture
              </h2>
              {features.map(f => (
                <div key={f.title} className="flex gap-4">
                  <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl border border-cyan-200 bg-cyan-50 text-cyan-700">
                    <span className="material-symbols-outlined">{f.icon}</span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-900">{f.title}</h3>
                    <p className="mt-1 text-sm leading-relaxed text-slate-500">{f.desc}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Testimonial */}
            <blockquote className="light-card p-6">
              <p className="font-headline italic leading-relaxed text-slate-500">
                &ldquo;VibeAnalytix fundamentally shifted how our team discovers patterns in legacy systems.
                An indispensable tool for technical intelligence.&rdquo;
              </p>
              <div className="mt-5 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-950 text-sm font-bold text-white">
                  MC
                </div>
                <div>
                  <p className="text-sm font-bold text-slate-900">Marcus Chen</p>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-cyan-700">CTO, NeuralScale</p>
                </div>
              </div>
            </blockquote>


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
