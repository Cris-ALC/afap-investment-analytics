from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "afap_analytics.duckdb"
)


def validate_database():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró la base: {DATABASE_PATH}"
        )

    connection = duckdb.connect(
        str(DATABASE_PATH),
        read_only=True,
    )

    try:
        print(
            "\n=== DATA QUALITY - AFAP ANALYTICS ===\n"
        )

        # ----------------------------------------------------
        # Dimensiones
        # ----------------------------------------------------

        period_count = connection.execute(
            "SELECT COUNT(*) FROM dim_period"
        ).fetchone()[0]

        afap_count = connection.execute(
            "SELECT COUNT(*) FROM dim_afap"
        ).fetchone()[0]

        subfund_count = connection.execute(
            "SELECT COUNT(*) FROM dim_subfund"
        ).fetchone()[0]

        currency_count = connection.execute(
            "SELECT COUNT(*) FROM dim_currency"
        ).fetchone()[0]

        instrument_count = connection.execute(
            "SELECT COUNT(*) FROM dim_instrument"
        ).fetchone()[0]

        literal_count = connection.execute(
            "SELECT COUNT(*) FROM dim_literal"
        ).fetchone()[0]

        print("DIMENSIONES")
        print(f"  Períodos: {period_count}")
        print(f"  Entidades: {afap_count}")
        print(f"  Subfondos: {subfund_count}")
        print(f"  Monedas: {currency_count}")
        print(f"  Instrumentos: {instrument_count}")
        print(f"  Literales: {literal_count}")

        # ----------------------------------------------------
        # Portfolio
        # ----------------------------------------------------

        portfolio_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM fact_portfolio_composition
            """
        ).fetchone()[0]

        portfolio_periods = connection.execute(
            """
            SELECT COUNT(DISTINCT period_id)
            FROM fact_portfolio_composition
            """
        ).fetchone()[0]

        portfolio_null_values = connection.execute(
            """
            SELECT COUNT(*)
            FROM fact_portfolio_composition
            WHERE valor_pct IS NULL
            """
        ).fetchone()[0]

        portfolio_duplicates = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    period_id,
                    afap_id,
                    subfund_id,
                    instrument_id,
                    currency_id,
                    COUNT(*) AS cantidad
                FROM fact_portfolio_composition
                GROUP BY
                    period_id,
                    afap_id,
                    subfund_id,
                    instrument_id,
                    currency_id
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        print("\nFACT_PORTFOLIO_COMPOSITION")
        print(f"  Filas: {portfolio_count}")
        print(f"  Períodos con datos: {portfolio_periods}")
        print(f"  valor_pct NULL: {portfolio_null_values}")
        print(f"  Duplicados: {portfolio_duplicates}")

        # ----------------------------------------------------
        # Portfolio por literal
        # ----------------------------------------------------

        literal_count_fact = connection.execute(
            """
            SELECT COUNT(*)
            FROM fact_portfolio_literal
            """
        ).fetchone()[0]

        literal_periods = connection.execute(
            """
            SELECT COUNT(DISTINCT period_id)
            FROM fact_portfolio_literal
            """
        ).fetchone()[0]

        literal_null_values = connection.execute(
            """
            SELECT COUNT(*)
            FROM fact_portfolio_literal
            WHERE valor_pct IS NULL
            """
        ).fetchone()[0]

        literal_duplicates = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    period_id,
                    afap_id,
                    subfund_id,
                    literal_id,
                    COUNT(*) AS cantidad
                FROM fact_portfolio_literal
                GROUP BY
                    period_id,
                    afap_id,
                    subfund_id,
                    literal_id
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        literal_invalid_totals = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    period_id,
                    afap_id,
                    subfund_id,
                    SUM(valor_pct) AS total_pct
                FROM fact_portfolio_literal
                GROUP BY
                    period_id,
                    afap_id,
                    subfund_id
                HAVING ABS(SUM(valor_pct) - 1.0) > 0.0002
            )
            """
        ).fetchone()[0]

        print("\nFACT_PORTFOLIO_LITERAL")

        print(
            f"  Filas: {literal_count_fact}"
        )

        print(
            f"  Períodos con datos: {literal_periods}"
        )

        print(
            f"  valor_pct NULL: {literal_null_values}"
        )

        print(
            f"  Duplicados: {literal_duplicates}"
        )

        print(
            "  Totales fuera de tolerancia: "
            f"{literal_invalid_totals}"
        )

        # ----------------------------------------------------
        # Returns
        # ----------------------------------------------------

        returns_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM fact_returns
            """
        ).fetchone()[0]

        returns_periods = connection.execute(
            """
            SELECT COUNT(DISTINCT period_id)
            FROM fact_returns
            """
        ).fetchone()[0]

        returns_null_values = connection.execute(
            """
            SELECT COUNT(*)
            FROM fact_returns
            WHERE rentabilidad_neta IS NULL
            """
        ).fetchone()[0]

        returns_duplicates = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    period_id,
                    afap_id,
                    tipo_metrica,
                    subfund_id,
                    COUNT(*) AS cantidad
                FROM fact_returns
                GROUP BY
                    period_id,
                    afap_id,
                    tipo_metrica,
                    subfund_id
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        print("\nFACT_RETURNS")
        print(f"  Filas: {returns_count}")
        print(f"  Períodos con datos: {returns_periods}")
        print(f"  rentabilidad_neta NULL: {returns_null_values}")
        print(f"  Duplicados: {returns_duplicates}")

        # ----------------------------------------------------
        # Integridad referencial
        # ----------------------------------------------------

        portfolio_orphans = connection.execute(
            """
            SELECT COUNT(*)
            FROM fact_portfolio_composition f
            LEFT JOIN dim_afap d
                ON f.afap_id = d.afap_id
            WHERE d.afap_id IS NULL
            """
        ).fetchone()[0]

        returns_orphans = connection.execute(
            """
            SELECT COUNT(*)
            FROM fact_returns f
            LEFT JOIN dim_afap d
                ON f.afap_id = d.afap_id
            WHERE d.afap_id IS NULL
            """
        ).fetchone()[0]

        literal_orphans = connection.execute(
            """
            SELECT COUNT(*)
            FROM fact_portfolio_literal f
            LEFT JOIN dim_literal d
                ON f.literal_id = d.literal_id
            WHERE d.literal_id IS NULL
            """
        ).fetchone()[0]

        print("\nINTEGRIDAD REFERENCIAL")
        print(
            "  Portfolio sin AFAP válida: "
            f"{portfolio_orphans}"
        )

        print(
            "  Literal fact sin literal válido: "
            f"{literal_orphans}"
        )

        print(
            "  Returns sin AFAP válida: "
            f"{returns_orphans}"
        )

        # ----------------------------------------------------
        # Resultado
        # ----------------------------------------------------

        errors = []

        if period_count != 32:
            errors.append(
                "dim_period no contiene 32 períodos"
            )

        if portfolio_count != 1205:
            errors.append(
                "fact_portfolio_composition "
                "no contiene 1205 filas"
            )

        if portfolio_periods != 8:
            errors.append(
                "portfolio no contiene 8 períodos"
            )

        if portfolio_null_values != 95:
            errors.append(
                "cantidad inesperada de valor_pct NULL"
            )

        if portfolio_duplicates != 0:
            errors.append(
                "portfolio contiene duplicados"
            )

        if literal_count != 6:
            errors.append(
                "dim_literal no contiene 6 literales"
            )

        if literal_count_fact != 720:
            errors.append(
                "fact_portfolio_literal "
                "no contiene 720 filas"
            )

        if literal_periods != 8:
            errors.append(
                "portfolio literal no contiene 8 períodos"
            )

        if literal_duplicates != 0:
            errors.append(
                "portfolio literal contiene duplicados"
            )

        if literal_invalid_totals != 0:
            errors.append(
                "portfolio literal contiene composiciones "
                "que no suman aproximadamente 100%"
            )

        if literal_orphans != 0:
            errors.append(
                "portfolio literal contiene literales "
                "sin dimensión"
            )

        if returns_count != 120:
            errors.append(
                "fact_returns no contiene 120 filas"
            )

        if returns_periods != 6:
            errors.append(
                "returns no contiene 6 períodos"
            )

        if returns_null_values != 0:
            errors.append(
                "returns contiene rentabilidades NULL"
            )

        if returns_duplicates != 0:
            errors.append(
                "returns contiene duplicados"
            )

        if portfolio_orphans != 0:
            errors.append(
                "portfolio contiene AFAP sin dimensión"
            )

        if returns_orphans != 0:
            errors.append(
                "returns contiene AFAP sin dimensión"
            )
      
        if errors:
            print(
                "\nRESULTADO: SE DETECTARON ERRORES"
            )

            for error in errors:
                print(
                    f"  - {error}"
                )

            raise ValueError(
                "La base no superó los controles "
                "de calidad."
            )

        print(
            "\nRESULTADO: TODOS LOS CONTROLES OK"
        )

    finally:
        connection.close()


if __name__ == "__main__":
    validate_database()