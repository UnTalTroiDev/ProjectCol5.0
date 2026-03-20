from __future__ import annotations

from typing import Any, Optional


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

