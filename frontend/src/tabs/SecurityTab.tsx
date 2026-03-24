import { useMemo } from 'react'
import {
  Bar, BarChart, CartesianGrid, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { CriminalidadResponse, VifResponse } from '../types'
import { API_URL, exportToCSV, SectionSkeleton, UnavailableCard, useFetch } from '../utils'

type Props = {
  comunaCode: string
  selectedYear: number | null
}

export default function SecurityTab({ comunaCode, selectedYear }: Props) {
  const params = useMemo(() => {
    const p = new URLSearchParams()
    if (selectedYear) p.set('year', String(selectedYear))
    return p.toString()
  }, [selectedYear])

  const { data: criminalidad, loading: crimLoading, error } = useFetch<CriminalidadResponse>(`${API_URL}/api/security/criminalidad?${params}`)
  const { data: vif, loading: vifLoading } = useFetch<VifResponse>(`${API_URL}/api/security/violencia-intrafamiliar?${params}`)

  return (
    <div className="tabContent">
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 16 }}>
        <h2 className="sectionTitle" style={{ margin: 0 }}>🔒 Seguridad — Criminalidad consolidada</h2>
        {criminalidad?.available && (
          <button className="exportBtn" onClick={() => exportToCSV(criminalidad.by_type as unknown as Record<string, unknown>[], 'criminalidad_por_tipo.csv')}>
            ⬇ Exportar CSV
          </button>
        )}
      </div>
      <p className="sectionDesc">Fuente: SISC, Secretaría de Seguridad · MEData. Cubre 10+ tipos de delito desde 2003.</p>
      {error && !criminalidad ? (
        <div className="errorBox"><div className="errorTitle">No pudimos cargar los datos</div><div className="errorMsg">{error}</div></div>
      ) : crimLoading ? <SectionSkeleton /> : criminalidad?.available ? (
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
      ) : <UnavailableCard label="Criminalidad consolidada" />)}

      {/* VIF */}
      {vifLoading ? <p className="loadingMsg">Cargando violencia intrafamiliar…</p> : vif?.available ? (
        <div className="sectionBlock">
          <h3 className="sectionTitle">Violencia Intrafamiliar (Medidas de Protección)</h3>
          <div className="domainCards">
            <div className="domainCard">
              <span className="domainCardLabel">Total medidas</span>
              <span className="domainCardValue">{vif.total?.toLocaleString()}</span>
            </div>
            <div className="domainCard">
              <span className="domainCardLabel">Último año</span>
              <span className="domainCardValue">{vif.latest_year ?? '—'}</span>
            </div>
            <div className="domainCard">
              <span className="domainCardLabel">Comunas con datos</span>
              <span className="domainCardValue">{vif.by_comuna.length}</span>
            </div>
          </div>
          <div className="twoCol">
            <div>
              <h4>Tendencia anual</h4>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={vif.series}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="year" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="total" stroke="#f59e0b" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div>
              <h4>Top comunas</h4>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={[...vif.by_comuna].sort((a, b) => b.casos - a.casos).slice(0, 10)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="comuna_code" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="casos" fill="#f59e0b" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      ) : vif && !vif.available ? <UnavailableCard label="Violencia intrafamiliar" /> : null}
    </div>
  )
}
