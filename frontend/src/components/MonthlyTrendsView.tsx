import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api, type MonthlyStats } from '../api/client'

export function MonthlyTrendsView() {
  const [cities, setCities] = useState<string[]>([])
  const [city, setCity] = useState('')
  const [year, setYear] = useState('')
  const [stats, setStats] = useState<MonthlyStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getCities().then(setCities).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    setError(null)
    api
      .getMonthlyStats({ city: city || undefined, year: year ? Number(year) : undefined })
      .then(setStats)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [city, year])

  const chartData = stats
    ? Object.entries(stats.monthly_totals)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([month, count]) => ({
          month,
          checkins: count,
          hotels: stats.unique_hotels_per_month[month] ?? 0,
        }))
    : []

  return (
    <div>
      <h2>Monthly Check-in Trends</h2>
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

      {stats && (
        <>
          <div style={{ display: 'flex', gap: 24, margin: '12px 0 24px' }}>
            <Stat label="Total check-ins" value={stats.total_checkins} />
            <Stat label="Unique hotels" value={stats.total_unique_hotels} />
            <Stat label="Cities" value={stats.total_cities} />
          </div>

          {chartData.length === 0 ? (
            <p>No data found. Run a scrape first, or seed sample data.</p>
          ) : (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="checkins" fill="#1c7c54" name="Check-ins" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 600 }}>{value}</div>
    </div>
  )
}
