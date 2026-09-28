from pathlib import Path
import argparse

import pandas as pd

from gross_returns_pipeline import run_gross_returns_pipeline


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def run_range(
    start: str,
    end: str,
):
    """
    Ejecuta el pipeline de Rentabilidad Bruta
    para un rango mensual y genera
    el histórico consolidado.
    """

    periods = pd.period_range(
        start=start,
        end=end,
        freq="M",
    )

    datasets = []
    errors = []

    print(
        "\n===================================="
    )
    print(
        "PIPELINE HISTÓRICO - RENTABILIDAD BRUTA"
    )
    print(
        "===================================="
    )

    print(
        f"Rango solicitado: {start} → {end}"
    )
    print(
        f"Meses a procesar: {len(periods)}"
    )

    for period in periods:

        year = period.year
        month = period.month

        print(
            "\n------------------------------------"
        )
        print(
            f"Procesando {month:02d}/{year}"
        )
        print(
            "------------------------------------"
        )

        try:
            df = run_gross_returns_pipeline(
                year=year,
                month=month,
            )

            datasets.append(df)

        except Exception as error:

            errors.append(
                {
                    "periodo": str(period),
                    "error": str(error),
                }
            )

            print(
                f"ERROR en {period}: {error}"
            )

    if errors:

        print(
            "\n===================================="
        )
        print(
            "EL HISTÓRICO NO SERÁ GENERADO"
        )
        print(
            "===================================="
        )

        print(
            f"Períodos con error: {len(errors)}"
        )

        for error in errors:
            print(
                f"{error['periodo']}: "
                f"{error['error']}"
            )

        raise RuntimeError(
            "Existen períodos con errores. "
            "Se cancela la generación "
            "del histórico consolidado."
        )

    history = pd.concat(
        datasets,
        ignore_index=True,
    )

    # Validar duplicados en la granularidad
    # definida para Rentabilidad Bruta.
    duplicates = history.duplicated(
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
            f"{duplicates} duplicados."
        )

    # Validar cobertura completa del rango.
    actual_periods = sorted(
        history["periodo"].unique()
    )

    expected_periods = [
        str(period)
        for period in periods
    ]

    if actual_periods != expected_periods:
        missing_periods = sorted(
            set(expected_periods)
            - set(actual_periods)
        )

        raise ValueError(
            "Los períodos del histórico "
            "no coinciden con el rango solicitado. "
            f"Faltantes: {missing_periods}"
        )

    # Validar nulos en la medida principal.
    null_returns = (
        history["rentabilidad_bruta"]
        .isna()
        .sum()
    )

    if null_returns > 0:
        raise ValueError(
            "Se encontraron "
            f"{null_returns} valores nulos "
            "en rentabilidad_bruta."
        )

    # Validar tipos de tasa.
    expected_rates = {
        "TRM",
        "TNA",
        "TRA",
    }

    actual_rates = set(
        history["tipo_tasa"].unique()
    )

    if actual_rates != expected_rates:
        raise ValueError(
            "Tipos de tasa inesperados. "
            f"Detectados: {actual_rates}"
        )

    output_path = (
        PROCESSED_DIR
        / "gross_returns_history.csv"
    )

    history.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        "\n===================================="
    )
    print(
        "HISTÓRICO BRUTO VALIDADO"
    )
    print(
        "===================================="
    )

    print(
        f"Períodos: {len(actual_periods)}"
    )
    print(
        f"Registros: {len(history)}"
    )
    print(
        f"Duplicados: {duplicates}"
    )
    print(
        f"Nulos rentabilidad_bruta: {null_returns}"
    )
    print(
        f"Archivo: {output_path}"
    )

    print(
        "\nRegistros por período:"
    )

    print(
        history.groupby("periodo")
        .size()
        .to_string()
    )

    return history


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Pipeline histórico de "
            "Rentabilidad Bruta de AFAP."
        )
    )

    parser.add_argument(
        "--start",
        required=True,
        help="Período inicial YYYY-MM.",
    )

    parser.add_argument(
        "--end",
        required=True,
        help="Período final YYYY-MM.",
    )

    args = parser.parse_args()

    run_range(
        start=args.start,
        end=args.end,
    )