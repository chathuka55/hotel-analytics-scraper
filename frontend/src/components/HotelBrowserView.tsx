import { useEffect, useState } from 'react'
import { api, type HotelRecord, type SourceInfo } from '../api/client'
import { Card, Empty, ErrorBox, Loading, ScoreBadge, SourceBadge, money } from './ui'

const PAGE_SIZE = 20

export function HotelBrowserView({ city }: { city: string }) {
  const [sources, setSources] = useState<SourceInfo[]>([])
  const [source, setSource] = useState('')
  const [page, setPage] = useState(0)
  const [items, setItems] = useState<HotelRecord[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getSources().then(setSources).catch(() => {})
  }, [])

  useEffect(() => {
    setPage(0)
  }, [city, source])

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
    <Card title={`Raw scraped records${total ? ` · ${total.toLocaleString()}` : ''}`}>
      <div className="filters">
        <label className="field">
          Source
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">All sources</option>
            {sources.map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
        </label>
      </div>

      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorBox message={error} />
      ) : items.length === 0 ? (
        <Empty />
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Hotel</th>
                  <th>Source</th>
                  <th>City</th>
                  <th>Check-in</th>
                  <th>Location</th>
                  <th>Room</th>
                  <th className="num">Rate</th>
                  <th className="num">Occupancy</th>
                  <th className="num">Score</th>
                </tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.id}>
                    <td className="hotel-cell">{r.hotel_name}</td>
                    <td><SourceBadge source={r.source} /></td>
                    <td className="muted">{r.city}</td>
                    <td className="muted">{r.checkin_date}</td>
                    <td className="muted">{r.address || '—'}</td>
                    <td className="muted">{r.room_type || '—'}</td>
                    <td className="num">{money(r.nightly_rate, r.currency)}</td>
                    <td className="num">{r.occupancy_pct.toFixed(0)}%</td>
                    <td className="num"><ScoreBadge score={r.guest_score} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 16 }}>
            <button className="ghost" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              ← Prev
            </button>
            <span className="muted" style={{ fontSize: 13 }}>
              Page {page + 1} of {maxPage + 1}
            </span>
            <button className="ghost" disabled={page >= maxPage} onClick={() => setPage((p) => p + 1)}>
              Next →
            </button>
          </div>
        </>
      )}
    </Card>
  )
}
