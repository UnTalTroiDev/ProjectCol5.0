from dataclasses import dataclass


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


DATASETS = DatasetURLS()

# Cache to avoid re-downloading CSVs on every request.
CSV_CACHE_TTL_SECONDS = 60 * 60 * 6  # 6 hours

