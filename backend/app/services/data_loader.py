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

# Cache principal: TTL de 6 horas.
_byte_cache: TTLCache[str, bytes] = TTLCache(maxsize=16, ttl=CSV_CACHE_TTL_SECONDS)

# Cache "stale": TTL de 24 horas. Sirve datos anteriores cuando MEData no responde.
# Se actualiza cada vez que una descarga fresca tiene exito.
_stale_cache: dict[str, bytes] = {}

_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_BASE = 2  # segundos; espera 2s, 4s, 8s entre intentos.


def _download_with_retry(url: str) -> bytes:
    """
    Descarga una URL con reintentos exponenciales.
    Lanza la ultima excepcion si todos los intentos fallan.
    """
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
                logger.warning(
                    "Error de red en intento %d/%d para %s: %s. Reintentando en %ds...",
                    attempt, _RETRY_ATTEMPTS, url, exc, wait,
                )
                time.sleep(wait)
        except requests.exceptions.HTTPError as exc:
            # Errores HTTP no son transitorios; no reintentamos.
            raise exc
    raise last_exc


@cached(_byte_cache)
def fetch_url_bytes(url: str) -> bytes:
    """
    Descarga el CSV desde `url` con reintentos y fallback a cache stale.

    - Intenta hasta 3 veces con backoff exponencial ante errores de red.
    - Si MEData sigue sin responder, sirve los ultimos bytes exitosos (stale cache).
    - Lanza HTTPException 503/502 solo si no hay datos previos disponibles.
    """
    try:
        content = _download_with_retry(url)
        _stale_cache[url] = content  # Actualizar cache stale con datos frescos.
        return content
    except requests.exceptions.Timeout:
        logger.error("Timeout definitivo al descargar dataset: %s", url)
        if url in _stale_cache:
            logger.warning("Sirviendo datos del cache stale para: %s", url)
            return _stale_cache[url]
        raise HTTPException(
            status_code=503,
            detail={
                "code": "UPSTREAM_TIMEOUT",
                "message": "El portal MEData no respondio a tiempo. Intente de nuevo en unos minutos.",
                "url": url,
            },
        )
    except requests.exceptions.ConnectionError as exc:
        logger.error("Error de conexion al descargar dataset %s: %s", url, exc)
        if url in _stale_cache:
            logger.warning("Sirviendo datos del cache stale para: %s", url)
            return _stale_cache[url]
        raise HTTPException(
            status_code=503,
            detail={
                "code": "UPSTREAM_UNAVAILABLE",
                "message": "No se pudo conectar al portal MEData. Verifique conectividad o intente mas tarde.",
                "url": url,
            },
        )
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        logger.error("MEData devolvio HTTP %s para %s", status, url)
        if url in _stale_cache:
            logger.warning("Sirviendo datos del cache stale para: %s", url)
            return _stale_cache[url]
        raise HTTPException(
            status_code=502,
            detail={
                "code": "UPSTREAM_HTTP_ERROR",
                "message": f"MEData devolvio un error HTTP {status} al descargar el dataset.",
                "url": url,
            },
        )


def read_csv_from_bytes(content: bytes, source_url: str = "") -> pd.DataFrame:
    """
    Lee CSVs sin asumir separador/encoding, intentando ser robusto con los
    datasets del portal. Lanza HTTPException 502 si el contenido no es CSV valido.
    """
    bio = BytesIO(content)
    try:
        return pd.read_csv(bio, sep=None, engine="python", encoding="utf-8")
    except UnicodeDecodeError:
        bio = BytesIO(content)
        try:
            return pd.read_csv(bio, sep=None, engine="python", encoding="latin1")
        except Exception as exc:
            logger.error("No se pudo parsear CSV (latin1) de %s: %s", source_url, exc)
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "UPSTREAM_PARSE_ERROR",
                    "message": "El dataset de MEData no pudo parsearse como CSV valido.",
                    "url": source_url,
                },
            )
    except Exception as exc:
        logger.error("No se pudo parsear CSV de %s: %s", source_url, exc)
        raise HTTPException(
            status_code=502,
            detail={
                "code": "UPSTREAM_PARSE_ERROR",
                "message": "El dataset de MEData no pudo parsearse como CSV valido.",
                "url": source_url,
            },
        )


def load_mobility_aforos() -> pd.DataFrame:
    url = DATASETS.mobility_aforos_vehiculares
    return read_csv_from_bytes(fetch_url_bytes(url), source_url=url)


def load_safety_homicidios() -> pd.DataFrame:
    url = DATASETS.safety_homicidios
    return read_csv_from_bytes(fetch_url_bytes(url), source_url=url)


def load_investment_por_comuna() -> pd.DataFrame:
    url = DATASETS.investment_inversion_por_comuna_2019
    return read_csv_from_bytes(fetch_url_bytes(url), source_url=url)


def load_safety_lesiones() -> Optional[pd.DataFrame]:
    """
    Carga el dataset de Lesiones Comunes de MEData.
    Devuelve None si el dataset no esta configurado o no esta disponible.
    """
    url = DATASETS.safety_lesiones_comunes
    if not url:
        return None
    try:
        return read_csv_from_bytes(fetch_url_bytes(url), source_url=url)
    except HTTPException:
        logger.warning("Dataset de lesiones no disponible: %s", url)
        return None


def load_dataset(name: str) -> Optional[pd.DataFrame]:
    """Carga segun nombre interno (usado para debug / extensiones)."""
    if name == "mobility":
        return load_mobility_aforos()
    if name == "safety":
        return load_safety_homicidios()
    if name == "investment":
        return load_investment_por_comuna()
    if name == "lesiones":
        return load_safety_lesiones()
    return None
