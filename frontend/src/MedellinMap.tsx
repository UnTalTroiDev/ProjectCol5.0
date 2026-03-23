import 'leaflet/dist/leaflet.css'
import { useState } from 'react'
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'
import type { Layer, PathOptions } from 'leaflet'
import type { Feature, FeatureCollection } from 'geojson'

// ── Approximate GeoJSON polygons for Medellín's 16 comunas ──────────────────
// Rectangles derived from the canonical tile-grid layout:
//  Col →  0          1          2          3          4
//  Row 0:                      [04]       [02]       [01]
//  Row 1: [07]       [05]      [06]       [03]
//  Row 2: [13]       [12]      [11]       [10]       [08]
//  Row 3:            [16]      [15]                  [09]
//  Row 4:                                            [14]
//
// col_lon = -75.652 + col * 0.026   |   row_lat = 6.355 - row * 0.038
// half-widths: dlon=0.012, dlat=0.017
// Coordinates in GeoJSON order: [longitude, latitude]

type ComunaMeta = { code: string; name: string; col: number; row: number }

const META: ComunaMeta[] = [
  { code: '01', name: 'Popular',            col: 4, row: 0 },
  { code: '02', name: 'Santa Cruz',         col: 3, row: 0 },
  { code: '03', name: 'Manrique',           col: 3, row: 1 },
  { code: '04', name: 'Aranjuez',           col: 2, row: 0 },
  { code: '05', name: 'Castilla',           col: 1, row: 1 },
  { code: '06', name: 'Doce de Octubre',    col: 2, row: 1 },
  { code: '07', name: 'Robledo',            col: 0, row: 1 },
  { code: '08', name: 'Villa Hermosa',      col: 4, row: 2 },
  { code: '09', name: 'Buenos Aires',       col: 4, row: 3 },
  { code: '10', name: 'La Candelaria',      col: 3, row: 2 },
  { code: '11', name: 'Laureles-Estadio',   col: 2, row: 2 },
  { code: '12', name: 'La América',         col: 1, row: 2 },
  { code: '13', name: 'San Javier',         col: 0, row: 2 },
  { code: '14', name: 'El Poblado',         col: 4, row: 4 },
  { code: '15', name: 'Guayabal',           col: 2, row: 3 },
  { code: '16', name: 'Belén',              col: 1, row: 3 },
]

const DLON = 0.012
const DLAT = 0.017

function buildGeoJSON(): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: META.map(({ code, name, col, row }): Feature => {
      const lon = -75.652 + col * 0.026
      const lat =  6.355 - row * 0.038
      return {
        type: 'Feature',
        properties: { code, name },
        geometry: {
          type: 'Polygon',
          coordinates: [[
            [lon - DLON, lat + DLAT],
            [lon + DLON, lat + DLAT],
            [lon + DLON, lat - DLAT],
            [lon - DLON, lat - DLAT],
            [lon - DLON, lat + DLAT],
          ]],
        },
      }
    }),
  }
}

const COMUNAS_GEOJSON = buildGeoJSON()

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

  const values = metric === 'mobility' ? data.mobility : data.safety

  const nums   = Object.values(values).filter(Number.isFinite)
  const minVal = nums.length ? Math.min(...nums) : 0
  const maxVal = nums.length ? Math.max(...nums) : 1

  function getColor(code: string): string {
    const val = values[code]
    if (val === undefined || !Number.isFinite(val)) return '#1e2030'
    const t = maxVal === minVal ? 0.5 : (val - minVal) / (maxVal - minVal)
    return rgbLerp(PALETTE[metric].low, PALETTE[metric].high, t)
  }

  function styleFeature(feature?: Feature): PathOptions {
    const code = (feature?.properties?.code ?? '') as string
    const isSel = selected === code
    return {
      fillColor:   getColor(code),
      fillOpacity: isSel ? 1.0 : 0.75,
      color:       isSel ? '#FFB347' : '#ffffff44',
      weight:      isSel ? 3 : 1,
    }
  }

  function onEachFeature(feature: Feature, layer: Layer) {
    const code = feature.properties?.code as string
    const name = feature.properties?.name as string

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const l = layer as any

    l.on({
      mouseover() {
        l.setStyle({ fillOpacity: 1.0, weight: 2, color: '#ffffffaa' })
        setHovered({ name, value: values[code] })
      },
      mouseout() {
        const isSel = selected === code
        l.setStyle({
          fillOpacity: isSel ? 1.0 : 0.75,
          weight:      isSel ? 3 : 1,
          color:       isSel ? '#FFB347' : '#ffffff44',
        })
        setHovered(null)
      },
      click() { onSelect(code) },
    })
  }

  const metricLabel = metric === 'mobility' ? 'Flujo vehicular' : 'Homicidios'

  // key forces GeoJSON layer remount when metric or values change
  const geoKey = `${metric}-${selected}-${JSON.stringify(values)}`

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
          <GeoJSON
            key={geoKey}
            data={COMUNAS_GEOJSON}
            style={styleFeature}
            onEachFeature={onEachFeature}
          />
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
