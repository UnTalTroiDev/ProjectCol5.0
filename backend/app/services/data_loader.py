from __future__ import annotations

from io import BytesIO
from typing import Optional

import pandas as pd
import requests
from cachetools import TTLCache, cached

from ..config import CSV_CACHE_TTL_SECONDS, DATASETS


_byte_cache: TTLCache[str, bytes] = TTLCache(maxsize=12, ttl=CSV_CACHE_TTL_SECONDS)


@cached(_byte_cache)
def fetch_url_bytes(url: str) -> bytes:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.content


def read_csv_from_bytes(content: bytes) -> pd.DataFrame:
    """
    Lee CSVs sin asumir separador/encoding, intentando ser robusto con los datasets del portal.
    """
    # Usamos engine='python' con sep=None para que autodetecte separador.
    # Encoding: probamos utf-8 y luego latin1.
    bio = BytesIO(content)
    try:
        return pd.read_csv(bio, sep=None, engine="python", encoding="utf-8")
    except UnicodeDecodeError:
        bio = BytesIO(content)
        return pd.read_csv(bio, sep=None, engine="python", encoding="latin1")


def load_mobility_aforos() -> pd.DataFrame:
    content = fetch_url_bytes(DATASETS.mobility_aforos_vehiculares)
    return read_csv_from_bytes(content)


def load_safety_homicidios() -> pd.DataFrame:
    content = fetch_url_bytes(DATASETS.safety_homicidios)
    return read_csv_from_bytes(content)


def load_investment_por_comuna() -> pd.DataFrame:
    content = fetch_url_bytes(DATASETS.investment_inversion_por_comuna_2019)
    return read_csv_from_bytes(content)


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

