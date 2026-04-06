'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { useAppStore } from '@/lib/store'
import { ArrowLeft, RefreshCw, AlertCircle, ChevronRight, ChevronDown, FileText, Folder, FolderOpen, LogOut, CheckCircle2 } from 'lucide-react'

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

  const { isAuthenticated, user, isCheckingAuth, pollJobStatus, getJobResults, retryJob, logout } = useAppStore()
  const [tab, setTab] = useState<'overview' | 'structure' | 'flow'>('overview')
  const [status, setStatus] = useState<any>(null)
  const [results, setResults] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [polling, setPolling] = useState(false)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)

  useEffect(() => {
    if (isCheckingAuth) return
    if (!isAuthenticated) {
      router.push('/auth')
      return
    }

    fetchStatus()
    const pollInterval = setInterval(fetchStatus, 3000)
    return () => clearInterval(pollInterval)
  }, [isAuthenticated, isCheckingAuth, jobId])

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
      <aside className="h-screen w-64 border-r border-outline-variant/10 bg-slate-950 flex flex-col p-4 gap-2 hidden lg:flex sticky top-0 shrink-0 z-20">
        <div className="mb-4 px-2 hover:cursor-pointer" onClick={() => router.push('/')}>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full border border-primary/30 flex items-center justify-center bg-primary/10">
              <span className="material-symbols-outlined text-sm text-primary">person</span>
            </div>
            <div>
              <p className="text-on-background text-xs font-semibold truncate max-w-[140px]">{user?.email}</p>
              <p className="text-primary text-[10px] tracking-widest uppercase">Project Area</p>
            </div>
          </div>
        </div>
        <button onClick={() => router.push('/')} className="bg-gradient-to-r from-primary to-primary-dim text-on-primary py-2.5 rounded-xl text-sm font-bold flex items-center justify-center gap-2 mb-4 hover:brightness-110 active:scale-95 transition-all shadow-[0_0_20px_rgba(182,160,255,0.2)]">
          <span className="material-symbols-outlined text-sm">add</span> New Analysis
        </button>
        <nav className="flex-1 flex flex-col gap-1">
          <div onClick={() => router.push('/dashboard')} className="nav-item cursor-pointer">
            <span className="material-symbols-outlined text-lg">folder_open</span>
            <span className="text-sm font-medium">Workspace</span>
          </div>
          <div className="nav-item-active">
            <span className="material-symbols-outlined text-lg">insights</span>
            <span className="text-sm font-medium">Analysis</span>
          </div>
          <div onClick={() => router.push('/history')} className="nav-item cursor-pointer">
            <span className="material-symbols-outlined text-lg">history</span>
            <span className="text-sm font-medium">History</span>
          </div>
        </nav>
        <div className="mt-auto border-t border-outline-variant/10 pt-4 flex flex-col gap-1">
          <button onClick={logout} className="nav-item hover:text-rose-400 w-full">
            <LogOut size={18} />
            <span className="text-sm font-medium uppercase tracking-widest">Logout</span>
          </button>
        </div>
      </aside>

      {/* ── Main Content Area ────────────────────────────────── */}
      <main className="flex-1 overflow-hidden flex flex-col z-10 w-full relative">
        <header className="p-8 pb-4 flex flex-col gap-4 border-b border-outline-variant/10 glass-panel">
          <div className="flex justify-between items-start">
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-3">
                <button onClick={() => router.push('/')} className="text-on-surface-variant hover:text-primary transition-colors flex items-center pr-2 border-r border-outline-variant/20">
                  <ArrowLeft size={20} />
                </button>
                <h1 className="text-3xl font-headline text-on-background">Job ID: {jobId.slice(0, 8)}...</h1>
                
                {status && status.status === 'completed' && <span className="badge-success">Completed</span>}
                {status && status.status === 'failed' && <span className="badge-error">Failed</span>}
                {status && status.status === 'in_progress' && <span className="badge-pending animate-pulse">In Progress</span>}
              </div>
              {status && <p className="text-on-surface-variant text-sm mt-1">Stage: {status.current_stage || 'Initializing...'}</p>}
            </div>
            
            <div className="flex gap-2">
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
                  <h2 className="text-2xl font-headline mb-4 italic text-on-surface">Neural Architecture Summary</h2>
                  <p className="text-on-surface-variant leading-loose whitespace-pre-wrap">
                    {results.explanations.overview_explanation}
                  </p>
                  
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
                  {results.explanations.file_tree ? (
                    <FileTreeNodeComponent node={results.explanations.file_tree} selectedFile={selectedFile} onSelectFile={setSelectedFile} />
                  ) : results.explanations.per_file_explanations ? (
                    <div className="space-y-0.5">
                      {Object.keys(results.explanations.per_file_explanations).map((fp: string) => (
                        <button key={fp} onClick={() => setSelectedFile(fp)} className={selectedFile === fp ? 'tree-item-active' : 'tree-item'}>
                          <span className="material-symbols-outlined text-[18px]">description</span>
                          <span className="truncate">{fp}</span>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-on-surface-variant p-3 italic">No structural data acquired.</p>
                  )}
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
                      <div className="prose prose-invert max-w-none text-on-surface-variant leading-relaxed">
                        <div dangerouslySetInnerHTML={{ __html: (getFileExplanation() || '').replace(/\n/g, '<br />') }}></div>
                      </div>
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

                  <p className="text-on-surface-variant leading-loose whitespace-pre-wrap">
                    {results.explanations.flow_explanation || 'Flow data pending mapping.'}
                  </p>

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
          
        </div>
      </main>
    </div>
  )
}
