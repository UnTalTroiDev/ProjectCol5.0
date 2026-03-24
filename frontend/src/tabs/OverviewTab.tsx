import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import MedellinMap from '../MedellinMap'
import type {
  ComunaOption, OverviewResponse, TrendsResponse, TrendsMetric,
} from '../types'
import { API_URL, formatCOP, metricValueText, severityClass } from '../utils'

type Props = {
  comunaCode: string
  comunas: ComunaOption[]
  selectedYear: number | null
  onSelectComuna: (code: string) => void
  onAvailableYears: (years: number[]) => void
}

export default function OverviewTab({ comunaCode, comunas, selectedYear, onSelectComuna, onAvailableYears }: Props) {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<OverviewResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [trendsMetric, setTrendsMetric] = useState<TrendsMetric>('safety')
  const [trendsData, setTrendsData] = useState<TrendsResponse | null>(null)
  const [trendsLoading, setTrendsLoading] = useState(false)

  const loadOverview = useCallback(async (code: string, year: number | null) => {
    setLoading(true); setError(null)
    try {
      const p = new URLSearchParams({ comuna_code: code })
      if (year) p.set('year', String(year))
      const res = await fetch(`${API_URL}/api/dashboard/overview?${p}`)
      if (!res.ok) throw new Error('No pudimos cargar los datos del dashboard.')
      setData(await res.json())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Ocurrio un problema inesperado.')
    } finally { setLoading(false) }
  }, [])

  const loadTrends = useCallback(async (metric: TrendsMetric, code: string) => {
    setTrendsLoading(true)
    try {
      const p = new URLSearchParams({ metric })
      if (code !== 'ALL') p.set('comuna_code', code)
      const res = await fetch(`${API_URL}/api/dashboard/trends?${p}`)
      if (!res.ok) return
      const json: TrendsResponse = await res.json()
      setTrendsData(json)
      if (metric === 'safety' && json.available_years.length > 0) onAvailableYears(json.available_years)
    } catch (e) { console.error('Trends fetch error:', e) } finally { setTrendsLoading(false) }
  }, [onAvailableYears])

  useEffect(() => {
    if (!comunas.length) return
    loadOverview(comunaCode, selectedYear)
    loadTrends(trendsMetric, comunaCode)
  }, [comunaCode, selectedYear, comunas.length, trendsMetric, loadOverview, loadTrends])

  useEffect(() => {
    if (!comunas.length) return
    loadTrends(trendsMetric, comunaCode)
  }, [trendsMetric, comunas.length, comunaCode, loadTrends])

  // ── Derived ──
  const mobilityChart = (data?.mobility_by_comuna ?? []).slice(0, 10).map(r => ({
    code: r.comuna_code, name: r.comuna_name ?? r.comuna_code, value: r.mobility_equiv_vehicles,
  }))
  const safetyChart = (data?.safety_by_comuna ?? []).slice(0, 10).map(r => ({
    code: r.comuna_code, name: r.comuna_name ?? r.comuna_code, value: r.safety_homicides,
  }))
  const mapData = useMemo(() => ({
    mobility: Object.fromEntries((data?.mobility_by_comuna ?? []).map(r => [r.comuna_code, r.mobility_equiv_vehicles])),
    safety: Object.fromEntries((data?.safety_by_comuna ?? []).map(r => [r.comuna_code, r.safety_homicides])),
  }), [data])
  const trendsChartData = (trendsData?.series ?? []).filter(p => p.value !== null).map(p => ({ year: String(p.year), value: p.value }))
  const trendsColor: Record<TrendsMetric, string> = { safety: 'var(--danger)', mobility: 'var(--primary)', investment: 'var(--invest)' }
  const trendsLabel: Record<TrendsMetric, string> = { safety: 'Homicidios', mobility: 'Flujo vehicular', investment: 'Inversión' }

  if (error && !data) {
    return (
      <div className="errorBox">
        <div className="errorTitle">No pudimos cargar los datos</div>
        <div className="errorMsg">{error}</div>
      </div>
    )
  }

  if (!data && loading) {
    return (
      <div className="grid">
        <section className="cards">
          {[0, 1, 2].map(i => (
            <div key={i} className="card skeleton-card">
              <div className="skeleton-line skeleton-w60" />
              <div className="skeleton-line skeleton-value" />
              <div className="skeleton-line skeleton-w40" />
            </div>
          ))}
        </section>
      </div>
    )
  }

  if (!data) return null

  return (
    <main className={`grid${loading ? ' grid--loading' : ''}`}>
      <section className="cards">
        {[
          { key: 'mobility_equiv_vehicles', label: 'Flujo vehicular', unit: 'vehículos equivalentes', metaKey: 'mobility_latest_year' },
          { key: 'safety_homicides', label: 'Homicidios', unit: 'casos', metaKey: 'safety_latest_year' },
          { key: 'investment_amount', label: 'Inversión pública', unit: 'COP', metaKey: 'investment_latest_year' },
        ].map(({ key, label, unit, metaKey }) => (
          <div key={key} className="card">
            <div className="cardTitle">{label}</div>
            <div className="cardValue">{metricValueText(data.metrics[key])}</div>
            <div className="cardUnit">{unit}</div>
            {comunaCode !== 'ALL' && data.city_averages[key] ? (
              <div className="cardCompare">
                <span className="cardCompareLabel">Promedio ciudad:</span>
                <span className="cardCompareValue">{metricValueText(data.city_averages[key])}</span>
              </div>
            ) : null}
            <div className="cardMeta">Año: {String(data.meta[metaKey] ?? '—')}</div>
          </div>
        ))}
      </section>

      <div className="mapRow">
        <MedellinMap data={mapData} selected={comunaCode} onSelect={onSelectComuna} />
        <section className="chartsStack">
          {[
            { title: 'Top 10 flujo vehicular', chartData: mobilityChart, colorVar: '--primary', colorMuted: '--primary-muted', dataKey: 'value' },
            { title: 'Top 10 homicidios', chartData: safetyChart, colorVar: '--danger', colorMuted: '--danger-muted', dataKey: 'value' },
          ].map(({ title, chartData, colorVar, colorMuted }) => (
            <div key={title} className="chartPanel">
              <div className="chartTitle">{title}</div>
              <div className="chartBody" style={{ height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {chartData.map(e => {
                        const sel = comunaCode !== 'ALL' && e.code === comunaCode
                        const all = comunaCode === 'ALL'
                        return <Cell key={e.code} fill={all || sel ? `var(${colorVar})` : `var(${colorMuted})`} fillOpacity={all ? 0.85 : sel ? 1 : 0.55} />
                      })}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          ))}
        </section>
      </div>

      {/* Tendencias */}
      <section className="chartPanel trendsPanel">
        <div className="trendsHeader">
          <div className="chartTitle">Tendencia histórica</div>
          <div className="trendsToggle">
            {(['safety', 'mobility', 'investment'] as TrendsMetric[]).map(m => (
              <button key={m} className={`trendsBtn${trendsMetric === m ? ` trendsBtn--active trendsBtn--${m}` : ''}`} onClick={() => setTrendsMetric(m)}>
                {trendsLabel[m]}
              </button>
            ))}
          </div>
        </div>
        {trendsLoading ? <div className="skeleton-rect" style={{ height: 200, marginTop: 8 }} /> :
          trendsChartData.length > 1 ? (
            <div style={{ height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendsChartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: number) => trendsMetric === 'investment' ? [`COP ${formatCOP(v)}`, trendsLabel[trendsMetric]] : [v.toLocaleString('es-CO'), trendsLabel[trendsMetric]]} />
                  <Line type="monotone" dataKey="value" stroke={trendsColor[trendsMetric]} strokeWidth={2.5} dot={{ r: 4, fill: trendsColor[trendsMetric] }} activeDot={{ r: 6 }} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : <div className="trendsEmpty">No hay suficientes puntos históricos para esta selección.</div>}
        <div className="trendsMeta">{trendsData ? `${data.selected.comuna_name ?? data.selected.comuna_code} · ${trendsData.series.length} puntos históricos` : null}</div>
      </section>

      {/* Recomendaciones */}
      <section className="recs">
        <div className="chartTitle">Análisis y recomendaciones</div>
        <div className="recsBox">
          <div className="recsMeta">Territorio: <b>{data.selected.comuna_name ?? data.selected.comuna_code}</b>{selectedYear ? <span className="recsYear"> · Año {selectedYear}</span> : null}</div>
          <ol className="recsList">
            {data.recommendations.map((r, i) => <li key={i} className={severityClass(r)}>{r}</li>)}
          </ol>
        </div>
      </section>
    </main>
  )
}
