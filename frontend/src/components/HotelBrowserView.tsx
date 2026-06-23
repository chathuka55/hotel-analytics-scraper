import { useEffect, useState } from 'react'
import { api, type HotelRecord, type SourceInfo } from '../api/client'

const PAGE_SIZE = 20

export function HotelBrowserView() {
  const [sources, setSources] = useState<SourceInfo[]>([])
  const [cities, setCities] = useState<string[]>([])
  const [source, setSource] = useState('')
  const [city, setCity] = useState('')
  const [page, setPage] = useState(0)
  const [items, setItems] = useState<HotelRecord[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getSources().then(setSources).catch(() => {})
    api.getCities().then(setCities).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    setError(null)
    api
      .getHotels({
        source: source || undefined,
        city: city || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      })
      .then((res) => {
        setItems(res.items)
        setTotal(res.total)
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [source, city, page])

  const maxPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1)

  return (
    <div>
      <h2>Browse Scraped Records</h2>
      <div style={{ display: 'flex', gap: 12, margin: '16px 0' }}>
        <label>
          Source
          <select
            value={source}
            onChange={(e) => {
              setSource(e.target.value)
              setPage(0)
            }}
          >
            <option value="">All sources</option>
            {sources.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          City
          <select
            value={city}
            onChange={(e) => {
              setCity(e.target.value)
              setPage(0)
            }}
          >
            <option value="">All cities</option>
            {cities.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading && <p>Loading...</p>}
      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p>No data found. Run a scrape first, or seed sample data.</p>
      )}

      {items.length > 0 && (
        <>
          <table>
            <thead>
              <tr>
                <th>Hotel</th>
                <th>Source</th>
                <th>City</th>
                <th>Check-in</th>
                <th>Check-out</th>
                <th>Rate</th>
                <th>Occupancy</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id}>
                  <td>{r.hotel_name}</td>
                  <td>{r.source}</td>
                  <td>{r.city}</td>
                  <td>{r.checkin_date}</td>
                  <td>{r.checkout_date}</td>
                  <td>
                    {r.currency} {r.nightly_rate.toFixed(2)}
                  </td>
                  <td>{r.occupancy_pct.toFixed(1)}%</td>
                  <td>{r.guest_score.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 12 }}>
            <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              Prev
            </button>
            <span>
              Page {page + 1} of {maxPage + 1} ({total} records)
            </span>
            <button disabled={page >= maxPage} onClick={() => setPage((p) => p + 1)}>
              Next
            </button>
          </div>
        </>
      )}
    </div>
  )
}
