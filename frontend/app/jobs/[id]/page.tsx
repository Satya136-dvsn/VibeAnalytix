'use client'


import { useState, useEffect, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { useAppStore } from '@/lib/store'
import { ArrowLeft, RefreshCw, AlertCircle, ChevronRight, ChevronDown, LogOut } from 'lucide-react'
import MarkdownRenderer from '@/components/MarkdownRenderer'
import DiagramViewer from '@/components/DiagramViewer'
import { apiClient } from '@/lib/api'

// Build a tree from a flat list of file paths.
// Handles both / and \ separators and strips any leading temp/absolute prefix.
function normalizePath(p: string): string {
  // Replace backslashes
  let s = p.replace(/\\/g, '/')
  // Strip anything before the first recognizable project segment
  // (keeps e.g. "src/api/index.ts" or "backend/app/routes.py")
  const prefixRe = /^(?:[A-Za-z]:|\/tmp\/[^/]+\/|\/var\/|\/home\/[^/]+\/)[^/]*\//
  s = s.replace(prefixRe, '')
  // Remove leading slashes
  s = s.replace(/^\/+/, '')
  return s
}

function buildFileTree(rawPaths: string[]): any {
  const root: any = { name: '(root)', path: '', is_dir: true, children: [] }
  for (const raw of rawPaths) {
    const p = normalizePath(raw)
    if (!p) continue
    const parts = p.split('/')
    let node = root
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      if (!part) continue
      const isLast = i === parts.length - 1
      const fullPath = parts.slice(0, i + 1).join('/')
      let child = node.children.find((c: any) => c.name === part)
      if (!child) {
        child = { name: part, path: isLast ? raw : fullPath, is_dir: !isLast, children: [] }
        node.children.push(child)
      }
      if (!isLast) node = child
    }
  }
  // Sort: dirs first, then files, both alphabetically
  const sortNode = (n: any) => {
    if (n.children) {
      n.children.sort((a: any, b: any) => {
        if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1
        return a.name.localeCompare(b.name)
      })
      n.children.forEach(sortNode)
    }
  }
  sortNode(root)
  return root
}

interface FileTreeNodeProps {
  node: any
  selectedFile: string | null
  onSelectFile: (path: string) => void
  depth?: number
}

function FileTreeNodeComponent({ node, selectedFile, onSelectFile, depth = 0 }: FileTreeNodeProps) {
  const [expanded, setExpanded] = useState(depth < 2)
  const isSelected = selectedFile === node.path

  if (node.is_dir) {
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className={`flex items-center gap-1.5 w-full text-left px-2 py-1.5 rounded-md text-sm transition-colors duration-150
            hover:bg-surface-container ${depth === 0 ? 'font-semibold text-on-surface' : 'text-on-surface-variant'}`}
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
        >
          {expanded ? <ChevronDown size={14} className="text-outline-variant flex-shrink-0" /> : <ChevronRight size={14} className="text-outline-variant flex-shrink-0" />}
          <span className="material-symbols-outlined text-[18px] text-tertiary">{expanded ? 'folder_open' : 'folder'}</span>
          <span className="truncate">{node.name}</span>
        </button>
        {expanded && node.children && (
          <div>
            {node.children.map((child: any, idx: number) => (
              <FileTreeNodeComponent key={`${child.path}-${idx}`} node={child} selectedFile={selectedFile} onSelectFile={onSelectFile} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <button
      onClick={() => onSelectFile(node.path)}
      className={`flex items-center gap-1.5 w-full text-left px-2 py-1.5 rounded-md text-sm transition-colors duration-150
        ${isSelected ? 'bg-primary/10 text-primary font-medium' : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'}`}
      style={{ paddingLeft: `${depth * 16 + 8}px` }}
    >
      <span className="material-symbols-outlined text-[18px]">description</span>
      <span className="truncate">{node.name}</span>
    </button>
  )
}

export default function JobResultsPage() {
  const router = useRouter()
  const params = useParams()
  const jobId = params.id as string

  const { isAuthenticated, isLoading, user, pollJobStatus, getJobResults, retryJob, logout } = useAppStore()
  const [tab, setTab] = useState<'overview' | 'structure' | 'flow' | 'diagrams'>('overview')
  const [status, setStatus] = useState<any>(null)
  const [results, setResults] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [polling, setPolling] = useState(false)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  
  // Chat States
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [chatQuery, setChatQuery] = useState('')
  const [chatHistory, setChatHistory] = useState<Array<{role: 'user' | 'assistant', content: string, sources?: any[]}>>([])
  const [chatLoading, setChatLoading] = useState(false)

  useEffect(() => {

    if (!isLoading && !isAuthenticated) {
      router.push('/auth')
      return
    }

    if (isAuthenticated) {
      fetchStatus()
      const pollInterval = setInterval(fetchStatus, 3000)
      return () => clearInterval(pollInterval)
    }
  }, [isAuthenticated, isLoading, jobId])

  const fetchStatus = async () => {
    try {
      const jobStatus = await pollJobStatus(jobId)
      setStatus(jobStatus)

      if (jobStatus.status === 'completed' || jobStatus.status === 'failed') {
        setPolling(false)
        if (jobStatus.status === 'completed') {
          const jobResults = await getJobResults(jobId)
          setResults(jobResults)
        }
      } else {
        setPolling(true)
        if (jobStatus.progress_pct >= 85) {
          try {
            const partialResults = await getJobResults(jobId)
            setResults(partialResults)
          } catch (e) {}
        }
      }
      setLoading(false)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch job status')
      setLoading(false)
    }
  }

  const getProjectName = (job: any) => {
    if (!job) return 'Neural Analysis'
    const ref = job.source_ref || ''
    if (job.source_type === 'github') {
      const parts = ref.replace(/\/$/, '').split('/')
      return parts[parts.length - 1]
    }
    return 'ZIP Upload'
  }

  const handleRetry = async () => {
    try {
      setLoading(true)
      const newJobId = await retryJob(jobId)
      if (newJobId) {
        router.push(`/jobs/${newJobId}`)
      } else {
        router.push('/')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to retry job')
      setLoading(false)
    }
  }

  const handleChat = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!chatQuery.trim() || chatLoading) return

    const query = chatQuery
    setChatHistory(prev => [...prev, { role: 'user', content: query }])
    setChatQuery('')
    setChatLoading(true)

    try {
      const res = await apiClient.chatWithRepo(jobId, query)
      setChatHistory(prev => [...prev, { role: 'assistant', content: res.answer, sources: res.sources }])
    } catch (err: any) {
      console.error(err)
      setChatHistory(prev => [...prev, { role: 'assistant', content: 'Neural engine communication failed. Cannot reach semantic store.' }])
    } finally {
      setChatLoading(false)
    }
  }

  const getFileExplanation = useCallback((): string | null => {
    if (!selectedFile || !results?.explanations?.per_file_explanations) return null
    return results.explanations.per_file_explanations[selectedFile] || null
  }, [selectedFile, results])

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center relative overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-primary/20 rounded-full blur-[100px] animate-pulse"></div>
        <span className="material-symbols-outlined text-6xl text-primary animate-spin mb-6">psychology</span>
        <h2 className="text-2xl font-headline text-on-surface">Initializing Logic Matrices...</h2>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-background text-on-background overflow-hidden relative">
      {/* Background glow */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[120px] pointer-events-none"></div>

      {/* ── Side Nav Bar ─────────────────────────────────────── */}
      <aside className="fixed top-0 left-0 h-screen w-64 bg-surface-container-low border-r border-outline-variant/10 flex flex-col py-6 px-4 gap-6 z-40 hidden lg:flex">
        {/* Brand */}
        <div className="flex items-center gap-3 px-2 mb-2 cursor-pointer" onClick={() => router.push('/dashboard')}>
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
          <button onClick={() => router.push('/dashboard')} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-all">
            <span className="material-symbols-outlined text-[20px]">folder_open</span>
            <span>Workspace</span>
          </button>
          <div className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-primary bg-primary/10 font-semibold transition-all">
            <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>insights</span>
            <span>Analysis</span>
            <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary" />
          </div>
          <button onClick={() => router.push('/history')} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-all">
            <span className="material-symbols-outlined text-[20px]">history</span>
            <span>History</span>
          </button>
          <button onClick={() => router.push('/settings')} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-all">
            <span className="material-symbols-outlined text-[20px]">settings</span>
            <span>Settings</span>
          </button>
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
            <span className="material-symbols-outlined text-[20px]">logout</span>
            <span className="text-xs uppercase tracking-widest">Logout</span>
          </button>
        </div>
      </aside>

      {/* ── Main Content Area ────────────────────────────────── */}
      <main className="flex-1 lg:ml-64 overflow-hidden flex flex-col z-10 w-full relative">
        <header className="p-8 pb-4 flex flex-col gap-4 border-b border-outline-variant/10 glass-panel">
          <div className="flex justify-between items-start">
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-3">
                <button onClick={() => router.push('/')} className="text-on-surface-variant hover:text-primary transition-colors flex items-center pr-2 border-r border-outline-variant/20">
                  <ArrowLeft size={20} />
                </button>
                <h1 className="text-3xl font-headline text-on-background"> {getProjectName(results || status)}</h1>
                
                {status && (
                  <div className="flex items-center gap-2">
                    {status.status === 'completed' && <span className="badge-success">Completed</span>}
                    {status.status === 'failed' && <span className="badge-error">Failed</span>}
                    {status.status === 'in_progress' && <span className="badge-pending animate-pulse">In Progress</span>}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-4 mt-1">
                {status && <p className="text-on-surface-variant text-sm border-r border-outline-variant/20 pr-4">Stage: {status.current_stage || 'Initializing...'}</p>}
                {status?.source_type === 'github' && (
                  <a href={status.source_ref} target="_blank" rel="noreferrer" className="text-[10px] text-primary uppercase tracking-widest hover:underline flex items-center gap-1">
                    <span className="material-symbols-outlined text-[14px]">link</span>
                    Source Registry
                  </a>
                )}
              </div>
            </div>
            
            <div className="flex gap-3">
              <button 
                onClick={handleRetry}
                className="btn-secondary px-4 py-2 text-xs flex items-center gap-2 border-primary/20 hover:bg-primary/5 text-primary" 
                title="Refresh analysis with latest repo state"
              >
                <span className="material-symbols-outlined text-[18px]">sync</span>
                Re-analyze
              </button>
              <button className="bg-surface-container-highest p-2 rounded-lg text-on-surface-variant hover:text-on-background transition-colors active:scale-95">
                <span className="material-symbols-outlined">share</span>
              </button>
              <button className="bg-surface-container-highest p-2 rounded-lg text-on-surface-variant hover:text-on-background transition-colors active:scale-95">
                <span className="material-symbols-outlined">download</span>
              </button>
            </div>
          </div>

          {(status?.status === 'completed' || results) && (
            <div className="flex gap-8 mt-4">
              <button onClick={() => setTab('overview')} className={tab === 'overview' ? 'tab-btn-active' : 'tab-btn'}>Overview</button>
              <button onClick={() => setTab('structure')} className={tab === 'structure' ? 'tab-btn-active' : 'tab-btn'}>Structure</button>
              <button onClick={() => setTab('flow')} className={tab === 'flow' ? 'tab-btn-active' : 'tab-btn'}>Flow</button>
              {results?.explanations?.architecture_diagrams && (
                <button onClick={() => setTab('diagrams')} className={tab === 'diagrams' ? 'tab-btn-active' : 'tab-btn'}>
                  <span className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[16px]">architecture</span>
                    Diagrams
                  </span>
                </button>
              )}
            </div>
          )}
        </header>

        <div className="flex-1 overflow-y-auto w-full p-8 relative">
          
          {error && (
            <div className="alert-error mx-auto mb-6 max-w-5xl">
              <AlertCircle size={20} className="flex-shrink-0" />
              <div>{error}</div>
            </div>
          )}

          {/* ── Failed State ─────────────────────────────────────── */}
          {status?.status === 'failed' && (
            <div className="mx-auto max-w-3xl alert-error flex-col p-8">
              <h3 className="text-lg font-bold text-error mb-2">Analysis Failed</h3>
              <p className="text-error mb-6 font-mono text-sm">{status.error_message}</p>
              <button onClick={handleRetry} className="btn-secondary self-start border-error/50 hover:bg-error/10 text-error">
                <RefreshCw size={18} /> Retry Engine
              </button>
            </div>
          )}

          {/* ── In-Progress State ────────────────────────────────── */}
          {status?.status === 'in_progress' && (
            <div className="mx-auto max-w-3xl card p-8 my-8 border-primary/30">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-primary flex items-center gap-2">
                  <span className="material-symbols-outlined animate-spin">memory</span>
                  Processing Subroutines
                </h3>
                <span className="text-primary font-mono text-sm">{status.progress_pct}%</span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${status.progress_pct}%` }}></div>
              </div>
              <p className="text-on-surface-variant text-xs mt-3 uppercase tracking-widest">{status.current_stage}</p>
            </div>
          )}

          {/* ── Progressive rendering: Overview ──────────────────── */}
          {(status?.status === 'completed' || (status?.status === 'in_progress' && results?.explanations?.overview_explanation)) && results?.explanations?.overview_explanation && tab === 'overview' && (
            <div className="max-w-5xl mx-auto space-y-6">
              <div className="card-elevated p-8 relative overflow-hidden bg-surface-container-low border-outline-variant/10">
                <div className="relative z-10">
                  <h2 className="text-2xl font-headline mb-6 italic text-on-surface border-b border-outline-variant/10 pb-4">Neural Architecture Report</h2>
                  <MarkdownRenderer content={results.explanations.overview_explanation} />

                  {results.explanations.external_deps?.length > 0 && (
                    <div className="mt-8 border-t border-outline-variant/10 pt-6">
                       <h3 className="section-label mb-3">External Dependencies</h3>
                       <div className="flex flex-wrap gap-2">
                         {results.explanations.external_deps.map((dep: string, i: number) => (
                           <span key={i} className="chip">{dep}</span>
                         ))}
                       </div>
                    </div>
                  )}
                </div>
                <div className="absolute right-0 top-0 w-1/3 h-full opacity-10 pointer-events-none bg-gradient-to-l from-primary/20 to-transparent"></div>
              </div>
            </div>
          )}

          {/* STRUCTURE TAB ────────────────────────────────────────── */}
          {status?.status === 'completed' && results && tab === 'structure' && (
            <div className="flex flex-col md:flex-row gap-8 max-w-7xl mx-auto h-full">
              {/* Left Panel: File Tree */}
              <div className="w-full md:w-80 flex-shrink-0 card p-4 flex flex-col gap-2 h-full max-h-[80vh] overflow-y-auto">
                <h3 className="section-label px-2 mb-2">Repository Structure</h3>
                <div className="bg-surface-container-lowest rounded-xl p-2 border border-outline-variant/5">
                  {(() => {
                    // Prefer API-provided file_tree, otherwise build one from per_file_explanations keys
                    const tree = results.explanations.file_tree ||
                      (results.explanations.per_file_explanations
                        ? buildFileTree(Object.keys(results.explanations.per_file_explanations))
                        : null)
                    if (!tree) return <p className="text-sm text-on-surface-variant p-3 italic">No structural data acquired.</p>
                    // If root has only one child dir, render that child directly
                    const renderRoot = (tree.children?.length === 1 && tree.children[0].is_dir) ? tree.children[0] : tree
                    return <FileTreeNodeComponent node={renderRoot} selectedFile={selectedFile} onSelectFile={setSelectedFile} />
                  })()}
                </div>
              </div>

              {/* Right Panel: File Explanation */}
              <div className="flex-1 card-elevated p-0 flex flex-col max-h-[80vh] overflow-hidden">
                {selectedFile ? (
                  <>
                    <div className="bg-surface-container-low px-6 py-4 border-b border-outline-variant/10 flex justify-between items-center shrink-0">
                       <span className="text-sm text-on-surface code-block font-medium">{selectedFile}</span>
                       <span className="section-label text-primary">Contextual Analysis</span>
                    </div>
                    <div className="p-8 overflow-y-auto flex-1">
                      <MarkdownRenderer content={getFileExplanation() || '_No explanation available for this file._'} />
                    </div>
                  </>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-on-surface-variant p-10 opacity-70">
                     <span className="material-symbols-outlined text-6xl mb-4 text-outline-variant">account_tree</span>
                     <p className="text-lg font-headline">Select a node to review insights.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* FLOW TAB ─────────────────────────────────────────────── */}
          {status?.status === 'completed' && results && tab === 'flow' && (
            <div className="max-w-5xl mx-auto space-y-8">
              <div className="card p-8 bg-surface-container-low relative overflow-hidden">
                <div className="relative z-10">
                  <h2 className="text-2xl font-headline mb-6 text-on-surface border-b border-outline-variant/10 pb-4">Execution Flow Analysis</h2>
                  
                  {results.explanations.entry_points?.length > 0 && (
                    <div className="mb-8">
                      <h3 className="section-label mb-3 text-tertiary">Entry Vectors</h3>
                      <div className="flex flex-wrap gap-2">
                        {results.explanations.entry_points.map((ep: string, i: number) => (
                          <span key={i} className="chip bg-tertiary/10 border-tertiary/20">{ep}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  <MarkdownRenderer content={results.explanations.flow_explanation || '_Flow data pending mapping._'} />

                  {results.explanations.circular_deps?.length > 0 && (
                    <div className="mt-8 p-6 bg-error-container/20 border border-error/30 rounded-xl">
                      <h3 className="section-label mb-3 text-error flex items-center gap-2">
                         <span className="material-symbols-outlined text-sm">warning</span> 
                         Circular Anomalies Detected
                      </h3>
                      <ul className="space-y-2 text-error-dim text-sm font-mono">
                        {results.explanations.circular_deps.map((cycle: string[], i: number) => (
                          <li key={i} className="bg-surface-container px-3 py-2 rounded-lg">{cycle.join(' → ')}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* DIAGRAMS TAB ──────────────────────────────────────────── */}
          {status?.status === 'completed' && results?.explanations?.architecture_diagrams && tab === 'diagrams' && (
            <div className="max-w-6xl mx-auto">
              {results.explanations.repo_metadata && (
                <div className="mb-6 card p-4 bg-surface-container-low border-outline-variant/10 flex flex-wrap gap-4 items-center">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-primary text-[18px]">hub</span>
                    <span className="font-semibold text-on-surface">{results.explanations.repo_metadata.name}</span>
                  </div>
                  {results.explanations.repo_metadata.description && (
                    <span className="text-sm text-on-surface-variant flex-1">{results.explanations.repo_metadata.description}</span>
                  )}
                  {typeof results.explanations.repo_metadata.stars === 'number' && (
                    <span className="chip text-[11px] flex items-center gap-1">
                      <span className="material-symbols-outlined text-[14px] text-tertiary">star</span>
                      {results.explanations.repo_metadata.stars.toLocaleString()}
                    </span>
                  )}
                  {results.explanations.repo_metadata.language && (
                    <span className="chip text-[11px] bg-primary/10 border-primary/20 text-primary">
                      {results.explanations.repo_metadata.language}
                    </span>
                  )}
                </div>
              )}
              <DiagramViewer diagrams={results.explanations.architecture_diagrams} />
            </div>
          )}
          
        </div>
      </main>

      {/* ── Chat Overlay ─────────────────────────────────────── */}
      {status?.status === 'completed' && results && (
        <div className={`fixed bottom-0 right-8 w-[450px] shadow-2xl transition-all duration-300 z-50 rounded-t-2xl border border-outline-variant/20 bg-surface/95 backdrop-blur-xl ${isChatOpen ? 'h-[600px] translate-y-0' : 'h-14 translate-y-0 cursor-pointer hover:bg-surface-container-high'}`}>
          {/* Header */}
          <div 
            onClick={() => setIsChatOpen(!isChatOpen)}
            className="h-14 px-5 flex items-center justify-between border-b border-outline-variant/10 rounded-t-2xl"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-primary to-primary-dim flex items-center justify-center shadow-lg shadow-primary/20">
                <span className="material-symbols-outlined text-sm text-on-primary" style={{ fontVariationSettings: "'FILL' 1" }}>robot_2</span>
              </div>
              <h3 className="font-semibold text-on-surface">Neural Chat</h3>
            </div>
            <button className="text-on-surface-variant hover:text-on-surface">
              <span className="material-symbols-outlined text-xl transition-transform duration-300 transform" style={{ rotate: isChatOpen ? '180deg' : '0deg' }}>
                expand_less
              </span>
            </button>
          </div>

          {/* Chat Body */}
          {isChatOpen && (
            <div className="flex flex-col h-[calc(600px-56px)] bg-surface">
              <div className="flex-1 overflow-y-auto p-5 space-y-6">
                {chatHistory.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center opacity-60 px-6">
                    <span className="material-symbols-outlined text-5xl mb-4 text-primary">chat_bubble</span>
                    <h4 className="font-headline text-lg text-on-surface mb-2">Ask about this repository</h4>
                    <p className="text-sm text-on-surface-variant">The Neural Engine has indexed the codebase semantic vectors. You can ask anything.</p>
                  </div>
                ) : (
                  chatHistory.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[85%] rounded-2xl p-4 ${msg.role === 'user' ? 'bg-primary text-on-primary rounded-tr-sm' : 'bg-surface-container-low text-on-surface rounded-tl-sm border border-outline-variant/10 shadow-lg'}`}>
                        <MarkdownRenderer content={msg.content} className="text-sm" />
                        {msg.sources && msg.sources.length > 0 && (
                          <div className="mt-4 pt-3 border-t border-outline-variant/20">
                            <p className="text-[10px] uppercase tracking-widest text-primary mb-2 font-bold">Vector References</p>
                            <div className="space-y-1">
                              {msg.sources.map((s, idx) => (
                                <div key={idx} className="bg-surface-container rounded p-2 flex items-center justify-between group">
                                  <span className="text-xs font-mono text-tertiary truncate">{s.file.split('/').pop()}</span>
                                  <span className="material-symbols-outlined text-[14px] text-on-surface-variant opacity-0 group-hover:opacity-100 transition-opacity">open_in_new</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
                {chatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-surface-container-low text-on-surface border border-outline-variant/10 rounded-2xl rounded-tl-sm p-4 flex gap-1 items-center">
                      <span className="w-2 h-2 rounded-full bg-primary animate-bounce"></span>
                      <span className="w-2 h-2 rounded-full bg-primary animate-bounce delay-75"></span>
                      <span className="w-2 h-2 rounded-full bg-primary animate-bounce delay-150"></span>
                    </div>
                  </div>
                )}
              </div>
              
              {/* Input Area */}
              <div className="p-4 bg-surface-container-low border-t border-outline-variant/10">
                <form onSubmit={handleChat} className="relative flex items-center">
                  <input
                    type="text"
                    value={chatQuery}
                    onChange={e => setChatQuery(e.target.value)}
                    placeholder="Search neural vectors..."
                    className="w-full bg-surface-container-highest border-none rounded-xl pl-4 pr-12 py-3 text-sm focus:ring-1 focus:ring-primary text-on-surface placeholder:text-on-surface-variant"
                  />
                  <button 
                    type="submit" 
                    disabled={chatLoading || !chatQuery.trim()}
                    className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center bg-primary text-on-primary rounded-lg shadow-md disabled:bg-surface-container-highest disabled:text-on-surface-variant transition-all hover:brightness-110 active:scale-95"
                  >
                    <span className="material-symbols-outlined text-[18px]">send</span>
                  </button>
                </form>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
