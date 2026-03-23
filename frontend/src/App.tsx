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
  metric: string; comuna_code: string; unit: string
  series: TrendPoint[]; available_years: number[]
}
type TrendsMetric = 'safety' | 'mobility' | 'investment'

type CriminalidadResponse = {
  available: boolean; available_years: number[]
  by_type: Array<{ crime_type: string; total: number }>
  series: Array<{ year?: number; month?: number; total: number }>
}

type NatalidadResponse = {
  available: boolean; latest_year: number; total_nacimientos: number
  by_comuna: Array<{ comuna_code: string; nacimientos: number }>
  by_sex: Array<{ [k: string]: unknown }>
  series: Array<{ year: number; nacimientos: number }>
}

type EstablecimientosResponse = {
  available: boolean; total: number
  by_comuna: Array<{ comuna_code: string; establecimientos: number }>
  by_modalidad: Array<{ modalidad: string; total: number }>
}

type ResiduosResponse = {
  available: boolean; latest_year: number; total_kg: number; unit: string
  by_type: Array<{ tipo_residuo: string; cantidad_kg: number }>
  series: Array<{ year?: number; month?: number; cantidad_kg: number }>
}

type ImcvResponse = {
  available: boolean; latest_year: number
  by_comuna: Array<{ comuna_code: string; imcv_promedio: number }>
  by_dimension: Array<{ dimension: string; promedio: number }>
  series: Array<{ year: number; imcv_promedio: number | null }>
}

type SiniestrosResponse = {
  available: boolean; latest_year: number; total_victimas: number
  by_type: Array<{ tipo_victima: string; total: number }>
  by_severity: Array<{ gravedad: string; total: number }>
  series: Array<{ year: number; victimas: number }>
}

type CitySummary = {
  available_domains: number; total_domains: number; message: string
  domains: Record<string, { available: boolean; label: string; latest_year?: number; [k: string]: unknown }>
}

type Tab = 'overview' | 'security' | 'health' | 'education' | 'environment' | 'quality' | 'city'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCOP(v: number) {
  return v.toLocaleString('es-CO', { maximumFractionDigits: 0 })
}

function metricValueText(m?: MetricBlock) {
  if (!m || m.value === null || !Number.isFinite(m.value)) return 'N/D'
  if (m.unit === 'COP') return formatCOP(m.value)
  return m.value.toLocaleString('es-CO', { maximumFractionDigits: 2 })
}

function severityClass(text: string) {
  const l = text.toLowerCase()
  if (l.includes('[critico]') || l.includes('alerta:')) return 'sev-critico'
  if (l.includes('[alto]')) return 'sev-alto'
  if (l.includes('[medio]')) return 'sev-medio'
  if (l.includes('[bajo]')) return 'sev-bajo'
  return ''
}

function UnavailableCard({ label }: { label: string }) {
  return (
    <div className="unavailableCard">
      <span className="unavailableIcon">⚠</span>
      <span>{label} — dataset no disponible en MEData en este momento.</span>
    </div>
  )
}

function SectionSkeleton() {
  return (
    <div className="chartPanel">
      <div className="skeleton-line skeleton-w50" style={{ marginBottom: 12 }} />
      <div className="skeleton-rect" style={{ height: 180 }} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab nav
// ---------------------------------------------------------------------------

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'overview',    label: 'Visión general',  icon: '🏙' },
  { id: 'security',    label: 'Seguridad',        icon: '🔒' },
  { id: 'health',      label: 'Salud',            icon: '🏥' },
  { id: 'education',   label: 'Educación',        icon: '📚' },
  { id: 'environment', label: 'Ambiente',         icon: '🌿' },
  { id: 'quality',     label: 'Calidad de vida',  icon: '📊' },
  { id: 'city',        label: 'Ciudad',           icon: '🗺' },
]

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('overview')

  // ── Shared filters ────────────────────────────────────────────────────────
  const [comunas, setComunas] = useState<ComunaOption[]>([])
  const [selected, setSelected] = useState<string>('ALL')
  const [selectedYear, setSelectedYear] = useState<number | null>(null)
  const [availableYears, setAvailableYears] = useState<number[]>([])

  // ── Overview ──────────────────────────────────────────────────────────────
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<OverviewResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [trendsMetric, setTrendsMetric] = useState<TrendsMetric>('safety')
  const [trendsData, setTrendsData] = useState<TrendsResponse | null>(null)
  const [trendsLoading, setTrendsLoading] = useState(false)

  // ── Security ──────────────────────────────────────────────────────────────
  const [criminalidad, setCriminalidad] = useState<CriminalidadResponse | null>(null)
  const [crimLoading, setCrimLoading] = useState(false)

  // ── Health ────────────────────────────────────────────────────────────────
  const [natalidad, setNatalidad] = useState<NatalidadResponse | null>(null)
  const [healthLoading, setHealthLoading] = useState(false)

  // ── Education ─────────────────────────────────────────────────────────────
  const [establecimientos, setEstablecimientos] = useState<EstablecimientosResponse | null>(null)
  const [eduLoading, setEduLoading] = useState(false)

  // ── Environment ───────────────────────────────────────────────────────────
  const [residuos, setResiduos] = useState<ResiduosResponse | null>(null)
  const [envLoading, setEnvLoading] = useState(false)

  // ── Quality ───────────────────────────────────────────────────────────────
  const [imcv, setImcv] = useState<ImcvResponse | null>(null)
  const [siniestros, setSiniestros] = useState<SiniestrosResponse | null>(null)
  const [qualityLoading, setQualityLoading] = useState(false)

  // ── City ──────────────────────────────────────────────────────────────────
  const [citySummary, setCitySummary] = useState<CitySummary | null>(null)
  const [cityLoading, setCityLoading] = useState(false)

  const comunaOptions = useMemo(() => {
    return [{ code: 'ALL', name: 'Toda la ciudad' } as ComunaOption].concat(comunas)
  }, [comunas])

  // ── Fetchers ──────────────────────────────────────────────────────────────

  async function loadComunas() {
    const res = await fetch(`${API_URL}/api/territory/comunas`)
    if (!res.ok) throw new Error('No pudimos obtener la lista de territorios.')
    const json = await res.json()
    setComunas(json.comunas ?? [])
    if (json.comunas?.length) setSelected(s => s === 'ALL' ? json.comunas[0].code : s)
  }

  async function loadOverview(code: string, year: number | null) {
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
  }

  async function loadTrends(metric: TrendsMetric, code: string) {
    setTrendsLoading(true)
    try {
      const p = new URLSearchParams({ metric })
      if (code !== 'ALL') p.set('comuna_code', code)
      const res = await fetch(`${API_URL}/api/dashboard/trends?${p}`)
      if (!res.ok) return
      const json: TrendsResponse = await res.json()
      setTrendsData(json)
      if (metric === 'safety' && json.available_years.length > 0) setAvailableYears(json.available_years)
    } catch { } finally { setTrendsLoading(false) }
  }

  async function loadSecurity() {
    setCrimLoading(true)
    try {
      const p = new URLSearchParams()
      if (selectedYear) p.set('year', String(selectedYear))
      const res = await fetch(`${API_URL}/api/security/criminalidad?${p}`)
      if (res.ok) setCriminalidad(await res.json())
    } catch { } finally { setCrimLoading(false) }
  }

  async function loadHealth() {
    setHealthLoading(true)
    try {
      const p = new URLSearchParams()
      if (selectedYear) p.set('year', String(selectedYear))
      const res = await fetch(`${API_URL}/api/health-data/natalidad?${p}`)
      if (res.ok) setNatalidad(await res.json())
    } catch { } finally { setHealthLoading(false) }
  }

  async function loadEducation() {
    setEduLoading(true)
    try {
      const p = new URLSearchParams()
      if (selected !== 'ALL') p.set('comuna_code', selected)
      const res = await fetch(`${API_URL}/api/education/establecimientos?${p}`)
      if (res.ok) setEstablecimientos(await res.json())
    } catch { } finally { setEduLoading(false) }
  }

  async function loadEnvironment() {
    setEnvLoading(true)
    try {
      const p = new URLSearchParams()
      if (selectedYear) p.set('year', String(selectedYear))
      const res = await fetch(`${API_URL}/api/environment/residuos?${p}`)
      if (res.ok) setResiduos(await res.json())
    } catch { } finally { setEnvLoading(false) }
  }

  async function loadQuality() {
    setQualityLoading(true)
    try {
      const p = new URLSearchParams()
      if (selectedYear) p.set('year', String(selectedYear))
      if (selected !== 'ALL') p.set('comuna_code', selected)
      const [imcvRes, sinRes] = await Promise.all([
        fetch(`${API_URL}/api/quality/imcv?${p}`),
        fetch(`${API_URL}/api/quality/siniestros-viales?${p}`),
      ])
      if (imcvRes.ok) setImcv(await imcvRes.json())
      if (sinRes.ok) setSiniestros(await sinRes.json())
    } catch { } finally { setQualityLoading(false) }
  }

  async function loadCitySummary() {
    setCityLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/city/summary`)
      if (res.ok) setCitySummary(await res.json())
    } catch { } finally { setCityLoading(false) }
  }

  // ── Effects ───────────────────────────────────────────────────────────────

  useEffect(() => {
    loadComunas().catch(e => {
      setError(e instanceof Error ? e.message : 'Sin conexion con el servidor.')
      setLoading(false)
    })
    loadCitySummary()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!comunas.length) return
    loadOverview(selected, selectedYear)
    loadTrends(trendsMetric, selected)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, selectedYear, comunas.length])

  useEffect(() => {
    if (!comunas.length) return
    loadTrends(trendsMetric, selected)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trendsMetric])

  // Lazy load por tab
  useEffect(() => {
    if (activeTab === 'security' && !criminalidad) loadSecurity()
    if (activeTab === 'health' && !natalidad) loadHealth()
    if (activeTab === 'education' && !establecimientos) loadEducation()
    if (activeTab === 'environment' && !residuos) loadEnvironment()
    if (activeTab === 'quality' && !imcv) loadQuality()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab])

  // Reload on filter change
  useEffect(() => {
    if (activeTab === 'security') loadSecurity()
    if (activeTab === 'health') loadHealth()
    if (activeTab === 'education') loadEducation()
    if (activeTab === 'environment') loadEnvironment()
    if (activeTab === 'quality') loadQuality()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedYear, selected])

  // ── Derived ───────────────────────────────────────────────────────────────

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

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="page">
      {/* Header */}
      <header className="header">
        <div>
          <h1>MedCity Dashboard</h1>
          <p className="subtitle">Datos abiertos de Medellín — MEData</p>
        </div>
        <div className="filters">
          <label>
            Territorio
            <select value={selected} onChange={e => setSelected(e.target.value)} aria-label="Territorio">
              {comunaOptions.map(c => (
                <option key={c.code} value={c.code}>
                  {c.code === 'ALL' ? c.name : c.name ? `${c.name} (${c.code})` : c.code}
                </option>
              ))}
            </select>
          </label>
          <label>
            Año
            <select value={selectedYear ?? ''} onChange={e => setSelectedYear(e.target.value ? Number(e.target.value) : null)} aria-label="Año">
              <option value="">Último disponible</option>
              {availableYears.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </label>
        </div>
      </header>

      {/* Tab nav */}
      <nav className="tabNav">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`tabBtn${activeTab === t.id ? ' tabBtn--active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            <span className="tabIcon">{t.icon}</span>
            <span className="tabLabel">{t.label}</span>
          </button>
        ))}
      </nav>

      {/* Error global */}
      {error && !data ? (
        <div className="errorBox">
          <div className="errorTitle">No pudimos cargar los datos</div>
          <div className="errorMsg">{error}</div>
        </div>
      ) : null}

      {/* ── TAB: Visión general ── */}
      {activeTab === 'overview' && (
        !data && loading ? (
          <div className="grid"><section className="cards">{[0,1,2].map(i => <div key={i} className="card skeleton-card"><div className="skeleton-line skeleton-w60" /><div className="skeleton-line skeleton-value" /><div className="skeleton-line skeleton-w40" /></div>)}</section></div>
        ) : data ? (
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
                  {selected !== 'ALL' && data.city_averages[key] ? (
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
              <MedellinMap data={mapData} selected={selected} onSelect={setSelected} />
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
                              const sel = selected !== 'ALL' && e.code === selected
                              const all = selected === 'ALL'
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
        ) : null
      )}

      {/* ── TAB: Seguridad ── */}
      {activeTab === 'security' && (
        <div className="tabContent">
          <h2 className="sectionTitle">🔒 Seguridad — Criminalidad consolidada</h2>
          <p className="sectionDesc">Fuente: SISC, Secretaría de Seguridad · MEData. Cubre 10+ tipos de delito desde 2003.</p>
          {crimLoading ? <SectionSkeleton /> : criminalidad?.available ? (
            <div className="grid">
              <div className="domainCards">
                <div className="domainCard">
                  <div className="domainCardLabel">Años disponibles</div>
                  <div className="domainCardValue">{criminalidad.available_years.length}</div>
                  <div className="domainCardSub">{criminalidad.available_years[0]} – {criminalidad.available_years[criminalidad.available_years.length - 1]}</div>
                </div>
                <div className="domainCard">
                  <div className="domainCardLabel">Tipos de delito</div>
                  <div className="domainCardValue">{criminalidad.by_type.length}</div>
                </div>
                <div className="domainCard">
                  <div className="domainCardLabel">Total registros</div>
                  <div className="domainCardValue">{criminalidad.series.reduce((s, p) => s + p.total, 0).toLocaleString('es-CO')}</div>
                </div>
              </div>

              <div className="twoCol">
                <div className="chartPanel">
                  <div className="chartTitle">Por tipo de delito</div>
                  <div style={{ height: 280 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={criminalidad.by_type.slice(0, 10)} layout="vertical" margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                        <XAxis type="number" tick={{ fontSize: 10 }} />
                        <YAxis type="category" dataKey="crime_type" tick={{ fontSize: 10 }} width={130} />
                        <Tooltip />
                        <Bar dataKey="total" fill="var(--danger)" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="chartPanel">
                  <div className="chartTitle">Tendencia anual (todos los delitos)</div>
                  <div style={{ height: 280 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={criminalidad.series.filter(p => 'year' in p)} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Line type="monotone" dataKey="total" stroke="var(--danger)" strokeWidth={2} dot={{ r: 3 }} connectNulls />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          ) : <UnavailableCard label="Criminalidad consolidada" />}
        </div>
      )}

      {/* ── TAB: Salud ── */}
      {activeTab === 'health' && (
        <div className="tabContent">
          <h2 className="sectionTitle">🏥 Salud — Natalidad</h2>
          <p className="sectionDesc">Fuente: Secretaría de Salud de Medellín · MEData. Nacimientos por año, sexo y comuna.</p>
          {healthLoading ? <SectionSkeleton /> : natalidad?.available ? (
            <div className="grid">
              <div className="domainCards">
                <div className="domainCard">
                  <div className="domainCardLabel">Nacimientos (año {natalidad.latest_year})</div>
                  <div className="domainCardValue">{natalidad.total_nacimientos.toLocaleString('es-CO')}</div>
                </div>
                {natalidad.by_sex.slice(0, 2).map((s: any, i) => (
                  <div key={i} className="domainCard">
                    <div className="domainCardLabel">{String(Object.values(s)[0])}</div>
                    <div className="domainCardValue">{Number(Object.values(s)[1]).toLocaleString('es-CO')}</div>
                  </div>
                ))}
              </div>
              <div className="twoCol">
                <div className="chartPanel">
                  <div className="chartTitle">Nacimientos por año</div>
                  <div style={{ height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={natalidad.series} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Line type="monotone" dataKey="nacimientos" stroke="var(--primary)" strokeWidth={2.5} dot={{ r: 4 }} connectNulls />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="chartPanel">
                  <div className="chartTitle">Top comunas por nacimientos</div>
                  <div style={{ height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={natalidad.by_comuna.slice(0, 10)} layout="vertical" margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                        <XAxis type="number" tick={{ fontSize: 10 }} />
                        <YAxis type="category" dataKey="comuna_code" tick={{ fontSize: 10 }} width={32} />
                        <Tooltip />
                        <Bar dataKey="nacimientos" fill="var(--primary)" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          ) : <UnavailableCard label="Natalidad" />}
        </div>
      )}

      {/* ── TAB: Educación ── */}
      {activeTab === 'education' && (
        <div className="tabContent">
          <h2 className="sectionTitle">📚 Educación — Establecimientos</h2>
          <p className="sectionDesc">Fuente: Secretaría de Educación · MEData. Directorio de instituciones educativas por comuna y modalidad.</p>
          {eduLoading ? <SectionSkeleton /> : establecimientos?.available ? (
            <div className="grid">
              <div className="domainCards">
                <div className="domainCard">
                  <div className="domainCardLabel">Total establecimientos</div>
                  <div className="domainCardValue">{establecimientos.total.toLocaleString('es-CO')}</div>
                </div>
                <div className="domainCard">
                  <div className="domainCardLabel">Comunas con datos</div>
                  <div className="domainCardValue">{establecimientos.by_comuna.length}</div>
                </div>
              </div>
              <div className="twoCol">
                <div className="chartPanel">
                  <div className="chartTitle">Por comuna</div>
                  <div style={{ height: 280 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={establecimientos.by_comuna.slice(0, 12)} layout="vertical" margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                        <XAxis type="number" tick={{ fontSize: 10 }} />
                        <YAxis type="category" dataKey="comuna_code" tick={{ fontSize: 10 }} width={32} />
                        <Tooltip />
                        <Bar dataKey="establecimientos" fill="var(--invest)" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="chartPanel">
                  <div className="chartTitle">Por modalidad</div>
                  <div style={{ height: 280 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={establecimientos.by_modalidad} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                        <XAxis dataKey="modalidad" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 10 }} />
                        <Tooltip />
                        <Bar dataKey="total" fill="var(--invest)" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          ) : <UnavailableCard label="Establecimientos educativos" />}
        </div>
      )}

      {/* ── TAB: Ambiente ── */}
      {activeTab === 'environment' && (
        <div className="tabContent">
          <h2 className="sectionTitle">🌿 Medio Ambiente — Residuos Sólidos</h2>
          <p className="sectionDesc">Fuente: Secretaría de Suministros · MEData. Generación de residuos ordinarios y aprovechables del Centro Administrativo Distrital.</p>
          {envLoading ? <SectionSkeleton /> : residuos?.available ? (
            <div className="grid">
              <div className="domainCards">
                <div className="domainCard">
                  <div className="domainCardLabel">Total residuos (año {residuos.latest_year})</div>
                  <div className="domainCardValue">{residuos.total_kg.toLocaleString('es-CO', { maximumFractionDigits: 0 })}</div>
                  <div className="domainCardSub">kg</div>
                </div>
                {residuos.by_type.slice(0, 2).map((t, i) => (
                  <div key={i} className="domainCard">
                    <div className="domainCardLabel">{t.tipo_residuo}</div>
                    <div className="domainCardValue">{t.cantidad_kg.toLocaleString('es-CO', { maximumFractionDigits: 0 })}</div>
                    <div className="domainCardSub">kg</div>
                  </div>
                ))}
              </div>
              <div className="twoCol">
                <div className="chartPanel">
                  <div className="chartTitle">Tendencia anual de residuos</div>
                  <div style={{ height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={residuos.series.filter(p => 'year' in p)} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip formatter={(v: number) => [`${v.toLocaleString('es-CO')} kg`, 'Residuos']} />
                        <Line type="monotone" dataKey="cantidad_kg" stroke="var(--primary)" strokeWidth={2.5} dot={{ r: 4 }} connectNulls />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="chartPanel">
                  <div className="chartTitle">Por tipo de residuo</div>
                  <div style={{ height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={residuos.by_type} margin={{ top: 8, right: 8, left: 0, bottom: 40 }}>
                        <XAxis dataKey="tipo_residuo" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" />
                        <YAxis tick={{ fontSize: 10 }} />
                        <Tooltip formatter={(v: number) => [`${v.toLocaleString('es-CO')} kg`]} />
                        <Bar dataKey="cantidad_kg" fill="var(--primary)" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          ) : <UnavailableCard label="Residuos sólidos" />}
        </div>
      )}

      {/* ── TAB: Calidad de vida ── */}
      {activeTab === 'quality' && (
        <div className="tabContent">
          <h2 className="sectionTitle">📊 Calidad de Vida — IMCV & Siniestros Viales</h2>
          <p className="sectionDesc">Índice Multidimensional de Calidad de Vida por comuna (DAP) + Víctimas en incidentes viales (Movilidad) · MEData.</p>
          {qualityLoading ? <SectionSkeleton /> : (
            <div className="grid">
              {imcv?.available ? (
                <div className="twoCol">
                  <div className="chartPanel">
                    <div className="chartTitle">IMCV por comuna (año {imcv.latest_year})</div>
                    <div style={{ height: 280 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={imcv.by_comuna.slice(0, 16)} layout="vertical" margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                          <XAxis type="number" tick={{ fontSize: 10 }} />
                          <YAxis type="category" dataKey="comuna_code" tick={{ fontSize: 10 }} width={32} />
                          <Tooltip />
                          <Bar dataKey="imcv_promedio" fill="var(--invest)" radius={[0, 4, 4, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                  <div className="chartPanel">
                    <div className="chartTitle">IMCV por dimensión</div>
                    <div style={{ height: 280 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={imcv.by_dimension} layout="vertical" margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                          <XAxis type="number" tick={{ fontSize: 10 }} />
                          <YAxis type="category" dataKey="dimension" tick={{ fontSize: 10 }} width={120} />
                          <Tooltip />
                          <Bar dataKey="promedio" fill="var(--invest)" radius={[0, 4, 4, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              ) : <UnavailableCard label="IMCV" />}

              {siniestros?.available ? (
                <div className="twoCol">
                  <div className="chartPanel">
                    <div className="chartTitle">Víctimas viales por año</div>
                    <div style={{ height: 220 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={siniestros.series} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                          <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                          <YAxis tick={{ fontSize: 11 }} />
                          <Tooltip />
                          <Line type="monotone" dataKey="victimas" stroke="var(--danger)" strokeWidth={2.5} dot={{ r: 4 }} connectNulls />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                  <div className="chartPanel">
                    <div className="chartTitle">Por tipo de víctima</div>
                    <div style={{ height: 220 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={siniestros.by_type} margin={{ top: 8, right: 8, left: 0, bottom: 40 }}>
                          <XAxis dataKey="tipo_victima" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" />
                          <YAxis tick={{ fontSize: 10 }} />
                          <Tooltip />
                          <Bar dataKey="total" fill="var(--danger)" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              ) : <UnavailableCard label="Siniestros viales" />}
            </div>
          )}
        </div>
      )}

      {/* ── TAB: Ciudad ── */}
      {activeTab === 'city' && (
        <div className="tabContent">
          <h2 className="sectionTitle">🗺 Ciudad — Estado de todos los datasets</h2>
          <p className="sectionDesc">Disponibilidad en tiempo real de cada dominio de datos de MEData.</p>
          {cityLoading ? <SectionSkeleton /> : citySummary ? (
            <div className="grid">
              <div className="cityBanner">
                <span className="cityBannerNum">{citySummary.available_domains}</span>
                <span className="cityBannerSlash">/</span>
                <span className="cityBannerTotal">{citySummary.total_domains}</span>
                <span className="cityBannerLabel">dominios disponibles</span>
              </div>
              <div className="domainGrid">
                {Object.entries(citySummary.domains).map(([key, d]) => (
                  <div key={key} className={`domainStatusCard${d.available ? ' domainStatusCard--ok' : ' domainStatusCard--off'}`}>
                    <div className="domainStatusDot" />
                    <div>
                      <div className="domainStatusLabel">{d.label}</div>
                      <div className="domainStatusMeta">
                        {d.available
                          ? `Disponible${d.latest_year ? ` · Año ${d.latest_year}` : ''}`
                          : 'No disponible en MEData'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}
