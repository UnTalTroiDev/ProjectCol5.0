import { useMemo } from 'react'
import {
  Bar, BarChart, CartesianGrid, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ResiduosResponse } from '../types'
import { API_URL, SectionSkeleton, UnavailableCard, useFetch } from '../utils'

type Props = {
  comunaCode: string
  selectedYear: number | null
}

export default function EnvironmentTab({ comunaCode, selectedYear }: Props) {
  const url = useMemo(() => {
    const p = new URLSearchParams()
    if (selectedYear) p.set('year', String(selectedYear))
    return `${API_URL}/api/environment/residuos?${p}`
  }, [selectedYear])

  const { data: residuos, loading: envLoading, error } = useFetch<ResiduosResponse>(url)

  return (
    <div className="tabContent">
      <h2 className="sectionTitle">🌿 Medio Ambiente — Residuos Sólidos</h2>
      <p className="sectionDesc">Fuente: Secretaría de Suministros · MEData. Generación de residuos ordinarios y aprovechables del Centro Administrativo Distrital.</p>
      {error && !residuos ? (
        <div className="errorBox"><div className="errorTitle">No pudimos cargar los datos</div><div className="errorMsg">{error}</div></div>
      ) : envLoading ? <SectionSkeleton /> : residuos?.available ? (
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
      ) : <UnavailableCard label="Residuos sólidos" />)}
    </div>
  )
}
