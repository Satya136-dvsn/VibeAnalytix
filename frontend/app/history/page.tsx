'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAppStore } from '@/lib/store'

// Shared sidebar nav component for app pages
function AppSidebar({ active }: { active: 'dashboard' | 'history' | 'settings' }) {
  const router = useRouter()
  const { user, logout } = useAppStore()

  const navItems = [
    { id: 'dashboard', icon: 'folder_open', label: 'Workspace', path: '/dashboard' },
    { id: 'history', icon: 'history', label: 'History', path: '/history' },
    { id: 'settings', icon: 'settings', label: 'Settings', path: '/settings' },
  ] as const

  return (
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
        {navItems.map(item => (
          <button
            key={item.id}
            onClick={() => router.push(item.path)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-150 ${
              active === item.id
                ? 'text-primary bg-primary/10 font-semibold'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]" style={active === item.id ? { fontVariationSettings: "'FILL' 1" } : {}}>{item.icon}</span>
            <span>{item.label}</span>
            {active === item.id && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary" />}
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
        <button
          onClick={() => { logout(); router.push('/') }}
          className="w-full flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-error transition-colors text-sm rounded-xl hover:bg-error/5"
        >
          <span className="material-symbols-outlined text-[20px]">logout</span>
          <span className="text-xs uppercase tracking-widest">Logout</span>
        </button>
      </div>
    </aside>
  )
}

// ── HISTORY PAGE ──────────────────────────────────────────────────────────────

type Filter = 'all' | 'completed' | 'in_progress' | 'failed'
type SortOrder = 'newest' | 'oldest' | 'duration'

export default function HistoryPage() {
  const router = useRouter()
  const { isAuthenticated, isLoading, getAllJobs } = useAppStore()
  const [filter, setFilter] = useState<Filter>('all')
  const [sort, setSort] = useState<SortOrder>('newest')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [jobs, setJobs] = useState<any[]>([])
  const [fetchingJobs, setFetchingJobs] = useState(true)

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/auth')
      return
    }
    
    if (isAuthenticated) {
      setFetchingJobs(true)
      getAllJobs()
        .then((data) => {
          // Format data to match UI expectations
          const formattedJobs = data.map((j: any) => {
            const created = new Date(j.created_at)
            const updated = new Date(j.updated_at)
            let duration = null
            if (j.status === 'completed' || j.status === 'failed') {
              const diffMs = updated.getTime() - created.getTime()
              const diffMins = Math.floor(diffMs / 60000)
              const diffSecs = Math.floor((diffMs % 60000) / 1000)
              duration = diffMins > 0 ? `${diffMins}m ${diffSecs}s` : `${diffSecs}s`
            }

            return {
              id: j.job_id,
              jobId: j.job_id,
              name: `Analysis - ${j.job_id.slice(0, 8)}`,
              status: j.status,
              progress: j.progress_pct,
              desc: j.error_message || (j.status === 'completed' ? 'Successfully analyzed repository logic and structure.' : `Stage: ${j.current_stage || 'Unknown'}`),
              date: created.toLocaleDateString(),
              time: created.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              duration,
              raw_created: created.getTime(),
              raw_duration: duration ? updated.getTime() - created.getTime() : 0,
            }
          })
          setJobs(formattedJobs)
          setFetchingJobs(false)
        })
        .catch((err) => {
          console.error('Failed to fetch jobs', err)
          setFetchingJobs(false)
        })
    }
  }, [isAuthenticated, isLoading, router])

  if (isLoading || !isAuthenticated) return null

  const filtered = jobs.filter(j => {
    if (filter !== 'all' && j.status !== filter) return false
    if (search && !j.name.toLowerCase().includes(search.toLowerCase())) return false
    return true
  }).sort((a, b) => {
    if (sort === 'newest') return b.raw_created - a.raw_created
    if (sort === 'oldest') return a.raw_created - b.raw_created
    if (sort === 'duration') return b.raw_duration - a.raw_duration
    return 0
  })

  const statusConfig = {
    completed: { color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20', label: 'Completed', icon: 'check_circle' },
    in_progress: { color: 'text-tertiary', bg: 'bg-tertiary/10 border-tertiary/20', label: 'In Progress', icon: 'pending' },
    queued: { color: 'text-tertiary', bg: 'bg-tertiary/10 border-tertiary/20', label: 'Queued', icon: 'hourglass_empty' },
    failed: { color: 'text-error', bg: 'bg-error/10 border-error/20', label: 'Failed', icon: 'error' },
  }

  return (
    <div className="flex min-h-screen bg-surface text-on-surface">
      <AppSidebar active="history" />

      <main className="flex-1 lg:ml-64 flex flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-30 glass-panel border-b border-outline-variant/10 flex items-center justify-between px-6 py-4 gap-4">
          <div className="flex items-center gap-6">
            <h1 className="font-headline text-xl italic text-on-surface hidden md:block">Intelligence Archive</h1>
            <nav className="hidden lg:flex items-center gap-1 text-sm">
              {(['all','completed','in_progress','failed'] as Filter[]).map(f => (
                <button
                  key={f}
                  onClick={() => { setFilter(f); setPage(1) }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all ${
                    filter === f ? 'bg-primary/15 text-primary' : 'text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  {f === 'all' ? 'All Jobs' : f === 'in_progress' ? 'In Progress' : f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-lg">search</span>
              <input
                type="text"
                value={search}
                onChange={e => { setSearch(e.target.value); setPage(1) }}
                placeholder="Search jobs..."
                className="bg-surface-container-highest border-none text-on-surface text-sm rounded-xl pl-10 pr-4 py-2 w-56 focus:ring-1 focus:ring-primary transition-all placeholder:text-on-surface-variant"
              />
            </div>
            <select
              value={sort}
              onChange={e => setSort(e.target.value as SortOrder)}
              className="bg-surface-container-highest border-none text-on-surface text-xs rounded-xl px-3 py-2.5 focus:ring-1 focus:ring-primary"
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="duration">By Duration</option>
            </select>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 px-6 py-8 max-w-5xl w-full mx-auto space-y-6">
          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Total Jobs', value: jobs.length.toString(), color: 'text-primary', icon: 'work' },
              { label: 'Completed', value: jobs.filter((j) => j.status === 'completed').length.toString(), color: 'text-emerald-400', icon: 'check_circle' },
              { label: 'In Progress', value: jobs.filter((j) => j.status === 'in_progress' || j.status === 'queued').length.toString(), color: 'text-tertiary', icon: 'pending' },
              { label: 'Failed', value: jobs.filter((j) => j.status === 'failed').length.toString(), color: 'text-error', icon: 'error' },
            ].map(s => (
              <div key={s.label} className="bg-surface-container-low rounded-xl p-4 border border-outline-variant/10 flex items-center gap-3">
                <span className={`material-symbols-outlined ${s.color}`} style={{ fontVariationSettings: "'FILL' 1" }}>{s.icon}</span>
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-on-surface-variant">{s.label}</p>
                  <p className={`text-xl font-semibold ${s.color}`}>{s.value}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Jobs list */}
          <div className="space-y-3">
            {fetchingJobs ? (
              <div className="bg-surface-container-low rounded-xl p-16 text-center border border-outline-variant/10">
                <span className="material-symbols-outlined text-5xl text-primary animate-spin mb-4 block">sync</span>
                <p className="text-on-surface-variant">Syncing with Intelligence Archive...</p>
              </div>
            ) : filtered.length === 0 ? (
              <div className="bg-surface-container-low rounded-xl p-16 text-center border border-outline-variant/10">
                <span className="material-symbols-outlined text-5xl text-on-surface-variant/30 mb-4 block">search_off</span>
                <p className="text-on-surface-variant">No jobs found matching your filters.</p>
                <button onClick={() => { setFilter('all'); setSearch('') }} className="btn-ghost mt-4 text-primary">Clear filters</button>
              </div>
            ) : filtered.map(job => {
              const cfg = statusConfig[job.status as keyof typeof statusConfig]
              return (
                <div
                  key={job.id}
                  onClick={() => job.status === 'completed' && router.push(`/jobs/${job.jobId}`)}
                  className={`group bg-surface-container-low hover:bg-surface-container-high transition-all duration-200 rounded-xl border border-outline-variant/10 hover:border-outline-variant/30 ${job.status === 'completed' ? 'cursor-pointer' : ''}`}
                >
                  <div className="p-5 flex flex-col md:flex-row gap-5 items-start md:items-center">
                    <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 border ${cfg.bg}`}>
                      <span className={`material-symbols-outlined ${cfg.color}`} style={job.status !== 'in_progress' ? { fontVariationSettings: "'FILL' 1" } : {}}>
                        {job.status === 'in_progress' ? 'pending' : cfg.icon}
                      </span>
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1 flex-wrap">
                        <h3 className="font-semibold text-on-surface truncate">{job.name}</h3>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${cfg.bg} ${cfg.color}`}>
                          {cfg.label}
                        </span>
                      </div>

                      {job.status === 'in_progress' && 'progress' in job ? (
                        <div className="mt-2 max-w-xs">
                          <div className="progress-track">
                            <div className="progress-fill" style={{ width: `${job.progress}%` }} />
                          </div>
                          <p className="text-[11px] text-on-surface-variant mt-1">{job.desc}</p>
                        </div>
                      ) : (
                        <p className={`text-sm leading-relaxed line-clamp-1 ${job.status === 'failed' ? 'text-error-dim' : 'text-on-surface-variant'}`}>{job.desc}</p>
                      )}

                      <div className="flex items-center gap-4 mt-2">
                        <span className="flex items-center gap-1 text-[11px] text-on-surface-variant/60 uppercase tracking-wider">
                          <span className="material-symbols-outlined text-xs">calendar_today</span>
                          {job.date} · {job.time}
                        </span>
                        {job.duration && (
                          <span className="flex items-center gap-1 text-[11px] text-on-surface-variant/60 uppercase tracking-wider">
                            <span className="material-symbols-outlined text-xs">timer</span>
                            {job.duration}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end md:self-center flex-shrink-0">
                      {job.status === 'completed' && (
                        <button className="px-4 py-2 text-xs font-semibold text-primary hover:bg-primary/10 rounded-lg transition-colors">
                          View Report
                        </button>
                      )}
                      {job.status === 'failed' && (
                        <button onClick={e => { e.stopPropagation(); router.push('/dashboard') }} className="px-4 py-2 text-xs font-semibold bg-surface-container-highest text-on-surface rounded-lg hover:bg-outline-variant/20 transition-colors">
                          Retry Job
                        </button>
                      )}
                      {job.status === 'in_progress' && (
                        <button className="px-4 py-2 text-xs font-semibold text-on-surface-variant hover:text-error rounded-lg transition-colors">
                          Cancel
                        </button>
                      )}
                      {job.status === 'completed' && (
                        <span className="material-symbols-outlined text-on-surface-variant opacity-0 group-hover:opacity-100 transition-opacity">chevron_right</span>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Pagination */}
          <div className="flex justify-between items-center pt-4 border-t border-outline-variant/10">
            <p className="text-xs text-on-surface-variant">
              Showing {filtered.length} of {jobs.length} results
            </p>
            <div className="flex gap-2">
              {[1, 2, 3].map(p => (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`w-9 h-9 rounded-lg text-xs font-bold transition-colors ${
                    page === p ? 'bg-surface-container-highest text-on-surface' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container-highest'
                  }`}
                >
                  {p}
                </button>
              ))}
              <button className="w-9 h-9 flex items-center justify-center rounded-lg bg-surface-container-low text-on-surface-variant hover:bg-surface-container-highest transition-colors">
                <span className="material-symbols-outlined text-sm">chevron_right</span>
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
