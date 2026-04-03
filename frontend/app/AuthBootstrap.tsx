'use client'

import { useEffect } from 'react'
import { useAppStore } from '@/lib/store'

/**
 * AuthBootstrap — runs once on app mount.
 * Restores authentication state from localStorage so that
 * page-level auth guards don't fire before the token check completes.
 */
export default function AuthBootstrap() {
  const checkAuth = useAppStore((state) => state.checkAuth)

  useEffect(() => {
    // If a token exists in localStorage, validate it and hydrate the store.
    const token = localStorage.getItem('access_token')
    if (token) {
      checkAuth()
    } else {
      // No token — immediately mark auth check as done
      useAppStore.setState({ isLoading: false })
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return null // renders nothing
}
