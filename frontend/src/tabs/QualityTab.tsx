import { useMemo } from 'react'
import {
  Bar, BarChart, CartesianGrid, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ImcvResponse, SiniestrosResponse } from '../types'
import { API_URL, SectionSkeleton, UnavailableCard, useFetch } from '../utils'

type Props = {
  comunaCode: string
  selectedYear: number | null
}

export default function QualityTab({ comunaCode, selectedYear }: Props) {
  const params = useMemo(() => {
    const p = new URLSearchParams()
    if (selectedYear) p.set('year', String(selectedYear))
    if (comunaCode !== 'ALL') p.set('comuna_code', comunaCode)
    return p.toString()
  }, [selectedYear, comunaCode])

  const { data: imcv, loading: imcvLoading, error } = useFetch<ImcvResponse>(`${API_URL}/api/quality/imcv?${params}`)
  const { data: siniestros, loading: sinLoading } = useFetch<SiniestrosResponse>(`${API_URL}/api/quality/siniestros-viales?${params}`)
  const qualityLoading = imcvLoading || sinLoading

  return (
    <div className="tabContent">
      <h2 className="sectionTitle">📊 Calidad de Vida — IMCV & Siniestros Viales</h2>
      <p className="sectionDesc">Índice Multidimensional de Calidad de Vida por comuna (DAP) + Víctimas en incidentes viales (Movilidad) · MEData.</p>
      {error && !imcv && !siniestros ? (
        <div className="errorBox"><div className="errorTitle">No pudimos cargar los datos</div><div className="errorMsg">{error}</div></div>
      ) : qualityLoading ? <SectionSkeleton /> : (
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
      ))}
    </div>
  )
}
