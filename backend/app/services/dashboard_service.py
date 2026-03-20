from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandas as pd
from cachetools import TTLCache, cached

from .data_loader import load_investment_por_comuna, load_mobility_aforos, load_safety_homicidios
from ..schemas.dashboard import OverviewResponse
from ..config import DATASETS
from ..utils.normalize import normalize_code


_SUMMARY_CACHE_TTL_SECONDS = 60 * 20  # 20 minutos: suficiente para demo.
_summary_cache: TTLCache[str, dict] = TTLCache(maxsize=2, ttl=_SUMMARY_CACHE_TTL_SECONDS)


def _pick_col(df: pd.DataFrame, candidates: List[str]) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    raise ValueError(f"No se encontro ninguna columna entre {candidates}. Columnas: {list(df.columns)[:30]}")


def _latest_year_from_column(df: pd.DataFrame, year_col: str) -> int:
    years = pd.to_numeric(df[year_col], errors="coerce").dropna()
    if years.empty:
        # fallback: intenta parsear datetime en columnas comunes.
        raise ValueError(f"No pude determinar ultimo año desde columna {year_col}")
    return int(years.max())


def _compute_mobility_by_comuna(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    import re

    def norm_key(s: Any) -> str:
        return re.sub(r"[^a-z0-9]", "", str(s).lower())

    year_col = None
    for c in df.columns:
        nk = norm_key(c)
        if nk == "aoentero" or nk.endswith("entero"):
            year_col = c
            break
    if not year_col:
        for c in df.columns:
            nk = norm_key(c)
            if nk == "ao":
                year_col = c
                break
    if not year_col:
        # fallback: intenta usar ANO_ENTERO/ANO si vienen bien nombrados.
        if "ANO_ENTERO" in df.columns:
            year_col = "ANO_ENTERO"
        elif "ANO" in df.columns:
            year_col = "ANO"
        else:
            year_col = _pick_col(df, ["FECHA_HORA", "FECHA", "FECHA_HECHO"])

    comuna_code_col = _pick_col(df, ["CODIGO", "COMUNA", "CODIGO_COMUNA"])
    comuna_name_col = "NOMBRE_COMUNA" if "NOMBRE_COMUNA" in df.columns else None

    value_col = "EQUIV_X_15_MIN" if "EQUIV_X_15_MIN" in df.columns else _pick_col(df, ["EQUIV_X_15_MIN", "VEHICULO_EQUIVALENTE", "VEHICULO_EQUIVALENTE_HORA"])

    df = df.copy()
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)
    latest_year = _latest_year_from_column(df, year_col)
    df = df[df[year_col] == latest_year]

    df["COMUNA_CODE_NORM"] = df[comuna_code_col].apply(lambda v: normalize_code(v))
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
    return latest_year, agg


def _compute_safety_by_comuna(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    import re

    def norm_key(s: Any) -> str:
        return re.sub(r"[^a-z0-9]", "", str(s).lower())

    cols_map = {norm_key(c): c for c in df.columns}

    # Esperado en el CSV: fecha_hecho, codigo_comuna, cantidad.
    date_col = cols_map.get("fechhecho") or cols_map.get("fechhecho") or None
    if not date_col:
        date_col = None
        for c in df.columns:
            nk = norm_key(c)
            if nk.endswith("hecho") and nk.startswith("fech"):
                date_col = c
                break
    if not date_col:
        date_col = _pick_col(df, ["FECHA_HECHO", "fecha_hecho", "FECHA"])

    comuna_code_col = cols_map.get("codigocomuna")
    if not comuna_code_col:
        comuna_code_col = _pick_col(df, ["CODIGO_COMUNA", "codigo_comuna", "COMUNA_CODE"])

    value_col = cols_map.get("cantidad")

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
    df = df.dropna(subset=[date_col])

    latest_date = df[date_col].max()
    latest_year = int(latest_date.year)
    df = df[df[date_col].dt.year == latest_year]

    df["COMUNA_CODE_NORM"] = df[comuna_code_col].apply(lambda v: normalize_code(v))
    df = df.dropna(subset=["COMUNA_CODE_NORM"])

    if value_col and value_col in df.columns:
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)
        agg = df.groupby("COMUNA_CODE_NORM", as_index=False)[value_col].sum().rename(columns={value_col: "safety_homicides"})
    else:
        # Si no existe una columna de cantidad, usamos conteo de filas.
        agg = df.groupby("COMUNA_CODE_NORM", as_index=False).size().rename(columns={"size": "safety_homicides"})

    agg = agg.rename(columns={"COMUNA_CODE_NORM": "comuna_code"})
    return latest_year, agg


def _compute_investment_by_comuna(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    import re

    def norm_key(s: Any) -> str:
        # Normaliza nombres de columnas (ej: 'Año' puede venir como 'A�o' por encoding).
        return re.sub(r"[^a-z0-9]", "", str(s).lower())

    cols_map = {norm_key(c): c for c in df.columns}

    year_col = cols_map.get("vigencia")
    if not year_col:
        for c in df.columns:
            nk = norm_key(c)
            if nk in {"anio", "ano", "year"}:
                year_col = c
                break
    if not year_col:
        raise ValueError(f"No se encontro columna de año/ vigencia en inversión. Columnas: {list(df.columns)[:30]}")

    comuna_code_col = cols_map.get("codigocomuna") or _pick_col(df, ["CODIGO_COMUNA", "codigo_comuna", "Comuna"])
    comuna_name_col = cols_map.get("nombrecomuna") or _pick_col(df, ["NOMBRE_COMUNA", "NomComuna", "comuna_name"])
    value_col = cols_map.get("inversion") or _pick_col(df, ["INVERSION", "Inversion", "inversion"])

    df = df.copy()
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")

    # INVERSION llega como texto tipo '$2.996.064.440' (con encoding raro). Nos quedamos con dígitos.
    df[value_col] = df[value_col].astype(str).str.replace(r"[^0-9]", "", regex=True)
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)

    latest_year = _latest_year_from_column(df, year_col)
    df = df[df[year_col] == latest_year]

    df["COMUNA_CODE_NORM"] = df[comuna_code_col].apply(lambda v: normalize_code(v))
    df = df.dropna(subset=["COMUNA_CODE_NORM"])

    agg = df.groupby(["COMUNA_CODE_NORM", comuna_name_col], as_index=False)[value_col].sum()
    agg = agg.rename(
        columns={
            "COMUNA_CODE_NORM": "comuna_code",
            value_col: "investment_amount",
            comuna_name_col: "comuna_name",
        }
    )
    return int(latest_year), agg


def _compute_city_averages(mobility: pd.DataFrame, safety: pd.DataFrame, investment: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    def sanitize(v: Any) -> Any:
        return None if pd.isna(v) else float(v)

    return {
        "mobility_equiv_vehicles": {"value": sanitize(mobility["mobility_equiv_vehicles"].mean()), "unit": "vehiculos_equivalentes"},
        "safety_homicides": {"value": sanitize(safety["safety_homicides"].mean()), "unit": "casos"},
        "investment_amount": {"value": sanitize(investment["investment_amount"].mean()), "unit": "COP"},
    }


def get_territory_comunas() -> List[Dict[str, Any]]:
    inv = _get_all_summaries()["investment"]
    inv_agg = inv["by"]
    inv_agg = inv_agg.sort_values(["comuna_code"])
    return [{"code": r["comuna_code"], "name": (r.get("comuna_name") if isinstance(r.get("comuna_name"), str) else None)} for _, r in inv_agg.iterrows()]


@cached(_summary_cache)
def _get_all_summaries() -> Dict[str, Any]:
    mobility_df = load_mobility_aforos()
    safety_df = load_safety_homicidios()
    investment_df = load_investment_por_comuna()

    mobility_latest_year, mobility_by = _compute_mobility_by_comuna(mobility_df)
    safety_latest_year, safety_by = _compute_safety_by_comuna(safety_df)
    investment_latest_year, investment_by = _compute_investment_by_comuna(investment_df)

    return {
        "mobility": {"latest_year": mobility_latest_year, "by": mobility_by},
        "safety": {"latest_year": safety_latest_year, "by": safety_by},
        "investment": {"latest_year": investment_latest_year, "by": investment_by},
    }


def get_dashboard_overview(comuna_code: str) -> OverviewResponse:
    summaries = _get_all_summaries()
    mobility_latest_year, mobility_by = summaries["mobility"]["latest_year"], summaries["mobility"]["by"]
    safety_latest_year, safety_by = summaries["safety"]["latest_year"], summaries["safety"]["by"]
    investment_latest_year, investment_by = summaries["investment"]["latest_year"], summaries["investment"]["by"]

    comuna_code = "ALL" if (not comuna_code) else comuna_code
    if comuna_code != "ALL":
        comuna_code_norm = normalize_code(comuna_code)
        comuna_code = comuna_code_norm if comuna_code_norm else "ALL"

    # Join para tener lookup de nombres y valores por comuna.
    comuna_name_lookup = (
        investment_by[["comuna_code", "comuna_name"]].drop_duplicates().set_index("comuna_code")["comuna_name"].to_dict()
    )

    # Valors para la seleccion.
    city_avgs = _compute_city_averages(mobility_by, safety_by, investment_by)

    def value_for(df: pd.DataFrame, col: str) -> float:
        if comuna_code == "ALL":
            return city_avgs[col]["value"]
        row = df[df["comuna_code"] == comuna_code]
        if row.empty:
            return float("nan")
        return float(row.iloc[0][col])

    selected_mobility = value_for(mobility_by, "mobility_equiv_vehicles")
    selected_safety = value_for(safety_by, "safety_homicides")
    selected_investment = value_for(investment_by, "investment_amount")

    # Reglas de recomendacion simples (demo hackathon): comparacion con promedio de ciudad.
    recs: List[str] = []
    avg_mobility = city_avgs["mobility_equiv_vehicles"]["value"]
    avg_safety = city_avgs["safety_homicides"]["value"]
    avg_investment = city_avgs["investment_amount"]["value"]

    if comuna_code == "ALL":
        recs = [
            "Comparar comunas: usar el filtro territorial para identificar prioridades de intervención.",
            "Priorizar comunas con mayor brecha entre seguridad y asignación de recursos.",
            "Alinear oportunidades para pymes con zonas de alto flujo y necesidades de servicio.",
        ]
    else:
        # Si hay valores faltantes, conservamos recomendaciones genéricas.
        if pd.isna(selected_safety) or pd.isna(selected_mobility) or pd.isna(selected_investment):
            recs = [
                "Completar el análisis en el piloto: asegurar correspondencia entre comuna y métricas.",
                "Usar el dashboard para identificar señales y validar con actores locales.",
                "Extender el prototipo con una capa de mapa para facilitar adopción.",
            ]
        else:
            if selected_safety > avg_safety and selected_investment < avg_investment:
                recs.append("Priorizar intervenciones de seguridad con enfoque territorial (prevención, vigilancia focalizada y seguimiento).")
            if selected_mobility > avg_mobility and selected_safety > avg_safety:
                recs.append("Optimizar planes de movilidad-seguridad: señalización, cultura vial y gestión de puntos críticos de circulación.")
            if selected_investment > avg_investment:
                recs.append("Visibilizar el impacto de la inversión: convertir datos en indicadores claros para actores y pymes (transparencia y oportunidades).")
            if not recs:
                recs = [
                    "Mantener estrategias actuales y monitorear tendencias: revisar cambios trimestre a trimestre.",
                    "Definir metas por comuna (seguridad, movilidad e inversión) y publicar resultados comparables.",
                    "Construir alianzas con emprendedores locales para usar el dashboard en decisiones operativas.",
                ]

    selected_name = None if comuna_code == "ALL" else comuna_name_lookup.get(comuna_code)
    selected = {"comuna_code": comuna_code, "comuna_name": selected_name}

    metrics = {
        "mobility_equiv_vehicles": {"value": None if pd.isna(selected_mobility) else float(selected_mobility), "unit": "vehiculos_equivalentes"},
        "safety_homicides": {"value": None if pd.isna(selected_safety) else float(selected_safety), "unit": "casos"},
        "investment_amount": {"value": None if pd.isna(selected_investment) else float(selected_investment), "unit": "COP"},
    }

    overview = OverviewResponse(
        meta={
            "mobility_latest_year": mobility_latest_year,
            "safety_latest_year": safety_latest_year,
            "investment_latest_year": investment_latest_year,
            "dataset_mobility_url": DATASETS.mobility_aforos_vehiculares,
            "dataset_safety_url": DATASETS.safety_homicidios,
            "dataset_investment_url": DATASETS.investment_inversion_por_comuna_2019,
        },
        selected=selected,
        metrics=metrics,  # type: ignore[arg-type]
        city_averages=city_avgs,  # type: ignore[arg-type]
        recommendations=recs,
        mobility_by_comuna=mobility_by.sort_values("mobility_equiv_vehicles", ascending=False).head(10).to_dict(orient="records"),
        safety_by_comuna=safety_by.sort_values("safety_homicides", ascending=False).head(10).to_dict(orient="records"),
    )
    return overview

