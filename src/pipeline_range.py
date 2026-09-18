import argparse
from pathlib import Path

import pandas as pd

from pipeline import run_portfolio_pipeline


PROCESSED_DIR = Path("data/processed")


def run_range(start: str, end: str) -> None:
    """
    Procesa todos los meses comprendidos entre start y end.

    Formato esperado:
    start = "2026-01"
    end   = "2026-08"
    """

    periods = pd.period_range(
        start=start,
        end=end,
        freq="M"
    )

    successful_files = []
    errors = []

    print("\n======================================")
    print(f"PROCESAMIENTO HISTÓRICO {start} → {end}")
    print("======================================")

    for period in periods:

        year = period.year
        month = period.month

        print(
            f"\n\n>>> Procesando {month:02d}/{year}"
        )

        try:
            run_portfolio_pipeline(
                year,
                month
            )

            output_path = PROCESSED_DIR / (
                f"portfolio_composition_"
                f"{year}_{month:02d}.csv"
            )

            if output_path.exists():
                successful_files.append(output_path)

        except Exception as error:

            print(
                f"\nERROR procesando "
                f"{month:02d}/{year}: {error}"
            )

            errors.append(
                {
                    "periodo": f"{year}-{month:02d}",
                    "error": str(error),
                }
            )

    if successful_files:

        dataframes = []

        for file_path in successful_files:

            df = pd.read_csv(file_path)

            dataframes.append(df)

        df_history = pd.concat(
            dataframes,
            ignore_index=True
        )

        history_path = (
            PROCESSED_DIR
            / "portfolio_composition_history.csv"
        )

        df_history.to_csv(
            history_path,
            index=False,
            encoding="utf-8-sig"
        )

        print("\n======================================")
        print("HISTÓRICO GENERADO")
        print("======================================")

        print(
            f"Meses procesados correctamente: "
            f"{len(successful_files)}"
        )

        print(
            f"Registros históricos: "
            f"{len(df_history)}"
        )

        print(
            f"Archivo consolidado: "
            f"{history_path}"
        )

    if errors:

        print("\nMeses con errores:")

        for item in errors:
            print(
                f"{item['periodo']} → "
                f"{item['error']}"
            )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Descarga y procesa un rango mensual "
            "de reportes AFAP."
        )
    )

    parser.add_argument(
        "--start",
        required=True,
        help="Mes inicial. Ejemplo: 2026-01",
    )

    parser.add_argument(
        "--end",
        required=True,
        help="Mes final. Ejemplo: 2026-08",
    )

    args = parser.parse_args()

    run_range(
        args.start,
        args.end
    )