'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAppStore } from '@/lib/store'

export default function AuthPage() {
  const router = useRouter()
  const { isAuthenticated, login, register } = useAppStore()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isAuthenticated) {
      router.push('/')
    }
  }, [isAuthenticated, router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      if (mode === 'login') {
        await login(email, password)
      } else {
        await register(email, password)
      }
      router.push('/')
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center px-4">
      <div className="card w-full max-w-md p-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2 text-center">
          VibeAnalytix
        </h1>
        <p className="text-slate-600 text-center mb-8">
          AI-powered code understanding engine
        </p>

        {error && (
          <div className="mb-6 p-4 bg-red-100 border border-red-300 rounded-lg text-red-800">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-slate-900 mb-2">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="input-field w-full"
              placeholder="user@example.com"
            />
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-900 mb-2">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="input-field w-full"
              placeholder="••••••••"
            />
          </div>

          <button type="submit" disabled={loading} className="w-full btn-primary">
            {loading
              ? 'Processing...'
              : mode === 'login'
                ? 'Login'
                : 'Create Account'}
          </button>
        </form>

        <div className="mt-6">
          <button
            onClick={() => {
              setMode(mode === 'login' ? 'register' : 'login')
              setError('')
            }}
            className="w-full text-center text-indigo-600 hover:text-indigo-700 text-sm font-medium"
          >
            {mode === 'login'
              ? "Don't have an account? Sign up"
              : 'Already have an account? Sign in'}
          </button>
        </div>
      </div>
    </div>
  )
}
