from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from cachetools import TTLCache, cached

from .data_loader import (
    load_investment_por_comuna,
    load_mobility_aforos,
    load_safety_homicidios,
    load_safety_lesiones,
)
from ..schemas.dashboard import OverviewResponse
from ..config import DATASETS
from ..utils.normalize import (
    norm_key,
    normalize_code,
    resolve_column,
    resolve_optional_column,
    resolve_year_column,
    latest_year_in_column,
    available_years_in_column,
)

logger = logging.getLogger(__name__)

_SUMMARY_CACHE_TTL_SECONDS = 60 * 20  # 20 minutos.
# maxsize=8 para acomodar distintas combinaciones de año por metrica.
_summary_cache: TTLCache[str, dict] = TTLCache(maxsize=8, ttl=_SUMMARY_CACHE_TTL_SECONDS)


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _compute_mobility_by_comuna(
    df: pd.DataFrame, year: Optional[int] = None
) -> Tuple[int, pd.DataFrame]:
    year_col = resolve_year_column(df)
    comuna_code_col = resolve_column(df, ["CODIGO", "COMUNA", "CODIGO_COMUNA"], label="codigo_comuna")
    comuna_name_col = resolve_optional_column(df, ["NOMBRE_COMUNA", "nombre_comuna"])
    value_col = resolve_column(
        df,
        ["EQUIV_X_15_MIN", "VEHICULO_EQUIVALENTE", "VEHICULO_EQUIVALENTE_HORA"],
        label="vehiculos_equivalentes",
    )

    df = df.copy()
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)

    selected_year = year if year is not None else latest_year_in_column(df, year_col)
    df = df[df[year_col] == selected_year]

    df["COMUNA_CODE_NORM"] = df[comuna_code_col].apply(normalize_code)
    df = df.dropna(subset=["COMUNA_CODE_NORM"])

    agg = df.groupby("COMUNA_CODE_NORM", as_index=False)[value_col].sum()
    agg = agg.rename(columns={value_col: "mobility_equiv_vehicles"})

    if comuna_name_col and comuna_name_col in df.columns:
        names = (
            df[["COMUNA_CODE_NORM", comuna_name_col]]
            .dropna()
            .drop_duplicates(subset=["COMUNA_CODE_NORM"])
            .rename(columns={comuna_name_col: "comuna_name"})
        )
        agg = agg.merge(names, on="COMUNA_CODE_NORM", how="left")

    agg = agg.rename(columns={"COMUNA_CODE_NORM": "comuna_code"})
    return selected_year, agg


def _compute_safety_by_comuna(
    df: pd.DataFrame, year: Optional[int] = None
) -> Tuple[int, pd.DataFrame]:
    date_col = resolve_column(df, ["FECHA_HECHO", "fecha_hecho", "FECHA"], label="fecha_hecho")
    comuna_code_col = resolve_column(
        df, ["CODIGO_COMUNA", "codigo_comuna", "COMUNA_CODE"], label="codigo_comuna"
    )
    value_col = resolve_optional_column(df, ["cantidad", "CANTIDAD"])

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
    df = df.dropna(subset=[date_col])

    if year is not None:
        selected_year = year
    else:
        selected_year = int(df[date_col].max().year)

    df = df[df[date_col].dt.year == selected_year]

    df["COMUNA_CODE_NORM"] = df[comuna_code_col].apply(normalize_code)
    df = df.dropna(subset=["COMUNA_CODE_NORM"])

    if value_col and value_col in df.columns:
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)
        agg = (
            df.groupby("COMUNA_CODE_NORM", as_index=False)[value_col]
            .sum()
            .rename(columns={value_col: "safety_homicides"})
        )
    else:
        agg = (
            df.groupby("COMUNA_CODE_NORM", as_index=False)
            .size()
            .rename(columns={"size": "safety_homicides"})
        )

    agg = agg.rename(columns={"COMUNA_CODE_NORM": "comuna_code"})
    return selected_year, agg


def _compute_investment_by_comuna(
    df: pd.DataFrame, year: Optional[int] = None
) -> Tuple[int, pd.DataFrame]:
    year_col = resolve_year_column(df)
    comuna_code_col = resolve_column(
        df, ["CODIGO_COMUNA", "codigo_comuna", "Comuna"], label="codigo_comuna"
    )
    comuna_name_col = resolve_column(
        df, ["NOMBRE_COMUNA", "NomComuna", "nombre_comuna", "comuna_name"], label="nombre_comuna"
    )
    value_col = resolve_column(df, ["INVERSION", "Inversion", "inversion"], label="inversion")

    df = df.copy()
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
    df[value_col] = (
        df[value_col].astype(str).str.replace(r"[^0-9]", "", regex=True)
    )
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)

    selected_year = year if year is not None else latest_year_in_column(df, year_col)
    df = df[df[year_col] == selected_year]

    df["COMUNA_CODE_NORM"] = df[comuna_code_col].apply(normalize_code)
    df = df.dropna(subset=["COMUNA_CODE_NORM"])

    agg = df.groupby(["COMUNA_CODE_NORM", comuna_name_col], as_index=False)[value_col].sum()
    agg = agg.rename(
        columns={
            "COMUNA_CODE_NORM": "comuna_code",
            value_col: "investment_amount",
            comuna_name_col: "comuna_name",
        }
    )
    return int(selected_year), agg


def _compute_lesiones_by_comuna(
    df: pd.DataFrame, year: Optional[int] = None
) -> Tuple[int, pd.DataFrame]:
    date_col = resolve_column(df, ["FECHA_HECHO", "fecha_hecho", "FECHA"], label="fecha_hecho")
    comuna_code_col = resolve_column(
        df, ["CODIGO_COMUNA", "codigo_comuna", "COMUNA_CODE", "CODIGO"], label="codigo_comuna"
    )
    value_col = resolve_optional_column(df, ["cantidad", "CANTIDAD"])

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
    df = df.dropna(subset=[date_col])

    if year is not None:
        selected_year = year
    else:
        selected_year = int(df[date_col].max().year)

    df = df[df[date_col].dt.year == selected_year]

    df["COMUNA_CODE_NORM"] = df[comuna_code_col].apply(normalize_code)
    df = df.dropna(subset=["COMUNA_CODE_NORM"])

    if value_col and value_col in df.columns:
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)
        agg = (
            df.groupby("COMUNA_CODE_NORM", as_index=False)[value_col]
            .sum()
            .rename(columns={value_col: "lesiones_count"})
        )
    else:
        agg = (
            df.groupby("COMUNA_CODE_NORM", as_index=False)
            .size()
            .rename(columns={"size": "lesiones_count"})
        )

    agg = agg.rename(columns={"COMUNA_CODE_NORM": "comuna_code"})
    return selected_year, agg


def _compute_city_averages(
    mobility: pd.DataFrame,
    safety: pd.DataFrame,
    investment: pd.DataFrame,
    lesiones: Optional[pd.DataFrame] = None,
) -> Dict[str, Dict[str, Any]]:
    def sanitize(v: Any) -> Any:
        return None if pd.isna(v) else float(v)

    avgs: Dict[str, Dict[str, Any]] = {
        "mobility_equiv_vehicles": {
            "value": sanitize(mobility["mobility_equiv_vehicles"].mean()),
            "unit": "vehiculos_equivalentes",
        },
        "safety_homicides": {
            "value": sanitize(safety["safety_homicides"].mean()),
            "unit": "casos",
        },
        "investment_amount": {
            "value": sanitize(investment["investment_amount"].mean()),
            "unit": "COP",
        },
    }
    if lesiones is not None and not lesiones.empty:
        avgs["lesiones_count"] = {
            "value": sanitize(lesiones["lesiones_count"].mean()),
            "unit": "casos",
        }
    return avgs


# ---------------------------------------------------------------------------
# Percentile-based recommendation engine
# ---------------------------------------------------------------------------

def _percentile_rank(series: pd.Series, value: float) -> float:
    """Devuelve el rango percentil (0-100) del valor dentro de la serie."""
    if series.empty or pd.isna(value):
        return 50.0
    return float((series < value).sum() / len(series) * 100)


def _severity_label(percentile: float, higher_is_worse: bool = True) -> str:
    """
    Convierte un percentil a etiqueta de severidad.
    higher_is_worse=True: percentil alto = peor (ej: homicidios).
    higher_is_worse=False: percentil bajo = peor (ej: inversion).
    """
    rank = percentile if higher_is_worse else (100 - percentile)
    if rank >= 80:
        return "critico"
    if rank >= 60:
        return "alto"
    if rank >= 40:
        return "medio"
    return "bajo"


def _build_recommendations(
    comuna_code: str,
    mobility_by: pd.DataFrame,
    safety_by: pd.DataFrame,
    investment_by: pd.DataFrame,
    lesiones_by: Optional[pd.DataFrame],
    selected_mobility: float,
    selected_safety: float,
    selected_investment: float,
    selected_lesiones: Optional[float],
    city_avgs: Dict[str, Any],
) -> List[str]:
    """
    Genera recomendaciones basadas en ranking percentil y correlaciones
    entre metricas, en lugar de simples comparaciones contra el promedio.
    """
    def _fmt(v: float) -> str:
        return f"{v:,.0f}"

    if comuna_code == "ALL":
        top_safety = safety_by.sort_values("safety_homicides", ascending=False).iloc[0]
        top_mob = mobility_by.sort_values("mobility_equiv_vehicles", ascending=False).iloc[0]
        avg_safety = city_avgs["safety_homicides"]["value"]
        avg_mobility = city_avgs["mobility_equiv_vehicles"]["value"]
        return [
            (
                f"La comuna {top_safety['comuna_code']} lidera en homicidios con "
                f"{_fmt(top_safety['safety_homicides'])} casos (promedio ciudad: {_fmt(avg_safety)}). "
                "Focalizar inversion en prevencion y vigilancia territorial."
            ),
            (
                f"Mayor flujo vehicular en comuna {top_mob['comuna_code']}: "
                f"{_fmt(top_mob['mobility_equiv_vehicles'])} vehiculos equivalentes "
                f"(promedio: {_fmt(avg_mobility)}). "
                "Cruzar con seguridad para priorizar infraestructura vial."
            ),
            "Identificar comunas con alta movilidad y alta criminalidad para intervenciones integrales.",
        ]

    if any(pd.isna(v) for v in [selected_safety, selected_mobility, selected_investment] if v is not None):
        return [
            "Datos insuficientes para esta comuna en uno o mas indicadores.",
            "Verificar correspondencia entre codigos de comuna en los datasets.",
            "Usar la vista global (ALL) para comparar el panorama de ciudad.",
        ]

    pct_safety = _percentile_rank(safety_by["safety_homicides"], selected_safety)
    pct_mobility = _percentile_rank(mobility_by["mobility_equiv_vehicles"], selected_mobility)
    pct_investment = _percentile_rank(investment_by["investment_amount"], selected_investment)

    sev_safety = _severity_label(pct_safety, higher_is_worse=True)
    sev_mobility = _severity_label(pct_mobility, higher_is_worse=True)
    sev_investment = _severity_label(pct_investment, higher_is_worse=False)

    recs: List[str] = []

    # Recomendacion de seguridad con percentil.
    recs.append(
        f"Seguridad [{sev_safety.upper()}]: {_fmt(selected_safety)} homicidios "
        f"— percentil {pct_safety:.0f} entre las comunas "
        f"(promedio ciudad: {_fmt(city_avgs['safety_homicides']['value'])})."
    )

    # Recomendacion de inversion cruzada con seguridad.
    if sev_safety in ("critico", "alto") and sev_investment in ("bajo", "medio"):
        gap = city_avgs["investment_amount"]["value"] - selected_investment
        recs.append(
            f"Brecha de inversion [{sev_investment.upper()}]: COP {_fmt(selected_investment)} "
            f"— percentil {pct_investment:.0f}. Brecha vs promedio: COP {_fmt(gap)}. "
            "Priorizar asignacion presupuestal para reducir criminalidad."
        )
    else:
        recs.append(
            f"Inversion [{sev_investment.upper()}]: COP {_fmt(selected_investment)} "
            f"— percentil {pct_investment:.0f} "
            f"(promedio ciudad: COP {_fmt(city_avgs['investment_amount']['value'])})."
        )

    # Recomendacion de movilidad.
    recs.append(
        f"Movilidad [{sev_mobility.upper()}]: {_fmt(selected_mobility)} vehiculos equivalentes "
        f"— percentil {pct_mobility:.0f} "
        f"(promedio ciudad: {_fmt(city_avgs['mobility_equiv_vehicles']['value'])})."
    )

    # Correlacion movilidad-seguridad.
    if sev_mobility in ("critico", "alto") and sev_safety in ("critico", "alto"):
        recs.append(
            "ALERTA: alto flujo vehicular y alta criminalidad simultaneos. "
            "Implementar control de acceso, camara de vigilancia y senal preventiva."
        )

    # Lesiones si disponibles.
    if selected_lesiones is not None and lesiones_by is not None and not lesiones_by.empty:
        pct_lesiones = _percentile_rank(lesiones_by["lesiones_count"], selected_lesiones)
        sev_les = _severity_label(pct_lesiones, higher_is_worse=True)
        recs.append(
            f"Lesiones comunes [{sev_les.upper()}]: {_fmt(selected_lesiones)} casos "
            f"— percentil {pct_lesiones:.0f}. "
            + (
                "Reforzar presencia policial y programas de convivencia."
                if sev_les in ("critico", "alto") else
                "Mantener monitoreo y acciones preventivas."
            )
        )

    return recs


# ---------------------------------------------------------------------------
# Summary cache (raw DataFrames, cacheado por "año" o "latest")
# ---------------------------------------------------------------------------

@cached(_summary_cache)
def _get_all_summaries(year_key: str = "latest") -> Dict[str, Any]:
    """
    Carga y cachea los DataFrames crudos de todos los datasets.
    year_key es "latest" o un string del año (ej: "2022") para que
    TTLCache lo use como clave.
    """
    logger.info("Cache miss: cargando todos los datasets desde MEData (year_key=%s)...", year_key)
    t0 = time.monotonic()

    year: Optional[int] = None if year_key == "latest" else int(year_key)

    mobility_df = load_mobility_aforos()
    safety_df = load_safety_homicidios()
    investment_df = load_investment_por_comuna()
    lesiones_df = load_safety_lesiones()

    mobility_latest_year, mobility_by = _compute_mobility_by_comuna(mobility_df, year=year)
    safety_latest_year, safety_by = _compute_safety_by_comuna(safety_df, year=year)
    investment_latest_year, investment_by = _compute_investment_by_comuna(investment_df, year=year)

    lesiones_result = None
    if lesiones_df is not None:
        try:
            lesiones_year, lesiones_by = _compute_lesiones_by_comuna(lesiones_df, year=year)
            lesiones_result = {"latest_year": lesiones_year, "by": lesiones_by}
        except Exception as exc:
            logger.warning("No se pudo computar lesiones: %s", exc)

    elapsed = time.monotonic() - t0
    logger.info("_get_all_summaries completado en %.2fs", elapsed)

    return {
        "mobility": {"latest_year": mobility_latest_year, "by": mobility_by},
        "safety": {"latest_year": safety_latest_year, "by": safety_by},
        "investment": {"latest_year": investment_latest_year, "by": investment_by},
        "lesiones": lesiones_result,
    }


def _get_available_years() -> Dict[str, List[int]]:
    """Devuelve los años disponibles por metrica sin filtrar."""
    mobility_df = load_mobility_aforos()
    safety_df = load_safety_homicidios()
    investment_df = load_investment_por_comuna()

    try:
        mob_year_col = resolve_year_column(mobility_df)
        mob_years = available_years_in_column(mobility_df, mob_year_col)
    except Exception:
        mob_years = []

    try:
        saf_date_col = resolve_column(
            safety_df, ["FECHA_HECHO", "fecha_hecho", "FECHA"], label="fecha_hecho"
        )
        safety_df = safety_df.copy()
        safety_df[saf_date_col] = pd.to_datetime(safety_df[saf_date_col], errors="coerce", dayfirst=True)
        saf_years = sorted(safety_df[saf_date_col].dt.year.dropna().unique().astype(int).tolist())
    except Exception:
        saf_years = []

    try:
        inv_year_col = resolve_year_column(investment_df)
        inv_years = available_years_in_column(investment_df, inv_year_col)
    except Exception:
        inv_years = []

    return {
        "mobility": mob_years,
        "safety": saf_years,
        "investment": inv_years,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_territory_comunas() -> List[Dict[str, Any]]:
    inv = _get_all_summaries()["investment"]
    inv_agg = inv["by"].sort_values("comuna_code")
    return [
        {
            "code": r["comuna_code"],
            "name": r.get("comuna_name") if isinstance(r.get("comuna_name"), str) else None,
        }
        for _, r in inv_agg.iterrows()
    ]


def get_dashboard_overview(
    comuna_code: str, year: Optional[int] = None
) -> OverviewResponse:
    logger.info("get_dashboard_overview: comuna_code=%r year=%r", comuna_code, year)

    year_key = "latest" if year is None else str(year)
    summaries = _get_all_summaries(year_key=year_key)

    mobility_latest_year = summaries["mobility"]["latest_year"]
    safety_latest_year = summaries["safety"]["latest_year"]
    investment_latest_year = summaries["investment"]["latest_year"]
    mobility_by = summaries["mobility"]["by"]
    safety_by = summaries["safety"]["by"]
    investment_by = summaries["investment"]["by"]
    lesiones_summary = summaries.get("lesiones")
    lesiones_by: Optional[pd.DataFrame] = lesiones_summary["by"] if lesiones_summary else None

    comuna_code = "ALL" if not comuna_code else comuna_code
    if comuna_code != "ALL":
        norm = normalize_code(comuna_code)
        comuna_code = norm if norm else "ALL"

    comuna_name_lookup = (
        investment_by[["comuna_code", "comuna_name"]]
        .drop_duplicates()
        .set_index("comuna_code")["comuna_name"]
        .to_dict()
    )

    city_avgs = _compute_city_averages(mobility_by, safety_by, investment_by, lesiones_by)

    def value_for(df: pd.DataFrame, col: str) -> float:
        if comuna_code == "ALL":
            return city_avgs[col]["value"]
        row = df[df["comuna_code"] == comuna_code]
        return float("nan") if row.empty else float(row.iloc[0][col])

    selected_mobility = value_for(mobility_by, "mobility_equiv_vehicles")
    selected_safety = value_for(safety_by, "safety_homicides")
    selected_investment = value_for(investment_by, "investment_amount")
    selected_lesiones: Optional[float] = None
    if lesiones_by is not None and not lesiones_by.empty:
        if comuna_code == "ALL":
            selected_lesiones = city_avgs.get("lesiones_count", {}).get("value")
        else:
            row = lesiones_by[lesiones_by["comuna_code"] == comuna_code]
            selected_lesiones = float(row.iloc[0]["lesiones_count"]) if not row.empty else None

    recs = _build_recommendations(
        comuna_code=comuna_code,
        mobility_by=mobility_by,
        safety_by=safety_by,
        investment_by=investment_by,
        lesiones_by=lesiones_by,
        selected_mobility=selected_mobility,
        selected_safety=selected_safety,
        selected_investment=selected_investment,
        selected_lesiones=selected_lesiones,
        city_avgs=city_avgs,
    )

    selected_name = None if comuna_code == "ALL" else comuna_name_lookup.get(comuna_code)

    metrics: Dict[str, Any] = {
        "mobility_equiv_vehicles": {
            "value": None if pd.isna(selected_mobility) else float(selected_mobility),
            "unit": "vehiculos_equivalentes",
        },
        "safety_homicides": {
            "value": None if pd.isna(selected_safety) else float(selected_safety),
            "unit": "casos",
        },
        "investment_amount": {
            "value": None if pd.isna(selected_investment) else float(selected_investment),
            "unit": "COP",
        },
    }
    if selected_lesiones is not None:
        metrics["lesiones_count"] = {"value": selected_lesiones, "unit": "casos"}

    meta: Dict[str, Any] = {
        "mobility_latest_year": mobility_latest_year,
        "safety_latest_year": safety_latest_year,
        "investment_latest_year": investment_latest_year,
        "dataset_mobility_url": DATASETS.mobility_aforos_vehiculares,
        "dataset_safety_url": DATASETS.safety_homicidios,
        "dataset_investment_url": DATASETS.investment_inversion_por_comuna_2019,
    }
    if lesiones_summary:
        meta["lesiones_latest_year"] = lesiones_summary["latest_year"]
        meta["dataset_lesiones_url"] = DATASETS.safety_lesiones_comunes

    return OverviewResponse(
        meta=meta,
        selected={"comuna_code": comuna_code, "comuna_name": selected_name},
        metrics=metrics,  # type: ignore[arg-type]
        city_averages=city_avgs,  # type: ignore[arg-type]
        recommendations=recs,
        mobility_by_comuna=(
            mobility_by.sort_values("mobility_equiv_vehicles", ascending=False)
            .head(10)
            .to_dict(orient="records")
        ),
        safety_by_comuna=(
            safety_by.sort_values("safety_homicides", ascending=False)
            .head(10)
            .to_dict(orient="records")
        ),
    )


def get_dashboard_trends(
    metric: str, comuna_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Devuelve serie temporal anual para una metrica dada.

    Args:
        metric: 'mobility' | 'safety' | 'investment'
        comuna_code: codigo de comuna o None para toda la ciudad.

    Returns:
        Dict con 'metric', 'comuna_code', 'series': [{'year': int, 'value': float}]
    """
    logger.info("get_dashboard_trends: metric=%r comuna_code=%r", metric, comuna_code)

    mobility_df = load_mobility_aforos()
    safety_df = load_safety_homicidios()
    investment_df = load_investment_por_comuna()

    available = _get_available_years()

    norm_code: Optional[str] = None
    if comuna_code and comuna_code.upper() != "ALL":
        norm_code = normalize_code(comuna_code)

    series: List[Dict[str, Any]] = []

    if metric == "mobility":
        years = available.get("mobility", [])
        for yr in years:
            try:
                _, agg = _compute_mobility_by_comuna(mobility_df, year=yr)
                if norm_code:
                    row = agg[agg["comuna_code"] == norm_code]
                    val = float(row.iloc[0]["mobility_equiv_vehicles"]) if not row.empty else None
                else:
                    val = float(agg["mobility_equiv_vehicles"].sum())
                series.append({"year": yr, "value": val})
            except Exception as exc:
                logger.warning("Trends mobility año %d: %s", yr, exc)

    elif metric == "safety":
        years = available.get("safety", [])
        for yr in years:
            try:
                _, agg = _compute_safety_by_comuna(safety_df, year=yr)
                if norm_code:
                    row = agg[agg["comuna_code"] == norm_code]
                    val = float(row.iloc[0]["safety_homicides"]) if not row.empty else None
                else:
                    val = float(agg["safety_homicides"].sum())
                series.append({"year": yr, "value": val})
            except Exception as exc:
                logger.warning("Trends safety año %d: %s", yr, exc)

    elif metric == "investment":
        years = available.get("investment", [])
        for yr in years:
            try:
                _, agg = _compute_investment_by_comuna(investment_df, year=yr)
                if norm_code:
                    row = agg[agg["comuna_code"] == norm_code]
                    val = float(row.iloc[0]["investment_amount"]) if not row.empty else None
                else:
                    val = float(agg["investment_amount"].sum())
                series.append({"year": yr, "value": val})
            except Exception as exc:
                logger.warning("Trends investment año %d: %s", yr, exc)

    else:
        raise ValueError(f"Metrica desconocida: '{metric}'. Valores validos: mobility, safety, investment.")

    return {
        "metric": metric,
        "comuna_code": norm_code or "ALL",
        "unit": {"mobility": "vehiculos_equivalentes", "safety": "casos", "investment": "COP"}.get(metric, ""),
        "series": series,
        "available_years": available.get(metric, []),
    }


def get_crime_stats(
    comuna_code: Optional[str] = None, year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Devuelve estadisticas combinadas de criminalidad (homicidios + lesiones)
    para una comuna o toda la ciudad.
    """
    logger.info("get_crime_stats: comuna_code=%r year=%r", comuna_code, year)

    year_key = "latest" if year is None else str(year)
    summaries = _get_all_summaries(year_key=year_key)

    safety_by = summaries["safety"]["by"]
    safety_year = summaries["safety"]["latest_year"]
    lesiones_summary = summaries.get("lesiones")
    lesiones_by = lesiones_summary["by"] if lesiones_summary else None
    lesiones_year = lesiones_summary["latest_year"] if lesiones_summary else None

    norm_code: Optional[str] = None
    if comuna_code and comuna_code.upper() != "ALL":
        norm_code = normalize_code(comuna_code)

    def _extract(df: Optional[pd.DataFrame], col: str) -> Optional[float]:
        if df is None or df.empty:
            return None
        if norm_code:
            row = df[df["comuna_code"] == norm_code]
            return float(row.iloc[0][col]) if not row.empty else None
        return float(df[col].sum())

    homicidios = _extract(safety_by, "safety_homicides")
    lesiones = _extract(lesiones_by, "lesiones_count") if lesiones_by is not None else None

    # Top 10 por cada metrica.
    top_homicidios = (
        safety_by.sort_values("safety_homicides", ascending=False)
        .head(10)
        .to_dict(orient="records")
    )
    top_lesiones = (
        lesiones_by.sort_values("lesiones_count", ascending=False)
        .head(10)
        .to_dict(orient="records")
        if lesiones_by is not None and not lesiones_by.empty
        else []
    )

    return {
        "comuna_code": norm_code or "ALL",
        "year": safety_year,
        "homicidios": {"value": homicidios, "unit": "casos", "year": safety_year},
        "lesiones_comunes": {
            "value": lesiones,
            "unit": "casos",
            "year": lesiones_year,
            "available": lesiones is not None,
        },
        "top_homicidios_by_comuna": top_homicidios,
        "top_lesiones_by_comuna": top_lesiones,
    }
