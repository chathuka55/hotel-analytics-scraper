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
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    api.getCities().then(setCities).catch(() => {})
  }, [])

  useEffect(() => {
    const onResize = () => {
      if (window.matchMedia('(min-width: 901px)').matches) {
        setMenuOpen(false)
      }
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    if (!menuOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false)
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [menuOpen])

  const active = TABS.find((t) => t.id === tab)!

  function selectTab(id: TabId) {
    setTab(id)
    setMenuOpen(false)
  }

  return (
    <div className={`app ${menuOpen ? 'menu-open' : ''}`}>
      {menuOpen && (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Close menu"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <aside id="app-sidebar" className={`sidebar ${menuOpen ? 'open' : ''}`}>
        <div className="brand">
          <span className="brand-logo">⛱</span>
          <span className="brand-text">
            <b>HotelScope</b>
            <span>Sri Lanka analytics</span>
          </span>
        </div>

        <nav className="sidebar-nav" aria-label="Main">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`nav-item ${tab === t.id ? 'active' : ''}`}
              onClick={() => selectTab(t.id)}
            >
              <span className="ico">{t.icon}</span>
              {t.label}
            </button>
          ))}
        </nav>
      </aside>

      <div className="main-shell">
        <header className="mobile-topbar">
          <button
            type="button"
            className="hamburger"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            aria-controls="app-sidebar"
            onClick={() => setMenuOpen((o) => !o)}
          >
            <span className={menuOpen ? 'is-open' : ''} />
          </button>
          <div className="mobile-brand">
            <span className="brand-logo">⛱</span>
            <b>HotelScope</b>
          </div>
          {tab !== 'scrape' && (
            <label className="field mobile-city">
              <span className="sr-only">City filter</span>
              <select value={city} onChange={(e) => setCity(e.target.value)} aria-label="City filter">
                <option value="">All cities</option>
                {cities.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>
          )}
        </header>

        <main className="content">
          <div className="page-head">
            <div className="page-head-title">
              <h1>{active.label}</h1>
              <div className="sub">{active.sub}</div>
            </div>
            {tab !== 'scrape' && (
              <label className="field desktop-city">
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
    </div>
  )
}

export default App
