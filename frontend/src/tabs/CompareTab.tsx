import { useCallback, useEffect, useState } from 'react'
import {
  Bar, BarChart, CartesianGrid,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ComunaOption, CompareResponse } from '../types'
import { API_URL, exportToCSV, SectionSkeleton } from '../utils'

type Props = {
  comunaCode: string
  comunas: ComunaOption[]
  selectedYear: number | null
}

export default function CompareTab({ comunaCode, comunas, selectedYear }: Props) {
  const [compareData, setCompareData] = useState<CompareResponse | null>(null)
  const [compareLoading, setCompareLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [compareSelected, setCompareSelected] = useState<string[]>([])

  const loadCompare = useCallback(async (codes: string[]) => {
    if (!codes.length) return
    setCompareLoading(true)
    setError(null)
    try {
      const p = new URLSearchParams({ comunas: codes.join(',') })
      if (selectedYear) p.set('year', String(selectedYear))
      const res = await fetch(`${API_URL}/api/dashboard/compare?${p}`)
      if (res.ok) setCompareData(await res.json())
    } catch (e) { setError("No se pudo conectar con el servidor."); console.error("Fetch error:", e) } finally { setCompareLoading(false) }
  }, [selectedYear])

  useEffect(() => {
    if (compareSelected.length > 0) loadCompare(compareSelected)
  }, [selectedYear, compareSelected, loadCompare])

  return (
    <div className="tabContent">
      <h2 className="sectionTitle">⚖️ Comparador de comunas</h2>
      <p className="sectionDesc">Selecciona varias comunas para comparar sus indicadores principales.</p>

      <div className="compareSelector">
        {comunas.map(c => (
          <label key={c.code} className={`comparePill${compareSelected.includes(c.code) ? ' comparePill--active' : ''}`}>
            <input
              type="checkbox"
              style={{ display: 'none' }}
              checked={compareSelected.includes(c.code)}
              onChange={e => {
                const next = e.target.checked
                  ? [...compareSelected, c.code]
                  : compareSelected.filter(x => x !== c.code)
                setCompareSelected(next)
                if (next.length) loadCompare(next)
                else setCompareData(null)
              }}
            />
            {c.code}{c.name ? ` · ${c.name}` : ''}
          </label>
        ))}
      </div>

      {error && !compareData ? (
        <div className="errorBox"><div className="errorTitle">No pudimos cargar los datos</div><div className="errorMsg">{error}</div></div>
      ) : compareLoading ? <SectionSkeleton /> : compareData && compareData.comunas.length > 0 ? (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
            <p className="sectionDesc" style={{ margin: 0 }}>Año: {compareData.year}</p>
            <button
              className="exportBtn"
              onClick={() => exportToCSV(compareData.comunas as unknown as Record<string, unknown>[], `comparacion_comunas_${compareData.year}.csv`)}
            >
              ⬇ Exportar CSV
            </button>
          </div>
          <div className="twoCol">
            <div>
              <h4>Homicidios por comuna</h4>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={compareData.comunas}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="comuna_code" />
                  <YAxis />
                  <Tooltip formatter={(v: number) => v?.toLocaleString()} />
                  <Bar dataKey="safety_homicides" name="Homicidios" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div>
              <h4>Inversión pública (COP)</h4>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={compareData.comunas}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="comuna_code" />
                  <YAxis />
                  <Tooltip formatter={(v: number) => v?.toLocaleString()} />
                  <Bar dataKey="investment_amount" name="Inversión" fill="#22c55e" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div>
            <h4>Movilidad — vehículos equivalentes</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={compareData.comunas}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="comuna_code" />
                <YAxis />
                <Tooltip formatter={(v: number) => v?.toLocaleString()} />
                <Bar dataKey="mobility_equiv_vehicles" name="Movilidad" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : !compareLoading && compareSelected.length === 0 ? (
        <p className="sectionDesc" style={{ marginTop: 16 }}>Selecciona al menos una comuna arriba para ver la comparación.</p>
      ) : null)}
    </div>
  )
}
