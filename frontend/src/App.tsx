import { useEffect, useMemo, useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import MedellinMap from './MedellinMap'
import './App.css'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ComunaOption = { code: string; name?: string | null }
type MetricBlock = { value: number | null; unit: string }

type OverviewResponse = {
  meta: Record<string, unknown>
  selected: { comuna_code: string; comuna_name?: string | null }
  metrics: Record<string, MetricBlock>
  city_averages: Record<string, MetricBlock>
  recommendations: string[]
  mobility_by_comuna: Array<{ comuna_code: string; comuna_name?: string; mobility_equiv_vehicles: number }>
  safety_by_comuna: Array<{ comuna_code: string; comuna_name?: string; safety_homicides: number }>
}

type TrendPoint = { year: number; value: number | null }

type TrendsResponse = {
  metric: string
  comuna_code: string
  unit: string
  series: TrendPoint[]
  available_years: number[]
}

type CrimeStatsResponse = {
  comuna_code: string
  year: number | null
  homicidios: { value: number | null; unit: string; year: number | null }
  lesiones_comunes: { value: number | null; unit: string; year: number | null; available: boolean }
  top_homicidios_by_comuna: Array<{ comuna_code: string; safety_homicides: number }>
  top_lesiones_by_comuna: Array<{ comuna_code: string; lesiones_count: number }>
}

type TrendsMetric = 'safety' | 'mobility' | 'investment'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCOP(value: number) {
  if (!Number.isFinite(value)) return 'N/D'
  return value.toLocaleString('es-CO', { maximumFractionDigits: 0 })
}

function metricValueText(m?: MetricBlock) {
  if (!m || m.value === null || !Number.isFinite(m.value)) return 'N/D'
  if (m.unit === 'COP') return formatCOP(m.value)
  return m.value.toLocaleString('es-CO', { maximumFractionDigits: 2 })
}

function severityClass(text: string): string {
  const lower = text.toLowerCase()
  if (lower.includes('[critico]')) return 'sev-critico'
  if (lower.includes('[alto]')) return 'sev-alto'
  if (lower.includes('[medio]')) return 'sev-medio'
  if (lower.includes('[bajo]')) return 'sev-bajo'
  if (lower.includes('alerta:')) return 'sev-critico'
  return ''
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function SkeletonGrid() {
  return (
    <main className="grid">
      <section className="cards">
        {[0, 1, 2].map((i) => (
          <div key={i} className="card skeleton-card">
            <div className="skeleton-line skeleton-w60" />
            <div className="skeleton-line skeleton-value" />
            <div className="skeleton-line skeleton-w40" />
          </div>
        ))}
      </section>
      <section className="charts">
        {[0, 1].map((i) => (
          <div key={i} className="chartPanel skeleton-chart">
            <div className="skeleton-line skeleton-w50" />
            <div className="skeleton-rect" />
          </div>
        ))}
      </section>
    </main>
  )
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export default function App() {
  const [comunas, setComunas] = useState<ComunaOption[]>([])
  const [selected, setSelected] = useState<string>('ALL')
  const [selectedYear, setSelectedYear] = useState<number | null>(null)
  const [availableYears, setAvailableYears] = useState<number[]>([])

  const [loading, setLoading] = useState<boolean>(true)
  const [data, setData] = useState<OverviewResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [trendsMetric, setTrendsMetric] = useState<TrendsMetric>('safety')
  const [trendsData, setTrendsData] = useState<TrendsResponse | null>(null)
  const [trendsLoading, setTrendsLoading] = useState(false)

  const [crimeStats, setCrimeStats] = useState<CrimeStatsResponse | null>(null)
  const [crimeLoading, setCrimeLoading] = useState(false)

  const comunaOptions = useMemo(() => {
    const base: ComunaOption[] = [{ code: 'ALL', name: 'Toda la ciudad' }]
    return base.concat(comunas)
  }, [comunas])

  // ── Fetchers ──────────────────────────────────────────────────────────────

  async function loadComunas() {
    const res = await fetch(`${API_URL}/api/territory/comunas`)
    if (!res.ok) throw new Error('No pudimos obtener la lista de territorios.')
    const json = await res.json()
    setComunas(json.comunas ?? [])
    if (json.comunas?.length) {
      setSelected((prev) => (prev === 'ALL' ? json.comunas[0].code : prev))
    }
  }

  async function loadOverview(comunaCode: string, year: number | null) {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ comuna_code: comunaCode })
      if (year !== null) params.set('year', String(year))
      const res = await fetch(`${API_URL}/api/dashboard/overview?${params}`)
      if (!res.ok) throw new Error('No pudimos cargar los datos del dashboard.')
      setData(await res.json())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Ocurrio un problema inesperado.')
    } finally {
      setLoading(false)
    }
  }

  async function loadTrends(metric: TrendsMetric, comunaCode: string) {
    setTrendsLoading(true)
    try {
      const params = new URLSearchParams({ metric })
      if (comunaCode !== 'ALL') params.set('comuna_code', comunaCode)
      const res = await fetch(`${API_URL}/api/dashboard/trends?${params}`)
      if (!res.ok) return
      const json: TrendsResponse = await res.json()
      setTrendsData(json)
      // Poblar años disponibles desde la primera llamada (safety).
      if (metric === 'safety' && json.available_years.length > 0) {
        setAvailableYears(json.available_years)
      }
    } catch {
      // Tendencias son opcionales: silenciar errores.
    } finally {
      setTrendsLoading(false)
    }
  }

  async function loadCrimeStats(comunaCode: string, year: number | null) {
    setCrimeLoading(true)
    try {
      const params = new URLSearchParams()
      if (comunaCode !== 'ALL') params.set('comuna_code', comunaCode)
      if (year !== null) params.set('year', String(year))
      const res = await fetch(`${API_URL}/api/dashboard/crime-stats?${params}`)
      if (!res.ok) return
      setCrimeStats(await res.json())
    } catch {
      // Crime stats son opcionales: silenciar errores.
    } finally {
      setCrimeLoading(false)
    }
  }

  // ── Effects ───────────────────────────────────────────────────────────────

  useEffect(() => {
    ;(async () => {
      await loadComunas()
    })().catch((e: unknown) => {
      setError(e instanceof Error ? e.message : 'No pudimos conectar con el servidor.')
      setLoading(false)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (comunas.length === 0) return
    loadOverview(selected, selectedYear).catch(() => {})
    loadTrends(trendsMetric, selected).catch(() => {})
    loadCrimeStats(selected, selectedYear).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, selectedYear, comunas.length])

  useEffect(() => {
    if (comunas.length === 0) return
    loadTrends(trendsMetric, selected).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trendsMetric])

  // ── Derived chart data ────────────────────────────────────────────────────

  const mobilityChart = (data?.mobility_by_comuna ?? []).slice(0, 10).map((r) => ({
    code: r.comuna_code,
    name: r.comuna_name ?? r.comuna_code,
    value: r.mobility_equiv_vehicles,
  }))

  const safetyChart = (data?.safety_by_comuna ?? []).slice(0, 10).map((r) => ({
    code: r.comuna_code,
    name: r.comuna_name ?? r.comuna_code,
    value: r.safety_homicides,
  }))

  const mapData = useMemo(() => ({
    mobility: Object.fromEntries(
      (data?.mobility_by_comuna ?? []).map((r) => [r.comuna_code, r.mobility_equiv_vehicles])
    ),
    safety: Object.fromEntries(
      (data?.safety_by_comuna ?? []).map((r) => [r.comuna_code, r.safety_homicides])
    ),
  }), [data])

  const trendsChartData = (trendsData?.series ?? [])
    .filter((p) => p.value !== null)
    .map((p) => ({ year: String(p.year), value: p.value }))

  const trendsColor: Record<TrendsMetric, string> = {
    safety: 'var(--danger)',
    mobility: 'var(--primary)',
    investment: 'var(--invest)',
  }

  const trendsLabel: Record<TrendsMetric, string> = {
    safety: 'Homicidios',
    mobility: 'Flujo vehicular',
    investment: 'Inversión pública',
  }

  const showSkeleton = !data && loading
  const showError = !!error && !data

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="page">
      {/* Header */}
      <header className="header">
        <div>
          <h1>MedCity Dashboard</h1>
          <p className="subtitle">Movilidad, seguridad e inversión pública de Medellín</p>
        </div>
        <div className="filters">
          <label>
            Territorio
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              aria-label="Seleccionar territorio"
            >
              {comunaOptions.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.code === 'ALL' ? c.name : c.name ? `${c.name} (${c.code})` : c.code}
                </option>
              ))}
            </select>
          </label>

          <label>
            Año
            <select
              value={selectedYear ?? ''}
              onChange={(e) => setSelectedYear(e.target.value ? Number(e.target.value) : null)}
              aria-label="Seleccionar año"
            >
              <option value="">Último disponible</option>
              {availableYears.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </label>
        </div>
      </header>

      {/* Error */}
      {showError ? (
        <div className="errorBox">
          <div className="errorTitle">No pudimos cargar los datos</div>
          <div className="errorMsg">{error}</div>
        </div>
      ) : null}

      {/* Skeleton */}
      {showSkeleton ? (
        <SkeletonGrid />
      ) : data ? (
        <main className={`grid${loading ? ' grid--loading' : ''}`}>

          {/* KPI Cards */}
          <section className="cards">
            <div className="card">
              <div className="cardTitle">Flujo vehicular</div>
              <div className="cardValue">{metricValueText(data.metrics.mobility_equiv_vehicles)}</div>
              <div className="cardUnit">vehículos equivalentes</div>
              {selected !== 'ALL' && data.city_averages.mobility_equiv_vehicles ? (
                <div className="cardCompare">
                  <span className="cardCompareLabel">Promedio ciudad:</span>
                  <span className="cardCompareValue">
                    {metricValueText(data.city_averages.mobility_equiv_vehicles)}
                  </span>
                </div>
              ) : null}
              <div className="cardMeta">Año: {String(data.meta.mobility_latest_year ?? '—')}</div>
            </div>

            <div className="card">
              <div className="cardTitle">Homicidios</div>
              <div className="cardValue">{metricValueText(data.metrics.safety_homicides)}</div>
              <div className="cardUnit">casos</div>
              {selected !== 'ALL' && data.city_averages.safety_homicides ? (
                <div className="cardCompare">
                  <span className="cardCompareLabel">Promedio ciudad:</span>
                  <span className="cardCompareValue">
                    {metricValueText(data.city_averages.safety_homicides)}
                  </span>
                </div>
              ) : null}
              <div className="cardMeta">Año: {String(data.meta.safety_latest_year ?? '—')}</div>
            </div>

            <div className="card">
              <div className="cardTitle">Inversión pública</div>
              <div className="cardValue">{metricValueText(data.metrics.investment_amount)}</div>
              <div className="cardUnit">COP</div>
              {selected !== 'ALL' && data.city_averages.investment_amount ? (
                <div className="cardCompare">
                  <span className="cardCompareLabel">Promedio ciudad:</span>
                  <span className="cardCompareValue">
                    {metricValueText(data.city_averages.investment_amount)}
                  </span>
                </div>
              ) : null}
              <div className="cardMeta">Año: {String(data.meta.investment_latest_year ?? '—')}</div>
            </div>
          </section>

          {/* Map + Bar charts */}
          <div className="mapRow">
            <MedellinMap data={mapData} selected={selected} onSelect={setSelected} />

            <section className="chartsStack">
              <div className="chartPanel">
                <div className="chartTitle">Top 10 por flujo vehicular</div>
                <div className="chartBody">
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={mobilityChart} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} />
                      <Tooltip />
                      <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                        {mobilityChart.map((entry) => {
                          const isSelected = selected !== 'ALL' && entry.code === selected
                          const isAll = selected === 'ALL'
                          return (
                            <Cell
                              key={entry.code}
                              fill={isAll || isSelected ? 'var(--primary)' : 'var(--primary-muted)'}
                              fillOpacity={isAll ? 0.85 : isSelected ? 1 : 0.55}
                            />
                          )
                        })}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="chartPanel">
                <div className="chartTitle">Top 10 por homicidios</div>
                <div className="chartBody">
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={safetyChart} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} />
                      <Tooltip />
                      <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                        {safetyChart.map((entry) => {
                          const isSelected = selected !== 'ALL' && entry.code === selected
                          const isAll = selected === 'ALL'
                          return (
                            <Cell
                              key={entry.code}
                              fill={isAll || isSelected ? 'var(--danger)' : 'var(--danger-muted)'}
                              fillOpacity={isAll ? 0.85 : isSelected ? 1 : 0.55}
                            />
                          )
                        })}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </section>
          </div>

          {/* Tendencias temporales */}
          <section className="chartPanel trendsPanel">
            <div className="trendsHeader">
              <div className="chartTitle">Tendencia histórica</div>
              <div className="trendsToggle">
                {(['safety', 'mobility', 'investment'] as TrendsMetric[]).map((m) => (
                  <button
                    key={m}
                    className={`trendsBtn${trendsMetric === m ? ' trendsBtn--active trendsBtn--' + m : ''}`}
                    onClick={() => setTrendsMetric(m)}
                  >
                    {trendsLabel[m]}
                  </button>
                ))}
              </div>
            </div>

            {trendsLoading ? (
              <div className="skeleton-rect" style={{ height: 200, marginTop: 8 }} />
            ) : trendsChartData.length > 1 ? (
              <div className="chartBody" style={{ height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendsChartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip
                      formatter={(val: number) =>
                        trendsMetric === 'investment'
                          ? [`COP ${formatCOP(val)}`, trendsLabel[trendsMetric]]
                          : [val.toLocaleString('es-CO'), trendsLabel[trendsMetric]]
                      }
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke={trendsColor[trendsMetric]}
                      strokeWidth={2.5}
                      dot={{ r: 4, fill: trendsColor[trendsMetric] }}
                      activeDot={{ r: 6 }}
                      connectNulls
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="trendsEmpty">
                {trendsChartData.length === 1
                  ? 'Solo hay datos de un año — no se puede mostrar tendencia.'
                  : 'No hay datos históricos disponibles para esta selección.'}
              </div>
            )}

            <div className="trendsMeta">
              {trendsData
                ? `${data.selected.comuna_name ?? data.selected.comuna_code} · ${trendsData.series.length} punto${trendsData.series.length !== 1 ? 's' : ''} histórico${trendsData.series.length !== 1 ? 's' : ''}`
                : null}
            </div>
          </section>

          {/* Crime stats */}
          {crimeStats ? (
            <section className="crimeSection">
              <div className="chartTitle crimeTitle">Estadísticas de criminalidad</div>
              <div className="crimeCards">
                <div className="crimeCard crimeCard--homicidios">
                  <div className="crimeCardLabel">Homicidios</div>
                  <div className="crimeCardValue">
                    {crimeStats.homicidios.value !== null
                      ? crimeStats.homicidios.value.toLocaleString('es-CO')
                      : 'N/D'}
                  </div>
                  <div className="crimeCardUnit">casos · año {crimeStats.homicidios.year ?? '—'}</div>
                </div>

                <div className={`crimeCard crimeCard--lesiones${!crimeStats.lesiones_comunes.available ? ' crimeCard--unavailable' : ''}`}>
                  <div className="crimeCardLabel">Lesiones comunes</div>
                  <div className="crimeCardValue">
                    {crimeStats.lesiones_comunes.available && crimeStats.lesiones_comunes.value !== null
                      ? crimeStats.lesiones_comunes.value.toLocaleString('es-CO')
                      : '—'}
                  </div>
                  <div className="crimeCardUnit">
                    {crimeStats.lesiones_comunes.available
                      ? `casos · año ${crimeStats.lesiones_comunes.year ?? '—'}`
                      : 'Dataset no disponible en MEData'}
                  </div>
                </div>

                {crimeStats.top_homicidios_by_comuna.length > 0 ? (
                  <div className="crimeChartWrap">
                    <div className="crimeChartLabel">Top comunas por homicidios</div>
                    <ResponsiveContainer width="100%" height={160}>
                      <BarChart
                        data={crimeStats.top_homicidios_by_comuna.slice(0, 8)}
                        margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
                        layout="vertical"
                      >
                        <XAxis type="number" tick={{ fontSize: 10 }} />
                        <YAxis
                          type="category"
                          dataKey="comuna_code"
                          tick={{ fontSize: 10 }}
                          width={28}
                        />
                        <Tooltip />
                        <Bar dataKey="safety_homicides" fill="var(--danger)" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : null}

                {crimeStats.top_lesiones_by_comuna.length > 0 ? (
                  <div className="crimeChartWrap">
                    <div className="crimeChartLabel">Top comunas por lesiones</div>
                    <ResponsiveContainer width="100%" height={160}>
                      <BarChart
                        data={crimeStats.top_lesiones_by_comuna.slice(0, 8)}
                        margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
                        layout="vertical"
                      >
                        <XAxis type="number" tick={{ fontSize: 10 }} />
                        <YAxis
                          type="category"
                          dataKey="comuna_code"
                          tick={{ fontSize: 10 }}
                          width={28}
                        />
                        <Tooltip />
                        <Bar dataKey="lesiones_count" fill="var(--invest)" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : null}
              </div>

              {crimeLoading ? <div className="crimeLoading">Actualizando...</div> : null}
            </section>
          ) : crimeLoading ? (
            <div className="chartPanel">
              <div className="skeleton-line skeleton-w50" style={{ marginBottom: 12 }} />
              <div className="skeleton-rect" style={{ height: 120 }} />
            </div>
          ) : null}

          {/* Recomendaciones */}
          <section className="recs">
            <div className="chartTitle">Análisis y recomendaciones</div>
            <div className="recsBox">
              <div className="recsMeta">
                Territorio: <b>{data.selected.comuna_name ?? data.selected.comuna_code}</b>
                {selectedYear ? <span className="recsYear"> · Año {selectedYear}</span> : null}
              </div>
              <ol className="recsList">
                {data.recommendations.map((r, idx) => (
                  <li key={`${idx}-${r.slice(0, 20)}`} className={severityClass(r)}>
                    {r}
                  </li>
                ))}
              </ol>
            </div>
          </section>

        </main>
      ) : null}
    </div>
  )
}
