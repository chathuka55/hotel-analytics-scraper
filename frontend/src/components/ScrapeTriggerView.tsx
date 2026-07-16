import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type ScrapeJobStatus, type SourceInfo } from '../api/client'
import { Card, ErrorBox, SourceBadge } from './ui'
import { LastScrapedPanel } from './LastScrapedPanel'

function defaultDate(daysFromNow: number): string {
  const d = new Date()
  d.setDate(d.getDate() + daysFromNow)
  return d.toISOString().slice(0, 10)
}

const STATUS_COLOR: Record<string, string> = {
  started: 'var(--warn)',
  success: 'var(--accent)',
  failed: 'var(--danger)',
}

export function ScrapeTriggerView({ city: globalCity }: { city: string }) {
  const [sources, setSources] = useState<SourceInfo[]>([])
  const [source, setSource] = useState('sltda')
  const [city, setCity] = useState(globalCity || 'Colombo')
  const [checkin, setCheckin] = useState(defaultDate(30))
  const [checkout, setCheckout] = useState(defaultDate(32))
  const [maxPages, setMaxPages] = useState(3)
  const [status, setStatus] = useState<ScrapeJobStatus | null>(null)
  const [history, setHistory] = useState<ScrapeJobStatus[]>([])
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadHistory = useCallback(() => {
    api.getScrapeHistory({ limit: 10 }).then(setHistory).catch(() => {})
  }, [])

  useEffect(() => {
    api.getSources().then(setSources).catch(() => {})
    loadHistory()
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [loadHistory])

  useEffect(() => {
    if (globalCity) setCity(globalCity)
  }, [globalCity])

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
            loadHistory()
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
      <LastScrapedPanel />
      <div className="grid grid-2 section" style={{ alignItems: 'start' }}>
      <Card title="Trigger a scrape job">
        <form onSubmit={handleSubmit} className="filters" style={{ marginBottom: 0 }}>
          <label className="field">
            Source
            <select value={source} onChange={(e) => setSource(e.target.value)}>
              {sources.map((s) => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </select>
          </label>
          <label className="field">
            City
            <input value={city} onChange={(e) => setCity(e.target.value)} />
          </label>
          <label className="field">
            Check-in
            <input type="date" value={checkin} onChange={(e) => setCheckin(e.target.value)} />
          </label>
          <label className="field">
            Check-out
            <input type="date" value={checkout} onChange={(e) => setCheckout(e.target.value)} />
          </label>
          <label className="field">
            Max pages
            <input type="number" min={1} max={20} value={maxPages} onChange={(e) => setMaxPages(Number(e.target.value))} />
          </label>
          <button type="submit" className="form-submit" disabled={submitting || status?.status === 'started'}>
            {submitting || status?.status === 'started' ? 'Running…' : 'Run scrape'}
          </button>
        </form>

        {error && <div style={{ marginTop: 14 }}><ErrorBox message={error} /></div>}

        {status && (
          <div className="card" style={{ marginTop: 16, background: 'var(--surface-2)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <strong>Job #{status.id}</strong>
              <span className="badge" style={{ color: STATUS_COLOR[status.status] }}>{status.status}</span>
            </div>
            {status.status === 'success' && <p className="muted" style={{ margin: '8px 0 0' }}>Records scraped: <b>{status.records_scraped}</b></p>}
            {status.status === 'failed' && <p style={{ margin: '8px 0 0', color: 'var(--danger)' }}>{status.error_message}</p>}
            {status.duration_seconds != null && <p className="dim" style={{ margin: '4px 0 0', fontSize: 12 }}>Took {status.duration_seconds.toFixed(1)}s</p>}
          </div>
        )}
      </Card>

      <Card title="Recent jobs">
        {history.length === 0 ? (
          <p className="muted" style={{ fontSize: 13 }}>No scrape jobs run yet.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {history.map((j) => (
              <div key={j.id} className="job-history-row">
                <SourceBadge source={j.source} />
                <span className="muted job-history-city">{j.city || '—'}</span>
                <span className="job-history-meta">{j.records_scraped} rec</span>
                <span className="badge" style={{ color: STATUS_COLOR[j.status] }}>{j.status}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
      </div>
    </div>
  )
}
