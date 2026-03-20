import { useMemo, useState } from 'react'

// ── Tile layout ────────────────────────────────────────────────
// Geographic approximation of Medellín's 16 comunas as a tile grid.
// (col, row) where (0,0) = northwest, (4,4) = southeast.
//
//  Col →  0          1          2          3          4
//  Row 0:                      [04]       [02]       [01]
//  Row 1: [07]       [05]      [06]       [03]
//  Row 2: [13]       [12]      [11]       [10]       [08]
//  Row 3:            [16]      [15]                  [09]
//  Row 4:                                            [14]

type ComunaTile = {
  code: string
  name: string
  short: string
  col: number
  row: number
}

const COMUNAS: ComunaTile[] = [
  { code: '01', name: 'Popular',          short: 'Popular',     col: 4, row: 0 },
  { code: '02', name: 'Santa Cruz',       short: 'Santa Cruz',  col: 3, row: 0 },
  { code: '03', name: 'Manrique',         short: 'Manrique',    col: 3, row: 1 },
  { code: '04', name: 'Aranjuez',         short: 'Aranjuez',    col: 2, row: 0 },
  { code: '05', name: 'Castilla',         short: 'Castilla',    col: 1, row: 1 },
  { code: '06', name: 'Doce de Octubre',  short: 'Doce Oct.',   col: 2, row: 1 },
  { code: '07', name: 'Robledo',          short: 'Robledo',     col: 0, row: 1 },
  { code: '08', name: 'Villa Hermosa',    short: 'V. Hermosa',  col: 4, row: 2 },
  { code: '09', name: 'Buenos Aires',     short: 'Bs. Aires',   col: 4, row: 3 },
  { code: '10', name: 'La Candelaria',    short: 'Candelaria',  col: 3, row: 2 },
  { code: '11', name: 'Laureles-Estadio', short: 'Laureles',    col: 2, row: 2 },
  { code: '12', name: 'La América',       short: 'La América',  col: 1, row: 2 },
  { code: '13', name: 'San Javier',       short: 'San Javier',  col: 0, row: 2 },
  { code: '14', name: 'El Poblado',       short: 'El Poblado',  col: 4, row: 4 },
  { code: '15', name: 'Guayabal',         short: 'Guayabal',    col: 2, row: 3 },
  { code: '16', name: 'Belén',            short: 'Belén',       col: 1, row: 3 },
]

const TILE_W = 88
const TILE_H = 68
const GAP = 6
const PAD = 12

const COLS = 5
const ROWS = 5

const SVG_W = PAD * 2 + COLS * TILE_W + (COLS - 1) * GAP  // 488
const SVG_H = PAD * 2 + ROWS * TILE_H + (ROWS - 1) * GAP  // 388

// ── Color interpolation ─────────────────────────────────────────
type RGB = [number, number, number]

const PALETTE: Record<MetricType, { low: RGB; high: RGB }> = {
  mobility: { low: [10, 30, 50],   high: [0, 196, 150]  },
  safety:   { low: [15, 15, 30],   high: [220, 50, 50]  },
}

const EMPTY_FILL = '#1e2030'

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t
}

function rgbLerp(low: RGB, high: RGB, t: number): string {
  const r = Math.round(lerp(low[0], high[0], t))
  const g = Math.round(lerp(low[1], high[1], t))
  const b = Math.round(lerp(low[2], high[2], t))
  return `rgb(${r},${g},${b})`
}

// ── Types ───────────────────────────────────────────────────────
export type MetricType = 'mobility' | 'safety'

export type MapData = {
  mobility: Record<string, number>
  safety: Record<string, number>
}

type Props = {
  data: MapData
  selected: string           // commune code or 'ALL'
  onSelect: (code: string) => void
}

// ── Component ───────────────────────────────────────────────────
export default function MedellinMap({ data, selected, onSelect }: Props) {
  const [metric, setMetric] = useState<MetricType>('mobility')
  const [hovered, setHovered] = useState<string | null>(null)

  const values = metric === 'mobility' ? data.mobility : data.safety

  const { minVal, maxVal } = useMemo(() => {
    const vals = Object.values(values).filter((v) => Number.isFinite(v))
    if (!vals.length) return { minVal: 0, maxVal: 1 }
    return { minVal: Math.min(...vals), maxVal: Math.max(...vals) }
  }, [values])

  function getTileColor(code: string): string {
    const val = values[code]
    if (val === undefined || !Number.isFinite(val)) return EMPTY_FILL
    const range = maxVal - minVal
    const t = range === 0 ? 0.5 : (val - minVal) / range
    const { low, high } = PALETTE[metric]
    return rgbLerp(low, high, t)
  }

  const hoveredComuna = hovered ? COMUNAS.find((c) => c.code === hovered) : null
  const hoveredVal = hovered ? values[hovered] : undefined

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
          >
            Movilidad
          </button>
          <button
            className={`mapToggleBtn${metric === 'safety' ? ' mapToggleBtn--active' : ''}`}
            onClick={() => setMetric('safety')}
          >
            Seguridad
          </button>
        </div>
      </div>

      {/* SVG tile map */}
      <div className="mapSvgWrap">
        <svg
          width="100%"
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          aria-label="Mapa coroplético de comunas de Medellín"
          role="img"
        >
          {COMUNAS.map((comuna) => {
            const x = PAD + comuna.col * (TILE_W + GAP)
            const y = PAD + comuna.row * (TILE_H + GAP)
            const cx = x + TILE_W / 2
            const cy = y + TILE_H / 2
            const isSelected = selected === comuna.code
            const isHovered = hovered === comuna.code

            return (
              <g
                key={comuna.code}
                onClick={() => onSelect(comuna.code)}
                onMouseEnter={() => setHovered(comuna.code)}
                onMouseLeave={() => setHovered(null)}
                style={{ cursor: 'pointer' }}
                role="button"
                aria-label={`${comuna.name}, seleccionar`}
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && onSelect(comuna.code)}
              >
                {/* Tile background */}
                <rect
                  x={x}
                  y={y}
                  width={TILE_W}
                  height={TILE_H}
                  rx={10}
                  fill={getTileColor(comuna.code)}
                  opacity={isHovered && !isSelected ? 0.8 : 1}
                />
                {/* Selection / hover ring */}
                {(isSelected || isHovered) && (
                  <rect
                    x={x + 1.5}
                    y={y + 1.5}
                    width={TILE_W - 3}
                    height={TILE_H - 3}
                    rx={9}
                    fill="none"
                    stroke={isSelected ? '#FFB347' : '#ffffff88'}
                    strokeWidth={isSelected ? 2.5 : 1.5}
                  />
                )}
                {/* Commune number */}
                <text
                  x={cx}
                  y={cy - 8}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={18}
                  fontWeight="900"
                  fill="#ffffff"
                  fontFamily="Inter, system-ui, sans-serif"
                  style={{ userSelect: 'none', pointerEvents: 'none' }}
                >
                  {comuna.code}
                </text>
                {/* Commune short name */}
                <text
                  x={cx}
                  y={cy + 14}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={9}
                  fill="#ffffffbb"
                  fontFamily="Inter, system-ui, sans-serif"
                  style={{ userSelect: 'none', pointerEvents: 'none' }}
                >
                  {comuna.short}
                </text>
              </g>
            )
          })}
        </svg>
      </div>

      {/* Hover info bar */}
      <div className="mapInfoBar">
        {hoveredComuna ? (
          <>
            <span className="mapInfoName">{hoveredComuna.name}</span>
            <span className="mapInfoVal">
              {metricLabel}:{' '}
              <b>
                {hoveredVal !== undefined && Number.isFinite(hoveredVal)
                  ? hoveredVal.toLocaleString('es-CO', { maximumFractionDigits: 0 })
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
            background:
              metric === 'mobility'
                ? `linear-gradient(to right, rgb(10,30,50), rgb(0,196,150))`
                : `linear-gradient(to right, rgb(15,15,30), rgb(220,50,50))`,
          }}
        />
        <span className="mapLegendLabel">Mayor</span>
      </div>
    </div>
  )
}
