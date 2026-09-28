"""Actualiza el histórico en una copia; nunca reconstruye la base original."""
import argparse
import os
from pathlib import Path
import shutil
import tempfile

import duckdb
import pandas as pd

from load_assets import load_fact_portfolio_assets
from load_facts import load_fact_portfolio_composition, load_fact_portfolio_literal

ROOT = Path(__file__).resolve().parent.parent


def validate_history(report, literal):
    periods = set(pd.to_datetime(report.fecha, errors="raise").dt.strftime("%Y-%m"))
    other = set(pd.to_datetime(literal.fecha, errors="raise").dt.strftime("%Y-%m"))
    if not periods or periods != other:
        raise ValueError("Los históricos tienen distinta cobertura mensual o están vacíos.")
    expected = set(pd.period_range(min(periods), max(periods), freq="M").astype(str))
    if periods != expected:
        raise ValueError("Hay meses faltantes dentro del histórico.")
    if report.duplicated(["fecha", "pagina", "fila_id", "afap_normalizada"]).any():
        raise ValueError("Hay filas duplicadas en el reporte completo.")
    sub = report.loc[report.seccion.eq("COMPOSICION") & report.fondo.isin(["CRECIMIENTO", "ACUMULACION", "RETIRO"])]
    totals = sub.loc[sub.tipo_fila.eq("TOTAL_GENERAL")]
    if len(totals) != 15 * len(periods) or totals.valor_pct.isna().any() or (totals.valor_pct - 1).abs().gt(.0002).any():
        raise ValueError("Faltan totales porcentuales o no equivalen al 100 %.")
    # El archivo de literales debe coincidir celda a celda con los subtotales.
    keys = ["fecha", "subfondo", "afap_normalizada", "literal"]
    source = sub.loc[sub.tipo_fila.eq("SUBTOTAL"), keys + ["valor_pct"]]
    joined = source.merge(literal[keys + ["valor_pct"]], on=keys, how="outer", validate="one_to_one", indicator=True)
    same = joined.valor_pct_x.eq(joined.valor_pct_y) | (joined.valor_pct_x.isna() & joined.valor_pct_y.isna())
    if not joined._merge.eq("both").all() or not same.all():
        raise ValueError("Los subtotales del reporte no coinciden con el histórico de literales.")
    print(f"Históricos: {len(periods)} meses, {len(report)} filas completas, {len(literal)} literales.")
    return periods


def migrate(source_db, output_db, portfolio_file, literal_file):
    source_db, output_db = Path(source_db).resolve(), Path(output_db).resolve()
    if source_db == output_db or output_db.exists():
        raise ValueError("La salida debe ser un archivo nuevo, distinto de la base original.")
    if not source_db.is_file():
        raise FileNotFoundError(source_db)
    report, literal = pd.read_csv(portfolio_file), pd.read_csv(literal_file)
    periods = validate_history(report, literal)
    output_db.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="portfolio_", suffix=".duckdb", dir=output_db.parent)
    os.close(fd)
    temp = Path(name)
    con = None
    output_created = False
    try:
        # Abrir en lectura impide copiar mientras otro proceso escribe la base.
        with duckdb.connect(str(source_db), read_only=True) as original:
            if Path(str(source_db) + ".wal").exists():
                raise ValueError("La base tiene un WAL pendiente. Cerrá las conexiones antes de copiarla.")
            shutil.copyfile(source_db, temp)
        con = duckdb.connect(str(temp))
        returns_before = con.execute("SELECT * FROM fact_returns ORDER BY ALL").fetchall()
        views_before = con.execute("SELECT view_name, sql FROM duckdb_views() WHERE NOT internal").fetchall()
        dims = ["dim_period", "dim_afap", "dim_subfund", "dim_currency", "dim_instrument", "dim_literal"]
        dims_before = {t: con.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in dims}
        old_periods = {r[0] for r in con.execute("""
            SELECT DISTINCT p.periodo FROM dim_period p JOIN (
                SELECT period_id FROM fact_portfolio_composition UNION
                SELECT period_id FROM fact_portfolio_literal
            ) f USING(period_id)
        """).fetchall()}
        if not old_periods <= periods:
            raise ValueError("El CSV omite meses ya cargados. No se publicará una base incompleta.")
        con.execute("BEGIN TRANSACTION")
        # Agregar nuevas categorías conservando las claves existentes.
        allowed = {"D. TRANSITORIA"} | {f"LITERAL {x}" for x in "ABCDEF"}
        labels = set(literal.literal.dropna())
        if not labels <= allowed or literal.literal.isna().any():
            raise ValueError("Categorías de literal desconocidas o vacías.")
        present = {row[1] for row in dims_before["dim_literal"]}
        next_id = max((row[0] for row in dims_before["dim_literal"]), default=0)
        for label in sorted(labels - present):
            next_id += 1
            con.execute("INSERT INTO dim_literal VALUES (?, ?)", [next_id, label])
        con.execute((ROOT / "sql" / "portfolio_assets.sql").read_text(encoding="utf-8"))
        load_fact_portfolio_composition(con, portfolio_file)
        load_fact_portfolio_literal(con, literal_file)
        count = load_fact_portfolio_assets(con, report)
        if con.execute("SELECT * FROM fact_returns ORDER BY ALL").fetchall() != returns_before:
            raise ValueError("La rentabilidad cambió durante la actualización.")
        for table, rows in dims_before.items():
            after = con.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            if (table != "dim_literal" and after != rows) or not set(rows) <= set(after):
                raise ValueError(f"Cambió una clave existente: {table}.")
        views_after = dict(con.execute("SELECT view_name, sql FROM duckdb_views() WHERE NOT internal").fetchall())
        for view, sql in views_before:
            if view != "vw_portfolio_assets" and views_after.get(view) != sql:
                raise ValueError(f"Cambió la vista existente {view}.")
        for fact, view in [("fact_portfolio_composition", "vw_portfolio_instrument"),
                           ("fact_portfolio_literal", "vw_portfolio_literal"),
                           ("fact_portfolio_assets", "vw_portfolio_assets")]:
            if con.execute(f"SELECT count(*) FROM {fact}").fetchone() != con.execute(f"SELECT count(*) FROM {view}").fetchone():
                raise ValueError(f"La vista {view} pierde registros.")
        con.execute("COMMIT")
        con.execute("CHECKPOINT")
        con.close()
        con = None
        # Evita reemplazar una salida creada por otra ejecución simultánea.
        with output_db.open("xb") as target, temp.open("rb") as source:
            output_created = True
            shutil.copyfileobj(source, target)
        print(f"OK - {count} importes cargados; rentabilidad preservada ({len(returns_before)} filas).")
        print(f"Base actualizada: {output_db}")
        print(f"Base original conservada: {source_db}")
    except Exception:
        if con is not None:
            con.close()  # Revierte la transacción pendiente.
        if output_created:
            output_db.unlink(missing_ok=True)
        raise
    finally:
        temp.unlink(missing_ok=True)
        Path(str(temp) + ".wal").unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-db", type=Path, default=ROOT / "data/afap_analytics.duckdb")
    parser.add_argument("--output-db", type=Path, default=ROOT / "data/afap_analytics_actualizada.duckdb")
    parser.add_argument("--portfolio", type=Path, default=ROOT / "data/processed/portfolio_composition_history.csv")
    parser.add_argument("--literal", type=Path, default=ROOT / "data/processed/portfolio_literal_history.csv")
    args = parser.parse_args()
    migrate(args.source_db, args.output_db, args.portfolio, args.literal)
