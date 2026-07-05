import { useEffect, useState } from 'react'
import { api, type HotelRecord, type RatedHotel } from '../api/client'
import { Card, Empty, ErrorBox, Loading, Rank, ScoreBadge, SourceBadge, money } from './ui'

export function PriceRatingsView({ city }: { city: string }) {
  const [minScore, setMinScore] = useState(8)
  const [cheapest, setCheapest] = useState<HotelRecord[]>([])
  const [bestRated, setBestRated] = useState<RatedHotel[]>([])
  const [bestValue, setBestValue] = useState<RatedHotel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    Promise.all([
      api.getCheapest({ city: city || undefined, min_score: minScore, limit: 10 }),
      api.getBestRated({ city: city || undefined, min_reviews: 50, limit: 10 }),
      api.getBestValue({ city: city || undefined, limit: 10 }),
    ])
      .then(([c, r, v]) => {
        setCheapest(c)
        setBestRated(r)
        setBestValue(v)
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [city, minScore])

  if (error) return <ErrorBox message={error} />

  return (
    <div>
      <div className="grid grid-2 section">
        <Card title="💸 Lowest price">
          <div className="filters" style={{ marginBottom: 14 }}>
            <label className="field">
              Minimum guest score: <b className="muted">{minScore.toFixed(1)}</b>
              <input
                type="range"
                min={0}
                max={9.5}
                step={0.5}
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                style={{ width: 220, padding: 0 }}
              />
            </label>
          </div>
          {loading ? (
            <Loading />
          ) : cheapest.length === 0 ? (
            <Empty label="No offers match that score" />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Hotel</th>
                    <th>Source</th>
                    <th className="num">Score</th>
                    <th className="num">Per night</th>
                  </tr>
                </thead>
                <tbody>
                  {cheapest.map((h) => (
                    <tr key={h.id}>
                      <td className="hotel-cell">
                        {h.hotel_name}
                        <div className="dim" style={{ fontSize: 12, fontWeight: 400 }}>{h.city}</div>
                      </td>
                      <td><SourceBadge source={h.source} /></td>
                      <td className="num"><ScoreBadge score={h.guest_score} /></td>
                      <td className="num"><b>{money(h.nightly_rate, h.currency)}</b></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title="✨ Best value (rating per dollar)">
          {loading ? (
            <Loading />
          ) : bestValue.length === 0 ? (
            <Empty />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Hotel</th>
                    <th className="num">Score</th>
                    <th className="num">Avg rate</th>
                  </tr>
                </thead>
                <tbody>
                  {bestValue.map((h, i) => (
                    <tr key={`${h.hotel_name}-${h.city}`}>
                      <td><Rank n={i + 1} /></td>
                      <td className="hotel-cell">
                        {h.hotel_name}
                        <div className="dim" style={{ fontSize: 12, fontWeight: 400 }}>{h.city}</div>
                      </td>
                      <td className="num"><ScoreBadge score={h.avg_guest_score} /></td>
                      <td className="num"><b>{money(h.avg_nightly_rate)}</b></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <Card title="🏆 Best rated overall (50+ reviews)">
        {loading ? (
          <Loading />
        ) : bestRated.length === 0 ? (
          <Empty />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Hotel</th>
                  <th>City</th>
                  <th className="num">Avg score</th>
                  <th className="num">Reviews</th>
                  <th className="num">Avg rate</th>
                </tr>
              </thead>
              <tbody>
                {bestRated.map((h, i) => (
                  <tr key={`${h.hotel_name}-${h.city}`}>
                    <td><Rank n={i + 1} /></td>
                    <td className="hotel-cell">{h.hotel_name}</td>
                    <td className="muted">{h.city}</td>
                    <td className="num"><ScoreBadge score={h.avg_guest_score} /></td>
                    <td className="num">{h.review_count.toLocaleString()}</td>
                    <td className="num">{money(h.avg_nightly_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
