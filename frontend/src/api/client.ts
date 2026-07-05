const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export interface TopHotel {
  hotel_name: string
  city: string
  checkin_count: number
  avg_nightly_rate: number
  avg_guest_score: number
}

export interface MonthlyStats {
  monthly_totals: Record<string, number>
  unique_hotels_per_month: Record<string, number>
  total_checkins: number
  total_unique_hotels: number
  total_cities: number
}

export interface HotelRecord {
  id: number
  hotel_name: string
  source: string
  city: string
  country: string
  checkin_date: string | null
  checkout_date: string | null
  nightly_rate: number
  currency: string
  available_rooms: number
  occupancy_pct: number
  room_type: string
  address?: string
  guest_score: number
  review_count: number
  scraped_at: string | null
  url: string
}

export interface HotelListResponse {
  items: HotelRecord[]
  total: number
}

export interface SourceInfo {
  id: string
  label: string
  requires_playwright: boolean
  legal_note: string
}

export interface SourceScrapeStatus {
  source: string
  label: string
  last_scraped_at: string | null
  last_attempt_at: string | null
  last_status: string
  last_error: string
  records_in_db: number
  using_cached_data: boolean
}

export interface LastScrapedSummary {
  overall_last_scraped_at: string | null
  last_automation_run_at: string | null
  data_from_cache: boolean
  sources: SourceScrapeStatus[]
}

export interface ScrapeRequest {
  source: string
  city: string
  checkin_date?: string | null
  checkout_date?: string | null
  max_pages: number
}

export interface ScrapeJobAccepted {
  log_id: number
  status: string
}

export interface ScrapeJobStatus {
  id: number
  source: string
  city: string
  status: string
  records_scraped: number
  error_message: string
  started_at: string | null
  completed_at: string | null
  duration_seconds: number | null
}

export interface RatedHotel {
  hotel_name: string
  city: string
  avg_guest_score: number
  avg_nightly_rate: number
  review_count: number
  checkin_count: number
  value_score: number | null
}

export interface Overview {
  total_records: number
  total_hotels: number
  total_cities: number
  avg_nightly_rate: number
  min_nightly_rate: number
  max_nightly_rate: number
  avg_guest_score: number
  by_source: Record<string, number>
  most_checkins: TopHotel | null
  cheapest: HotelRecord | null
  best_rated: RatedHotel | null
  best_value: RatedHotel | null
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${body}`)
  }
  return res.json() as Promise<T>
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  if (entries.length === 0) return ''
  return '?' + new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString()
}

export const api = {
  getTopHotels: (params: { city?: string; month?: number; year?: number; limit?: number }) =>
    request<TopHotel[]>(`/api/hotels/top${qs(params)}`),

  getMonthlyStats: (params: { city?: string; year?: number }) =>
    request<MonthlyStats>(`/api/stats/monthly${qs(params)}`),

  getOverview: (params: { city?: string }) =>
    request<Overview>(`/api/stats/overview${qs(params)}`),

  getCheapest: (params: { city?: string; min_score?: number; limit?: number }) =>
    request<HotelRecord[]>(`/api/hotels/cheapest${qs(params)}`),

  getBestRated: (params: { city?: string; min_reviews?: number; limit?: number }) =>
    request<RatedHotel[]>(`/api/hotels/best-rated${qs(params)}`),

  getBestValue: (params: { city?: string; limit?: number }) =>
    request<RatedHotel[]>(`/api/hotels/best-value${qs(params)}`),

  getHotels: (params: { source?: string; city?: string; limit?: number; offset?: number }) =>
    request<HotelListResponse>(`/api/hotels${qs(params)}`),

  getSources: () => request<SourceInfo[]>('/api/meta/sources'),

  getCities: () => request<string[]>('/api/meta/cities'),

  getLastScraped: () => request<LastScrapedSummary>('/api/meta/last-scraped'),

  triggerScrape: (body: ScrapeRequest) =>
    request<ScrapeJobAccepted>('/api/scrape', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getScrapeStatus: (logId: number) => request<ScrapeJobStatus>(`/api/scrape/${logId}`),

  getScrapeHistory: (params: { source?: string; limit?: number }) =>
    request<ScrapeJobStatus[]>(`/api/scrape/history${qs(params)}`),
}
