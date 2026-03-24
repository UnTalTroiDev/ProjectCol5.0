import { useMemo } from 'react'
import {
  Bar, BarChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { EstablecimientosResponse } from '../types'
import { API_URL, SectionSkeleton, UnavailableCard, useFetch } from '../utils'

type Props = {
  comunaCode: string
  selectedYear: number | null
}

export default function EducationTab({ comunaCode, selectedYear }: Props) {
  const url = useMemo(() => {
    const p = new URLSearchParams()
    if (comunaCode !== 'ALL') p.set('comuna_code', comunaCode)
    return `${API_URL}/api/education/establecimientos?${p}`
  }, [comunaCode])

  const { data: establecimientos, loading: eduLoading, error } = useFetch<EstablecimientosResponse>(url)

  return (
    <div className="tabContent">
      <h2 className="sectionTitle">📚 Educación — Establecimientos</h2>
      <p className="sectionDesc">Fuente: Secretaría de Educación · MEData. Directorio de instituciones educativas por comuna y modalidad.</p>
      {error && !establecimientos ? (
        <div className="errorBox"><div className="errorTitle">No pudimos cargar los datos</div><div className="errorMsg">{error}</div></div>
      ) : eduLoading ? <SectionSkeleton /> : establecimientos?.available ? (
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
      ) : <UnavailableCard label="Establecimientos educativos" />)}
    </div>
  )
}
