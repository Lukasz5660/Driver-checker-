import { useCallback, useEffect, useState } from 'react'
import './App.css'

type BackendStatus = {
  service: string
  status: string
  message: string
}

const buildApiUrl = (path: string) => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL
  if (!baseUrl) {
    return path
  }

  const sanitizedBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl
  return `${sanitizedBase}${path}`
}

function App() {
  const [status, setStatus] = useState<BackendStatus | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = useCallback(
    async (signal?: AbortSignal) => {
      setIsLoading(true)
      setError(null)

      try {
        const response = await fetch(buildApiUrl('/api/status'), { signal })

        if (!response.ok) {
          throw new Error(`Backend responded with status ${response.status}`)
        }

        const payload = (await response.json()) as BackendStatus
        setStatus(payload)
      } catch (err) {
        if (signal?.aborted) {
          return
        }

        setStatus(null)
        setError(err instanceof Error ? err.message : 'Unable to reach the backend')
      } finally {
        if (!signal?.aborted) {
          setIsLoading(false)
        }
      }
    },
    [],
  )

  useEffect(() => {
    const controller = new AbortController()
    fetchStatus(controller.signal)

    return () => {
      controller.abort()
    }
  }, [fetchStatus])

  return (
    <div className="app">
      <header>
        <h1>Driver Checker</h1>
        <p>
          A lightweight starter project that pairs a React + Vite frontend with a Python
          Flask backend. Use it as the foundation for building richer driver monitoring
          experiences.
        </p>
      </header>

      <section className="status-card">
        <div className="status-card__header">
          <h2>Backend status</h2>
          <button type="button" onClick={() => fetchStatus()} disabled={isLoading}>
            {isLoading ? 'Checking…' : 'Refresh status'}
          </button>
        </div>

        {isLoading ? <p className="status-loading">Checking backend availability…</p> : null}

        {!isLoading && error ? (
          <p className="status-error">Unable to reach the backend: {error}</p>
        ) : null}

        {!isLoading && status ? (
          <dl className="status-summary">
            <div>
              <dt>Service</dt>
              <dd>{status.service}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd
                className={`status-indicator ${
                  status.status.toLowerCase() === 'ok' ? 'status-ok' : 'status-bad'
                }`}
              >
                {status.status}
              </dd>
            </div>
            <div>
              <dt>Message</dt>
              <dd>{status.message}</dd>
            </div>
          </dl>
        ) : null}
      </section>
    </div>
  )
}

export default App
