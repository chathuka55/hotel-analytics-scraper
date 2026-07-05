import { useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api, type MonthlyStats } from '../api/client'
import { Card, Empty, ErrorBox, Loading, monthLabel } from './ui'

export function MonthlyTrendsView({ city }: { city: string }) {
  const [year, setYear] = useState('')
  const [stats, setStats] = useState<MonthlyStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
        .map(([m, count]) => ({
          month: monthLabel(m),
          checkins: count,
          hotels: stats.unique_hotels_per_month[m] ?? 0,
        }))
    : []

  return (
    <div>
      <div className="grid grid-3 section">
        <Stat label="Total check-ins" value={stats?.total_checkins ?? 0} icon="📈" />
        <Stat label="Unique hotels" value={stats?.total_unique_hotels ?? 0} icon="🏨" />
        <Stat label="Cities" value={stats?.total_cities ?? 0} icon="📍" />
      </div>

      <Card title="Check-in trend by month">
        <div className="filters">
          <label className="field">
            Year
            <input type="number" placeholder="All years" value={year} onChange={(e) => setYear(e.target.value)} style={{ width: 120 }} />
          </label>
        </div>

        {loading ? (
          <Loading />
        ) : error ? (
          <ErrorBox message={error} />
        ) : chartData.length === 0 ? (
          <Empty />
        ) : (
          <ResponsiveContainer width="100%" height={340}>
            <AreaChart data={chartData} margin={{ top: 10, right: 12, left: -12, bottom: 0 }}>
              <defs>
                <linearGradient id="fillCheckins" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#2dd4a7" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="#2dd4a7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#243150" vertical={false} />
              <XAxis dataKey="month" stroke="#6b7aa0" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#6b7aa0" fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip
                cursor={{ stroke: '#38bdf8', strokeWidth: 1 }}
                contentStyle={{ background: '#18223b', border: '1px solid #243150', borderRadius: 10, color: '#e7ecf6' }}
              />
              <Area type="monotone" dataKey="checkins" stroke="#2dd4a7" strokeWidth={2.5} fill="url(#fillCheckins)" name="Check-ins" />
              <Line type="monotone" dataKey="hotels" stroke="#a78bfa" strokeWidth={2} dot={false} name="Unique hotels" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </Card>
    </div>
  )
}

function Stat({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="card kpi">
      <span className="spark">{icon}</span>
      <div className="label">{label}</div>
      <div className="value">{value.toLocaleString()}</div>
    </div>
  )
}
