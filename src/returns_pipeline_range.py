from pathlib import Path
import argparse

import pandas as pd

from returns_pipeline import run_returns_pipeline


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def run_range(
    start: str,
    end: str,
):
    """
    Ejecuta el pipeline de Rentabilidad Neta
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
        "PIPELINE HISTÓRICO - RENTABILIDAD NETA"
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
            df = run_returns_pipeline(
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

    expected_records = (
        len(periods) * 20
    )

    if len(history) != expected_records:
        raise ValueError(
            "Cantidad inesperada de registros. "
            f"Esperados: {expected_records}. "
            f"Obtenidos: {len(history)}."
        )

    duplicates = history.duplicated(
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
            f"{duplicates} duplicados."
        )

    actual_periods = sorted(
        history.periodo.unique()
    )

    if len(actual_periods) != len(periods):
        raise ValueError(
            "La cantidad de períodos del dataset "
            "no coincide con el rango solicitado."
        )

    output_path = (
        PROCESSED_DIR
        / "returns_history.csv"
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
        "HISTÓRICO VALIDADO"
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
        f"Archivo: {output_path}"
    )

    return history


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Pipeline histórico de "
            "Rentabilidad Neta de AFAP."
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