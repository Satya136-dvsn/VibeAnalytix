'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { useAppStore } from '@/lib/store'
import { ArrowLeft, RefreshCw, AlertCircle, ChevronRight, ChevronDown, FileText, Folder, FolderOpen } from 'lucide-react'

/* ================================================================
   File Tree Component — recursive, interactive, with selection
   ================================================================ */
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
          className={`flex items-center gap-1.5 w-full text-left px-2 py-1.5 rounded-md text-sm
            hover:bg-indigo-50 transition-colors duration-150
            ${depth === 0 ? 'font-semibold text-slate-800' : 'text-slate-700'}`}
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
        >
          {expanded ? (
            <ChevronDown size={14} className="text-slate-400 flex-shrink-0" />
          ) : (
            <ChevronRight size={14} className="text-slate-400 flex-shrink-0" />
          )}
          {expanded ? (
            <FolderOpen size={16} className="text-amber-500 flex-shrink-0" />
          ) : (
            <Folder size={16} className="text-amber-500 flex-shrink-0" />
          )}
          <span className="truncate">{node.name}</span>
        </button>
        {expanded && node.children && (
          <div>
            {node.children.map((child: any, idx: number) => (
              <FileTreeNodeComponent
                key={`${child.path}-${idx}`}
                node={child}
                selectedFile={selectedFile}
                onSelectFile={onSelectFile}
                depth={depth + 1}
              />
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <button
      onClick={() => onSelectFile(node.path)}
      className={`flex items-center gap-1.5 w-full text-left px-2 py-1.5 rounded-md text-sm
        transition-colors duration-150
        ${isSelected
          ? 'bg-indigo-100 text-indigo-700 font-medium'
          : 'text-slate-600 hover:bg-slate-100'}`}
      style={{ paddingLeft: `${depth * 16 + 8}px` }}
    >
      <FileText size={14} className={`flex-shrink-0 ${isSelected ? 'text-indigo-500' : 'text-slate-400'}`} />
      <span className="truncate">{node.name}</span>
    </button>
  )
}

/* ================================================================
   Main Job Results Page
   ================================================================ */
export default function JobResultsPage() {
  const router = useRouter()
  const params = useParams()
  const jobId = params.id as string

  const { isAuthenticated, pollJobStatus, getJobResults, retryJob } = useAppStore()
  const [tab, setTab] = useState<'overview' | 'structure' | 'flow'>('overview')
  const [status, setStatus] = useState<any>(null)
  const [results, setResults] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [polling, setPolling] = useState(false)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/auth')
      return
    }

    // Initial fetch
    fetchStatus()

    // Setup polling
    const pollInterval = setInterval(fetchStatus, 3000)
    return () => clearInterval(pollInterval)
  }, [isAuthenticated, jobId])

  const fetchStatus = async () => {
    try {
      const jobStatus = await pollJobStatus(jobId)
      setStatus(jobStatus)

      // If completed or failed, fetch results
      if (jobStatus.status === 'completed' || jobStatus.status === 'failed') {
        setPolling(false)
        if (jobStatus.status === 'completed') {
          const jobResults = await getJobResults(jobId)
          setResults(jobResults)
        }
      } else {
        setPolling(true)
        // Fetch partial results for progressive rendering
        if (jobStatus.progress_pct >= 85) {
          try {
            const partialResults = await getJobResults(jobId)
            setResults(partialResults)
          } catch (e) {
            // ignore 404
          }
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

  /* Get per-file explanation for the selected file */
  const getFileExplanation = useCallback((): string | null => {
    if (!selectedFile || !results?.explanations?.per_file_explanations) return null
    return results.explanations.per_file_explanations[selectedFile] || null
  }, [selectedFile, results])

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mb-4"></div>
          <p className="text-white text-lg">Loading job...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => router.push('/')}
              className="flex items-center gap-2 text-indigo-600 hover:text-indigo-700"
            >
              <ArrowLeft size={20} />
              Back
            </button>

            {status && (
              <div className="flex items-center gap-4">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  status.status === 'completed'
                    ? 'bg-green-100 text-green-800'
                    : status.status === 'failed'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-blue-100 text-blue-800'
                }`}>
                  {status.status.toUpperCase()}
                </span>

                {polling && (
                  <div className="flex items-center gap-2 text-slate-600">
                    <div className="animate-spin">
                      <RefreshCw size={18} />
                    </div>
                    <span>{status.progress_pct}%</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {status && status.current_stage && (
            <div className="text-sm text-slate-600">
              Stage: {status.current_stage}
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-100 border border-red-300 rounded-lg text-red-800 flex items-start gap-3">
            <AlertCircle size={20} className="flex-shrink-0 mt-0.5" />
            <div>{error}</div>
          </div>
        )}

        {/* ── Failed State ─────────────────────────────────────── */}
        {status?.status === 'failed' && (
          <div className="mb-6 p-6 bg-red-50 border border-red-200 rounded-lg">
            <h3 className="text-lg font-semibold text-red-900 mb-2">Job Failed</h3>
            <p className="text-red-800 mb-4">{status.error_message}</p>
            <button
              onClick={handleRetry}
              className="btn-primary flex items-center gap-2"
            >
              <RefreshCw size={18} />
              Retry Job
            </button>
          </div>
        )}

        {/* ── In-Progress State ────────────────────────────────── */}
        {status?.status === 'in_progress' && (
          <div className="mb-8 p-6 bg-blue-50 border border-blue-200 rounded-lg">
            <h3 className="text-lg font-semibold text-blue-900 mb-2">Processing</h3>
            <div className="w-full bg-blue-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${status.progress_pct}%` }}
              ></div>
            </div>
            <p className="text-blue-800 mt-2">
              {status.progress_pct}% - {status.current_stage}
            </p>
          </div>
        )}

        {/* ── Progressive rendering: Overview available early ──── */}
        {(status?.status === 'completed' || (status?.status === 'in_progress' && results?.explanations?.overview_explanation)) && results?.explanations?.overview_explanation && (
          <div className="mb-6 card p-8">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">
              Project Overview <span className="text-sm font-normal text-indigo-600">(preview)</span>
            </h2>
            <p className="text-slate-700 whitespace-pre-wrap">
              {results.explanations.overview_explanation}
            </p>
          </div>
        )}

        {/* ── Completed State — Tabs ──────────────────────────── */}
        {status?.status === 'completed' && results && (
          <>
            {/* Tab bar */}
            <div className="flex gap-4 mb-8 border-b border-slate-200">
              <button
                id="tab-overview"
                onClick={() => setTab('overview')}
                className={`px-4 py-2 font-medium border-b-2 transition-colors ${
                  tab === 'overview'
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
              >
                Overview
              </button>
              <button
                id="tab-structure"
                onClick={() => setTab('structure')}
                className={`px-4 py-2 font-medium border-b-2 transition-colors ${
                  tab === 'structure'
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
              >
                Structure
              </button>
              <button
                id="tab-flow"
                onClick={() => setTab('flow')}
                className={`px-4 py-2 font-medium border-b-2 transition-colors ${
                  tab === 'flow'
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
              >
                Flow
              </button>
            </div>

            {/* ── Tab Content ──────────────────────────────────── */}

            {/* OVERVIEW TAB */}
            {tab === 'overview' && (
              <div className="card p-8">
                <h2 className="text-2xl font-bold text-slate-900 mb-4">
                  Project Overview
                </h2>
                <p className="text-slate-700 whitespace-pre-wrap">
                  {results.explanations.overview_explanation ||
                    'No overview available yet'}
                </p>

                {results.explanations.external_deps?.length > 0 && (
                  <div className="mt-8">
                    <h3 className="text-lg font-semibold text-slate-900 mb-4">
                      External Dependencies
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {results.explanations.external_deps.map((dep: string, i: number) => (
                        <span
                          key={i}
                          className="px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full text-sm"
                        >
                          {dep}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* STRUCTURE TAB — file tree + per-file explanation panel */}
            {tab === 'structure' && (
              <div className="flex gap-6 h-[calc(100vh-280px)] min-h-[500px]">
                {/* Left panel — file/folder tree */}
                <div className="w-72 flex-shrink-0 card overflow-y-auto">
                  <div className="p-3 border-b border-slate-200">
                    <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
                      Files
                    </h3>
                  </div>
                  <div className="p-2">
                    {results.explanations.file_tree ? (
                      <FileTreeNodeComponent
                        node={results.explanations.file_tree}
                        selectedFile={selectedFile}
                        onSelectFile={setSelectedFile}
                      />
                    ) : (
                      // Fallback: list per_file_explanations keys as flat list
                      results.explanations.per_file_explanations &&
                      Object.keys(results.explanations.per_file_explanations).length > 0 ? (
                        <div className="space-y-0.5">
                          {Object.keys(results.explanations.per_file_explanations).map((fp: string) => (
                            <button
                              key={fp}
                              onClick={() => setSelectedFile(fp)}
                              className={`flex items-center gap-1.5 w-full text-left px-2 py-1.5 rounded-md text-sm
                                transition-colors duration-150
                                ${selectedFile === fp
                                  ? 'bg-indigo-100 text-indigo-700 font-medium'
                                  : 'text-slate-600 hover:bg-slate-100'}`}
                            >
                              <FileText size={14} className={`flex-shrink-0 ${selectedFile === fp ? 'text-indigo-500' : 'text-slate-400'}`} />
                              <span className="truncate">{fp}</span>
                            </button>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-slate-500 p-3">No files to display</p>
                      )
                    )}
                  </div>
                </div>

                {/* Right panel — per-file explanation */}
                <div className="flex-1 card overflow-y-auto">
                  {selectedFile ? (
                    <div className="p-6">
                      <h3 className="text-lg font-bold text-slate-900 mb-1 flex items-center gap-2">
                        <FileText size={18} className="text-indigo-500" />
                        {selectedFile}
                      </h3>
                      <div className="mt-4 text-slate-700 whitespace-pre-wrap leading-relaxed">
                        {getFileExplanation() || (
                          <span className="text-slate-400 italic">
                            No explanation available for this file.
                          </span>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full text-slate-400">
                      <div className="text-center">
                        <FileText size={48} className="mx-auto mb-3 opacity-30" />
                        <p className="text-lg">Select a file to view its explanation</p>
                        <p className="text-sm mt-1">Click on any file in the tree</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* FLOW TAB */}
            {tab === 'flow' && (
              <div className="card p-8">
                <h2 className="text-2xl font-bold text-slate-900 mb-4">
                  Execution Flow
                </h2>

                {results.explanations.entry_points?.length > 0 && (
                  <div className="mb-6 p-4 bg-indigo-50 border border-indigo-200 rounded-lg">
                    <h3 className="text-sm font-semibold text-indigo-800 uppercase tracking-wider mb-2">
                      Entry Points
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {results.explanations.entry_points.map((ep: string, i: number) => (
                        <span
                          key={i}
                          className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-medium"
                        >
                          {ep}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <p className="text-slate-700 whitespace-pre-wrap leading-relaxed">
                  {results.explanations.flow_explanation ||
                    'Flow analysis not yet available'}
                </p>

                {results.explanations.circular_deps?.length > 0 && (
                  <div className="mt-8 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                    <h3 className="text-sm font-semibold text-amber-800 uppercase tracking-wider mb-2">
                      ⚠ Circular Dependencies Detected
                    </h3>
                    <ul className="space-y-1 text-amber-700 text-sm">
                      {results.explanations.circular_deps.map((cycle: string[], i: number) => (
                        <li key={i} className="font-mono">
                          {cycle.join(' → ')}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
