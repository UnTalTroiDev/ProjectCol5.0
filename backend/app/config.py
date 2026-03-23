import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DatasetURLS:
    # ── Movilidad ──────────────────────────────────────────────────────────
    mobility_aforos_vehiculares: str = (
        "http://medata.gov.co/sites/default/files/distribution/1-023-25-000301/"
        "Aforos_Vehiculares.csv"
    )
    mobility_victimas_incidentes_viales: str = (
        "http://medata.gov.co/sites/default/files/distribution/1-023-25-000360/"
        "Mede_Victimas_inci.csv"
    )

    # ── Seguridad ──────────────────────────────────────────────────────────
    safety_homicidios: str = (
        "http://medata.gov.co/sites/default/files/distribution/1-027-23-000008/"
        "homicidio.csv"
    )
    safety_lesiones_comunes: str = field(
        default_factory=lambda: os.getenv(
            "MEDATA_LESIONES_URL",
            "http://medata.gov.co/sites/default/files/distribution/1-027-23-000007/"
            "lesiones_personales.csv",
        )
    )
    # Criminalidad consolidada: homicidios, hurtos a personas/carros/motos/residencias,
    # extorsion, violencia intrafamiliar, etc. Enero 2003 – presente.
    security_criminalidad_consolidada: str = (
        "http://medata.gov.co/sites/default/files/distribution/1-027-23-000306/"
        "consolidado_cantidad_casos_criminalidad_por_anio_mes.csv"
    )
    social_violencia_intrafamiliar: str = (
        "http://medata.gov.co/sites/default/files/distribution/1-027-23-000028/"
        "solicitud_de_medidas_de_proteccion_por_violencia_intrafamiliar.csv"
    )

    # ── Inversión pública ──────────────────────────────────────────────────
    investment_inversion_por_comuna_2019: str = (
        "http://medata.gov.co/sites/default/files/distribution/1-002-11-000278/"
        "inversion_por_comuna_y_corregimiento_medellin_2019.csv"
    )

    # ── Salud ──────────────────────────────────────────────────────────────
    health_natalidad: str = (
        "http://medata.gov.co/sites/default/files/distribution/1-026-22-000029/"
        "natalidad.csv"
    )
    health_hospitalizacion: str = (
        "http://medata.gov.co/sites/default/files/distribution/1-026-22-000126/"
        "registro_hospitalizacion_prestacion_servicios_medicos.csv"
    )

    # ── Educación ──────────────────────────────────────────────────────────
    education_establecimientos: str = (
        "http://medata.gov.co/sites/default/files/distribution/1-011-08-000122/"
        "directorio_establecimientos_educativos.csv"
    )
    education_ambiente_escolar: str = (
        "http://medata.gov.co/sites/default/files/distribution/1-011-08-000068/"
        "historico_indicadores_ambiente_escolar.csv"
    )

    # ── Medio Ambiente ─────────────────────────────────────────────────────
    environment_residuos_solidos: str = (
        "http://medata.gov.co/sites/default/files/distribution/1-028-02-000599/"
        "generacion_residuos_solidos_centro_administrativo_distrital.csv"
    )

    # ── Calidad de Vida ────────────────────────────────────────────────────
    quality_imcv: str = (
        "http://medata.gov.co/sites/default/files/distribution/1-002-09-000041/"
        "indice_multidimensional_encuesta_calidad_de_vida.csv"
    )


DATASETS = DatasetURLS()

# Cache para evitar re-descargar CSVs en cada request.
CSV_CACHE_TTL_SECONDS = int(os.getenv("CSV_CACHE_TTL_SECONDS", str(60 * 60 * 6)))  # 6 horas
