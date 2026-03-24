import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import Landing from './Landing.tsx'

if (import.meta.env.PROD && !import.meta.env.VITE_API_URL) {
  console.warn(
    '[MedCity] VITE_API_URL is not set. API calls will default to http://localhost:8000. ' +
    'Set VITE_API_URL at build time for production deployments.'
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/dashboard" element={<App />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
