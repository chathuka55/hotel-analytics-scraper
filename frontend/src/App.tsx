import { useEffect, useState } from 'react'
import { api } from './api/client'
import { OverviewView } from './components/OverviewView'
import { TopHotelsView } from './components/TopHotelsView'
import { PriceRatingsView } from './components/PriceRatingsView'
import { MonthlyTrendsView } from './components/MonthlyTrendsView'
import { HotelBrowserView } from './components/HotelBrowserView'
import { ScrapeTriggerView } from './components/ScrapeTriggerView'
import { LastScrapedPanel } from './components/LastScrapedPanel'

type TabId = 'overview' | 'top' | 'price' | 'monthly' | 'browse' | 'scrape'

const TABS: { id: TabId; label: string; icon: string; sub: string }[] = [
  { id: 'overview', label: 'Overview', icon: '◎', sub: 'Headline answers & KPIs' },
  { id: 'top', label: 'Top Hotels', icon: '🔥', sub: 'Ranked by check-ins' },
  { id: 'price', label: 'Price & Ratings', icon: '💸', sub: 'Lowest price · best rated · best value' },
  { id: 'monthly', label: 'Monthly Trends', icon: '📈', sub: 'Check-in volume over time' },
  { id: 'browse', label: 'Browse Records', icon: '🗂', sub: 'Raw scraped data' },
  { id: 'scrape', label: 'Run Scrape', icon: '⚡', sub: 'Trigger a scrape job' },
]

function App() {
  const [tab, setTab] = useState<TabId>('overview')
  const [cities, setCities] = useState<string[]>([])
  const [city, setCity] = useState('')

  useEffect(() => {
    api.getCities().then(setCities).catch(() => {})
  }, [])

  const active = TABS.find((t) => t.id === tab)!

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-logo">⛱</span>
          <span className="brand-text">
            <b>HotelScope</b>
            <span>Sri Lanka analytics</span>
          </span>
        </div>

        {TABS.map((t) => (
          <button key={t.id} className={`nav-item ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>
            <span className="ico">{t.icon}</span>
            {t.label}
          </button>
        ))}
      </aside>

      <main className="content">
        <div className="page-head">
          <div>
            <h1>{active.label}</h1>
            <div className="sub">{active.sub}</div>
          </div>
          {tab !== 'scrape' && (
            <label className="field" style={{ minWidth: 180 }}>
              City filter
              <select value={city} onChange={(e) => setCity(e.target.value)}>
                <option value="">All cities</option>
                {cities.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>
          )}
          <LastScrapedPanel compact />
        </div>

        {tab === 'overview' && <LastScrapedPanel />}

        {tab === 'overview' && <OverviewView city={city} />}
        {tab === 'top' && <TopHotelsView city={city} />}
        {tab === 'price' && <PriceRatingsView city={city} />}
        {tab === 'monthly' && <MonthlyTrendsView city={city} />}
        {tab === 'browse' && <HotelBrowserView city={city} />}
        {tab === 'scrape' && <ScrapeTriggerView city={city} />}
      </main>
    </div>
  )
}

export default App
