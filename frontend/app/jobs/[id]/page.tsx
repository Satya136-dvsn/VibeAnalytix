'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { useAppStore } from '@/lib/store'
import { ArrowLeft, RefreshCw, AlertCircle } from 'lucide-react'

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
      router.push(`/jobs/${newJobId}`)
    } catch (err: any) {
      setError(err.message || 'Failed to retry job')
      setLoading(false)
    }
  }

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
      {/* Header */}
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

        {status?.status === 'completed' && results && (
          <>
            {/* Tabs */}
            <div className="flex gap-4 mb-8 border-b border-slate-200">
              <button
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

            {/* Tab Content */}
            <div className="card p-8">
              {tab === 'overview' && (
                <div>
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

              {tab === 'structure' && (
                <div>
                  <h2 className="text-2xl font-bold text-slate-900 mb-4">
                    Code Structure
                  </h2>
                  <div className="prose prose-sm max-w-none text-slate-700">
                    {results.explanations.project_summary ? (
                      <p>{results.explanations.project_summary}</p>
                    ) : (
                      <p>Structure analysis not yet available</p>
                    )}
                  </div>

                  {results.explanations.entry_points?.length > 0 && (
                    <div className="mt-8">
                      <h3 className="text-lg font-semibold text-slate-900 mb-4">
                        Entry Points
                      </h3>
                      <ul className="space-y-2">
                        {results.explanations.entry_points.map((ep: string, i: number) => (
                          <li key={i} className="flex items-center gap-2 text-slate-700">
                            <span className="w-2 h-2 bg-indigo-600 rounded-full"></span>
                            {ep}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {tab === 'flow' && (
                <div>
                  <h2 className="text-2xl font-bold text-slate-900 mb-4">
                    Execution Flow
                  </h2>
                  <p className="text-slate-700 whitespace-pre-wrap">
                    {results.explanations.flow_explanation ||
                      'Flow analysis not yet available'}
                  </p>
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  )
}
