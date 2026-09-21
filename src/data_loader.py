from pathlib import Path
from collections import defaultdict
import re

import pdfplumber
import pandas as pd



PDF_PATH = Path("data/raw/cocf03d0726.pdf")


# Posición horizontal aproximada de cada columna
def detect_columns(page):
    """
    Detecta automáticamente la posición horizontal
    de las cinco columnas de AFAP en cada página.
    """

    words = page.extract_words()

    header_names = {
        "SURA": "SURA",
        "INTEGRACIÓN": "INTEGRACION",
        "INTEGRACION": "INTEGRACION",
        "REPÚBLICA": "REPUBLICA",
        "REPUBLICA": "REPUBLICA",
        "ITAÚ": "ITAU",
        "ITAU": "ITAU",
        "SISTEMA": "TOTAL_SISTEMA",
    }

    columns = {}

    for word in words:
        text = word["text"].upper()

        if text in header_names:
            column_name = header_names[text]

            # Usamos el centro horizontal del encabezado.
            center = (
                word["x0"] + word["x1"]
            ) / 2

            columns[column_name] = center

    expected = {
        "SURA",
        "INTEGRACION",
        "REPUBLICA",
        "ITAU",
        "TOTAL_SISTEMA",
    }

    if set(columns) != expected:
        raise ValueError(
            "No fue posible detectar correctamente "
            f"las columnas del PDF. Detectadas: {columns}"
        )

    return columns


def assign_column(x0, column_x):
    """
    Determina a qué AFAP pertenece un porcentaje
    utilizando las columnas detectadas en la página.
    """

    ordered_columns = sorted(
        column_x,
        key=lambda column: column_x[column]
    )

    centers = [
        column_x[column]
        for column in ordered_columns
    ]

    boundaries = []

    for left, right in zip(
        centers,
        centers[1:]
    ):
        boundaries.append(
            (left + right) / 2
        )

    for index, column in enumerate(
        ordered_columns
    ):
        left_boundary = (
            float("-inf")
            if index == 0
            else boundaries[index - 1]
        )

        right_boundary = (
            float("inf")
            if index == len(ordered_columns) - 1
            else boundaries[index]
        )

        if left_boundary <= x0 < right_boundary:
            return column

    return None


def extract_rows(page):
    """
    Reconstruye las filas de una página utilizando
    las coordenadas de cada palabra.
    """

    words = page.extract_words()

    column_x = detect_columns(page)

    # El inicio de la primera columna numérica
    # también nos sirve para separar la descripción.
    first_column_x = min(column_x.values())

    rows = defaultdict(list)

    for word in words:
        top = round(word["top"], 1)
        rows[top].append(word)

    extracted_rows = []

    for top in sorted(rows):

        row_words = sorted(
            rows[top],
            key=lambda word: word["x0"]
        )

        description_parts = []
        percentages = {}

        for word in row_words:
            text = word["text"]

            if text.endswith("%"):
                column = assign_column(
                    word["x0"],
                    column_x
                )

                if column:
                    percentages[column] = text

            else:
                if word["x0"] < first_column_x:
                    description_parts.append(text)

        description = " ".join(
            description_parts
        ).strip()

        if percentages:
            extracted_rows.append(
                {
                    "description": description,
                    **percentages,
                }
            )

    return extracted_rows

def extract_report_date(text: str) -> pd.Timestamp:
    """
    Extrae la fecha de corte del encabezado del reporte.
    Ejemplo: 31/8/2026 -> Timestamp('2026-08-31')
    """

    match = re.search(
        r"\b(\d{1,2}/\d{1,2}/\d{4})\b",
        text
    )

    if not match:
        raise ValueError("No se pudo identificar la fecha del reporte.")

    return pd.to_datetime(
        match.group(1),
        format="%d/%m/%Y"
    )

def identify_section(text: str) -> str:
    """
    Identifica el fondo o subfondo de la página.
    """

    text = text.upper()

    if "SUBFONDO DE CRECIMIENTO" in text:
        return "CRECIMIENTO"

    if "SUBFONDO DE ACUMULACIÓN" in text:
        return "ACUMULACION"

    if "SUBFONDO DE RETIRO" in text:
        return "RETIRO"

    if "FONDO VOLUNTARIO PREVISIONAL" in text:
        return "FVP"

    return "DESCONOCIDO"

def build_composition_dataframe(
    pdf_path: Path,
    page_index: int = 0
):

    with pdfplumber.open(pdf_path) as pdf:

        page = pdf.pages[page_index]

        text = page.extract_text() or ""

        rows = extract_rows(page)

    df = pd.DataFrame(rows)

    column_order = [
        "description",
        "SURA",
        "INTEGRACION",
        "REPUBLICA",
        "ITAU",
        "TOTAL_SISTEMA",
    ]

    df = df.reindex(columns=column_order)

    fecha = extract_report_date(text)
    subfondo = identify_section(text)

    return df, fecha, subfondo

def classify_row(description: str) -> str:
    """
    Clasifica cada fila del reporte según su función.
    """

    if not isinstance(description, str):
        return "UNKNOWN"

    text = description.strip().upper()

    if text == "TOTALES":
        return "TOTAL_GENERAL"

    if text.startswith("PARTICIPACIÓN"):
        return "PARTICIPACION"

    if text.startswith("TOTAL LITERAL"):
        return "SUBTOTAL"

    if text == "TOTAL D. TRANSITORIA":
        return "SUBTOTAL"

    return "DETALLE"


def transform_composition_to_long(
    df: pd.DataFrame,
    fecha: pd.Timestamp,
    subfondo: str
) -> pd.DataFrame:

    df_long = df.melt(
        id_vars=["description"],
        value_vars=[
            "SURA",
            "INTEGRACION",
            "REPUBLICA",
            "ITAU",
            "TOTAL_SISTEMA",
        ],
        var_name="afap",
        value_name="valor_pct",
    )

    df_long["valor_pct"] = (
        df_long["valor_pct"]
        .str.replace("%", "", regex=False)
        .astype(float)
        / 100
    )

    df_long["fecha"] = fecha
    df_long["subfondo"] = subfondo

    df_long = df_long.rename(
        columns={
            "description": "instrumento_raw"
        }
    )

    df_long["tipo_fila"] = df_long["instrumento_raw"].apply(
        classify_row
    )

    df_long = df_long[
        [
            "fecha",
            "subfondo",
            "afap",
            "tipo_fila",
            "instrumento_raw",
            "valor_pct",
        ]
    ]

    return df_long


def load_all_subfunds(pdf_path: Path) -> pd.DataFrame:
    """
    Procesa Crecimiento, Acumulación y Retiro
    y los une en un único DataFrame.
    """

    composition_pages = [0, 2, 4]

    dataframes = []

    for page_index in composition_pages:

        df_wide, fecha, subfondo = build_composition_dataframe(
            pdf_path,
            page_index=page_index
        )

        df_long = transform_composition_to_long(
            df_wide,
            fecha,
            subfondo
        )

        dataframes.append(df_long)

    df_all = pd.concat(
        dataframes,
        ignore_index=True
    )

    return df_all

def get_portfolio_detail(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve únicamente las filas de detalle de la composición,
    excluyendo subtotales, totales y participaciones.
    """

    df_detail = df[
        df["tipo_fila"] == "DETALLE"
    ].copy()

    return df_detail

def get_portfolio_literal_totals(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Devuelve la composición del activo a nivel de literal.

    Incluye:
    - D. TRANSITORIA
    - LITERAL A
    - LITERAL B
    - LITERAL C
    - LITERAL D
    - LITERAL F

    Excluye la fila TOTALES, que se utiliza únicamente
    como control de calidad.
    """

    df_totals = df[
        df["tipo_fila"] == "SUBTOTAL"
    ].copy()

    df_totals["literal"] = (
        df_totals["instrumento_raw"]
        .str.upper()
        .str.replace(
            "TOTAL ",
            "",
            regex=False,
        )
        .str.strip()
    )

    return df_totals

def enrich_detail_structure(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstruye la jerarquía:
    Literal -> Instrumento -> Moneda.

    También resuelve filas de continuación como UP o US,
    que heredan el instrumento de la fila anterior.
    """

    df = df.copy()

    currencies = {"UY", "UI", "US", "UP", "UR"}

    literals = []
    instruments = []
    currencies_found = []

    # Guardamos el estado por subfondo y AFAP
    states = {}

    for _, row in df.iterrows():

        key = (
            row["fecha"],
            row["subfondo"],
            row["afap"],
        )

        if key not in states:
            states[key] = {
                "literal": None,
                "instrumento": None,
            }

        state = states[key]

        raw = str(row["instrumento_raw"]).strip()

        # -------------------------------------------------
        # 1. Detectar si comienza un nuevo Literal
        # -------------------------------------------------

        literal_match = re.match(
            r"^LITERAL\s+([A-Z])"
            r"(?:\s*-\s*\(Ver Anexo\))?\s+(.+)$",
            raw,
            flags=re.IGNORECASE,
        )

        if literal_match:

            state["literal"] = (
                f"LITERAL {literal_match.group(1).upper()}"
            )

            remaining_text = literal_match.group(2).strip()

        else:
            remaining_text = raw

        # -------------------------------------------------
        # 2. Detectar filas que solo contienen moneda
        #    Ej.: UP / US
        # -------------------------------------------------

        if remaining_text.upper() in currencies:

            currency = remaining_text.upper()

            # Hereda el instrumento anterior
            instrument = state["instrumento"]

        else:

            # ---------------------------------------------
            # 3. Separar moneda al final del texto
            # ---------------------------------------------

            parts = remaining_text.rsplit(" ", 1)

            if (
                len(parts) == 2
                and parts[1].upper() in currencies
            ):

                instrument = parts[0].strip()
                currency = parts[1].upper()

            else:

                instrument = remaining_text
                currency = None

            # Guardamos el último instrumento válido
            state["instrumento"] = instrument

        literals.append(state["literal"])
        instruments.append(instrument)
        currencies_found.append(currency)

    df["literal"] = literals
    df["instrumento"] = instruments
    df["moneda_raw"] = currencies_found

    return df

def normalize_dimensions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega versiones normalizadas de AFAP y moneda,
    conservando los valores originales extraídos del PDF.
    """

    df = df.copy()

    afap_map = {
        "SURA": "AFAP SURA",
        "INTEGRACION": "INTEGRACION AFAP",
        "REPUBLICA": "REPUBLICA AFAP",
        "ITAU": "AFAP ITAU",
        "TOTAL_SISTEMA": "TOTAL SISTEMA",
    }

    currency_map = {
        "UY": "UYU",
        "US": "USD",
        "UI": "UI",
        "UP": "UP",
        "UR": "UR",
    }

    df["afap_normalizada"] = df["afap"].map(afap_map)

    df["moneda"] = df["moneda_raw"].map(currency_map)

    return df

def validate_portfolio_data(
    df_all: pd.DataFrame,
    df_detail: pd.DataFrame
) -> None:
    """
    Ejecuta controles básicos de calidad sobre
    los datos extraídos del reporte.
    """

    print("\n--- CONTROLES DE CALIDAD ---")

    expected_subfunds = {
        "CRECIMIENTO",
        "ACUMULACION",
        "RETIRO",
    }

    detected_subfunds = set(
        df_all["subfondo"].dropna().unique()
    )

    if detected_subfunds == expected_subfunds:
        print("OK - Se detectaron los 3 subfondos esperados.")
    else:
        print(
            "ERROR - Subfondos detectados:",
            detected_subfunds
        )

    expected_afaps = {
        "SURA",
        "INTEGRACION",
        "REPUBLICA",
        "ITAU",
        "TOTAL_SISTEMA",
    }

    detected_afaps = set(
        df_all["afap"].dropna().unique()
    )

    if detected_afaps == expected_afaps:
        print("OK - Se detectaron todas las AFAP y el total del sistema.")
    else:
        print(
            "ERROR - Entidades detectadas:",
            detected_afaps
        )

    invalid_percentages = df_all[
        (df_all["valor_pct"] < 0)
        | (df_all["valor_pct"] > 1)
    ]

    if invalid_percentages.empty:
        print("OK - No hay porcentajes fuera del rango 0%-100%.")
    else:
        print(
            "ERROR - Hay porcentajes fuera del rango esperado."
        )

    missing_instruments = df_detail[
        df_detail["instrumento"].isna()
    ]

    if missing_instruments.empty:
        print("OK - No hay registros de detalle sin instrumento.")
    else:
        print(
            f"ADVERTENCIA - Hay {len(missing_instruments)} "
            "registros sin instrumento."
        )

def validate_total_percentages(df_all: pd.DataFrame) -> None:
    """
    Verifica que la fila TOTALES sea igual a 100%
    para cada subfondo y cada AFAP/Total Sistema.
    """

    totals = df_all[
        df_all["tipo_fila"] == "TOTAL_GENERAL"
    ].copy()

    print("\n--- CONTROL DE TOTALES ---")

    invalid_totals = totals[
        (totals["valor_pct"] - 1.0).abs() > 0.0001
    ]

    if invalid_totals.empty:
        print(
            "OK - Todos los totales por subfondo y entidad "
            "son iguales a 100%."
        )
    else:
        print("ERROR - Se encontraron totales distintos de 100%:")

        print(
            invalid_totals[
                [
                    "subfondo",
                    "afap",
                    "valor_pct",
                ]
            ].to_string(index=False)
        )

def validate_literal_percentages(
    df_literals: pd.DataFrame
) -> None:
    """
    Valida la composición completa a nivel de literal.

    Para cada combinación subfondo + entidad:
    - deben existir las 6 categorías esperadas;
    - la suma debe ser aproximadamente 100%.

    Se admite una pequeña diferencia por redondeo.
    """

    print("\n--- CONTROL DE COMPOSICIÓN POR LITERAL ---")

    expected_literals = {
        "D. TRANSITORIA",
        "LITERAL A",
        "LITERAL B",
        "LITERAL C",
        "LITERAL D",
        "LITERAL F",
    }

    detected_literals = set(
        df_literals["literal"]
        .dropna()
        .unique()
    )

    if detected_literals != expected_literals:
        raise ValueError(
            "Categorías de literal inesperadas. "
            f"Detectadas: {detected_literals}"
        )

    totals = (
        df_literals
        .groupby(
            ["subfondo", "afap"],
            as_index=False,
        )["valor_pct"]
        .sum()
    )

    if len(totals) != 15:
        raise ValueError(
            "Se esperaban 15 combinaciones "
            "subfondo-entidad."
        )

    # 0.0002 equivale a 0,02 puntos porcentuales.
    invalid_totals = totals[
        (totals["valor_pct"] - 1.0).abs()
        > 0.0002
    ]

    if not invalid_totals.empty:
        raise ValueError(
            "La composición por literal no suma "
            "aproximadamente 100%:\n"
            + invalid_totals.to_string(index=False)
        )

    print(
        "OK - Se detectaron las 6 categorías esperadas."
    )

    print(
        "OK - Se detectaron las 15 combinaciones "
        "subfondo-entidad."
    )

    print(
        "OK - La composición por literal suma "
        "aproximadamente 100%."
    )

def save_processed_portfolio(
    df: pd.DataFrame,
    output_path: Path
) -> None:
    """
    Guarda el dataset procesado en formato CSV.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"\nDataset guardado en: {output_path}")

if __name__ == "__main__":

    df_all = load_all_subfunds(PDF_PATH)

    df_detail = get_portfolio_detail(df_all)

    df_detail = enrich_detail_structure(df_detail)

    df_detail = normalize_dimensions(df_detail)

    validate_portfolio_data(
        df_all,
        df_detail
    )

    validate_total_percentages(
        df_all
    )

    df_detail["archivo_origen"] = PDF_PATH.name

    print("\nFilas de detalle:")
    print(len(df_detail))

    print("\nNormalización de AFAP:")
    print(
        df_detail[
            ["afap", "afap_normalizada"]
        ]
        .drop_duplicates()
        .to_string(index=False)
    )

    print("\nNormalización de monedas:")
    print(
        df_detail[
            ["moneda_raw", "moneda"]
        ]
        .drop_duplicates()
        .sort_values("moneda_raw")
        .to_string(index=False)
    )