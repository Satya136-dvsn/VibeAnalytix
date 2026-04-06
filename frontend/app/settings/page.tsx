'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAppStore } from '@/lib/store'

// Shared sidebar (same as history)
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
      <div className="flex items-center gap-3 px-2 mb-2">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-primary to-primary-dim flex items-center justify-center">
          <span className="material-symbols-outlined text-on-primary text-base" style={{ fontVariationSettings: "'FILL' 1" }}>psychology</span>
        </div>
        <div>
          <span className="font-headline text-lg italic text-on-surface">VibeAnalytix</span>
          <p className="text-[10px] uppercase tracking-[0.2em] text-primary">Neural Engine</p>
        </div>
      </div>

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

// Toggle component
function Toggle({ enabled, onToggle }: { enabled: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className={`relative w-11 h-6 rounded-full transition-all duration-300 ${enabled ? 'bg-primary' : 'bg-surface-container-highest'}`}
    >
      <div className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-all duration-300 ${enabled ? 'left-6' : 'left-1'}`} />
    </button>
  )
}

export default function SettingsPage() {
  const router = useRouter()
  const { isAuthenticated, isLoading, user } = useAppStore()

  // Form states
  const [token, setToken] = useState('ghp_************************')
  const [showToken, setShowToken] = useState(false)
  const [tokenVerified, setTokenVerified] = useState<null | boolean>(null)
  const [verifyingToken, setVerifyingToken] = useState(false)

  const [prefs, setPrefs] = useState({ autoAnalysis: true, deepRefactoring: false, verboseLogs: true, emailNotifications: true })
  const [depth, setDepth] = useState(75)
  const [complexity, setComplexity] = useState('standard')
  const [excludePatterns, setExcludePatterns] = useState(['*.min.js', '/vendor/*', '.pyc', 'node_modules/'])
  const [newPattern, setNewPattern] = useState('')

  const [saved, setSaved] = useState(false)
  const [activeSection, setActiveSection] = useState<'repository' | 'analysis' | 'team' | 'notifications'>('repository')

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push('/auth')
  }, [isAuthenticated, isLoading, router])

  if (isLoading || !isAuthenticated) return null

  const handleVerifyToken = async () => {
    setVerifyingToken(true)
    setTokenVerified(null)
    await new Promise(r => setTimeout(r, 1800))
    setVerifyingToken(false)
    setTokenVerified(token.length > 10)
  }

  const handleSave = async () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const removePattern = (p: string) => setExcludePatterns(prev => prev.filter(x => x !== p))
  const addPattern = () => {
    if (newPattern && !excludePatterns.includes(newPattern)) {
      setExcludePatterns(prev => [...prev, newPattern])
      setNewPattern('')
    }
  }

  const sections = [
    { id: 'repository', icon: 'lock', label: 'Repository Access' },
    { id: 'analysis', icon: 'analytics', label: 'Analysis Preferences' },
    { id: 'team', icon: 'group', label: 'Team & Access' },
    { id: 'notifications', icon: 'notifications', label: 'Notifications' },
  ] as const

  const teamMembers = [
    { name: 'Sarah Chen', email: 'sarah.c@intel.arch', role: 'Lead Architect', active: true, initials: 'SC' },
    { name: 'Marcus Thorne', email: 'm.thorne@intel.arch', role: 'System Auditor', active: false, lastSeen: '4h ago', initials: 'MT' },
    { name: 'Elena Rodriguez', email: 'elena.r@intel.arch', role: 'Analyst', active: false, lastSeen: '12m ago', initials: 'ER' },
  ]

  return (
    <div className="flex min-h-screen bg-surface text-on-surface">
      <AppSidebar active="settings" />

      <main className="flex-1 lg:ml-64 flex flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-30 glass-panel border-b border-outline-variant/10 flex items-center justify-between px-6 py-4">
          <div>
            <h1 className="font-headline text-xl italic text-on-surface">Settings & Oversight</h1>
            <p className="text-xs text-on-surface-variant">Configure the behavioral parameters for the Neural Intelligence engine.</p>
          </div>
          <div className="flex items-center gap-3">
            {saved && (
              <span className="flex items-center gap-2 text-emerald-400 text-sm animate-fade-up">
                <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
                Settings saved!
              </span>
            )}
            <button onClick={handleSave} className="btn-primary px-6 py-2.5 rounded-xl">
              Save Changes
            </button>
          </div>
        </header>

        <div className="flex-1 flex">
          {/* Settings sidebar */}
          <nav className="hidden md:flex flex-col gap-1 w-52 p-4 border-r border-outline-variant/10 flex-shrink-0">
            {sections.map(s => (
              <button
                key={s.id}
                onClick={() => setActiveSection(s.id)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-left transition-all ${
                  activeSection === s.id ? 'bg-primary/10 text-primary font-semibold' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">{s.icon}</span>
                {s.label}
              </button>
            ))}
          </nav>

          {/* Settings content */}
          <div className="flex-1 p-6 md:p-8 overflow-y-auto">
            <div className="max-w-3xl space-y-8">

              {/* ── Repository Access ── */}
              {activeSection === 'repository' && (
                <div className="space-y-6 animate-fade-up">
                  <div className="border-l-2 border-primary pl-5">
                    <h2 className="font-headline text-2xl italic text-on-surface">Repository Access</h2>
                    <p className="text-on-surface-variant text-sm mt-1">Manage secure connections to your version control providers.</p>
                  </div>

                  <div className="bg-surface-container-low rounded-2xl p-6 border border-outline-variant/10 space-y-5">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="material-symbols-outlined text-primary">hub</span>
                      <h3 className="font-headline text-lg italic">GitHub Integration</h3>
                    </div>

                    <div className="space-y-2">
                      <label className="section-label">Personal Access Token</label>
                      <div className="relative group">
                        <input
                          type={showToken ? 'text' : 'password'}
                          value={token}
                          onChange={e => { setToken(e.target.value); setTokenVerified(null) }}
                          className="input-field pr-12 font-mono"
                          placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                        />
                        <button
                          onClick={() => setShowToken(!showToken)}
                          className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-primary transition-colors"
                        >
                          <span className="material-symbols-outlined text-sm">{showToken ? 'visibility_off' : 'visibility'}</span>
                        </button>
                      </div>
                      {tokenVerified !== null && (
                        <div className={`flex items-center gap-2 text-sm ${tokenVerified ? 'text-emerald-400' : 'text-error'}`}>
                          <span className="material-symbols-outlined text-base" style={{ fontVariationSettings: "'FILL' 1" }}>
                            {tokenVerified ? 'check_circle' : 'cancel'}
                          </span>
                          {tokenVerified ? 'Token verified successfully.' : 'Invalid token. Please check and try again.'}
                        </div>
                      )}
                    </div>

                    <div className="flex gap-3">
                      <button onClick={handleVerifyToken} disabled={verifyingToken} className="btn-primary px-6 py-2.5 rounded-xl flex-1">
                        {verifyingToken ? (
                          <span className="flex items-center gap-2">
                            <span className="w-4 h-4 border-2 border-on-primary/30 border-t-on-primary rounded-full animate-spin" />
                            Verifying...
                          </span>
                        ) : 'Verify Connection'}
                      </button>
                      <button className="btn-secondary px-5 py-2.5 rounded-xl">Rotate Token</button>
                    </div>
                  </div>
                </div>
              )}

              {/* ── Analysis Preferences ── */}
              {activeSection === 'analysis' && (
                <div className="space-y-6 animate-fade-up">
                  <div className="border-l-2 border-primary pl-5">
                    <h2 className="font-headline text-2xl italic text-on-surface">Analysis Preferences</h2>
                    <p className="text-on-surface-variant text-sm mt-1">Fine-tune the neural engine's behavior and analysis parameters.</p>
                  </div>

                  {/* Quick toggles */}
                  <div className="bg-surface-container-low rounded-2xl p-6 border border-outline-variant/10 space-y-5">
                    <h3 className="font-headline text-lg italic">Engine Behavior</h3>
                    {[
                      { key: 'autoAnalysis', label: 'Auto-Analysis', desc: 'Automatically analyze newly pushed commits' },
                      { key: 'deepRefactoring', label: 'Deep Refactoring Mode', desc: 'Enable multi-pass recursive analysis (slower, more thorough)' },
                      { key: 'verboseLogs', label: 'Verbose Execution Logs', desc: 'Store full log output for every analysis run' },
                    ].map(item => (
                      <div key={item.key} className="flex items-center justify-between gap-4">
                        <div>
                          <p className="text-sm font-medium text-on-surface">{item.label}</p>
                          <p className="text-xs text-on-surface-variant">{item.desc}</p>
                        </div>
                        <Toggle
                          enabled={prefs[item.key as keyof typeof prefs]}
                          onToggle={() => setPrefs(p => ({ ...p, [item.key]: !p[item.key as keyof typeof prefs] }))}
                        />
                      </div>
                    ))}
                  </div>

                  {/* Depth slider */}
                  <div className="bg-surface-container-low rounded-2xl p-6 border border-outline-variant/10 space-y-5">
                    <h3 className="font-headline text-lg italic">Execution Constraints</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <label className="section-label">Max Analysis Depth</label>
                        <span className="text-xs text-primary font-mono">{Math.round(depth * 20)} Lines</span>
                      </div>
                      <input
                        type="range"
                        min="1"
                        max="100"
                        value={depth}
                        onChange={e => setDepth(Number(e.target.value))}
                        className="w-full h-1.5 rounded-full appearance-none bg-surface-container-highest accent-primary cursor-pointer"
                      />
                      <div className="flex justify-between text-[10px] text-on-surface-variant/50 uppercase tracking-wider">
                        <span>200 Lines</span><span>1,000 Lines</span><span>2,000 Lines</span>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="section-label">Complexity Threshold</label>
                      <select
                        value={complexity}
                        onChange={e => setComplexity(e.target.value)}
                        className="w-full bg-surface-container-highest border-0 rounded-xl px-4 py-3 text-on-surface text-sm focus:ring-1 focus:ring-primary appearance-none"
                      >
                        <option value="strict">Strict (McCabe &gt; 10)</option>
                        <option value="standard">Standard (McCabe &gt; 15)</option>
                        <option value="lax">Lax (McCabe &gt; 25)</option>
                      </select>
                    </div>
                  </div>

                  {/* Exclusion patterns */}
                  <div className="bg-surface-container-low rounded-2xl p-6 border border-outline-variant/10 space-y-4">
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-on-surface-variant">block</span>
                      <h3 className="font-headline text-lg italic">Exclusion Rules</h3>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {excludePatterns.map(p => (
                        <span key={p} className="chip flex items-center gap-2">
                          {p}
                          <button onClick={() => removePattern(p)} className="hover:text-error transition-colors">
                            <span className="material-symbols-outlined text-xs">close</span>
                          </button>
                        </span>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={newPattern}
                        onChange={e => setNewPattern(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && addPattern()}
                        placeholder="Add pattern (e.g. /dist/*)"
                        className="input-field flex-1"
                      />
                      <button onClick={addPattern} className="btn-secondary px-5 rounded-xl">Add</button>
                    </div>
                  </div>
                </div>
              )}

              {/* ── Team ── */}
              {activeSection === 'team' && (
                <div className="space-y-6 animate-fade-up">
                  <div className="border-l-2 border-primary pl-5 flex items-end justify-between">
                    <div>
                      <h2 className="font-headline text-2xl italic text-on-surface">Authorized Architects</h2>
                      <p className="text-on-surface-variant text-sm mt-1">The core collective responsible for System governance.</p>
                    </div>
                    <button className="btn-secondary flex items-center gap-2 px-5 py-2.5 rounded-xl">
                      <span className="material-symbols-outlined text-base">person_add</span>
                      Invite
                    </button>
                  </div>

                  <div className="bg-surface-container-low rounded-2xl overflow-hidden border border-outline-variant/10">
                    <table className="w-full">
                      <thead>
                        <tr className="bg-surface-container-highest/30 border-b border-outline-variant/10">
                          {['Architect', 'Role', 'Status', ''].map(h => (
                            <th key={h} className="px-6 py-3 text-left text-[11px] uppercase tracking-widest text-on-surface-variant">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-outline-variant/10">
                        {teamMembers.map(m => (
                          <tr key={m.email} className="hover:bg-surface-container-highest/20 transition-colors">
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/30 to-primary-dim/30 border border-primary/20 flex items-center justify-center text-sm font-bold text-primary">
                                  {m.initials}
                                </div>
                                <div>
                                  <p className="text-sm font-medium text-on-surface">{m.name}</p>
                                  <p className="text-[11px] text-on-surface-variant">{m.email}</p>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <span className="px-2.5 py-1 bg-surface-container-highest text-on-surface-variant text-[11px] font-medium uppercase tracking-wide rounded-lg border border-outline-variant/20">
                                {m.role}
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              {m.active ? (
                                <div className="flex items-center gap-2">
                                  <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                                  <span className="text-xs text-emerald-400">Active now</span>
                                </div>
                              ) : (
                                <span className="text-xs text-on-surface-variant/60">Last seen {m.lastSeen}</span>
                              )}
                            </td>
                            <td className="px-6 py-4 text-right">
                              <button className="text-on-surface-variant hover:text-error transition-colors">
                                <span className="material-symbols-outlined">more_horiz</span>
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* ── Notifications ── */}
              {activeSection === 'notifications' && (
                <div className="space-y-6 animate-fade-up">
                  <div className="border-l-2 border-primary pl-5">
                    <h2 className="font-headline text-2xl italic text-on-surface">Notification Settings</h2>
                    <p className="text-on-surface-variant text-sm mt-1">Choose when and how VibeAnalytix notifies you of important events.</p>
                  </div>

                  <div className="bg-surface-container-low rounded-2xl p-6 border border-outline-variant/10 space-y-5">
                    {[
                      { key: 'emailNotifications', label: 'Email Notifications', desc: 'Receive job completion and failure alerts by email' },
                      { key: 'autoAnalysis', label: 'Browser Notifications', desc: 'Browser push notifications for running jobs' },
                    ].map(item => (
                      <div key={item.key} className="flex items-center justify-between gap-4 py-2 border-b border-outline-variant/10 last:border-0">
                        <div>
                          <p className="text-sm font-medium text-on-surface">{item.label}</p>
                          <p className="text-xs text-on-surface-variant">{item.desc}</p>
                        </div>
                        <Toggle
                          enabled={prefs[item.key as keyof typeof prefs]}
                          onToggle={() => setPrefs(p => ({ ...p, [item.key]: !p[item.key as keyof typeof prefs] }))}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
