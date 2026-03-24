"""
Format MedCity Dashboard data into WhatsApp-friendly daily newsletter text.

WhatsApp formatting: *bold*, _italic_, ~strikethrough~, ```code```.
Max message length: 4096 characters.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096


def _fmt(v: float | int | None) -> str:
    if v is None:
        return "N/D"
    return f"{v:,.0f}"


def format_daily_newsletter(
    overview: Dict[str, Any],
    security: Dict[str, Any],
    city_summary: Dict[str, Any],
) -> str:
    """
    Build a single WhatsApp newsletter message from aggregated data.

    Args:
        overview: Result of get_dashboard_overview(comuna_code="ALL").model_dump()
        security: Result of get_criminalidad_consolidada()
        city_summary: Result of city_summary() endpoint
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%d/%m/%Y")

    lines: List[str] = []

    # ── Header ────────────────────────────────────────────────────────────
    lines.append(f"*MedCity Dashboard*")
    lines.append(f"_Newsletter diario — {date_str}_")
    lines.append("")

    # ── KPIs from overview ────────────────────────────────────────────────
    metrics = overview.get("metrics", {})
    city_avgs = overview.get("city_averages", {})

    mobility = metrics.get("mobility_equiv_vehicles", {})
    safety = metrics.get("safety_homicides", {})
    investment = metrics.get("investment_amount", {})

    lines.append("*Indicadores clave de Medellin:*")
    lines.append("")

    if mobility.get("value") is not None:
        lines.append(f"Flujo vehicular: *{_fmt(mobility['value'])}* vehiculos equiv.")
    if safety.get("value") is not None:
        lines.append(f"Homicidios: *{_fmt(safety['value'])}* casos")
    if investment.get("value") is not None:
        lines.append(f"Inversion publica: *COP {_fmt(investment['value'])}*")

    lesiones = metrics.get("lesiones_count", {})
    if lesiones.get("value") is not None:
        lines.append(f"Lesiones comunes: *{_fmt(lesiones['value'])}* casos")

    # ── Recommendations ───────────────────────────────────────────────────
    recs = overview.get("recommendations", [])
    if recs:
        lines.append("")
        lines.append("*Analisis del territorio:*")
        for i, rec in enumerate(recs[:3], 1):
            lines.append(f"{i}. {rec}")

    # ── Top comunas by safety ─────────────────────────────────────────────
    safety_ranking = overview.get("safety_by_comuna", [])
    if safety_ranking:
        lines.append("")
        lines.append("*Comunas con mas homicidios:*")
        for item in safety_ranking[:5]:
            code = item.get("comuna_code", "?")
            name = item.get("comuna_name", "")
            val = item.get("safety_homicides", 0)
            label = f"Comuna {code}" + (f" ({name})" if name else "")
            lines.append(f"  - {label}: {_fmt(val)}")

    # ── Crime highlights ──────────────────────────────────────────────────
    if security.get("available"):
        by_type = security.get("by_type", [])
        if by_type:
            lines.append("")
            lines.append("*Criminalidad consolidada:*")
            for item in by_type[:5]:
                lines.append(f"  - {item['crime_type']}: {_fmt(item['total'])}")

    # ── Domain availability ───────────────────────────────────────────────
    avail = city_summary.get("available_domains", 0)
    total = city_summary.get("total_domains", 0)
    if total > 0:
        lines.append("")
        lines.append(f"_Estado de datos: {avail}/{total} dominios disponibles_")

    # ── Footer ────────────────────────────────────────────────────────────
    lines.append("")
    lines.append("_Fuente: MEData — Datos abiertos de Medellin_")
    lines.append("_MedCity Dashboard v0.4.0_")

    msg = "\n".join(lines)
    if len(msg) > MAX_MESSAGE_LENGTH:
        msg = msg[: MAX_MESSAGE_LENGTH - 3] + "..."
    return msg


def format_comuna_newsletter(
    overview: Dict[str, Any],
    comuna_code: str,
) -> str:
    """
    Build a WhatsApp message with insights for a specific comuna.

    Args:
        overview: Result of get_dashboard_overview(comuna_code=code).model_dump()
        comuna_code: The target comuna code.
    """
    selected = overview.get("selected", {})
    name = selected.get("comuna_name") or f"Comuna {comuna_code}"
    metrics = overview.get("metrics", {})
    recs = overview.get("recommendations", [])

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%d/%m/%Y")

    lines: List[str] = [
        f"*MedCity Dashboard*",
        f"_Reporte {name} — {date_str}_",
        "",
    ]

    # KPIs
    for key, label in [
        ("mobility_equiv_vehicles", "Flujo vehicular"),
        ("safety_homicides", "Homicidios"),
        ("investment_amount", "Inversion publica"),
        ("lesiones_count", "Lesiones comunes"),
    ]:
        m = metrics.get(key, {})
        val = m.get("value")
        if val is not None:
            unit_prefix = "COP " if m.get("unit") == "COP" else ""
            lines.append(f"{label}: *{unit_prefix}{_fmt(val)}*")

    # Recommendations
    if recs:
        lines.append("")
        lines.append("*Analisis:*")
        for i, rec in enumerate(recs[:5], 1):
            lines.append(f"{i}. {rec}")

    lines.append("")
    lines.append("_Fuente: MEData — Datos abiertos de Medellin_")

    msg = "\n".join(lines)
    if len(msg) > MAX_MESSAGE_LENGTH:
        msg = msg[: MAX_MESSAGE_LENGTH - 3] + "..."
    return msg
