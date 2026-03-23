from __future__ import annotations

import logging
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
_stale_cache: dict[str, bytes] = {}

_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_BASE = 2


def _download_with_retry(url: str) -> bytes:
    last_exc: Exception = RuntimeError("Sin intentos realizados")
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            logger.info("Descargando dataset (intento %d/%d): %s", attempt, _RETRY_ATTEMPTS, url)
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            logger.info("Dataset descargado OK (%d bytes): %s", len(resp.content), url)
            return resp.content
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
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
    """Descarga con retry y fallback a stale cache."""
    try:
        content = _download_with_retry(url)
        _stale_cache[url] = content
        return content
    except requests.exceptions.Timeout:
        if url in _stale_cache:
            logger.warning("Sirviendo stale cache para: %s", url)
            return _stale_cache[url]
        raise HTTPException(status_code=503, detail={"code": "UPSTREAM_TIMEOUT", "url": url})
    except requests.exceptions.ConnectionError as exc:
        if url in _stale_cache:
            logger.warning("Sirviendo stale cache para: %s", url)
            return _stale_cache[url]
        raise HTTPException(status_code=503, detail={"code": "UPSTREAM_UNAVAILABLE", "url": url})
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        if url in _stale_cache:
            logger.warning("Sirviendo stale cache para: %s", url)
            return _stale_cache[url]
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
