from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import threading
import time
from io import BytesIO
from typing import Optional

import httpx
import pandas as pd
from cachetools import TTLCache
from fastapi import HTTPException

from ..config import CSV_CACHE_TTL_SECONDS, DATASETS

logger = logging.getLogger(__name__)

_byte_cache: TTLCache[str, bytes] = TTLCache(maxsize=32, ttl=CSV_CACHE_TTL_SECONDS)
_cache_lock = threading.Lock()

# ── SQLite stale cache ─────────────────────────────────────────────────────
_SQLITE_PATH = os.getenv("STALE_CACHE_DB", "/tmp/medata_stale.sqlite3")

_local = threading.local()


def _get_db() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(_SQLITE_PATH)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS stale_cache "
            "(url TEXT PRIMARY KEY, content BLOB NOT NULL, updated_at REAL NOT NULL)"
        )
        conn.commit()
        _local.conn = conn
    return conn


def _stale_put(url: str, content: bytes) -> None:
    try:
        _get_db().execute(
            "INSERT INTO stale_cache(url, content, updated_at) VALUES(?,?,?) "
            "ON CONFLICT(url) DO UPDATE SET content=excluded.content, updated_at=excluded.updated_at",
            (url, content, time.time()),
        )
        _get_db().commit()
    except Exception as exc:
        logger.warning("stale_put failed: %s", exc)


def _stale_get(url: str) -> Optional[bytes]:
    try:
        row = _get_db().execute("SELECT content FROM stale_cache WHERE url=?", (url,)).fetchone()
        return row[0] if row else None
    except Exception as exc:
        logger.warning("stale_get failed: %s", exc)
        return None


_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_BASE = 2


async def _download_with_retry(url: str) -> bytes:
    last_exc: Exception = RuntimeError("Sin intentos realizados")
    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0), follow_redirects=True) as client:
        for attempt in range(1, _RETRY_ATTEMPTS + 1):
            try:
                logger.info("Descargando dataset (intento %d/%d): %s", attempt, _RETRY_ATTEMPTS, url)
                resp = await client.get(url)
                resp.raise_for_status()
                logger.info("Dataset descargado OK (%d bytes): %s", len(resp.content), url)
                return resp.content
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                if attempt < _RETRY_ATTEMPTS:
                    wait = _RETRY_BACKOFF_BASE ** attempt
                    logger.warning("Reintentando en %ds (%d/%d): %s", wait, attempt, _RETRY_ATTEMPTS, url)
                    await asyncio.sleep(wait)
            except httpx.HTTPStatusError as exc:
                raise exc
    raise last_exc


async def fetch_url_bytes(url: str) -> bytes:
    """Descarga con retry, cache TTL en memoria y fallback a stale cache (SQLite)."""
    with _cache_lock:
        cached = _byte_cache.get(url)
    if cached is not None:
        return cached

    try:
        content = await _download_with_retry(url)
        with _cache_lock:
            _byte_cache[url] = content
        _stale_put(url, content)
        return content
    except httpx.TimeoutException:
        stale = _stale_get(url)
        if stale is not None:
            logger.warning("Sirviendo stale cache para: %s", url)
            return stale
        raise HTTPException(status_code=503, detail={"code": "UPSTREAM_TIMEOUT", "url": url})
    except httpx.ConnectError:
        stale = _stale_get(url)
        if stale is not None:
            logger.warning("Sirviendo stale cache para: %s", url)
            return stale
        raise HTTPException(status_code=503, detail={"code": "UPSTREAM_UNAVAILABLE", "url": url})
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        stale = _stale_get(url)
        if stale is not None:
            logger.warning("Sirviendo stale cache para: %s", url)
            return stale
        raise HTTPException(status_code=502, detail={"code": "UPSTREAM_HTTP_ERROR", "http_status": status, "url": url})


def read_csv_from_bytes(content: bytes, source_url: str = "") -> pd.DataFrame:
    """Lee CSV con deteccion automatica de separador y encoding."""
    bio = BytesIO(content)
    try:
        return pd.read_csv(bio, sep=None, engine="python", encoding="utf-8")
    except UnicodeDecodeError:
        bio = BytesIO(content)
        try:
            return pd.read_csv(bio, sep=None, engine="python", encoding="latin1")
        except Exception:
            raise HTTPException(status_code=502, detail={"code": "UPSTREAM_PARSE_ERROR", "url": source_url})
    except Exception:
        raise HTTPException(status_code=502, detail={"code": "UPSTREAM_PARSE_ERROR", "url": source_url})


async def _safe_load(url: str) -> Optional[pd.DataFrame]:
    """Carga un dataset opcionalmente — devuelve None si no esta disponible."""
    try:
        content = await fetch_url_bytes(url)
        return read_csv_from_bytes(content, source_url=url)
    except HTTPException:
        logger.warning("Dataset no disponible: %s", url)
        return None


# ── Loaders principales ────────────────────────────────────────────────────

async def load_mobility_aforos() -> pd.DataFrame:
    url = DATASETS.mobility_aforos_vehiculares
    return read_csv_from_bytes(await fetch_url_bytes(url), source_url=url)

async def load_mobility_siniestros() -> Optional[pd.DataFrame]:
    return await _safe_load(DATASETS.mobility_victimas_incidentes_viales)

async def load_safety_homicidios() -> pd.DataFrame:
    url = DATASETS.safety_homicidios
    return read_csv_from_bytes(await fetch_url_bytes(url), source_url=url)

async def load_safety_lesiones() -> Optional[pd.DataFrame]:
    return await _safe_load(DATASETS.safety_lesiones_comunes)

async def load_security_criminalidad() -> Optional[pd.DataFrame]:
    return await _safe_load(DATASETS.security_criminalidad_consolidada)

async def load_social_violencia_intrafamiliar() -> Optional[pd.DataFrame]:
    return await _safe_load(DATASETS.social_violencia_intrafamiliar)

async def load_investment_por_comuna() -> pd.DataFrame:
    url = DATASETS.investment_inversion_por_comuna_2019
    return read_csv_from_bytes(await fetch_url_bytes(url), source_url=url)

async def load_health_natalidad() -> Optional[pd.DataFrame]:
    return await _safe_load(DATASETS.health_natalidad)

async def load_health_hospitalizacion() -> Optional[pd.DataFrame]:
    return await _safe_load(DATASETS.health_hospitalizacion)

async def load_education_establecimientos() -> Optional[pd.DataFrame]:
    return await _safe_load(DATASETS.education_establecimientos)

async def load_education_ambiente_escolar() -> Optional[pd.DataFrame]:
    return await _safe_load(DATASETS.education_ambiente_escolar)

async def load_environment_residuos() -> Optional[pd.DataFrame]:
    return await _safe_load(DATASETS.environment_residuos_solidos)

async def load_quality_imcv() -> Optional[pd.DataFrame]:
    return await _safe_load(DATASETS.quality_imcv)
