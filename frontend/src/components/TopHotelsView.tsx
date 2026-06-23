import { useEffect, useState } from 'react'
import { api, type TopHotel } from '../api/client'

export function TopHotelsView() {
  const [cities, setCities] = useState<string[]>([])
  const [city, setCity] = useState('')
  const [month, setMonth] = useState('')
  const [year, setYear] = useState('')
  const [hotels, setHotels] = useState<TopHotel[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getCities().then(setCities).catch(() => {})
  }, [])

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

  return (
    <div>
      <h2>Top Hotels by Check-ins</h2>
      <div style={{ display: 'flex', gap: 12, margin: '16px 0' }}>
        <label>
          City
          <select value={city} onChange={(e) => setCity(e.target.value)}>
            <option value="">All cities</option>
            {cities.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label>
          Month
          <select value={month} onChange={(e) => setMonth(e.target.value)}>
            <option value="">All months</option>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label>
          Year
          <input
            type="number"
            placeholder="e.g. 2026"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            style={{ width: 90 }}
          />
        </label>
      </div>

      {loading && <p>Loading...</p>}
      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      {!loading && !error && hotels.length === 0 && (
        <p>No data found. Run a scrape first, or seed sample data.</p>
      )}

      {hotels.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Hotel</th>
              <th>City</th>
              <th>Check-ins</th>
              <th>Avg rate</th>
              <th>Avg score</th>
            </tr>
          </thead>
          <tbody>
            {hotels.map((h, i) => (
              <tr key={`${h.hotel_name}-${h.city}`}>
                <td>{i + 1}</td>
                <td>{h.hotel_name}</td>
                <td>{h.city}</td>
                <td>{h.checkin_count}</td>
                <td>${h.avg_nightly_rate.toFixed(2)}</td>
                <td>{h.avg_guest_score.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
