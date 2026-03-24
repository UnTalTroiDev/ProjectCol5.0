from __future__ import annotations

import logging
import os
import sqlite3
import time
from io import BytesIO
from typing import Optional

import pandas as pd
import requests
from cachetools import TTLCache, cached
from fastapi import HTTPException

from ..config import CSV_CACHE_TTL_SECONDS, DATASETS

logger = logging.getLogger(__name__)

_byte_cache: TTLCache[str, bytes] = TTLCache(maxsize=32, ttl=CSV_CACHE_TTL_SECONDS)

# ── SQLite stale cache ─────────────────────────────────────────────────────
_SQLITE_PATH = os.getenv("STALE_CACHE_DB", "/tmp/medata_stale.sqlite3")

def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_SQLITE_PATH, check_same_thread=False)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS stale_cache "
        "(url TEXT PRIMARY KEY, content BLOB NOT NULL, updated_at REAL NOT NULL)"
    )
    conn.commit()
    return conn

_db: sqlite3.Connection = _get_db()


def _stale_put(url: str, content: bytes) -> None:
    try:
        _db.execute(
            "INSERT INTO stale_cache(url, content, updated_at) VALUES(?,?,?) "
            "ON CONFLICT(url) DO UPDATE SET content=excluded.content, updated_at=excluded.updated_at",
            (url, content, time.time()),
        )
        _db.commit()
    except Exception as exc:
        logger.warning("stale_put failed: %s", exc)


def _stale_get(url: str) -> Optional[bytes]:
    try:
        row = _db.execute("SELECT content FROM stale_cache WHERE url=?", (url,)).fetchone()
        return row[0] if row else None
    except Exception as exc:
        logger.warning("stale_get failed: %s", exc)
        return None

_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_BASE = 2


def _download_with_retry(url: str) -> bytes:
    last_exc: Exception = RuntimeError("Sin intentos realizados")
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            logger.info("Descargando dataset (intento %d/%d): %s", attempt, _RETRY_ATTEMPTS, url)
            resp = requests.get(url, timeout=(15, 300), stream=True)
            resp.raise_for_status()
            chunks = []
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if chunk:
                    chunks.append(chunk)
            content = b"".join(chunks)
            logger.info("Dataset descargado OK (%d bytes): %s", len(content), url)
            return content
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
        ) as exc:
            last_exc = exc
            if attempt < _RETRY_ATTEMPTS:
                wait = _RETRY_BACKOFF_BASE ** attempt
                logger.warning("Reintentando en %ds (%d/%d): %s", wait, attempt, _RETRY_ATTEMPTS, url)
                time.sleep(wait)
        except requests.exceptions.HTTPError as exc:
            raise exc
    raise last_exc


@cached(_byte_cache)
def fetch_url_bytes(url: str) -> bytes:
    """Descarga con retry y fallback a stale cache (SQLite persistente)."""
    try:
        content = _download_with_retry(url)
        _stale_put(url, content)
        return content
    except requests.exceptions.Timeout:
        stale = _stale_get(url)
        if stale is not None:
            logger.warning("Sirviendo stale cache para: %s", url)
            return stale
        raise HTTPException(status_code=503, detail={"code": "UPSTREAM_TIMEOUT", "url": url})
    except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError):
        stale = _stale_get(url)
        if stale is not None:
            logger.warning("Sirviendo stale cache para: %s", url)
            return stale
        raise HTTPException(status_code=503, detail={"code": "UPSTREAM_UNAVAILABLE", "url": url})
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
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
        except Exception as exc:
            raise HTTPException(status_code=502, detail={"code": "UPSTREAM_PARSE_ERROR", "url": source_url})
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"code": "UPSTREAM_PARSE_ERROR", "url": source_url})


def _safe_load(url: str) -> Optional[pd.DataFrame]:
    """Carga un dataset opcionalmente — devuelve None si no esta disponible."""
    try:
        return read_csv_from_bytes(fetch_url_bytes(url), source_url=url)
    except HTTPException:
        logger.warning("Dataset no disponible: %s", url)
        return None


# ── Loaders principales ────────────────────────────────────────────────────

def load_mobility_aforos() -> pd.DataFrame:
    url = DATASETS.mobility_aforos_vehiculares
    return read_csv_from_bytes(fetch_url_bytes(url), source_url=url)

def load_mobility_siniestros() -> Optional[pd.DataFrame]:
    return _safe_load(DATASETS.mobility_victimas_incidentes_viales)

def load_safety_homicidios() -> pd.DataFrame:
    url = DATASETS.safety_homicidios
    return read_csv_from_bytes(fetch_url_bytes(url), source_url=url)

def load_safety_lesiones() -> Optional[pd.DataFrame]:
    return _safe_load(DATASETS.safety_lesiones_comunes)

def load_security_criminalidad() -> Optional[pd.DataFrame]:
    return _safe_load(DATASETS.security_criminalidad_consolidada)

def load_social_violencia_intrafamiliar() -> Optional[pd.DataFrame]:
    return _safe_load(DATASETS.social_violencia_intrafamiliar)

def load_investment_por_comuna() -> pd.DataFrame:
    url = DATASETS.investment_inversion_por_comuna_2019
    return read_csv_from_bytes(fetch_url_bytes(url), source_url=url)

def load_health_natalidad() -> Optional[pd.DataFrame]:
    return _safe_load(DATASETS.health_natalidad)

def load_health_hospitalizacion() -> Optional[pd.DataFrame]:
    return _safe_load(DATASETS.health_hospitalizacion)

def load_education_establecimientos() -> Optional[pd.DataFrame]:
    return _safe_load(DATASETS.education_establecimientos)

def load_education_ambiente_escolar() -> Optional[pd.DataFrame]:
    return _safe_load(DATASETS.education_ambiente_escolar)

def load_environment_residuos() -> Optional[pd.DataFrame]:
    return _safe_load(DATASETS.environment_residuos_solidos)

def load_quality_imcv() -> Optional[pd.DataFrame]:
    return _safe_load(DATASETS.quality_imcv)
