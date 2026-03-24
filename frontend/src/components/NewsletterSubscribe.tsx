import { useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

type ComunaOption = { code: string; name?: string | null }

export default function NewsletterSubscribe({ comunas }: { comunas: ComunaOption[] }) {
  const [phone, setPhone] = useState('+57')
  const [comuna, setComuna] = useState('ALL')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setResult(null)

    try {
      const res = await fetch(`${API_URL}/api/newsletter/subscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone_number: phone.trim(), comuna_code: comuna }),
      })
      if (res.ok) {
        setResult({ ok: true, msg: 'Te has suscrito al newsletter diario por WhatsApp.' })
        setPhone('+57')
        setComuna('ALL')
      } else {
        const body = await res.json().catch(() => null)
        const detail = body?.detail
        const msg = typeof detail === 'string'
          ? detail
          : detail?.message ?? 'No se pudo completar la suscripcion. Intenta de nuevo.'
        setResult({ ok: false, msg })
      }
    } catch {
      setResult({ ok: false, msg: 'Error de conexion. Intenta de nuevo.' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="nlSection">
      <div className="nlCard">
        <div className="nlHeader">
          <span className="nlIcon">💬</span>
          <div>
            <h3 className="nlTitle">Newsletter diario por WhatsApp</h3>
            <p className="nlDesc">
              Recibe cada manana un resumen con los indicadores clave de Medellin
              directamente en tu WhatsApp.
            </p>
          </div>
        </div>

        <form className="nlForm" onSubmit={handleSubmit}>
          <label className="nlLabel">
            Numero WhatsApp
            <input
              className="nlInput"
              type="tel"
              placeholder="+573001234567"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              required
              minLength={12}
              maxLength={16}
            />
          </label>

          <label className="nlLabel">
            Territorio
            <select
              className="nlSelect"
              value={comuna}
              onChange={e => setComuna(e.target.value)}
            >
              <option value="ALL">Toda la ciudad</option>
              {comunas.map(c => (
                <option key={c.code} value={c.code}>
                  {c.name ? `${c.name} (${c.code})` : `Comuna ${c.code}`}
                </option>
              ))}
            </select>
          </label>

          <button className="nlSubmit" type="submit" disabled={submitting}>
            {submitting ? 'Suscribiendo...' : 'Suscribirme'}
          </button>
        </form>

        {result && (
          <div className={`nlResult ${result.ok ? 'nlResult--ok' : 'nlResult--err'}`}>
            {result.msg}
          </div>
        )}
      </div>
    </section>
  )
}
