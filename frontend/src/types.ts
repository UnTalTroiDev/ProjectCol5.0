// ---------------------------------------------------------------------------
// Shared types for MedCity Dashboard
// ---------------------------------------------------------------------------

export type ComunaOption = { code: string; name?: string | null }
export type MetricBlock = { value: number | null; unit: string }

export type OverviewResponse = {
  meta: Record<string, unknown>
  selected: { comuna_code: string; comuna_name?: string | null }
  metrics: Record<string, MetricBlock>
  city_averages: Record<string, MetricBlock>
  recommendations: string[]
  mobility_by_comuna: Array<{ comuna_code: string; comuna_name?: string; mobility_equiv_vehicles: number }>
  safety_by_comuna: Array<{ comuna_code: string; comuna_name?: string; safety_homicides: number }>
}

export type TrendPoint = { year: number; value: number | null }
export type TrendsResponse = {
  metric: string; comuna_code: string; unit: string
  series: TrendPoint[]; available_years: number[]
}
export type TrendsMetric = 'safety' | 'mobility' | 'investment'

export type CriminalidadResponse = {
  available: boolean; available_years: number[]
  by_type: Array<{ crime_type: string; total: number }>
  series: Array<{ year?: number; month?: number; total: number }>
}

export type VifResponse = {
  available: boolean; latest_year: number | null; total: number
  by_comuna: Array<{ comuna_code: string; casos: number }>
  series: Array<{ year: number; total: number }>
}

export type NatalidadResponse = {
  available: boolean; latest_year: number; total_nacimientos: number
  by_comuna: Array<{ comuna_code: string; nacimientos: number }>
  by_sex: Array<{ [k: string]: unknown }>
  series: Array<{ year: number; nacimientos: number }>
}

export type EstablecimientosResponse = {
  available: boolean; total: number
  by_comuna: Array<{ comuna_code: string; establecimientos: number }>
  by_modalidad: Array<{ modalidad: string; total: number }>
}

export type ResiduosResponse = {
  available: boolean; latest_year: number; total_kg: number; unit: string
  by_type: Array<{ tipo_residuo: string; cantidad_kg: number }>
  series: Array<{ year?: number; month?: number; cantidad_kg: number }>
}

export type ImcvResponse = {
  available: boolean; latest_year: number
  by_comuna: Array<{ comuna_code: string; imcv_promedio: number }>
  by_dimension: Array<{ dimension: string; promedio: number }>
  series: Array<{ year: number; imcv_promedio: number | null }>
}

export type SiniestrosResponse = {
  available: boolean; latest_year: number; total_victimas: number
  by_type: Array<{ tipo_victima: string; total: number }>
  by_severity: Array<{ gravedad: string; total: number }>
  series: Array<{ year: number; victimas: number }>
}

export type CitySummary = {
  available_domains: number; total_domains: number; message: string
  domains: Record<string, { available: boolean; label: string; latest_year?: number; [k: string]: unknown }>
}

export type CompareRow = {
  comuna_code: string; comuna_name: string
  mobility_equiv_vehicles: number | null
  safety_homicides: number | null
  investment_amount: number | null
  lesiones_count?: number | null
}

export type CompareResponse = { year: number; comunas: CompareRow[] }

export type Tab = 'overview' | 'security' | 'health' | 'education' | 'environment' | 'quality' | 'city' | 'compare'
