import { useEffect, useRef, useState } from 'react'
import type { MetricBlock } from './types'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const CHART_COLORS = {
  primary: 'var(--primary)',
  primaryMuted: 'var(--primary-muted)',
  danger: 'var(--danger)',
  dangerMuted: 'var(--danger-muted)',
  invest: 'var(--invest)',
  border: 'var(--border)',
}

// ---------------------------------------------------------------------------
// Formatters
// ---------------------------------------------------------------------------

export function formatCOP(v: number) {
  return v.toLocaleString('es-CO', { maximumFractionDigits: 0 })
}

export function metricValueText(m?: MetricBlock) {
  if (!m || m.value === null || !Number.isFinite(m.value)) return 'N/D'
  if (m.unit === 'COP') return formatCOP(m.value)
  return m.value.toLocaleString('es-CO', { maximumFractionDigits: 2 })
}

export function severityClass(text: string) {
  const l = text.toLowerCase()
  if (l.includes('[critico]') || l.includes('alerta:')) return 'sev-critico'
  if (l.includes('[alto]')) return 'sev-alto'
  if (l.includes('[medio]')) return 'sev-medio'
  if (l.includes('[bajo]')) return 'sev-bajo'
  return ''
}

// ---------------------------------------------------------------------------
// Shared UI components
// ---------------------------------------------------------------------------

export function UnavailableCard({ label }: { label: string }) {
  return (
    <div className="unavailableCard">
      <span className="unavailableIcon">⚠</span>
      <span>{label} — dataset no disponible en MEData en este momento.</span>
    </div>
  )
}

export function SectionSkeleton() {
  return (
    <div className="chartPanel">
      <div className="skeleton-line skeleton-w50" style={{ marginBottom: 12 }} />
      <div className="skeleton-rect" style={{ height: 180 }} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// useFetch — lightweight data fetching hook with in-memory cache
// ---------------------------------------------------------------------------

const fetchCache = new Map<string, { data: unknown; ts: number }>()
const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

export function useFetch<T>(url: string | null) {
  const [data, setData] = useState<T | null>(() => {
    if (!url) return null
    const cached = fetchCache.get(url)
    if (cached && Date.now() - cached.ts < CACHE_TTL) return cached.data as T
    return null
  })
  const [loading, setLoading] = useState(!data && !!url)
  const [error, setError] = useState<string | null>(null)
  const urlRef = useRef(url)
  urlRef.current = url

  useEffect(() => {
    if (!url) { setData(null); setLoading(false); return }

    const cached = fetchCache.get(url)
    if (cached && Date.now() - cached.ts < CACHE_TTL) {
      setData(cached.data as T)
      setLoading(false)
      setError(null)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    fetch(url)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then((json: T) => {
        fetchCache.set(url, { data: json, ts: Date.now() })
        if (!cancelled) { setData(json); setLoading(false) }
      })
      .catch(e => {
        if (!cancelled) { setError(e instanceof Error ? e.message : 'Error de red'); setLoading(false) }
      })

    return () => { cancelled = true }
  }, [url])

  return { data, loading, error }
}

// ---------------------------------------------------------------------------
// CSV export utility
// ---------------------------------------------------------------------------

export function exportToCSV(rows: Record<string, unknown>[], filename: string) {
  if (!rows.length) return
  const headers = Object.keys(rows[0])
  const lines = [
    headers.join(','),
    ...rows.map(r =>
      headers.map(h => {
        const v = r[h]
        const s = v == null ? '' : String(v)
        return s.includes(',') || s.includes('"') || s.includes('\n')
          ? `"${s.replace(/"/g, '""')}"` : s
      }).join(',')
    ),
  ]
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}
