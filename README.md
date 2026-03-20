# MedCity Dashboard

> Inteligencia territorial para Medellín: movilidad, seguridad e inversión pública en tiempo real.

Dashboard interactivo de datos abiertos de Medellín (MEData) que permite explorar y comparar indicadores clave por comuna. Desarrollado para hackathon Smart Cities.

---

## Qué hace

Selecciona cualquier comuna de Medellín y obtén al instante:

- **Movilidad** — Aforos vehiculares (vehículos equivalentes)
- **Seguridad** — Casos de homicidio
- **Inversión territorial** — Inversión pública en COP

Cada indicador se compara automáticamente contra el **promedio de la ciudad** y genera **recomendaciones accionables** con cifras concretas.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | React 19 + TypeScript + Vite + Recharts |
| Backend | Python 3.11 + FastAPI + Pandas |
| Datos | CSVs abiertos de [MEData](https://medata.gov.co) con caché en memoria (TTL 6h) |
| Infraestructura | Docker + docker-compose |

---

## Arquitectura

```
Browser (React)
    │
    │  REST / JSON
    ▼
FastAPI (Python)
    │
    │  HTTP + caché TTL
    ▼
CSVs MEData (Aforos · Homicidios · Inversión)
```

El backend descarga los datasets al primer request y los cachea en memoria. La capa de servicio agrega, normaliza y calcula promedios por anno. El frontend consume 2 endpoints y renderiza KPI cards, gráficas top-10 y recomendaciones.

---

## Inicio rápido con Docker

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api/health

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
```

Ver `.env.example` para la referencia completa.

---

## Endpoints de la API

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/health` | Healthcheck |
| GET | `/api/territory/comunas` | Lista de comunas disponibles |
| GET | `/api/dashboard/overview?comuna_code=ALL` | KPIs, rankings y recomendaciones (ALL o código de comuna) |

---

## Tests

```bash
pytest backend/tests/
```

11 casos de prueba con TestClient real (sin mocks) que cubren health, listado de comunas, estructura de overview y validación de errores 404.

---

## Estructura del proyecto

```
ProjectCol5.0/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, endpoints
│   │   ├── config.py            # URLs de datasets, TTL de caché
│   │   ├── schemas/             # Pydantic models (OverviewResponse, etc.)
│   │   ├── services/
│   │   │   ├── dashboard_service.py  # Agregación, promedios, recomendaciones
│   │   │   └── data_loader.py        # Descarga de CSVs, caché TTL
│   │   └── utils/normalize.py   # Normalización de códigos de comuna
│   ├── tests/test_api.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Dashboard principal
│   │   ├── App.css              # Estilos del dashboard
│   │   └── index.css            # Design tokens, dark mode
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Fuentes de datos

| Dataset | Fuente |
|---|---|
| Aforos Vehiculares | MEData — Secretaría de Movilidad |
| Homicidios | MEData — Secretaría de Seguridad |
| Inversión por comuna | MEData — Secretaría de Hacienda |
