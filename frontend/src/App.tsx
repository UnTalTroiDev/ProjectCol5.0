import { useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import './App.css'

type ComunaOption = { code: string; name?: string | null }

type MetricBlock = { value: number | null; unit: string }

type OverviewResponse = {
  meta: Record<string, any>
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

export default function App() {
  const [comunas, setComunas] = useState<ComunaOption[]>([])
  const [selected, setSelected] = useState<string>('ALL')
  const [loading, setLoading] = useState<boolean>(true)
  const [data, setData] = useState<OverviewResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const comunaOptions = useMemo(() => {
    const base: ComunaOption[] = [{ code: 'ALL', name: 'Todas las comunas' }]
    return base.concat(comunas)
  }, [comunas])

  async function loadComunas() {
    const res = await fetch(`${API_URL}/api/territory/comunas`)
    if (!res.ok) throw new Error(`Error cargando comunas: ${res.status}`)
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
      if (!res.ok) throw new Error(`Error cargando overview: ${res.status}`)
      const json: OverviewResponse = await res.json()
      setData(json)
    } catch (e: any) {
      setError(e?.message ?? 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    ;(async () => {
      await loadComunas()
    })().catch((e) => {
      setError(e?.message ?? 'Error cargando comunas')
      setLoading(false)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (comunas.length === 0) return
    loadOverview(selected).catch((e) => setError(e?.message ?? 'Error cargando dashboard'))
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

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>MedCity Dashboard</h1>
          <p className="subtitle">
            Dashboard demo con datos abiertos de Medellín (MEData): movilidad, homicidios e inversión territorial.
          </p>
        </div>
        <div className="filter">
          <label>
            Comuna / territorio:
            <select value={selected} onChange={(e) => setSelected(e.target.value)} aria-label="Seleccionar comuna">
              {comunaOptions.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.name ? `${c.name} (${c.code})` : c.code}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      {error ? (
        <div className="errorBox">
          <div className="errorTitle">No se pudo cargar el dashboard</div>
          <div className="errorMsg">{error}</div>
        </div>
      ) : null}

      {loading || !data ? (
        <div className="loading">Cargando...</div>
      ) : (
        <main className="grid">
          <section className="cards">
            <div className="card">
              <div className="cardTitle">Movilidad (equivalentes)</div>
              <div className="cardValue">{metricValueText(data.metrics.mobility_equiv_vehicles)}</div>
              <div className="cardMeta">Año: {data.meta.mobility_latest_year}</div>
            </div>
            <div className="card">
              <div className="cardTitle">Homicidios (casos)</div>
              <div className="cardValue">{metricValueText(data.metrics.safety_homicides)}</div>
              <div className="cardMeta">Año: {data.meta.safety_latest_year}</div>
            </div>
            <div className="card">
              <div className="cardTitle">Inversión pública</div>
              <div className="cardValue">{metricValueText(data.metrics.investment_amount)}</div>
              <div className="cardMeta">Año: {data.meta.investment_latest_year}</div>
            </div>
          </section>

          <section className="charts">
            <div className="chartPanel">
              <div className="chartTitle">Movilidad por comuna (top)</div>
              <div className="chartBody">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={mobilityChart} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill="#2563eb" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="chartPanel">
              <div className="chartTitle">Homicidios por comuna (top)</div>
              <div className="chartBody">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={safetyChart} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill="#dc2626" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>

          <section className="recs">
            <div className="chartTitle">Recomendaciones accionables</div>
            <div className="recsBox">
              <div className="recsMeta">
                Territorio seleccionado: <b>{data.selected.comuna_name ?? data.selected.comuna_code}</b>
              </div>
              <ol className="recsList">
                {data.recommendations.map((r, idx) => (
                  <li key={`${idx}-${r.slice(0, 20)}`}>{r}</li>
                ))}
              </ol>
            </div>
          </section>
        </main>
      )}
    </div>
  )
}

