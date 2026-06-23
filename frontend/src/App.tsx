import { useState } from 'react'
import { TopHotelsView } from './components/TopHotelsView'
import { MonthlyTrendsView } from './components/MonthlyTrendsView'
import { HotelBrowserView } from './components/HotelBrowserView'
import { ScrapeTriggerView } from './components/ScrapeTriggerView'

const TABS = [
  { id: 'top', label: 'Top Hotels', render: () => <TopHotelsView /> },
  { id: 'monthly', label: 'Monthly Trends', render: () => <MonthlyTrendsView /> },
  { id: 'browse', label: 'Browse Hotels', render: () => <HotelBrowserView /> },
  { id: 'scrape', label: 'Run Scrape', render: () => <ScrapeTriggerView /> },
] as const

function App() {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]['id']>('top')

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '24px 16px' }}>
      <h1 style={{ fontSize: 28, marginBottom: 4 }}>Sri Lanka Hotel Analytics</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>
        Check-in data scraped from Booking.com, Agoda, Expedia, SLTDA &amp; data.gov.lk
      </p>

      <nav style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--border)', marginBottom: 24 }}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              background: activeTab === tab.id ? 'var(--text-h)' : 'transparent',
              color: activeTab === tab.id ? '#fff' : 'var(--text)',
              border: 'none',
              borderRadius: '6px 6px 0 0',
              padding: '10px 16px',
            }}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main>{TABS.find((t) => t.id === activeTab)?.render()}</main>
    </div>
  )
}

export default App
