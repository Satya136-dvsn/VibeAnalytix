'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
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
  const strengthColors = ['', 'bg-error', 'bg-yellow-500', 'bg-tertiary', 'bg-emerald-400']

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

  return (
    <div className="min-h-screen bg-surface text-on-surface flex flex-col">
      {/* Ambient glows */}
      <div className="fixed top-[-15%] left-[-10%] w-[600px] h-[600px] bg-primary/8 rounded-full blur-[140px] pointer-events-none" />
      <div className="fixed bottom-[-15%] right-[-10%] w-[500px] h-[500px] bg-tertiary/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 glass-panel border-b border-outline-variant/10 flex justify-between items-center px-8 py-4">
        <button onClick={() => router.push('/')} className="text-2xl font-headline italic text-on-surface hover:text-primary transition-colors">
          VibeAnalytix
        </button>
        <div className="flex items-center gap-4">
          <span className="text-sm text-on-surface-variant">Already an architect?</span>
          <button onClick={() => router.push('/auth')} className="btn-secondary text-sm px-5 py-2">
            Sign In
          </button>
        </div>
      </nav>

      <main className="flex-grow flex pt-24 pb-12">
        <div className="max-w-6xl w-full mx-auto px-6 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">

          {/* Left: Form */}
          <div className="space-y-8 animate-fade-up">
            <div className="space-y-3">
              <span className="text-[11px] uppercase tracking-[0.3em] text-primary font-bold">Free Forever Plan</span>
              <h1 className="text-5xl font-headline leading-tight text-on-surface">
                Engineer Your<br /><span className="italic text-primary">Understanding.</span>
              </h1>
              <p className="text-on-surface-variant leading-relaxed max-w-md">
                Join 2,000+ developers who transform complex repositories into clear, structured narratives with neural precision.
              </p>
            </div>

            <div className="bg-surface-container-low rounded-2xl p-8 border border-outline-variant/10 neural-glow">
              {error && (
                <div className="alert-error mb-6">
                  <span className="material-symbols-outlined text-lg flex-shrink-0">error</span>
                  <span>{error}</span>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="space-y-2">
                  <label className="section-label">Full Name</label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="Nikola Tesla"
                    className="input-field"
                  />
                </div>

                <div className="space-y-2">
                  <label className="section-label">Work Email</label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                    placeholder="nikola@wardenclyffe.io"
                    required
                    className="input-field"
                  />
                </div>

                <div className="space-y-2">
                  <label className="section-label">Password</label>
                  <div className="relative">
                    <input
                      type={showPass ? 'text' : 'password'}
                      value={form.password}
                      onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                      placeholder="Min. 8 characters"
                      required
                      className="input-field pr-12"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPass(!showPass)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-primary transition-colors"
                    >
                      <span className="material-symbols-outlined text-xl">{showPass ? 'visibility' : 'visibility_off'}</span>
                    </button>
                  </div>
                  {form.password && (
                    <div className="space-y-1.5 pt-1">
                      <div className="flex gap-1">
                        {[1,2,3,4].map(i => (
                          <div key={i} className={`h-1 flex-1 rounded-full transition-all duration-300 ${i <= strength ? strengthColors[strength] : 'bg-surface-container-highest'}`} />
                        ))}
                      </div>
                      <p className="text-[11px] text-on-surface-variant">{strengthLabels[strength]}</p>
                    </div>
                  )}
                </div>

                <div className="pt-2">
                  <button type="submit" disabled={loading} className="btn-primary w-full py-4 text-base rounded-xl">
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <span className="w-4 h-4 border-2 border-on-primary/30 border-t-on-primary rounded-full animate-spin" />
                        Creating Your Workspace...
                      </span>
                    ) : 'Create Architect Account'}
                  </button>
                </div>

                <p className="text-[11px] text-on-surface-variant text-center leading-relaxed">
                  By creating an account, you agree to our <span className="text-primary cursor-pointer hover:underline">Terms of Service</span> and <span className="text-primary cursor-pointer hover:underline">Privacy Policy</span>.
                </p>
              </form>
            </div>
          </div>

          {/* Right: Features */}
          <div className="hidden lg:flex flex-col gap-6 animate-fade-up" style={{ animationDelay: '0.1s' }}>
            <div className="bg-surface-container-low rounded-2xl p-8 border border-outline-variant/10 space-y-8">
              <h3 className="font-headline text-2xl italic text-on-surface">Precision Architecture</h3>
              {[
                { icon: 'verified_user', title: 'SOC2 Compliance', desc: 'Enterprise-grade security protocols ensuring your architectural data is strictly audited and protected at every layer.' },
                { icon: 'security', title: 'Sandboxed Ingestion', desc: 'Repositories are analyzed in ephemeral isolated environments. No code ever leaves the secure perimeter — guaranteed.' },
                { icon: 'psychology', title: 'Neural Multi-Pass', desc: 'Recursive AI passes map every edge case, dependency chain, and logical flow before synthesizing final intelligence.' },
              ].map(f => (
                <div key={f.title} className="flex gap-4">
                  <div className="flex-shrink-0 w-11 h-11 bg-primary/10 rounded-xl flex items-center justify-center text-primary border border-primary/20">
                    <span className="material-symbols-outlined">{f.icon}</span>
                  </div>
                  <div>
                    <h4 className="font-semibold text-on-surface mb-1">{f.title}</h4>
                    <p className="text-sm text-on-surface-variant leading-relaxed">{f.desc}</p>
                  </div>
                </div>
              ))}
            </div>

            <blockquote className="glass-panel rounded-2xl p-6 border border-outline-variant/10">
              <p className="italic font-headline text-on-surface-variant leading-relaxed mb-4">
                "VibeAnalytix fundamentally shifted how our team discovers patterns in legacy systems. An indispensable tool for technical intelligence."
              </p>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-primary to-primary-dim flex items-center justify-center text-sm font-bold text-on-primary">MC</div>
                <div>
                  <p className="text-sm font-bold text-on-surface">Marcus Chen</p>
                  <p className="text-[10px] uppercase tracking-widest text-primary">CTO, NeuralScale</p>
                </div>
              </div>
            </blockquote>
          </div>

        </div>
      </main>
    </div>
  )
}
