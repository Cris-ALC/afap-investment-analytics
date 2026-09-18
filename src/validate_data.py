from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "portfolio_composition_history.csv"


def load_data():
    """Carga el histórico consolidado de composición del portafolio."""

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo histórico: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    return df


def validate_structure(df):
    """Realiza controles básicos sobre la estructura del dataset."""

    print("\n=== VALIDACIÓN ESTRUCTURAL ===")

    print(f"Filas: {len(df):,}")
    print(f"Columnas: {len(df.columns)}")

    fechas = sorted(df["fecha"].dropna().unique())
    print(f"Períodos: {len(fechas)}")
    print(f"Desde: {fechas[0]}")
    print(f"Hasta: {fechas[-1]}")

    subfondos = sorted(df["subfondo"].dropna().unique())
    print(f"Subfondos: {subfondos}")

    afaps = sorted(df["afap_normalizada"].dropna().unique())
    print(f"AFAP: {afaps}")

    duplicados = df.duplicated().sum()
    print(f"Filas duplicadas: {duplicados}")

    print("\nValores faltantes por columna:")

    faltantes = df.isna().sum()
    faltantes = faltantes[faltantes > 0]

    if faltantes.empty:
        print("OK - No se detectaron valores faltantes.")
    else:
        print(faltantes)

    if duplicados == 0:
        print("OK - No se detectaron filas completamente duplicadas.")
    else:
        print("ADVERTENCIA - Se detectaron filas duplicadas.")

    print("\n=== VALORES FALTANTES POR PERÍODO Y SUBFONDO ===")

    missing = df.query("valor_pct != valor_pct")

    missing_summary = pd.crosstab(
        missing.fecha,
        missing.subfondo
    )

    print(missing_summary)

    print("\n=== DETALLE DE VALORES FALTANTES ===")

    missing_detail = missing.loc[
        :,
        [
            "fecha",
            "subfondo",
            "afap_normalizada",
            "literal",
            "instrumento",
            "moneda",
        ]
    ]

    print(
        missing_detail.to_string(
            index=False
        )
    )


def main():

    print("AFAP Investment Analytics - Validación de datos")

    df = load_data()

    validate_structure(df)


if __name__ == "__main__":
    main()