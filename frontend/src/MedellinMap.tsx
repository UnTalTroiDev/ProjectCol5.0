import 'leaflet/dist/leaflet.css'
import { useRef, useState, useEffect, useCallback } from 'react'
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'
import type L from 'leaflet'
import type { Layer, Path, PathOptions } from 'leaflet'
import type { Feature, FeatureCollection } from 'geojson'

type FeatureLayer = Path & { feature?: Feature }

// ── Color interpolation ──────────────────────────────────────────────────────
type RGB = [number, number, number]
export type MetricType = 'mobility' | 'safety'

const PALETTE: Record<MetricType, { low: RGB; high: RGB }> = {
  mobility: { low: [10, 30, 50],  high: [0, 196, 150] },
  safety:   { low: [15, 15, 30],  high: [220, 50, 50] },
}

function lerp(a: number, b: number, t: number) { return a + (b - a) * t }

function rgbLerp(low: RGB, high: RGB, t: number): string {
  return `rgb(${Math.round(lerp(low[0], high[0], t))},${Math.round(lerp(low[1], high[1], t))},${Math.round(lerp(low[2], high[2], t))})`
}

// ── Types ────────────────────────────────────────────────────────────────────
export type MapData = {
  mobility: Record<string, number>
  safety:   Record<string, number>
}

type Props = {
  data:     MapData
  selected: string              // commune code or 'ALL'
  onSelect: (code: string) => void
}

// ── Component ────────────────────────────────────────────────────────────────
export default function MedellinMap({ data, selected, onSelect }: Props) {
  const [metric, setMetric] = useState<MetricType>('mobility')
  const [hovered, setHovered] = useState<{ name: string; value: number | undefined } | null>(null)
  const [geoData, setGeoData] = useState<FeatureCollection | null>(null)
  const geoRef = useRef<L.GeoJSON | null>(null)

  // Load real GeoJSON boundaries from public/comunas.geojson
  useEffect(() => {
    fetch('/comunas.geojson')
      .then(r => r.json())
      .then((fc: FeatureCollection) => setGeoData(fc))
      .catch(() => {
        // Fallback: empty feature collection
        console.warn('Failed to load comunas.geojson')
      })
  }, [])

  const values = metric === 'mobility' ? data.mobility : data.safety

  const nums   = Object.values(values).filter(Number.isFinite)
  const minVal = nums.length ? Math.min(...nums) : 0
  const maxVal = nums.length ? Math.max(...nums) : 1

  const getColor = useCallback((code: string): string => {
    const val = values[code]
    if (val === undefined || !Number.isFinite(val)) return '#1e2030'
    const t = maxVal === minVal ? 0.5 : (val - minVal) / (maxVal - minVal)
    return rgbLerp(PALETTE[metric].low, PALETTE[metric].high, t)
  }, [values, minVal, maxVal, metric])

  // Re-style existing layers instead of remounting the entire GeoJSON
  useEffect(() => {
    const layer = geoRef.current
    if (!layer) return
    layer.eachLayer((l) => {
      const leafletLayer = l as FeatureLayer
      const code = leafletLayer.feature?.properties?.code as string | undefined
      if (!code) return
      const isSel = selected === code
      leafletLayer.setStyle({
        fillColor:   getColor(code),
        fillOpacity: isSel ? 1.0 : 0.75,
        color:       isSel ? '#FFB347' : '#ffffff44',
        weight:      isSel ? 3 : 1,
      })
    })
  }, [values, selected, metric, getColor])

  const styleFeature = useCallback((feature?: Feature): PathOptions => {
    const code = (feature?.properties?.code ?? '') as string
    const isSel = selected === code
    return {
      fillColor:   getColor(code),
      fillOpacity: isSel ? 1.0 : 0.75,
      color:       isSel ? '#FFB347' : '#ffffff44',
      weight:      isSel ? 3 : 1,
    }
  }, [selected, getColor])

  const onEachFeature = useCallback((feature: Feature, layer: Layer) => {
    const code = feature.properties?.code as string
    const name = feature.properties?.name as string

    const l = layer as FeatureLayer

    l.on({
      mouseover() {
        l.setStyle({ fillOpacity: 1.0, weight: 2, color: '#ffffffaa' })
        setHovered({ name, value: data.mobility[code] ?? data.safety[code] })
      },
      mouseout() {
        setHovered(null)
      },
      click() { onSelect(code) },
    })
  }, [data, onSelect])

  const metricLabel = metric === 'mobility' ? 'Flujo vehicular' : 'Homicidios'

  return (
    <div className="mapPanel">
      {/* Header */}
      <div className="mapHeader">
        <div className="chartTitle">Mapa por comunas</div>
        <div className="mapToggle">
          <button
            className={`mapToggleBtn${metric === 'mobility' ? ' mapToggleBtn--active' : ''}`}
            onClick={() => setMetric('mobility')}
          >Movilidad</button>
          <button
            className={`mapToggleBtn${metric === 'safety' ? ' mapToggleBtn--active' : ''}`}
            onClick={() => setMetric('safety')}
          >Seguridad</button>
        </div>
      </div>

      {/* Leaflet map */}
      <div style={{ height: 340, borderRadius: 10, overflow: 'hidden' }}>
        <MapContainer
          center={[6.2442, -75.5812]}
          zoom={12}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={false}
          zoomControl
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
            subdomains="abcd"
            maxZoom={19}
          />
          {geoData && (
            <GeoJSON
              ref={geoRef}
              data={geoData}
              style={styleFeature}
              onEachFeature={onEachFeature}
            />
          )}
        </MapContainer>
      </div>

      {/* Hover info bar */}
      <div className="mapInfoBar">
        {hovered ? (
          <>
            <span className="mapInfoName">{hovered.name}</span>
            <span className="mapInfoVal">
              {metricLabel}:{' '}
              <b>
                {hovered.value !== undefined && Number.isFinite(hovered.value)
                  ? hovered.value.toLocaleString('es-CO', { maximumFractionDigits: 0 })
                  : 'N/D'}
              </b>
            </span>
            <span className="mapInfoHint">↵ clic para filtrar</span>
          </>
        ) : (
          <span className="mapInfoHint">Pasa el cursor sobre una comuna para ver su valor</span>
        )}
      </div>

      {/* Color legend */}
      <div className="mapLegend">
        <span className="mapLegendLabel">Menor</span>
        <div
          className="mapLegendBar"
          style={{
            background: metric === 'mobility'
              ? 'linear-gradient(to right, rgb(10,30,50), rgb(0,196,150))'
              : 'linear-gradient(to right, rgb(15,15,30), rgb(220,50,50))',
          }}
        />
        <span className="mapLegendLabel">Mayor</span>
      </div>
    </div>
  )
}
