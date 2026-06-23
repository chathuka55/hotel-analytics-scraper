import { useEffect, useRef, useState } from 'react'
import { api, type ScrapeJobStatus, type SourceInfo } from '../api/client'

const SAFE_SOURCES = new Set(['sltda', 'datagovlk'])

function defaultDate(daysFromNow: number): string {
  const d = new Date()
  d.setDate(d.getDate() + daysFromNow)
  return d.toISOString().slice(0, 10)
}

export function ScrapeTriggerView() {
  const [sources, setSources] = useState<SourceInfo[]>([])
  const [source, setSource] = useState('sltda')
  const [city, setCity] = useState('Colombo')
  const [checkin, setCheckin] = useState(defaultDate(30))
  const [checkout, setCheckout] = useState(defaultDate(32))
  const [maxPages, setMaxPages] = useState(3)
  const [status, setStatus] = useState<ScrapeJobStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    api.getSources().then(setSources).catch(() => {})
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const selectedSource = sources.find((s) => s.id === source)
  const isSafe = SAFE_SOURCES.has(source)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    setStatus(null)

    try {
      const { log_id } = await api.triggerScrape({
        source,
        city,
        checkin_date: checkin,
        checkout_date: checkout,
        max_pages: maxPages,
      })

      pollRef.current = setInterval(async () => {
        try {
          const s = await api.getScrapeStatus(log_id)
          setStatus(s)
          if (s.status !== 'started' && pollRef.current) {
            clearInterval(pollRef.current)
            pollRef.current = null
          }
        } catch (e) {
          setError(String(e))
          if (pollRef.current) clearInterval(pollRef.current)
        }
      }, 2000)
    } catch (e) {
      setError(String(e))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h2>Trigger a Scrape</h2>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexWrap: 'wrap', gap: 12, margin: '16px 0' }}>
        <label>
          Source
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            {sources.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          City
          <input value={city} onChange={(e) => setCity(e.target.value)} />
        </label>
        <label>
          Check-in
          <input type="date" value={checkin} onChange={(e) => setCheckin(e.target.value)} />
        </label>
        <label>
          Check-out
          <input type="date" value={checkout} onChange={(e) => setCheckout(e.target.value)} />
        </label>
        <label>
          Max pages
          <input
            type="number"
            min={1}
            max={20}
            value={maxPages}
            onChange={(e) => setMaxPages(Number(e.target.value))}
            style={{ width: 70 }}
          />
        </label>
        <div style={{ alignSelf: 'flex-end' }}>
          <button type="submit" disabled={submitting || status?.status === 'started'}>
            {submitting ? 'Starting...' : 'Run scrape'}
          </button>
        </div>
      </form>

      {!isSafe && selectedSource && (
        <p style={{ color: 'var(--danger)', background: 'var(--danger-bg)', padding: '8px 12px', borderRadius: 6 }}>
          Heads up: {selectedSource.label} is a commercial site. Triggering this performs a live
          HTTP request against it (same as the CLI does) — respect robots.txt and rate limits.
          Prefer SLTDA or data.gov.lk for safe demoing.
        </p>
      )}

      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

      {status && (
        <div style={{ marginTop: 16 }}>
          <h3>Job #{status.id}</h3>
          <p>
            Status: <strong>{status.status}</strong>
            {status.status === 'started' && ' (polling...)'}
          </p>
          {status.status === 'success' && <p>Records scraped: {status.records_scraped}</p>}
          {status.status === 'failed' && (
            <p style={{ color: 'var(--danger)' }}>Error: {status.error_message}</p>
          )}
          {status.duration_seconds != null && <p>Duration: {status.duration_seconds.toFixed(1)}s</p>}
        </div>
      )}
    </div>
  )
}
