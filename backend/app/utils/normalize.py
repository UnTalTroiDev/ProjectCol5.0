from __future__ import annotations

import re
from typing import Any, Optional


def norm_key(s: Any) -> str:
    """
    Convierte un nombre de columna a una clave minuscula sin caracteres especiales,
    util para comparar nombres de columnas con tildes, espacios o encodings rotos.

    Ejemplos:
        'Año'        -> 'ao'   (acento eliminado junto con la n-tilde rota)
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

    # Si parece entero, lo normalizamos con ceros a la izquierda.
    if s.isdigit():
        return s.zfill(width)

    return s


def pick_first_present(df, candidates: list[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None

