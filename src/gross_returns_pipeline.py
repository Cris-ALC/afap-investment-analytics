from pathlib import Path
import argparse

import pandas as pd

from gross_returns_download import download_returns_report
from gross_returns_loader import extract_gross_returns


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def validate_gross_returns_data(df):
    """
    Ejecuta controles básicos de calidad
    sobre los datos de Rentabilidad Bruta.
    """

    expected_columns = {
        "periodo",
        "afap_raw",
        "tipo_fondo",
        "tipo_tasa",
        "rentabilidad_bruta",
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

    if df.empty:
        raise ValueError(
            "El dataset de Rentabilidad Bruta "
            "está vacío."
        )

    if df["rentabilidad_bruta"].isna().any():
        raise ValueError(
            "Se encontraron valores nulos "
            "en rentabilidad_bruta."
        )

    duplicates = df.duplicated(
        subset=[
            "periodo",
            "afap_raw",
            "tipo_fondo",
            "tipo_tasa",
        ]
    ).sum()

    if duplicates > 0:
        raise ValueError(
            "Se encontraron "
            f"{duplicates} registros duplicados."
        )

    expected_rates = {
        "TRM",
        "TNA",
        "TRA",
    }

    detected_rates = set(
        df["tipo_tasa"].unique()
    )

    if detected_rates != expected_rates:
        raise ValueError(
            "Tipos de tasa inesperados. "
            f"Detectados: {detected_rates}"
        )

    required_funds = {
        "CRECIMIENTO",
        "ACUMULACION",
        "RETIRO",
        "FAP",
    }

    detected_funds = set(
        df["tipo_fondo"].unique()
    )

    missing_funds = (
        required_funds
        - detected_funds
    )

    if missing_funds:
        raise ValueError(
            "Faltan fondos obligatorios: "
            f"{missing_funds}"
        )

    print("Controles de calidad: OK")


def run_gross_returns_pipeline(
    year: int,
    month: int,
):
    """
    Ejecuta el pipeline mensual de
    Rentabilidad Bruta.
    """

    print(
        "\n===================================="
    )

    print(
        f"Rentabilidad Bruta - "
        f"{month:02d}/{year}"
    )

    print(
        "====================================\n"
    )

    # 1. Descargar / localizar PDF
    pdf_path = download_returns_report(
        year=year,
        month=month,
    )

    # 2. Extraer información
    df = extract_gross_returns(
        pdf_path
    )

    print(
        f"Registros extraídos: {len(df)}"
    )

    # 3. Validar período
    expected_period = (
        f"{year}-{month:02d}"
    )

    periods = df["periodo"].unique()

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
    validate_gross_returns_data(df)

    # 5. Guardar dataset procesado
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        PROCESSED_DIR
        / f"gross_returns_{year}_{month:02d}.csv"
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
            "Rentabilidad Bruta de AFAP."
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

    run_gross_returns_pipeline(
        year=args.year,
        month=args.month,
    )