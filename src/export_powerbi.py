
from pathlib import Path
import argparse
import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data/afap_analytics_actualizada.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "powerbi/data_actualizada"

# Vistas existentes
VIEWS = [
    "vw_portfolio_literal",
    "vw_portfolio_instrument",
    "vw_returns",
    "vw_gross_returns",
]

# Dimensiones existentes
DIMENSIONS = [
    "dim_period",
    "dim_afap",
    "dim_subfund",
    "dim_literal",
    "dim_instrument",
    "dim_currency",
]


def export_views(db_path=DB_PATH, output_dir=OUTPUT_DIR):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path), read_only=True)

    try:
        available = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
        views = VIEWS + (["vw_portfolio_assets"] if "vw_portfolio_assets" in available else [])
        for table in views + DIMENSIONS:
            output_path = output_dir / f"{table}.csv"
            escaped_path = output_path.as_posix().replace("'", "''")

            con.execute(
                f"""
                COPY (
                    SELECT *
                    FROM {table}
                )
                TO '{escaped_path}'
                (HEADER, DELIMITER ',')
                """
            )

            count = con.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            print(
                f"OK: {output_path} | {count} registros"
            )

    finally:
        con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exporta vistas y dimensiones para Power BI.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    export_views(args.db, args.output)
    
