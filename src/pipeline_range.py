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

    successful_composition_files = []
    successful_literal_files = []
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

            composition_path = PROCESSED_DIR / (
                f"portfolio_composition_"
                f"{year}_{month:02d}.csv"
            )

            literal_path = PROCESSED_DIR / (
                f"portfolio_literal_"
                f"{year}_{month:02d}.csv"
            )

            if not composition_path.exists():
                raise FileNotFoundError(
                    "No se generó el archivo de "
                    f"composición: {composition_path}"
                )

            if not literal_path.exists():
                raise FileNotFoundError(
                    "No se generó el archivo de "
                    f"literales: {literal_path}"
                )

            successful_composition_files.append(
                composition_path
            )

            successful_literal_files.append(
                literal_path
            )

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

    # -----------------------------------
    # HISTÓRICO DE DETALLE
    # -----------------------------------

    if successful_composition_files:
        composition_dataframes = []

        for file_path in successful_composition_files:
            df = pd.read_csv(file_path)
            composition_dataframes.append(df)

        df_composition_history = pd.concat(
            composition_dataframes,
            ignore_index=True
        )

        composition_history_path = (
            PROCESSED_DIR
            / "portfolio_composition_history.csv"
        )

        df_composition_history.to_csv(
            composition_history_path,
            index=False,
            encoding="utf-8-sig"
        )

    # -----------------------------------
    # HISTÓRICO POR LITERAL
    # -----------------------------------

    if successful_literal_files:
        literal_dataframes = []

        for file_path in successful_literal_files:
            df = pd.read_csv(file_path)
            literal_dataframes.append(df)

        df_literal_history = pd.concat(
            literal_dataframes,
            ignore_index=True
        )

        literal_history_path = (
            PROCESSED_DIR
            / "portfolio_literal_history.csv"
        )

        df_literal_history.to_csv(
            literal_history_path,
            index=False,
            encoding="utf-8-sig"
        )

    # -----------------------------------
    # RESUMEN
    # -----------------------------------

    print("\n======================================")
    print("HISTÓRICOS GENERADOS")
    print("======================================")

    print(
        f"Meses procesados correctamente: "
        f"{len(successful_composition_files)}"
    )

    if successful_composition_files:
        print(
            f"Registros composición detalle: "
            f"{len(df_composition_history)}"
        )

        print(
            f"Archivo: "
            f"{composition_history_path}"
        )

    if successful_literal_files:
        print(
            f"Registros composición literal: "
            f"{len(df_literal_history)}"
        )

        print(
            f"Archivo: "
            f"{literal_history_path}"
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