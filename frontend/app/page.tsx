'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAppStore } from '@/lib/store'
import { Github, Upload, LogOut, LogIn } from 'lucide-react'

export default function SubmissionPage() {
  const router = useRouter()
  const { isAuthenticated, user, logout, submitJob } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [githubUrl, setGithubUrl] = useState('')
  const [zipFile, setZipFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [mode, setMode] = useState<'github' | 'zip'>('github')

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/auth')
    }
  }, [isAuthenticated, router])

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

  if (!isAuthenticated) {
    return null // Redirect in progress
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-800/50 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-white">VibeAnalytix</h1>
          <div className="flex items-center gap-4">
            <span className="text-slate-300">{user?.email}</span>
            <button
              onClick={logout}
              className="btn-secondary flex items-center gap-2"
            >
              <LogOut size={18} />
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-2xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-white mb-4">
            Understand Any Codebase
          </h2>
          <p className="text-xl text-slate-300">
            Upload your code and get instant, AI-powered analysis
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-900/20 border border-red-700 rounded-lg text-red-200">
            {error}
          </div>
        )}

        {/* Submission Form */}
        <div className="card p-8">
          {/* Mode Selector */}
          <div className="flex gap-4 mb-8">
            <button
              onClick={() => setMode('github')}
              className={`flex-1 py-3 px-4 rounded-lg font-medium transition-colors ${
                mode === 'github'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-100 text-slate-900 hover:bg-slate-200'
              }`}
            >
              <Github className="inline mr-2" size={20} />
              GitHub URL
            </button>
            <button
              onClick={() => setMode('zip')}
              className={`flex-1 py-3 px-4 rounded-lg font-medium transition-colors ${
                mode === 'zip'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-100 text-slate-900 hover:bg-slate-200'
              }`}
            >
              <Upload className="inline mr-2" size={20} />
              ZIP File
            </button>
          </div>

          {/* GitHub URL Form */}
          {mode === 'github' && (
            <form onSubmit={handleSubmitGithub}>
              <div className="mb-6">
                <label className="block text-sm font-medium text-slate-900 mb-2">
                  GitHub Repository URL
                </label>
                <input
                  type="url"
                  placeholder="https://github.com/owner/repo"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  required
                  className="input-field w-full"
                />
                <p className="text-sm text-slate-600 mt-2">
                  Enter the HTTPS URL of any public GitHub repository
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full btn-primary"
              >
                {loading ? 'Submitting...' : 'Analyze Repository'}
              </button>
            </form>
          )}

          {/* ZIP File Form */}
          {mode === 'zip' && (
            <form onSubmit={handleSubmitZip}>
              <div className="mb-6">
                <label className="block text-sm font-medium text-slate-900 mb-2">
                  ZIP File
                </label>
                <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center hover:border-indigo-500 transition-colors cursor-pointer">
                  <input
                    type="file"
                    accept=".zip"
                    onChange={(e) => setZipFile(e.target.files?.[0] || null)}
                    required
                    className="hidden"
                    id="zip-input"
                  />
                  <label
                    htmlFor="zip-input"
                    className="cursor-pointer flex flex-col items-center"
                  >
                    <Upload size={32} className="text-slate-400 mb-2" />
                    <p className="text-sm font-medium text-slate-900">
                      {zipFile ? zipFile.name : 'Click to select or drag and drop'}
                    </p>
                    <p className="text-sm text-slate-600">
                      Max 100 MB, ZIP format only
                    </p>
                  </label>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || !zipFile}
                className="w-full btn-primary"
              >
                {loading ? 'Submitting...' : 'Analyze Code'}
              </button>
            </form>
          )}
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
          <div className="card p-6">
            <h3 className="font-bold text-slate-900 mb-2">Fast Analysis</h3>
            <p className="text-sm text-slate-600">
              Get results in minutes with our optimized pipeline
            </p>
          </div>
          <div className="card p-6">
            <h3 className="font-bold text-slate-900 mb-2">AI-Powered</h3>
            <p className="text-sm text-slate-600">
              Advanced understanding using OpenAI GPT-4
            </p>
          </div>
          <div className="card p-6">
            <h3 className="font-bold text-slate-900 mb-2">Complete View</h3>
            <p className="text-sm text-slate-600">
              See overview, structure, and execution flow
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
