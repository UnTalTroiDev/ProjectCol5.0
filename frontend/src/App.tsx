import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import NewsletterSubscribe from './components/NewsletterSubscribe'
import './App.css'

import type { ComunaOption, Tab } from './types'
import { API_URL, SectionSkeleton } from './utils'

const OverviewTab = lazy(() => import('./tabs/OverviewTab'))
const SecurityTab = lazy(() => import('./tabs/SecurityTab'))
const HealthTab = lazy(() => import('./tabs/HealthTab'))
const EducationTab = lazy(() => import('./tabs/EducationTab'))
const EnvironmentTab = lazy(() => import('./tabs/EnvironmentTab'))
const QualityTab = lazy(() => import('./tabs/QualityTab'))
const CityTab = lazy(() => import('./tabs/CityTab'))
const CompareTab = lazy(() => import('./tabs/CompareTab'))

// ---------------------------------------------------------------------------
// Tab nav
// ---------------------------------------------------------------------------

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'overview',    label: 'Visión general',  icon: '🏙' },
  { id: 'security',    label: 'Seguridad',        icon: '🔒' },
  { id: 'health',      label: 'Salud',            icon: '🏥' },
  { id: 'education',   label: 'Educación',        icon: '📚' },
  { id: 'environment', label: 'Ambiente',         icon: '🌿' },
  { id: 'quality',     label: 'Calidad de vida',  icon: '📊' },
  { id: 'city',        label: 'Ciudad',           icon: '🗺' },
  { id: 'compare',     label: 'Comparar',         icon: '⚖️' },
]

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('overview')

  // ── Shared filters ────────────────────────────────────────────────────────
  const [comunas, setComunas] = useState<ComunaOption[]>([])
  const [selected, setSelected] = useState<string>('ALL')
  const [selectedYear, setSelectedYear] = useState<number | null>(null)
  const [availableYears, setAvailableYears] = useState<number[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const comunaOptions = useMemo(() => {
    return [{ code: 'ALL', name: 'Toda la ciudad' } as ComunaOption].concat(comunas)
  }, [comunas])

  // ── Load comunas on mount ─────────────────────────────────────────────────

  useEffect(() => {
    async function loadComunas() {
      const res = await fetch(`${API_URL}/api/territory/comunas`)
      if (!res.ok) throw new Error('No pudimos obtener la lista de territorios.')
      const json = await res.json()
      setComunas(json.comunas ?? [])
      if (json.comunas?.length) setSelected(s => s === 'ALL' ? json.comunas[0].code : s)
    }
    loadComunas().catch(e => {
      setError(e instanceof Error ? e.message : 'Sin conexion con el servidor.')
      setLoading(false)
    }).finally(() => setLoading(false))
  }, [])

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="page">
      {/* Header */}
      <header className="header">
        <div>
          <h1>MedCity Dashboard</h1>
          <p className="subtitle">Datos abiertos de Medellín — MEData</p>
        </div>
        <div className="filters">
          <label>
            Territorio
            <select value={selected} onChange={e => setSelected(e.target.value)} aria-label="Territorio">
              {comunaOptions.map(c => (
                <option key={c.code} value={c.code}>
                  {c.code === 'ALL' ? c.name : c.name ? `${c.name} (${c.code})` : c.code}
                </option>
              ))}
            </select>
          </label>
          <label>
            Año
            <select value={selectedYear ?? ''} onChange={e => setSelectedYear(e.target.value ? Number(e.target.value) : null)} aria-label="Año">
              <option value="">Último disponible</option>
              {availableYears.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </label>
        </div>
      </header>

      {/* Tab nav */}
      <nav className="tabNav">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`tabBtn${activeTab === t.id ? ' tabBtn--active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            <span className="tabIcon">{t.icon}</span>
            <span className="tabLabel">{t.label}</span>
          </button>
        ))}
      </nav>

      {/* Error global */}
      {error && !comunas.length ? (
        <div className="errorBox">
          <div className="errorTitle">No pudimos cargar los datos</div>
          <div className="errorMsg">{error}</div>
        </div>
      ) : null}

      {/* ── Tabs ── */}
      <Suspense fallback={<SectionSkeleton />}>
        {activeTab === 'overview' && (
          <OverviewTab
            comunaCode={selected}
            comunas={comunas}
            selectedYear={selectedYear}
            onSelectComuna={setSelected}
            onAvailableYears={setAvailableYears}
          />
        )}
        {activeTab === 'security' && (
          <SecurityTab comunaCode={selected} selectedYear={selectedYear} />
        )}
        {activeTab === 'health' && (
          <HealthTab comunaCode={selected} selectedYear={selectedYear} />
        )}
        {activeTab === 'education' && (
          <EducationTab comunaCode={selected} selectedYear={selectedYear} />
        )}
        {activeTab === 'environment' && (
          <EnvironmentTab comunaCode={selected} selectedYear={selectedYear} />
        )}
        {activeTab === 'quality' && (
          <QualityTab comunaCode={selected} selectedYear={selectedYear} />
        )}
        {activeTab === 'city' && <CityTab />}
        {activeTab === 'compare' && (
          <CompareTab comunaCode={selected} comunas={comunas} selectedYear={selectedYear} />
        )}
      </Suspense>
      {/* Newsletter WhatsApp subscription */}
      <NewsletterSubscribe comunas={comunas} />
    </div>
  )
}
