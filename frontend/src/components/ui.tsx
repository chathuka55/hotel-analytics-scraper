import type { ReactNode } from 'react'

export function money(value: number, currency = 'USD'): string {
  const sym = currency === 'USD' ? '$' : currency === 'LKR' ? 'Rs ' : `${currency} `
  return `${sym}${value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

export function scoreClass(score: number): string {
  if (score >= 8.5) return 'score'
  if (score >= 7) return 'score mid'
  return 'score low'
}

export function ScoreBadge({ score }: { score: number }) {
  return <span className={scoreClass(score)}>{score.toFixed(1)}</span>
}

export function SourceBadge({ source }: { source: string }) {
  return <span className={`badge src-${source}`}>{source}</span>
}

export function Rank({ n }: { n: number }) {
  const cls = n <= 3 ? `rank r${n}` : 'rank'
  return <span className={cls}>{n}</span>
}

export function Card({ title, children, className = '' }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <div className={`card ${className}`}>
      {title && <div className="card-title">{title}</div>}
      {children}
    </div>
  )
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="state">
      <div className="spinner" />
      <div>{label}</div>
    </div>
  )
}

export function Empty({ label = 'No data yet' }: { label?: string }) {
  return (
    <div className="state">
      <div className="big">∅</div>
      <div>{label}</div>
    </div>
  )
}

export function ErrorBox({ message }: { message: string }) {
  return <div className="error-box">⚠ {message}</div>
}

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
export function monthLabel(ym: string): string {
  const [, m] = ym.split('-')
  const idx = Number(m) - 1
  return MONTH_NAMES[idx] ? `${MONTH_NAMES[idx]} ${ym.split('-')[0]}` : ym
}
