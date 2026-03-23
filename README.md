# MedCity Dashboard

> Inteligencia territorial para Medellín: 7 dominios de datos abiertos en tiempo real.

Dashboard interactivo de datos abiertos de Medellín (MEData) que permite explorar y comparar indicadores clave por comuna. Desarrollado para hackathon Smart Cities.

---

## Qué hace

Selecciona cualquier comuna de Medellín y explora **7 dominios de datos** con navegación por tabs:

- 🏙 **Visión general** — Movilidad, seguridad e inversión pública con tendencias históricas y recomendaciones basadas en percentiles
- 🔒 **Seguridad** — Criminalidad consolidada: 10+ tipos de delito (homicidios, hurtos, extorsión, delitos sexuales) desde 2003
- 🏥 **Salud** — Natalidad por año, sexo y comuna; egresos hospitalarios por diagnóstico
- 📚 **Educación** — Directorio de 806+ establecimientos educativos por comuna y modalidad; indicadores de ambiente escolar
- 🌿 **Medio Ambiente** — Generación de residuos sólidos ordinarios y aprovechables por tipo y mes
- 📊 **Calidad de vida** — Índice Multidimensional de Calidad de Vida (IMCV) por comuna y dimensión; víctimas en incidentes viales
- 🗺 **Ciudad** — Panel de disponibilidad en tiempo real de todos los datasets MEData

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | React 19 + TypeScript + Vite + Recharts |
| Backend | Python 3.11 + FastAPI + Pandas |
| Datos | 12 datasets CSV de [MEData](https://medata.gov.co) con caché TTL 6h + stale fallback 24h |
| Infraestructura | Docker + docker-compose |

---

## Arquitectura

```
Browser (React — 7 tabs)
    │
    │  REST / JSON
    ▼
FastAPI v0.3.0 (Python)
    │  retry 3x + backoff + stale cache
    ▼
MEData CSVs — 12 datasets (Movilidad · Seguridad · Salud · Educación · Ambiente · Calidad)
    │
    ▼
Pandas — agregación por comuna, percentiles, tendencias anuales
```

---

## Inicio rápido con Docker

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Documentación interactiva: http://localhost:8000/docs

---

## Inicio manual (sin Docker)

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Variables de entorno opcionales (crear `.env` en la raíz):

```env
VITE_API_URL=http://127.0.0.1:8000
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CSV_CACHE_TTL_SECONDS=21600
MEDATA_LESIONES_URL=http://medata.gov.co/...  # opcional
```

---

## Endpoints de la API

### Sistema

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/health` | Healthcheck — versión y estado |
| GET | `/api/city/summary` | KPIs de todos los dominios en una sola llamada |

### Territorio

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/territory/comunas` | Lista de 16 comunas disponibles |

### Dashboard principal (Movilidad · Seguridad · Inversión)

| Método | Endpoint | Parámetros | Descripción |
|---|---|---|---|
| GET | `/api/dashboard/overview` | `comuna_code`, `year` | KPIs, rankings y recomendaciones por percentil |
| GET | `/api/dashboard/trends` | `metric`, `comuna_code` | Serie temporal por año (`mobility`, `safety`, `investment`) |
| GET | `/api/dashboard/crime-stats` | `comuna_code`, `year` | Homicidios + lesiones comunes combinados |

### Seguridad ampliada

| Método | Endpoint | Parámetros | Descripción |
|---|---|---|---|
| GET | `/api/security/criminalidad` | `year`, `crime_type` | Criminalidad consolidada por tipo de delito (2003–hoy) |
| GET | `/api/security/violencia-intrafamiliar` | `year` | Medidas de protección VIF por comuna |

### Salud

| Método | Endpoint | Parámetros | Descripción |
|---|---|---|---|
| GET | `/api/health-data/natalidad` | `year` | Nacimientos por año, sexo y comuna |
| GET | `/api/health-data/hospitalizacion` | `year` | Egresos hospitalarios por diagnóstico |

### Educación

| Método | Endpoint | Parámetros | Descripción |
|---|---|---|---|
| GET | `/api/education/establecimientos` | `comuna_code` | Directorio de instituciones educativas |
| GET | `/api/education/ambiente-escolar` | `year` | Indicadores históricos de convivencia escolar |

### Medio Ambiente

| Método | Endpoint | Parámetros | Descripción |
|---|---|---|---|
| GET | `/api/environment/residuos` | `year` | Residuos sólidos ordinarios y aprovechables (kg/mes) |

### Calidad de Vida

| Método | Endpoint | Parámetros | Descripción |
|---|---|---|---|
| GET | `/api/quality/imcv` | `year`, `comuna_code` | Índice Multidimensional de Calidad de Vida por comuna |
| GET | `/api/quality/siniestros-viales` | `year`, `comuna_code` | Víctimas en incidentes viales por tipo y gravedad |

---

## Fuentes de datos MEData

| Dataset | Secretaría | Recurso MEData |
|---|---|---|
| Aforos Vehiculares | Movilidad | `1-023-25-000301` |
| Víctimas Incidentes Viales | Movilidad | `1-023-25-000360` |
| Homicidios | Seguridad (SISC) | `1-027-23-000008` |
| Lesiones Personales | Seguridad (SISC) | `1-027-23-000007` |
| Criminalidad Consolidada | Seguridad (SISC) | `1-027-23-000306` |
| Violencia Intrafamiliar | Seguridad (SISC) | `1-027-23-000028` |
| Inversión por Comuna | Hacienda | `1-002-11-000278` |
| Natalidad | Salud | `1-026-22-000029` |
| Hospitalización | Salud | `1-026-22-000126` |
| Establecimientos Educativos | Educación | `1-011-08-000122` |
| Ambiente Escolar | Educación | `1-011-08-000068` |
| Residuos Sólidos | Suministros | `1-028-02-000599` |
| IMCV Calidad de Vida | Planeación (DAP) | `1-002-09-000041` |

Todos los datos son abiertos bajo licencia **Creative Commons BY-SA 4.0** · [medata.gov.co](https://medata.gov.co)

---

## Tests

```bash
pytest backend/tests/
```

Cubre: health, comunas, overview (ALL y por código), tendencias, crime-stats, filtros de año, validación 404/422.

---

## Estructura del proyecto

```
ProjectCol5.0/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI v0.3.0 — 15 endpoints
│   │   ├── config.py                  # URLs de 13 datasets MEData
│   │   ├── schemas/
│   │   │   ├── dashboard.py           # OverviewResponse, TrendsResponse, etc.
│   │   │   └── city.py                # CitySummaryResponse
│   │   ├── services/
│   │   │   ├── data_loader.py         # Descarga CSV con retry + stale cache
│   │   │   ├── dashboard_service.py   # Movilidad, seguridad, inversión
│   │   │   ├── security_service.py    # Criminalidad consolidada + VIF
│   │   │   ├── health_service.py      # Natalidad + hospitalización
│   │   │   ├── education_service.py   # Establecimientos + ambiente escolar
│   │   │   ├── environment_service.py # Residuos sólidos
│   │   │   └── quality_service.py     # IMCV + siniestros viales
│   │   └── utils/normalize.py         # resolve_column, normalize_code, etc.
│   ├── tests/test_api.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # Dashboard con 7 tabs de navegación
│   │   ├── App.css                    # Estilos — tabs, domain cards, charts
│   │   ├── MedellinMap.tsx            # Mapa coroplético interactivo
│   │   ├── Landing.tsx                # Página de inicio
│   │   └── index.css                  # Design tokens + dark mode
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```
