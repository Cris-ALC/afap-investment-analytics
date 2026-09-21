from pathlib import Path
import argparse

import duckdb

from load_dimensions import (
    load_dim_afap,
    load_dim_subfund,
    load_dim_currency,
    load_dim_instrument,
    load_dim_literal,
)

from load_facts import (
    load_fact_portfolio_composition,
    load_fact_portfolio_literal,
    load_fact_returns,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"

DATABASE_PATH = (
    DATA_DIR
    / "afap_analytics.duckdb"
)

CREATE_TABLES_SQL = (
    PROJECT_ROOT
    / "sql"
    / "create_tables.sql"
)

LOAD_DIMENSIONS_SQL = (
    PROJECT_ROOT
    / "sql"
    / "load_dimensions.sql"
)


def validate_files():
    """
    Comprueba que existan los archivos SQL
    necesarios para construir la base.
    """

    required_files = [
        CREATE_TABLES_SQL,
        LOAD_DIMENSIONS_SQL,
    ]

    for file_path in required_files:
        if not file_path.exists():
            raise FileNotFoundError(
                f"No se encontró el archivo: {file_path}"
            )


def create_database(rebuild=False):
    """
    Crea la base DuckDB y ejecuta
    el modelo dimensional.

    Si rebuild=True, elimina primero
    la base existente y la reconstruye
    completamente desde cero.
    """

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    validate_files()

    print(
        "\n=== AFAP ANALYTICS DATABASE ===\n"
    )

    if rebuild and DATABASE_PATH.exists():
        print(
            f"Eliminando base existente: {DATABASE_PATH}"
        )

        DATABASE_PATH.unlink()

        print(
            "Base existente eliminada."
        )

    elif rebuild:
        print(
            "No existe una base previa. "
            "Se creará desde cero."
        )

    else:
        print(
            "Modo normal: se utilizará la base existente "
            "si ya fue creada."
        )

    create_tables_sql = (
        CREATE_TABLES_SQL.read_text(
            encoding="utf-8"
        )
    )

    load_dimensions_sql = (
        LOAD_DIMENSIONS_SQL.read_text(
            encoding="utf-8"
        )
    )

    connection = duckdb.connect(
        str(DATABASE_PATH)
    )

    try:
        # ----------------------------------------------------
        # Crear estructura de tablas
        # ----------------------------------------------------

        connection.execute(
            create_tables_sql
        )

        print(
            "\nModelo dimensional creado."
        )

        # ----------------------------------------------------
        # Cargar dimensiones generadas por SQL
        # ----------------------------------------------------

        connection.execute(
            load_dimensions_sql
        )

        print(
            "dim_period cargada."
        )

        # ----------------------------------------------------
        # Cargar dimensiones desde datasets procesados
        # ----------------------------------------------------

        load_dim_afap(
            connection
        )

        load_dim_subfund(
            connection
        )

        load_dim_currency(
            connection
        )

        load_dim_instrument(
            connection
        )

        load_dim_literal(
            connection
        )

        load_fact_portfolio_composition(
            connection
        )

        load_fact_portfolio_literal(
            connection
        )
        
        load_fact_returns(
            connection
        )
        
        # ----------------------------------------------------
        # Mostrar tablas disponibles
        # ----------------------------------------------------

        tables = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_name
            """
        ).fetchall()

        print(
            "\nTablas disponibles:"
        )

        for table in tables:
            print(
                f"  - {table[0]}"
            )

        # ----------------------------------------------------
        # Control dim_period
        # ----------------------------------------------------

        period_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM dim_period
            """
        ).fetchone()[0]

        print(
            f"\nPeríodos cargados: {period_count}"
        )

        if period_count != 32:
            raise ValueError(
                "Se esperaban 32 períodos "
                f"y se encontraron {period_count}."
            )

        # ----------------------------------------------------
        # Control dim_afap
        # ----------------------------------------------------

        afap_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM dim_afap
            """
        ).fetchone()[0]

        print(
            f"Entidades AFAP cargadas: {afap_count}"
        )

        if afap_count != 6:
            raise ValueError(
                "Se esperaban 6 entidades en dim_afap "
                f"y se encontraron {afap_count}."
            )

        # ----------------------------------------------------
        # Control dim_subfund
        # ----------------------------------------------------

        subfund_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM dim_subfund
            """
        ).fetchone()[0]

        print(
            f"Subfondos cargados: {subfund_count}"
        )

        if subfund_count != 3:
            raise ValueError(
                "Se esperaban 3 subfondos "
                f"y se encontraron {subfund_count}."
            )

        # ----------------------------------------------------
        # Control dim_currency
        # ----------------------------------------------------

        currency_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM dim_currency
            """
        ).fetchone()[0]

        print(
            f"Monedas cargadas: {currency_count}"
        )

        if currency_count != 4:
            raise ValueError(
                "Se esperaban 4 monedas "
                f"y se encontraron {currency_count}."
            )

        # ----------------------------------------------------
        # Control dim_literal
        # ----------------------------------------------------

        literal_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM dim_literal
            """
        ).fetchone()[0]

        print(
            f"Literales cargados: {literal_count}"
        )

        if literal_count != 6:
            raise ValueError(
                "Se esperaban 6 literales "
                f"y se encontraron {literal_count}."
            )


        # ----------------------------------------------------
        # Resultado final
        # ----------------------------------------------------

        print(
            "\nControles de base de datos: OK"
        )

    finally:
        connection.close()

        print(
            "Conexión cerrada correctamente."
        )


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Crea la base DuckDB del proyecto "
            "AFAP Investment Analytics."
        )
    )

    parser.add_argument(
        "--rebuild",
        action="store_true",
        help=(
            "Elimina la base existente y "
            "la reconstruye desde cero."
        ),
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    create_database(
        rebuild=args.rebuild
    )