import { useEffect, useState } from 'react'
import { api, type LastScrapedSummary } from '../api/client'
import { SourceBadge } from './ui'

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return 'Never'
  const date = new Date(iso.endsWith('Z') ? iso : `${iso}Z`)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

const STATUS_COLOR: Record<string, string> = {
  success: 'var(--accent)',
  failed: 'var(--danger)',
  started: 'var(--warn)',
  never: 'var(--muted)',
}

export function LastScrapedPanel({ compact = false }: { compact?: boolean }) {
  const [data, setData] = useState<LastScrapedSummary | null>(null)

  useEffect(() => {
    api.getLastScraped().then(setData).catch(() => {})
    const timer = setInterval(() => {
      api.getLastScraped().then(setData).catch(() => {})
    }, 60_000)
    return () => clearInterval(timer)
  }, [])

  if (!data) return null

  if (compact) {
    return (
      <div className="last-scraped-compact">
        <span className="last-scraped-label">Last scraped</span>
        <strong>{formatWhen(data.overall_last_scraped_at)}</strong>
        {data.data_from_cache && (
          <span className="cache-pill">Showing cached data — some sites unavailable</span>
        )}
      </div>
    )
  }

  return (
    <div className="last-scraped-panel">
      <div className="last-scraped-head">
        <div>
          <div className="last-scraped-title">Scrape freshness</div>
          <div className="last-scraped-meta">
            Overall last data: <strong>{formatWhen(data.overall_last_scraped_at)}</strong>
            {data.last_automation_run_at && (
              <>
                {' · '}
                Last automation run: <strong>{formatWhen(data.last_automation_run_at)}</strong>
              </>
            )}
          </div>
        </div>
        {data.data_from_cache && (
          <span className="cache-pill">Cached fallback active for failed sources</span>
        )}
      </div>

      <div className="last-scraped-grid">
        {data.sources.map((row) => (
          <div key={row.source} className="last-scraped-row">
            <SourceBadge source={row.source} />
            <div className="last-scraped-row-main">
              <div>{formatWhen(row.last_scraped_at)}</div>
              <div className="dim" style={{ fontSize: 12 }}>
                {row.records_in_db.toLocaleString()} records
                {row.using_cached_data ? ' · cached' : ''}
              </div>
            </div>
            <span className="badge" style={{ color: STATUS_COLOR[row.last_status] ?? 'var(--muted)' }}>
              {row.last_status}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
