'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAppStore } from '@/lib/store'
import { Github, Upload, LogOut, CheckCircle2, AlertCircle, FileArchive } from 'lucide-react'

export default function SubmissionPage() {
  const router = useRouter()
  const { isAuthenticated, isLoading, user, logout, submitJob, pollJobStatus, getAllJobs } = useAppStore()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/auth')
      return
    }

    if (!isLoading && isAuthenticated) {
      getAllJobs().then(data => {
        const formatted = data.slice(0, 3).map((j: any) => ({
          id: j.job_id,
          name: j.github_url ? j.github_url.split('/').pop() : 'Project Archive',
          status: j.status,
          progress: j.progress_pct,
          updated_at: new Date(j.updated_at).toLocaleDateString()
        }));
        setRecentJobs(formatted);
      }).catch(console.error);
    }
  }, [isAuthenticated, isLoading, router, getAllJobs])

  const [loading, setLoading] = useState(false)
  const [githubUrl, setGithubUrl] = useState('')
  const [zipFile, setZipFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [mode, setMode] = useState<'github' | 'zip'>('github')
  const [recentJobs, setRecentJobs] = useState<any[]>([])

  const handleSubmitGithub = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const formData = new FormData()
      formData.append('github_url', githubUrl)

      const jobId = await submitJob(formData)
      router.push(`/jobs/${jobId}`)
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'Failed to submit job')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitZip = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    if (!zipFile) {
      setError('Please select a ZIP file')
      setLoading(false)
      return
    }

    try {
      const formData = new FormData()
      formData.append('zip_file', zipFile)

      const jobId = await submitJob(formData)
      router.push(`/jobs/${jobId}`)
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'Failed to submit job')
    } finally {
      setLoading(false)
    }
  }

  if (isLoading || !isAuthenticated) {
    return null
  }

  return (
    <div className="flex min-h-screen bg-background text-on-background">
      {/* ── Side NavBar ────────────────────────────────────────── */}
      <aside className="fixed top-0 left-0 h-screen w-64 bg-surface-container-low border-r border-outline-variant/10 flex flex-col py-6 px-4 gap-6 z-40 hidden lg:flex">
        {/* Brand */}
        <div className="flex items-center gap-3 px-2 mb-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-primary to-primary-dim flex items-center justify-center">
            <span className="material-symbols-outlined text-on-primary text-base" style={{ fontVariationSettings: "'FILL' 1" }}>psychology</span>
          </div>
          <div>
            <span className="font-headline text-lg italic text-on-surface">VibeAnalytix</span>
            <p className="text-[10px] uppercase tracking-[0.2em] text-primary">Neural Engine</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-1">
          {([
            { id: 'dashboard', icon: 'folder_open', label: 'Workspace', path: '/dashboard' },
            { id: 'history', icon: 'history', label: 'History', path: '/history' },
            { id: 'settings', icon: 'settings', label: 'Settings', path: '/settings' },
          ] as const).map(item => (
            <button
              key={item.id}
              onClick={() => router.push(item.path)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-150 ${
                item.id === 'dashboard'
                  ? 'text-primary bg-primary/10 font-semibold'
                  : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]" style={item.id === 'dashboard' ? { fontVariationSettings: "'FILL' 1" } : {}}>{item.icon}</span>
              <span>{item.label}</span>
              {item.id === 'dashboard' && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary" />}
            </button>
          ))}
        </nav>

        {/* User section */}
        <div className="mt-auto space-y-3">
          <div className="px-3 py-4 bg-surface-container rounded-xl border border-outline-variant/10">
            <p className="text-[10px] text-on-surface-variant uppercase tracking-widest mb-1 truncate">{user?.email ?? 'Architect'}</p>
            <p className="text-xs text-primary font-medium flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              Neural Engine Active
            </p>
          </div>
          <button onClick={logout} className="w-full flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-error transition-colors text-sm rounded-xl hover:bg-error/5">
            <LogOut size={18} />
            <span className="text-xs uppercase tracking-widest">Logout</span>
          </button>
        </div>
      </aside>


      {/* ── Main Content ───────────────────────────────────────── */}
      <main className="flex-grow flex flex-col min-h-screen relative overflow-hidden lg:ml-64">
        {/* Background Ambient Glows */}
        <div className="absolute top-[-10%] right-[-5%] w-[400px] h-[400px] bg-primary/10 rounded-full blur-[120px] pointer-events-none"></div>

        {/* ── Header ───────────────────────────────────────────── */}
        <header className="h-16 flex justify-between items-center px-8 w-full sticky top-0 z-50 glass-panel border-b border-outline-variant/10">
          <nav className="hidden md:flex gap-6">
            <a href="#" className="text-primary font-semibold border-b-2 border-primary text-sm py-5">Dashboard</a>
            <a href="#" className="text-on-surface-variant hover:text-on-surface text-sm py-5 transition-all">Platform</a>
          </nav>
          <div className="flex items-center gap-4">
             <div className="relative hidden sm:block">
               <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-lg">search</span>
               <input type="text" placeholder="Search architecture..." className="bg-surface-container-highest border-none rounded-full py-1.5 pl-10 pr-4 text-xs focus:ring-1 focus:ring-primary w-64 transition-all text-on-surface placeholder:text-on-surface-variant" />
             </div>
          </div>
        </header>

        <div className="flex-grow max-w-5xl mx-auto w-full px-8 py-12 relative z-10 animate-fade-up">

          {/* ── Hero ───────────────────────────────────────────── */}
          <section className="mb-16">
            <div className="mb-12">
              <h2 className="font-headline text-4xl mb-2 text-on-surface">Welcome back, <span className="text-primary italic">Developer.</span></h2>
              <p className="text-on-surface-variant text-sm tracking-tight">Initialize neural engine for deep repository inspection.</p>
            </div>

            {error && (
              <div className="alert-error mb-6">
                <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <div className="max-w-3xl">
              <div className="bg-surface-container-low rounded-2xl p-1 border border-outline-variant/15 neural-glow backdrop-blur-md relative overflow-hidden">
                <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-primary/5 to-transparent pointer-events-none"></div>
                
                {/* Mode Selectors */}
                <div className="flex gap-1 mb-1 z-10 relative">
                  <button
                    onClick={() => setMode('github')}
                    className={`flex-1 py-3 text-xs font-bold uppercase tracking-widest rounded-xl transition-all ${
                      mode === 'github'
                        ? 'text-primary bg-surface-container-highest shadow-inner'
                        : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
                    }`}
                  >
                    <Github className="inline-block mr-2 w-4 h-4 mb-0.5" />
                    GitHub Repository
                  </button>
                  <button
                    onClick={() => setMode('zip')}
                    className={`flex-1 py-3 text-xs font-bold uppercase tracking-widest rounded-xl transition-all ${
                      mode === 'zip'
                        ? 'text-primary bg-surface-container-highest shadow-inner'
                        : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
                    }`}
                  >
                    <FileArchive className="inline-block mr-2 w-4 h-4 mb-0.5" />
                    Upload ZIP
                  </button>
                </div>

                {/* Form Area */}
                <div className="p-8 relative z-10">
                  {mode === 'github' ? (
                    <form onSubmit={handleSubmitGithub} className="space-y-6">
                      <div className="relative">
                        <label className="section-label absolute -top-2 left-4 bg-surface-container-low px-2 z-10">Repository Endpoint</label>
                        <input
                          type="url"
                          value={githubUrl}
                          onChange={(e) => setGithubUrl(e.target.value)}
                          placeholder="https://github.com/user/repo"
                          required
                          className="w-full bg-surface-container-lowest border border-outline-variant/20 rounded-xl py-4 px-6 text-on-surface focus:ring-1 focus:ring-primary transition-all font-mono text-sm placeholder:text-outline-variant"
                        />
                      </div>
                      <div className="flex flex-col items-center pt-2">
                        <button type="submit" disabled={loading || !githubUrl} className="group relative px-12 py-4 bg-gradient-to-r from-primary to-primary-dim rounded-xl text-on-primary font-bold tracking-tight transition-all active:scale-95 shadow-[0_0_30px_rgba(182,160,255,0.3)] disabled:opacity-50 disabled:cursor-not-allowed">
                          <div className="absolute inset-0 rounded-xl bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                          <span className="relative flex items-center gap-3">
                            {loading ? 'INITIALIZING NEURAL ENGINE...' : 'START DEEP ANALYSIS'}
                            <span className={`material-symbols-outlined text-xl ${loading ? 'animate-spin' : 'animate-pulse'}`}>psychology</span>
                          </span>
                        </button>
                        <p className="mt-4 text-[10px] text-on-surface-variant uppercase tracking-[0.3em]">Neural Precision Engine v4.2.0</p>
                      </div>
                    </form>
                  ) : (
                    <form onSubmit={handleSubmitZip} className="space-y-6">
                      <div className="relative">
                        <label className="section-label absolute -top-2 left-4 bg-surface-container-low px-2 z-10">Archive Upload</label>
                        <div className="w-full bg-surface-container-lowest border-2 border-dashed border-outline-variant/20 rounded-xl py-12 px-6 text-center hover:border-primary/50 transition-all group">
                          <input
                            type="file"
                            accept=".zip"
                            onChange={(e) => setZipFile(e.target.files?.[0] || null)}
                            required
                            className="hidden"
                            id="zip-upload"
                          />
                          <label htmlFor="zip-upload" className="cursor-pointer flex flex-col items-center">
                            <Upload className="w-8 h-8 text-on-surface-variant group-hover:text-primary transition-colors mb-3" />
                            <p className="text-sm font-medium text-on-surface mb-1">
                              {zipFile ? zipFile.name : 'Click to select project archive'}
                            </p>
                            <p className="text-xs text-on-surface-variant">ZIP format only (Max 100MB)</p>
                          </label>
                        </div>
                      </div>
                      <div className="flex flex-col items-center pt-2">
                        <button type="submit" disabled={loading || !zipFile} className="group relative px-12 py-4 bg-gradient-to-r from-primary to-primary-dim rounded-xl text-on-primary font-bold tracking-tight transition-all active:scale-95 shadow-[0_0_30px_rgba(182,160,255,0.3)] disabled:opacity-50 disabled:cursor-not-allowed">
                          <div className="absolute inset-0 rounded-xl bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                          <span className="relative flex items-center gap-3">
                            {loading ? 'UPLOADING ARCHIVE...' : 'START DEEP ANALYSIS'}
                            <span className={`material-symbols-outlined text-xl ${loading ? 'animate-spin' : 'animate-pulse'}`}>psychology</span>
                          </span>
                        </button>
                        <p className="mt-4 text-[10px] text-on-surface-variant uppercase tracking-[0.3em]">Neural Precision Engine v4.2.0</p>
                      </div>
                    </form>
                  )}
                </div>
              </div>
            </div>
          </section>

          <section className="mb-16">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-headline italic text-on-surface">Recent Intelligence Reports</h3>
              <div className="flex gap-2">
                <button className="px-3 py-1 text-[10px] uppercase tracking-widest text-on-surface-variant hover:text-primary transition-colors">All Projects</button>
                <button className="px-3 py-1 text-[10px] uppercase tracking-widest text-primary bg-primary/10 rounded-full border border-primary/20">Active Analysis</button>
              </div>
            </div>

            <div className="space-y-3">
              {recentJobs.length === 0 ? (
                <div className="card p-12 text-center border-dashed border-outline-variant/30 bg-transparent">
                  <span className="material-symbols-outlined text-4xl text-on-surface-variant/20 mb-2">analytics</span>
                  <p className="text-sm text-on-surface-variant">No recent analysis deployment detected in neural registry.</p>
                </div>
              ) : (
                recentJobs.map((job) => (
                  <div 
                    key={job.id} 
                    onClick={() => job.status === 'completed' && router.push(`/jobs/${job.id}`)}
                    className="card p-4 flex items-center gap-6 hover:bg-surface-container-high transition-all cursor-pointer group"
                  >
                    <div className="w-12 h-12 rounded-xl bg-slate-900 border border-outline-variant/10 flex items-center justify-center text-on-surface-variant group-hover:text-primary transition-colors">
                      <span className="material-symbols-outlined">{job.status === 'completed' ? 'terminal' : 'account_tree'}</span>
                    </div>
                    <div className="flex-1">
                      <h4 className="text-sm font-semibold text-on-surface mb-0.5">{job.name}</h4>
                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-1.5">
                          <span className={`w-1.5 h-1.5 rounded-full ${job.status === 'completed' ? 'bg-emerald-400' : 'bg-primary animate-pulse'}`} />
                          <span className="text-[10px] uppercase tracking-wider text-on-surface-variant">{job.status === 'completed' ? 'Success' : 'Processing'}</span>
                        </span>
                        <span className="text-[10px] text-outline/40 uppercase tracking-widest">Modified {job.updated_at}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      {job.status !== 'completed' && (
                        <div className="mb-1">
                          <div className="w-24 h-1 bg-surface-container-highest rounded-full overflow-hidden">
                            <div className="h-full bg-primary" style={{ width: `${job.progress}%` }} />
                          </div>
                          <p className="text-[9px] text-primary mt-1 uppercase tracking-widest">{job.progress}% Deep structural scan</p>
                        </div>
                      )}
                      {job.status === 'completed' ? (
                         <span className="text-[10px] text-primary font-bold uppercase tracking-widest group-hover:underline">View Results</span>
                      ) : (
                        <span className="material-symbols-outlined text-on-surface-variant animate-spin text-sm">sync</span>
                      )}
                    </div>
                    <span className="material-symbols-outlined text-on-surface-variant/30 group-hover:text-on-surface transition-colors">more_vert</span>
                  </div>
                ))
              )}
            </div>
          </section>

          {/* ── Features Info ────────────────────────────────────── */}
          <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="card p-6 border-transparent bg-surface-container">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary mb-4 border border-primary/20">
                <span className="material-symbols-outlined">bolt</span>
              </div>
              <h3 className="font-semibold text-on-surface mb-2 tracking-tight">Fast Analysis</h3>
              <p className="text-sm text-on-surface-variant leading-relaxed">
                Get results in minutes with our optimized multi-pass parsing architecture.
              </p>
            </div>
            <div className="card p-6 border-transparent bg-surface-container">
              <div className="w-10 h-10 rounded-lg bg-tertiary/10 flex items-center justify-center text-tertiary mb-4 border border-tertiary/20">
                <span className="material-symbols-outlined">psychology</span>
              </div>
              <h3 className="font-semibold text-on-surface mb-2 tracking-tight">AI-Powered</h3>
              <p className="text-sm text-on-surface-variant leading-relaxed">
                Advanced understanding leveraging the latest LLMs and semantic embeddings.
              </p>
            </div>
            <div className="card p-6 border-transparent bg-surface-container">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 mb-4 border border-emerald-500/20">
                <span className="material-symbols-outlined">account_tree</span>
              </div>
              <h3 className="font-semibold text-on-surface mb-2 tracking-tight">Complete View</h3>
              <p className="text-sm text-on-surface-variant leading-relaxed">
                See high-level overviews, granular file structures, and execution flows seamlessly.
              </p>
            </div>
          </section>

        </div>
        
        {/* ── Footer ───────────────────────────────────────────── */}
        <footer className="w-full bg-slate-950 border-t border-outline-variant/10 flex flex-col md:flex-row justify-between items-center px-12 py-6 mt-auto shrink-0 z-10">
          <div className="mb-4 md:mb-0">
            <span className="text-lg font-headline italic text-slate-100">VibeAnalytix</span>
            <p className="text-[10px] uppercase tracking-[0.25em] text-slate-500 mt-1">© 2024 VibeAnalytix. Neural Precision Engineering.</p>
          </div>
          <div className="flex gap-6">
            <a href="#" className="text-[10px] uppercase tracking-widest text-slate-500 hover:text-primary transition-colors">Security Architecture</a>
            <a href="#" className="text-[10px] uppercase tracking-widest text-slate-500 hover:text-primary transition-colors">Terminal Details</a>
          </div>
        </footer>
      </main>
    </div>
  )
}
