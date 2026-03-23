from __future__ import annotations

import re
from typing import Any, List, Optional

import pandas as pd


def norm_key(s: Any) -> str:
    """
    Convierte un nombre de columna a clave minuscula sin caracteres especiales.

    Ejemplos:
        'Año'        -> 'ao'
        'FECHA_HECHO'-> 'fechahecho'
        'Código'     -> 'cdigo'
    """
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def normalize_code(value: Any, width: int = 2) -> Optional[str]:
    """
    Normaliza codigos de comuna/barrio para uniones consistentes.
    Para numeros, rellena con ceros a la izquierda (ej: 1 -> '01').
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s.isdigit():
        return s.zfill(width)
    return s


def pick_first_present(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def resolve_column(df: pd.DataFrame, candidates: List[str], label: str = "columna") -> str:
    """
    Resuelve el nombre real de una columna buscando primero por nombre exacto
    y luego por clave normalizada (norm_key). Centraliza la logica dispersa de
    _pick_col / cols_map.get() en los servicios de agregacion.

    Raises:
        ValueError: si ninguna variante se encontro.
    """
    # 1. Busqueda exacta.
    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    # 2. Busqueda normalizada.
    norm_to_real = {norm_key(c): c for c in df.columns}
    for candidate in candidates:
        real = norm_to_real.get(norm_key(candidate))
        if real is not None:
            return real

    raise ValueError(
        f"No se encontro la columna '{label}' entre las variantes {candidates}. "
        f"Columnas disponibles: {list(df.columns)[:30]}"
    )


def resolve_optional_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Igual que resolve_column pero devuelve None si no existe."""
    try:
        return resolve_column(df, candidates)
    except ValueError:
        return None


def resolve_year_column(df: pd.DataFrame) -> str:
    """
    Detecta la columna de año en DataFrames de MEData, que puede venir con
    distintos nombres y encodings rotos (ANO_ENTERO, AÑO, vigencia, etc.).
    """
    return resolve_column(
        df,
        [
            "ANO_ENTERO", "AÑO_ENTERO", "ANO", "AÑO", "YEAR",
            "vigencia", "VIGENCIA", "anio", "ANIO",
            "ano_entero", "año_entero", "año",
        ],
        label="año/vigencia",
    )


def latest_year_in_column(df: pd.DataFrame, year_col: str) -> int:
    """Extrae el año mas reciente de una columna numerica de años."""
    years = pd.to_numeric(df[year_col], errors="coerce").dropna()
    if years.empty:
        raise ValueError(
            f"La columna '{year_col}' no contiene valores numericos de año validos."
        )
    return int(years.max())


def available_years_in_column(df: pd.DataFrame, year_col: str) -> List[int]:
    """Devuelve lista ordenada de años disponibles en la columna dada."""
    years = pd.to_numeric(df[year_col], errors="coerce").dropna().unique()
    return sorted(int(y) for y in years)
