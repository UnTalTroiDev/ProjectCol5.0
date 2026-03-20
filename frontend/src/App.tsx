import { useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import './App.css'

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

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function formatCOP(value: number) {
  if (!Number.isFinite(value)) return 'N/D'
  return value.toLocaleString('es-CO', { maximumFractionDigits: 0 })
}

function metricValueText(m?: MetricBlock) {
  if (!m || m.value === null || !Number.isFinite(m.value)) return 'N/D'
  if (m.unit === 'COP') return `${formatCOP(m.value)}`
  return `${m.value.toLocaleString('es-CO', { maximumFractionDigits: 2 })}`
}

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

export default function App() {
  const [comunas, setComunas] = useState<ComunaOption[]>([])
  const [selected, setSelected] = useState<string>('ALL')
  const [loading, setLoading] = useState<boolean>(true)
  const [data, setData] = useState<OverviewResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const comunaOptions = useMemo(() => {
    const base: ComunaOption[] = [{ code: 'ALL', name: 'Toda la ciudad' }]
    return base.concat(comunas)
  }, [comunas])

  async function loadComunas() {
    const res = await fetch(`${API_URL}/api/territory/comunas`)
    if (!res.ok) throw new Error('No pudimos obtener la lista de territorios. Recarga la pagina para intentarlo de nuevo.')
    const json = await res.json()
    setComunas(json.comunas ?? [])
    if (json.comunas?.length) {
      setSelected((prev) => (prev === 'ALL' ? json.comunas[0].code : prev))
    }
  }

  async function loadOverview(comunaCode: string) {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `${API_URL}/api/dashboard/overview?comuna_code=${encodeURIComponent(comunaCode)}`
      )
      if (!res.ok) throw new Error('No pudimos cargar los datos del dashboard. Revisa tu conexion e intenta de nuevo.')
      const json: OverviewResponse = await res.json()
      setData(json)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Ocurrio un problema inesperado. Recarga la pagina para intentarlo de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    ;(async () => {
      await loadComunas()
    })().catch((e: unknown) => {
      setError(e instanceof Error ? e.message : 'No pudimos conectar con el servidor. Revisa tu conexion e intenta de nuevo.')
      setLoading(false)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (comunas.length === 0) return
    loadOverview(selected).catch((e: unknown) =>
      setError(e instanceof Error ? e.message : 'No pudimos cargar el dashboard. Revisa tu conexion e intenta de nuevo.')
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, comunas.length])

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

  const showSkeleton = !data && loading
  const showError = !!error && !data

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>MedCity Dashboard</h1>
          <p className="subtitle">
            Movilidad, seguridad e inversión pública de Medellín
          </p>
        </div>
        <div className="filter">
          <label>
            Territorio
            <select value={selected} onChange={(e) => setSelected(e.target.value)} aria-label="Seleccionar territorio">
              {comunaOptions.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.code === 'ALL' ? c.name : c.name ? `${c.name} (${c.code})` : c.code}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      {showError ? (
        <div className="errorBox">
          <div className="errorTitle">No pudimos cargar los datos</div>
          <div className="errorMsg">{error}</div>
        </div>
      ) : null}

      {showSkeleton ? (
        <SkeletonGrid />
      ) : data ? (
        <main className={`grid${loading ? ' grid--loading' : ''}`}>
          <section className="cards">
            <div className="card">
              <div className="cardTitle">Flujo vehicular</div>
              <div className="cardValue">{metricValueText(data.metrics.mobility_equiv_vehicles)}</div>
              <div className="cardUnit">vehiculos equivalentes</div>
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

          <section className="charts">
            <div className="chartPanel">
              <div className="chartTitle">Top 10 comunas por flujo vehicular</div>
              <div className="chartBody">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={mobilityChart} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis />
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
              <div className="chartTitle">Top 10 comunas por homicidios</div>
              <div className="chartBody">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={safetyChart} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis />
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

          <section className="recs">
            <div className="chartTitle">Analisis y recomendaciones</div>
            <div className="recsBox">
              <div className="recsMeta">
                Territorio: <b>{data.selected.comuna_name ?? data.selected.comuna_code}</b>
              </div>
              <ol className="recsList">
                {data.recommendations.map((r, idx) => (
                  <li key={`${idx}-${r.slice(0, 20)}`}>{r}</li>
                ))}
              </ol>
            </div>
          </section>
        </main>
      ) : null}
    </div>
  )
}
