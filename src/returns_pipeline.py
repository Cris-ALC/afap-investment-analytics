from pathlib import Path
import argparse

import pandas as pd

from returns_download import download_returns_report
from returns_loader import extract_returns


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def validate_returns_data(df):
    """
    Ejecuta controles básicos de calidad
    sobre los datos de Rentabilidad Neta.
    """

    expected_columns = {
        "periodo",
        "afap_raw",
        "tipo_metrica",
        "subfondo",
        "rentabilidad_neta",
        "archivo_origen",
    }

    missing_columns = (
        expected_columns
        - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Faltan columnas esperadas: "
            f"{missing_columns}"
        )

    if len(df) != 20:
        raise ValueError(
            "Se esperaban 20 registros "
            f"y se obtuvieron {len(df)}."
        )

    if df.rentabilidad_neta.isna().any():
        raise ValueError(
            "Se encontraron valores nulos "
            "en rentabilidad_neta."
        )

    duplicates = df.duplicated(
        subset=[
            "periodo",
            "afap_raw",
            "tipo_metrica",
            "subfondo",
        ]
    ).sum()

    if duplicates > 0:
        raise ValueError(
            "Se encontraron "
            f"{duplicates} registros duplicados."
        )

    afap_count = df.afap_raw.nunique()

    if afap_count != 4:
        raise ValueError(
            "Se esperaban 4 AFAP "
            f"y se encontraron {afap_count}."
        )

    print("Controles de calidad: OK")


def run_returns_pipeline(
    year: int,
    month: int,
):
    """
    Ejecuta el pipeline mensual de
    Rentabilidad Neta.
    """

    print(
        "\n===================================="
    )

    print(
        f"Rentabilidad Neta - "
        f"{month:02d}/{year}"
    )

    print(
        "====================================\n"
    )

    # 1. Descargar PDF
    pdf_path = download_returns_report(
        year=year,
        month=month,
    )

    # 2. Extraer información
    df = extract_returns(
        pdf_path
    )

    print(
        f"Registros extraídos: {len(df)}"
    )

    # 3. Validar período
    expected_period = (
        f"{year}-{month:02d}"
    )

    periods = df.periodo.unique()

    if (
        len(periods) != 1
        or periods[0] != expected_period
    ):
        raise ValueError(
            "El período detectado en el PDF "
            "no coincide con el solicitado. "
            f"Esperado: {expected_period}. "
            f"Detectado: {periods}"
        )

    print(
        f"Período validado: {expected_period}"
    )

    # 4. Controles de calidad
    validate_returns_data(df)

    # 5. Guardar dataset procesado
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        PROCESSED_DIR
        / f"returns_{year}_{month:02d}.csv"
    )

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"CSV guardado: {output_path}"
    )

    return df


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Pipeline mensual de "
            "Rentabilidad Neta de AFAP."
        )
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Año del reporte.",
    )

    parser.add_argument(
        "--month",
        type=int,
        required=True,
        choices=range(1, 13),
        help="Mes del reporte (1-12).",
    )

    args = parser.parse_args()

    run_returns_pipeline(
        year=args.year,
        month=args.month,
    )