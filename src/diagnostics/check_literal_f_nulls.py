
from pathlib import Path

import duckdb
import pdfplumber


DB_PATH = Path("data/afap_analytics.duckdb")
RAW_DIR = Path("data/raw")


def get_null_cases():
    """Obtiene los literales F sin porcentaje en DuckDB."""
    con = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        return con.execute("""
            SELECT
                p.periodo,
                a.afap_nombre,
                s.subfund_nombre,
                f.archivo_origen
            FROM fact_portfolio_literal f
            JOIN dim_period p
                ON f.period_id = p.period_id
            JOIN dim_afap a
                ON f.afap_id = a.afap_id
            JOIN dim_subfund s
                ON f.subfund_id = s.subfund_id
            JOIN dim_literal l
                ON f.literal_id = l.literal_id
            WHERE f.valor_pct IS NULL
              AND l.literal = 'LITERAL F'
            ORDER BY
                p.periodo,
                a.afap_nombre
        """).fetchall()
    finally:
        con.close()


def inspect_pdf(pdf_path):
    """Extrae la fila del LITERAL F conservando coordenadas."""
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""

            if (
                "SUBFONDO DE ACUMUL" not in text.upper()
                or "LITERAL F" not in text.upper()
            ):
                continue

            words = page.extract_words(
                x_tolerance=2,
                y_tolerance=3
            )

            # Localizar la fila que contiene "Total LITERAL F".
            for word in words:
                if word["text"].upper() != "LITERAL":
                    continue

                y = word["top"]

                row = [
                    w for w in words
                    if abs(w["top"] - y) < 4
                ]

                row_text = " ".join(
                    w["text"] for w in row
                ).upper()

                if "TOTAL" not in row_text or "F" not in row_text:
                    continue

                values = [
                    (
                        round(w["x0"], 2),
                        w["text"]
                    )
                    for w in row
                    if "%" in w["text"]
                ]

                return page_number, values

    return None, None



def main():
    cases = get_null_cases()

    # Coordenadas aproximadas de las columnas
    # de la página de Acumulación.
    columns = {
        "AFAP SURA": 450,
        "INTEGRACION AFAP": 606,
        "REPUBLICA AFAP": 762,
        "AFAP ITAU": 918,
        "TOTAL SISTEMA": 1076,
    }

    print("=== VERIFICACIÓN DEL LITERAL F ===")

    checked_files = {}

    for periodo, afap, subfondo, filename in cases:
        pdf_path = RAW_DIR / filename

        if not pdf_path.exists():
            print(f"{periodo} | {afap} | PDF NO ENCONTRADO")
            continue

        if filename not in checked_files:
            _, values = inspect_pdf(pdf_path)
            checked_files[filename] = values

        values = checked_files[filename]

        if values is None:
            print(f"{periodo} | {afap} | FILA NO ENCONTRADA")
            continue

        expected_x = columns[afap]

        matches = [
            value
            for x, value in values
            if abs(x - expected_x) < 40
        ]

        if matches:
            print(
                f"{periodo} | {afap} | "
                f"REVISAR: PDF contiene {matches[0]}"
            )
        else:
            print(
                f"{periodo} | {afap} | "
                "OK: celda vacía en el PDF"
            )


if __name__ == "__main__":
    main()