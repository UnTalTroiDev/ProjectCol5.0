import { useEffect, useState } from 'react'
import type { CitySummary } from '../types'
import { API_URL, SectionSkeleton } from '../utils'

export default function CityTab() {
  const [citySummary, setCitySummary] = useState<CitySummary | null>(null)
  const [cityLoading, setCityLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function loadCitySummary() {
    setCityLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_URL}/api/city/summary`)
      if (res.ok) setCitySummary(await res.json())
      else setError(`Error ${res.status}: no se pudo cargar el resumen.`)
    } catch (e) {
      setError('No se pudo conectar con el servidor.')
      console.error('CityTab fetch error:', e)
    } finally { setCityLoading(false) }
  }

  useEffect(() => {
    loadCitySummary()
  }, [])

  return (
    <div className="tabContent">
      <h2 className="sectionTitle">🗺 Ciudad — Estado de todos los datasets</h2>
      <p className="sectionDesc">Disponibilidad en tiempo real de cada dominio de datos de MEData.</p>
      {cityLoading ? <SectionSkeleton /> : error ? (
        <div className="unavailableCard"><span className="unavailableIcon">!</span><span>{error}</span></div>
      ) : citySummary ? (
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
  )
}
