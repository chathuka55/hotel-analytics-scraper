import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api, type MonthlyStats, type Overview } from '../api/client'
import { Card, Empty, ErrorBox, Loading, ScoreBadge, money, monthLabel } from './ui'

const SOURCE_COLORS: Record<string, string> = {
  booking: '#60a5fa',
  agoda: '#fb7185',
  expedia: '#fcd34d',
  google: '#4285f4',
  sltda: '#2dd4a7',
}

export function OverviewView({ city }: { city: string }) {
  const [data, setData] = useState<Overview | null>(null)
  const [monthly, setMonthly] = useState<MonthlyStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    Promise.all([
      api.getOverview({ city: city || undefined }),
      api.getMonthlyStats({ city: city || undefined }),
    ])
      .then(([o, m]) => {
        setData(o)
        setMonthly(m)
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [city])

  if (loading) return <Loading />
  if (error) return <ErrorBox message={error} />
  if (!data || data.total_records === 0) return <Empty />

  const sourceData = Object.entries(data.by_source).map(([name, value]) => ({ name, value }))
  const trendData = monthly
    ? Object.entries(monthly.monthly_totals)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([m, count]) => ({ month: monthLabel(m), checkins: count }))
    : []

  return (
    <div>
      {/* KPI row */}
      <div className="grid grid-4 section">
        <Kpi label="Records collected" value={data.total_records.toLocaleString()} meta="check-in data points" icon="🗂" />
        <Kpi label="Hotels tracked" value={data.total_hotels.toLocaleString()} meta={`across ${data.total_cities} cities`} icon="🏨" />
        <Kpi label="Avg nightly rate" value={money(data.avg_nightly_rate)} meta={`${money(data.min_nightly_rate)} – ${money(data.max_nightly_rate)}`} icon="💵" />
        <Kpi label="Avg guest score" value={data.avg_guest_score.toFixed(1)} meta="out of 10" icon="⭐" />
      </div>

      {/* Winner highlights */}
      <div className="section">
        <div className="section-head">
          <h2>Headline answers{city ? ` — ${city}` : ''}</h2>
        </div>
        <div className="grid grid-4">
          <Highlight
            cls=""
            tag="🔥 Most check-ins"
            name={data.most_checkins?.hotel_name ?? '—'}
            sub={data.most_checkins?.city ?? ''}
            stats={[
              { label: 'Check-ins', value: String(data.most_checkins?.checkin_count ?? 0) },
              { label: 'Avg rate', value: money(data.most_checkins?.avg_nightly_rate ?? 0) },
            ]}
          />
          <Highlight
            cls="gold"
            tag="💸 Lowest price (good rating)"
            name={data.cheapest?.hotel_name ?? '—'}
            sub={data.cheapest?.city ?? ''}
            stats={[
              { label: 'Per night', value: money(data.cheapest?.nightly_rate ?? 0, data.cheapest?.currency) },
              { label: 'Score', node: <ScoreBadge score={data.cheapest?.guest_score ?? 0} /> },
            ]}
          />
          <Highlight
            cls="violet"
            tag="🏆 Best rated overall"
            name={data.best_rated?.hotel_name ?? '—'}
            sub={data.best_rated?.city ?? ''}
            stats={[
              { label: 'Score', node: <ScoreBadge score={data.best_rated?.avg_guest_score ?? 0} /> },
              { label: 'Reviews', value: (data.best_rated?.review_count ?? 0).toLocaleString() },
            ]}
          />
          <Highlight
            cls="rose"
            tag="✨ Best value"
            name={data.best_value?.hotel_name ?? '—'}
            sub={data.best_value?.city ?? ''}
            stats={[
              { label: 'Score', node: <ScoreBadge score={data.best_value?.avg_guest_score ?? 0} /> },
              { label: 'Avg rate', value: money(data.best_value?.avg_nightly_rate ?? 0) },
            ]}
          />
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-2">
        <Card title="Monthly check-in volume">
          {trendData.length === 0 ? (
            <Empty />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={trendData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <XAxis dataKey="month" stroke="#6b7aa0" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#6b7aa0" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip
                  cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                  contentStyle={{ background: '#18223b', border: '1px solid #243150', borderRadius: 10, color: '#e7ecf6' }}
                />
                <Bar dataKey="checkins" radius={[6, 6, 0, 0]} fill="#2dd4a7" name="Check-ins" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card title="Records by source">
          {sourceData.length === 0 ? (
            <Empty />
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <ResponsiveContainer width="55%" height={220}>
                <PieChart>
                  <Pie data={sourceData} dataKey="value" nameKey="name" innerRadius={52} outerRadius={88} paddingAngle={3} stroke="none">
                    {sourceData.map((s) => (
                      <Cell key={s.name} fill={SOURCE_COLORS[s.name] ?? '#94a3c4'} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#18223b', border: '1px solid #243150', borderRadius: 10, color: '#e7ecf6' }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {sourceData.map((s) => (
                  <div key={s.name} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                    <span style={{ width: 11, height: 11, borderRadius: 3, background: SOURCE_COLORS[s.name] ?? '#94a3c4' }} />
                    <span style={{ flex: 1, textTransform: 'capitalize' }}>{s.name}</span>
                    <b>{s.value}</b>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

function Kpi({ label, value, meta, icon }: { label: string; value: string; meta: string; icon: string }) {
  return (
    <div className="card kpi">
      <span className="spark">{icon}</span>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      <div className="meta">{meta}</div>
    </div>
  )
}

type Stat = { label: string; value?: string; node?: React.ReactNode }
function Highlight({ cls, tag, name, sub, stats }: { cls: string; tag: string; name: string; sub: string; stats: Stat[] }) {
  return (
    <div className={`highlight ${cls}`}>
      <span className="tag">{tag}</span>
      <div className="hl-name">{name}</div>
      <div className="hl-city">{sub}</div>
      <div className="hl-stat">
        {stats.map((s) => (
          <div key={s.label}>
            <span>{s.label}</span>
            {s.node ?? <b>{s.value}</b>}
          </div>
        ))}
      </div>
    </div>
  )
}
