import argparse
from pathlib import Path

from data_loader import (
    load_complete_report,
    EXPECTED_SUBFUNDS,
    get_portfolio_detail,
    get_portfolio_literal_totals,
    enrich_detail_structure,
    normalize_dimensions,
    validate_portfolio_data,
    validate_total_percentages,
    validate_literal_percentages,
    validate_missing_percentages,
    save_processed_portfolio,
)


def run_portfolio_pipeline(
    year: int,
    month: int,
    pdf_path: Path | None = None
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

    # 1. Usar un PDF local o conservar la descarga mensual habitual.
    if pdf_path is None:
        import truststore
        truststore.inject_into_ssl()
        from download_data import download_portfolio_report
        pdf_path = download_portfolio_report(year, month)
    pdf_path = Path(pdf_path)

    # 2. Extraer todas las tablas: subfondos, totales monetarios, FVP y anexos.
    df_complete = load_complete_report(pdf_path)
    report_date = df_complete["fecha"].iloc[0]
    if (report_date.year, report_date.month) != (year, month):
        raise ValueError(
            f"El PDF corresponde a {report_date:%Y-%m}, "
            f"pero se solicitó {year}-{month:02d}. No se guardaron archivos."
        )

    # Mantener el ámbito y esquema originales de los controles y literales.
    # Los importes, el FVP y los anexos permanecen en df_complete para el CSV.
    mask = (
        df_complete["seccion"].eq("COMPOSICION")
        & df_complete["subfondo"].isin(EXPECTED_SUBFUNDS)
        & df_complete["tipo_valor"].eq("PORCENTAJE")
    )
    df_all = df_complete.loc[mask, [
        "fecha", "subfondo", "afap", "tipo_fila", "instrumento_raw", "valor_pct"
    ]].copy()

    print("\n--- DIAGNÓSTICO DESPUÉS DE LA EXTRACCIÓN ---")

    print("AFAP detectadas:")
    print(df_all["afap"].unique())

    print("\nPorcentajes de ITAU y UNION_CAPITAL:")
    print(
        df_all[
            df_all["afap"].isin(["ITAU", "UNION_CAPITAL"])
        ]
        .groupby(["subfondo", "afap", "tipo_fila"])["valor_pct"]
        .agg(["count", "sum"])
        .to_string()
    )


    # 3. Conservar filas analíticas
    df_detail = get_portfolio_detail(
        df_all
    )
    # Composición completa a nivel de literal
    df_literals = get_portfolio_literal_totals(
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

    afap_map = {
        "SURA": "AFAP SURA",
        "INTEGRACION": "INTEGRACION AFAP",
        "REPUBLICA": "REPUBLICA AFAP",
        "ITAU": "AFAP ITAU",
        "UNION_CAPITAL": "UNION CAPITAL AFAP",
        "TOTAL_SISTEMA": "TOTAL SISTEMA",
    }

    df_literals["afap_normalizada"] = (
        df_literals["afap"].map(afap_map)
    )


    print("\n--- DIAGNÓSTICO AFAP Y LITERALES ---")

    print(
        df_literals
        .groupby(
            ["subfondo", "afap", "afap_normalizada"],
            dropna=False
        )["valor_pct"]
        .agg(["count", "sum"])
        .to_string()
    )


    # 6. Controles de calidad
    validate_portfolio_data(
        df_all,
        df_detail
    )

    validate_missing_percentages(df_all)
    
    validate_total_percentages(
        df_all
    )

    validate_literal_percentages(
        df_literals
    )
    # 7. Trazabilidad
    df_detail["archivo_origen"] = (
        pdf_path.name
    )
    
    df_literals["archivo_origen"] = (
        pdf_path.name
    )

    # 8. La fecha viene del propio PDF
    report_date = df_complete["fecha"].iloc[0]

    output_path = Path(
        "data/processed/"
        f"portfolio_composition_"
        f"{report_date:%Y_%m}.csv"
    )

    literal_output_path = Path(
        "data/processed/"
        f"portfolio_literal_"
        f"{report_date:%Y_%m}.csv"
    )

    # 9. Guardar todas las filas del reporte y la salida analítica por literal.
    # Ambos archivos se escriben solo después de pasar los controles anteriores.
    save_processed_portfolio(
        df_complete,
        output_path
    )

    save_processed_portfolio(
        df_literals,
        literal_output_path
    )

    print("\n--- COBERTURA DEL REPORTE COMPLETO ---")
    print(df_complete.groupby(["pagina", "seccion", "fondo"]).size().rename("registros").to_string())
    print(f"\nRegistros del CSV completo: {len(df_complete)}")
    print(f"Importes monetarios: {df_complete['tipo_valor'].eq('IMPORTE').sum()}")
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

    parser.add_argument(
        "--pdf",
        type=Path,
        help="PDF local opcional; omite la descarga y verifica que coincida con año/mes.",
    )

    args = parser.parse_args()

    run_portfolio_pipeline(
        args.year,
        args.month,
        pdf_path=args.pdf
    )
