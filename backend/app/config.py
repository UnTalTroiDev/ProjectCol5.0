import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DatasetURLS:
    mobility_aforos_vehiculares: str = (
        "http://medata.gov.co/sites/default/files/distribution/1-023-25-000301/"
        "Aforos_Vehiculares.csv"
    )
    safety_homicidios: str = (
        "http://medata.gov.co/sites/default/files/distribution/1-027-23-000008/"
        "homicidio.csv"
    )
    investment_inversion_por_comuna_2019: str = (
        "http://medata.gov.co/sites/default/files/distribution/1-002-11-000278/"
        "inversion_por_comuna_y_corregimiento_medellin_2019.csv"
    )
    # Dataset de Lesiones Comunes (Secretaria de Seguridad).
    # Configurable via variable de entorno MEDATA_LESIONES_URL para facilitar
    # actualizaciones sin cambiar codigo.
    safety_lesiones_comunes: str = field(
        default_factory=lambda: os.getenv(
            "MEDATA_LESIONES_URL",
            "http://medata.gov.co/sites/default/files/distribution/1-027-23-000007/"
            "lesiones_personales.csv",
        )
    )


DATASETS = DatasetURLS()

# Cache para evitar re-descargar CSVs en cada request.
CSV_CACHE_TTL_SECONDS = int(os.getenv("CSV_CACHE_TTL_SECONDS", str(60 * 60 * 6)))  # 6 horas
