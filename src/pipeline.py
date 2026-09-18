import truststore

truststore.inject_into_ssl()

import argparse
from pathlib import Path

from download_data import download_portfolio_report

from data_loader import (
    load_all_subfunds,
    get_portfolio_detail,
    enrich_detail_structure,
    normalize_dimensions,
    validate_portfolio_data,
    validate_total_percentages,
    save_processed_portfolio,
)


def run_portfolio_pipeline(
    year: int,
    month: int
) -> None:

    print(
        "\n======================================"
    )
    print(
        f"AFAP PORTFOLIO PIPELINE - "
        f"{month:02d}/{year}"
    )
    print(
        "======================================\n"
    )

    # 1. Buscar y descargar PDF
    pdf_path = download_portfolio_report(
        year,
        month
    )

    # 2. Extraer los tres subfondos
    df_all = load_all_subfunds(
        pdf_path
    )

    # 3. Conservar filas analíticas
    df_detail = get_portfolio_detail(
        df_all
    )

    # 4. Reconstruir Literal / instrumento / moneda
    df_detail = enrich_detail_structure(
        df_detail
    )

    # 5. Normalizar dimensiones
    df_detail = normalize_dimensions(
        df_detail
    )

    # 6. Controles de calidad
    validate_portfolio_data(
        df_all,
        df_detail
    )

    validate_total_percentages(
        df_all
    )

    # 7. Trazabilidad
    df_detail["archivo_origen"] = (
        pdf_path.name
    )

    # 8. La fecha viene del propio PDF
    report_date = df_detail[
        "fecha"
    ].iloc[0]

    output_path = Path(
        "data/processed/"
        f"portfolio_composition_"
        f"{report_date:%Y_%m}.csv"
    )

    # 9. Guardar dataset procesado
    save_processed_portfolio(
        df_detail,
        output_path
    )

    print("\nPIPELINE COMPLETADO CORRECTAMENTE.")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Descarga y procesa reportes "
            "mensuales de composición AFAP."
        )
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Año del reporte. Ejemplo: 2026",
    )

    parser.add_argument(
        "--month",
        type=int,
        required=True,
        choices=range(1, 13),
        help="Mes del reporte. Ejemplo: 7",
    )

    args = parser.parse_args()

    run_portfolio_pipeline(
        args.year,
        args.month
    )