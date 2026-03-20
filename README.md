# MedCity Dashboard (Hackathon)

Prototipo con **backend Python (FastAPI)** y **frontend React** para un dashboard tipo Smart Cities usando datos abiertos de MEData:
- Movilidad: `Aforos Vehiculares`
- Seguridad: `Homicidio`
- Inversión territorial: `Inversión por comuna y corregimiento`

## Requisitos

- Python 3.10+
- Node.js 18+

## Ejecutar backend

```bash
pip install -r backend/requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Endpoints:
- `GET http://127.0.0.1:8000/api/health`
- `GET http://127.0.0.1:8000/api/territory/comunas`
- `GET http://127.0.0.1:8000/api/dashboard/overview?comuna_code=ALL` (o un código de comuna como `01`)

## Ejecutar frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Opcional:
- `VITE_API_URL=http://127.0.0.1:8000`

## Notas del prototipo

- La API usa una caché en memoria (TTL 20 min) para que el demo sea más fluido.
- Si una métrica no existe para una comuna seleccionada, el backend devuelve `null` y el frontend muestra `N/D`.

