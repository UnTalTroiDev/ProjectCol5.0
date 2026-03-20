from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Tuple

import pandas as pd
from cachetools import TTLCache, cached

from .data_loader import load_investment_por_comuna, load_mobility_aforos, load_safety_homicidios
from ..schemas.dashboard import OverviewResponse
from ..config import DATASETS
from ..utils.normalize import norm_key, normalize_code

logger = logging.getLogger(__name__)

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
    logger.info("Cache miss: cargando todos los datasets desde MEData...")
    t0 = time.monotonic()

    mobility_df = load_mobility_aforos()
    logger.info("Mobility dataset cargado: %d filas", len(mobility_df))

    safety_df = load_safety_homicidios()
    logger.info("Safety dataset cargado: %d filas", len(safety_df))

    investment_df = load_investment_por_comuna()
    logger.info("Investment dataset cargado: %d filas", len(investment_df))

    mobility_latest_year, mobility_by = _compute_mobility_by_comuna(mobility_df)
    logger.info("Mobility computado: año %d, %d comunas", mobility_latest_year, len(mobility_by))

    safety_latest_year, safety_by = _compute_safety_by_comuna(safety_df)
    logger.info("Safety computado: año %d, %d comunas", safety_latest_year, len(safety_by))

    investment_latest_year, investment_by = _compute_investment_by_comuna(investment_df)
    logger.info("Investment computado: año %d, %d comunas", investment_latest_year, len(investment_by))

    elapsed = time.monotonic() - t0
    logger.info("_get_all_summaries completado en %.2fs", elapsed)

    return {
        "mobility": {"latest_year": mobility_latest_year, "by": mobility_by},
        "safety": {"latest_year": safety_latest_year, "by": safety_by},
        "investment": {"latest_year": investment_latest_year, "by": investment_by},
    }


def get_dashboard_overview(comuna_code: str) -> OverviewResponse:
    logger.info("get_dashboard_overview: comuna_code=%r", comuna_code)
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

    def _fmt(v: float) -> str:
        """Formatea un float grande con separadores de miles, sin decimales."""
        return f"{v:,.0f}"

    if comuna_code == "ALL":
        top_safety = safety_by.sort_values("safety_homicides", ascending=False).iloc[0]
        top_mob = mobility_by.sort_values("mobility_equiv_vehicles", ascending=False).iloc[0]
        recs = [
            (
                f"Comparar comunas: la comuna con mas homicidios ({top_safety['comuna_code']}) "
                f"registra {_fmt(top_safety['safety_homicides'])} casos vs. "
                f"promedio ciudad de {_fmt(avg_safety)}. "
                "Usar el filtro territorial para identificar prioridades de inversion."
            ),
            (
                f"Mayor flujo vehicular en comuna {top_mob['comuna_code']}: "
                f"{_fmt(top_mob['mobility_equiv_vehicles'])} vehiculos equivalentes "
                f"vs. promedio {_fmt(avg_mobility)}. "
                "Cruzar con seguridad para focalizar infraestructura."
            ),
            "Alinear oportunidades para pymes con zonas de alto flujo y necesidades de servicio.",
        ]
    else:
        # Si hay valores faltantes, conservamos recomendaciones genericas.
        if pd.isna(selected_safety) or pd.isna(selected_mobility) or pd.isna(selected_investment):
            logger.warning(
                "Valores faltantes para comuna %s: safety=%s mobility=%s investment=%s",
                comuna_code, selected_safety, selected_mobility, selected_investment,
            )
            recs = [
                "Completar el analisis en el piloto: asegurar correspondencia entre comuna y metricas.",
                "Usar el dashboard para identificar senales y validar con actores locales.",
                "Extender el prototipo con una capa de mapa para facilitar adopcion.",
            ]
        else:
            if selected_safety > avg_safety and selected_investment < avg_investment:
                pct_safety = (selected_safety - avg_safety) / avg_safety * 100
                gap_inv = avg_investment - selected_investment
                recs.append(
                    f"Priorizar seguridad: esta comuna tiene {_fmt(selected_safety)} homicidios "
                    f"({pct_safety:+.1f}% sobre el promedio de {_fmt(avg_safety)}), "
                    f"con una brecha de inversion de COP {_fmt(gap_inv)} respecto al promedio. "
                    "Focalizar prevencion y vigilancia territorial."
                )
            if selected_mobility > avg_mobility and selected_safety > avg_safety:
                pct_mob = (selected_mobility - avg_mobility) / avg_mobility * 100
                recs.append(
                    f"Movilidad-seguridad critica: {_fmt(selected_mobility)} vehiculos equivalentes "
                    f"({pct_mob:+.1f}% sobre promedio de {_fmt(avg_mobility)}) "
                    f"y {_fmt(selected_safety)} homicidios (promedio {_fmt(avg_safety)}). "
                    "Intervenir en senalizacion, cultura vial y puntos criticos de circulacion."
                )
            if selected_investment > avg_investment:
                pct_inv = (selected_investment - avg_investment) / avg_investment * 100
                recs.append(
                    f"Inversion destacada: COP {_fmt(selected_investment)} "
                    f"({pct_inv:+.1f}% sobre promedio de COP {_fmt(avg_investment)}). "
                    "Visibilizar impacto con indicadores claros para actores y pymes."
                )
            if not recs:
                recs = [
                    (
                        f"Indicadores dentro del rango promedio: "
                        f"seguridad {_fmt(selected_safety)} casos (promedio {_fmt(avg_safety)}), "
                        f"movilidad {_fmt(selected_mobility)} (promedio {_fmt(avg_mobility)}), "
                        f"inversion COP {_fmt(selected_investment)} (promedio COP {_fmt(avg_investment)}). "
                        "Mantener estrategias actuales y monitorear tendencias trimestralmente."
                    ),
                    "Definir metas por comuna y publicar resultados comparables.",
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

