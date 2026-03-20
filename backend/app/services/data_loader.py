from __future__ import annotations

import logging
from io import BytesIO
from typing import Optional

import pandas as pd
import requests
from cachetools import TTLCache, cached
from fastapi import HTTPException

from ..config import CSV_CACHE_TTL_SECONDS, DATASETS

logger = logging.getLogger(__name__)

_byte_cache: TTLCache[str, bytes] = TTLCache(maxsize=12, ttl=CSV_CACHE_TTL_SECONDS)


@cached(_byte_cache)
def fetch_url_bytes(url: str) -> bytes:
    """
    Descarga el CSV desde `url`. Lanza HTTPException 503 si MEData no responde
    o devuelve un status de error, de modo que el cliente recibe un mensaje
    claro en lugar de un traceback 500.
    """
    try:
        logger.info("Descargando dataset: %s", url)
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        logger.info("Dataset descargado OK (%d bytes): %s", len(resp.content), url)
        return resp.content
    except requests.exceptions.Timeout:
        logger.error("Timeout al descargar dataset: %s", url)
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
    Lee CSVs sin asumir separador/encoding, intentando ser robusto con los datasets del portal.
    Lanza HTTPException 502 si el contenido no puede parsearse como CSV valido.
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


def load_dataset(name: str) -> Optional[pd.DataFrame]:
    """
    Carga segun nombre interno (usado para debug / extensiones).
    """
    if name == "mobility":
        return load_mobility_aforos()
    if name == "safety":
        return load_safety_homicidios()
    if name == "investment":
        return load_investment_por_comuna()
    return None

