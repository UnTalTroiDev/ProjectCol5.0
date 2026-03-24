import { useMemo } from 'react'
import {
  Bar, BarChart, CartesianGrid, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { NatalidadResponse } from '../types'
import { API_URL, SectionSkeleton, UnavailableCard, useFetch } from '../utils'

type Props = {
  comunaCode: string
  selectedYear: number | null
}

export default function HealthTab({ comunaCode, selectedYear }: Props) {
  const url = useMemo(() => {
    const p = new URLSearchParams()
    if (selectedYear) p.set('year', String(selectedYear))
    return `${API_URL}/api/health-data/natalidad?${p}`
  }, [selectedYear])

  const { data: natalidad, loading: healthLoading, error } = useFetch<NatalidadResponse>(url)

  return (
    <div className="tabContent">
      <h2 className="sectionTitle">🏥 Salud — Natalidad</h2>
      <p className="sectionDesc">Fuente: Secretaría de Salud de Medellín · MEData. Nacimientos por año, sexo y comuna.</p>
      {error && !natalidad ? (
        <div className="errorBox"><div className="errorTitle">No pudimos cargar los datos</div><div className="errorMsg">{error}</div></div>
      ) : healthLoading ? <SectionSkeleton /> : natalidad?.available ? (
        <div className="grid">
          <div className="domainCards">
            <div className="domainCard">
              <div className="domainCardLabel">Nacimientos (año {natalidad.latest_year})</div>
              <div className="domainCardValue">{natalidad.total_nacimientos.toLocaleString('es-CO')}</div>
            </div>
            {natalidad.by_sex.slice(0, 2).map((s, i) => {
              const vals = Object.values(s)
              return (
                <div key={i} className="domainCard">
                  <div className="domainCardLabel">{String(vals[0])}</div>
                  <div className="domainCardValue">{Number(vals[1]).toLocaleString('es-CO')}</div>
                </div>
              )
            })}
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
      ) : <UnavailableCard label="Natalidad" />)}
    </div>
  )
}
