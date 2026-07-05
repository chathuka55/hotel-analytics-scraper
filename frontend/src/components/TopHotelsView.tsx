import { useEffect, useState } from 'react'
import { api, type TopHotel } from '../api/client'
import { Card, Empty, ErrorBox, Loading, Rank, ScoreBadge, money } from './ui'

export function TopHotelsView({ city }: { city: string }) {
  const [month, setMonth] = useState('')
  const [year, setYear] = useState('')
  const [hotels, setHotels] = useState<TopHotel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api
      .getTopHotels({
        city: city || undefined,
        month: month ? Number(month) : undefined,
        year: year ? Number(year) : undefined,
        limit: 20,
      })
      .then(setHotels)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [city, month, year])

  const maxCount = hotels.reduce((m, h) => Math.max(m, h.checkin_count), 0) || 1

  return (
    <Card title="Hotels ranked by check-in count">
      <div className="filters">
        <label className="field">
          Month
          <select value={month} onChange={(e) => setMonth(e.target.value)}>
            <option value="">All months</option>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </label>
        <label className="field">
          Year
          <input type="number" placeholder="e.g. 2026" value={year} onChange={(e) => setYear(e.target.value)} style={{ width: 110 }} />
        </label>
      </div>

      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorBox message={error} />
      ) : hotels.length === 0 ? (
        <Empty />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Hotel</th>
                <th>City</th>
                <th style={{ width: 220 }}>Check-ins</th>
                <th className="num">Avg rate</th>
                <th className="num">Avg score</th>
              </tr>
            </thead>
            <tbody>
              {hotels.map((h, i) => (
                <tr key={`${h.hotel_name}-${h.city}`}>
                  <td><Rank n={i + 1} /></td>
                  <td className="hotel-cell">{h.hotel_name}</td>
                  <td className="muted">{h.city}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{ flex: 1, height: 8, background: 'var(--surface-3)', borderRadius: 999, overflow: 'hidden' }}>
                        <div style={{ width: `${(h.checkin_count / maxCount) * 100}%`, height: '100%', background: 'linear-gradient(90deg, #2dd4a7, #38bdf8)', borderRadius: 999 }} />
                      </div>
                      <b style={{ minWidth: 22, textAlign: 'right' }}>{h.checkin_count}</b>
                    </div>
                  </td>
                  <td className="num">{money(h.avg_nightly_rate)}</td>
                  <td className="num"><ScoreBadge score={h.avg_guest_score} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}
