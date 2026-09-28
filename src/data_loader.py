"""Extracción y controles de composición de cartera de AFAP (BCU).

Compatible con los encabezados ITAU y UNION_CAPITAL. Las funciones originales
siguen disponibles para pipeline.py. Para extraer todas las tablas y anexos de
un PDF local: python src/data_loader.py --pdf data/raw/cocf03d0124.pdf
"""
from pathlib import Path
from collections import defaultdict
import re
import unicodedata

import pdfplumber
import pandas as pd

PDF_PATH = Path("data/raw/cocf03d0726.pdf")

COMMON_AFAPS = {"SURA", "INTEGRACION", "REPUBLICA", "TOTAL_SISTEMA"}
VARIABLE_AFAPS = {"ITAU", "UNION_CAPITAL"}
EXPECTED_SUBFUNDS = {"CRECIMIENTO", "ACUMULACION", "RETIRO"}
EXPECTED_LITERALS = {
    "D. TRANSITORIA", "LITERAL A", "LITERAL B", "LITERAL C",
    "LITERAL D", "LITERAL F",
}


def _without_accents(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    )


def detect_columns(page):
    """Obtiene los centros de las cinco columnas según el encabezado real."""
    header_names = {
        "SURA": "SURA", "INTEGRACION": "INTEGRACION",
        "REPUBLICA": "REPUBLICA", "ITAU": "ITAU",
        "UNION": "UNION_CAPITAL", "SISTEMA": "TOTAL_SISTEMA",
    }
    columns = {}
    for word in page.extract_words():
        text = _without_accents(word["text"].upper().strip(" :"))
        if text in header_names:
            name = header_names[text]
            center = (word["x0"] + word["x1"]) / 2
            if name in columns and abs(columns[name] - center) > 5:
                raise ValueError(f"Encabezado duplicado para {name}: {columns[name]} y {center}")
            columns[name] = center

    missing = COMMON_AFAPS - set(columns)
    variable = VARIABLE_AFAPS & set(columns)
    if missing or len(variable) != 1 or len(columns) != 5:
        raise ValueError(
            "No fue posible detectar las cinco columnas. "
            f"Detectadas: {columns}. Faltantes: {missing}. "
            f"ITAU/UNION_CAPITAL detectadas: {variable}"
        )
    return columns


def assign_column(x0, column_x):
    """Asigna cada porcentaje a la columna cuyo intervalo contiene su x0."""
    ordered_columns = sorted(column_x, key=lambda column: column_x[column])
    centers = [column_x[column] for column in ordered_columns]
    boundaries = [(left + right) / 2 for left, right in zip(centers, centers[1:])]
    for index, column in enumerate(ordered_columns):
        left_boundary = float("-inf") if index == 0 else boundaries[index - 1]
        right_boundary = float("inf") if index == len(ordered_columns) - 1 else boundaries[index]
        if left_boundary <= x0 < right_boundary:
            return column
    return None


def extract_rows(page):
    """Reconstruye filas del PDF a partir de las posiciones de las palabras."""
    words = page.extract_words()
    column_x = detect_columns(page)
    first_column_x = min(column_x.values())
    rows = defaultdict(list)
    for word in words:
        rows[round(word["top"], 1)].append(word)

    extracted_rows = []
    for top in sorted(rows):
        row_words = sorted(rows[top], key=lambda word: word["x0"])
        description_parts = []
        percentages = {}
        for word in row_words:
            text = word["text"]
            if text.endswith("%"):
                column = assign_column(word["x0"], column_x)
                if column:
                    percentages[column] = text
            elif word["x0"] < first_column_x:
                description_parts.append(text)
        description = " ".join(description_parts).strip()
        if percentages:
            extracted_rows.append({"description": description, **percentages})
    return extracted_rows


def extract_report_date(text: str) -> pd.Timestamp:
    """Extrae la fecha de corte (día/mes/año) del encabezado."""
    match = re.search(r"\b(\d{1,2}/\d{1,2}/\d{4})\b", text)
    if not match:
        raise ValueError("No se pudo identificar la fecha del reporte.")
    return pd.to_datetime(match.group(1), format="%d/%m/%Y")


def identify_section(text: str) -> str:
    text = _without_accents(text.upper())
    # Algunos títulos del FVP también dicen "SUBFONDO DE ACUMULACIÓN".
    # Identificar primero el fondo evita mezclarlo con el régimen obligatorio.
    if "FONDO VOLUNTARIO PREVISIONAL" in text:
        return "FVP"
    if "SUBFONDO DE CRECIMIENTO" in text:
        return "CRECIMIENTO"
    if "SUBFONDO DE ACUMULACION" in text:
        return "ACUMULACION"
    if "SUBFONDO DE RETIRO" in text:
        return "RETIRO"
    return "DESCONOCIDO"


def build_composition_dataframe(pdf_path: Path, page_index: int = 0):
    """Conserva las cinco columnas reales, sin crear ITAU ficticia."""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_index]
        text = page.extract_text() or ""
        rows = extract_rows(page)
    df = pd.DataFrame(rows)
    variable = [name for name in ("ITAU", "UNION_CAPITAL") if name in df.columns]
    if len(variable) != 1:
        raise ValueError(
            "Se esperaba una columna ITAU o UNION_CAPITAL. "
            f"Columnas disponibles: {df.columns.tolist()}"
        )
    column_order = [
        "description", "SURA", "INTEGRACION", "REPUBLICA",
        variable[0], "TOTAL_SISTEMA",
    ]
    missing = [column for column in column_order if column not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {missing}")
    return df[column_order].copy(), extract_report_date(text), identify_section(text)


def classify_row(description: str) -> str:
    if not isinstance(description, str):
        return "UNKNOWN"
    text = description.strip().upper()
    if text == "TOTALES":
        return "TOTAL_GENERAL"
    if text.startswith("PARTICIPACIÓN") or text.startswith("PARTICIPACION"):
        return "PARTICIPACION"
    if text.startswith("TOTAL LITERAL") or text == "TOTAL D. TRANSITORIA":
        return "SUBTOTAL"
    return "DETALLE"


def transform_composition_to_long(
    df: pd.DataFrame, fecha: pd.Timestamp, subfondo: str
) -> pd.DataFrame:
    """Transforma la tabla ancha sin perder UNION_CAPITAL o ITAU."""
    variable = [name for name in ("ITAU", "UNION_CAPITAL") if name in df.columns]
    if len(variable) != 1:
        raise ValueError(f"Se esperaba ITAU o UNION_CAPITAL. Columnas: {df.columns.tolist()}")
    afap_columns = ["SURA", "INTEGRACION", "REPUBLICA", variable[0], "TOTAL_SISTEMA"]
    missing = [column for column in ["description", *afap_columns] if column not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas: {missing}")

    df_long = df.melt(
        id_vars=["description"], value_vars=afap_columns,
        var_name="afap", value_name="valor_pct",
    )
    raw_pct = df_long["valor_pct"].astype("string").str.replace("%", "", regex=False).str.strip()
    df_long["valor_pct"] = raw_pct.map(
        lambda raw: None if pd.isna(raw) else _report_number(raw, percentage=True)
    )
    df_long["fecha"] = fecha
    df_long["subfondo"] = subfondo
    df_long = df_long.rename(columns={"description": "instrumento_raw"})
    df_long["tipo_fila"] = df_long["instrumento_raw"].apply(classify_row)
    return df_long[[
        "fecha", "subfondo", "afap", "tipo_fila", "instrumento_raw", "valor_pct"
    ]]


def load_all_subfunds(pdf_path: Path) -> pd.DataFrame:
    """Procesa las páginas de composición: Crecimiento, Acumulación y Retiro."""
    dataframes = []
    for page_index in [0, 2, 4]:
        df_wide, fecha, subfondo = build_composition_dataframe(pdf_path, page_index=page_index)
        dataframes.append(transform_composition_to_long(df_wide, fecha, subfondo))
    return pd.concat(dataframes, ignore_index=True)


def get_portfolio_detail(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["tipo_fila"] == "DETALLE"].copy()


def get_portfolio_literal_totals(df: pd.DataFrame) -> pd.DataFrame:
    df_totals = df[df["tipo_fila"] == "SUBTOTAL"].copy()
    df_totals["literal"] = (
        df_totals["instrumento_raw"].str.upper()
        .str.replace("TOTAL ", "", regex=False).str.strip()
    )
    return df_totals


def enrich_detail_structure(df: pd.DataFrame) -> pd.DataFrame:
    """Reconstruye literal, instrumento y moneda, por subfondo y AFAP."""
    df = df.copy()
    currencies = {"UY", "UI", "US", "UP", "UR"}
    literals, instruments, currencies_found = [], [], []
    states = {}
    for _, row in df.iterrows():
        key = (row["fecha"], row["subfondo"], row["afap"])
        if key not in states:
            states[key] = {"literal": None, "instrumento": None}
        state = states[key]
        raw = str(row["instrumento_raw"]).strip()
        literal_match = re.match(
            r"^LITERAL\s+([A-Z])(?:\s*-\s*\(Ver Anexo\))?\s+(.+)$",
            raw, flags=re.IGNORECASE,
        )
        if literal_match:
            state["literal"] = f"LITERAL {literal_match.group(1).upper()}"
            remaining_text = literal_match.group(2).strip()
        else:
            remaining_text = raw
        if remaining_text.upper() in currencies:
            currency = remaining_text.upper()
            instrument = state["instrumento"]
        else:
            parts = remaining_text.rsplit(" ", 1)
            if len(parts) == 2 and parts[1].upper() in currencies:
                instrument = parts[0].strip()
                currency = parts[1].upper()
            else:
                instrument = remaining_text
                currency = None
            state["instrumento"] = instrument
        literals.append(state["literal"])
        instruments.append(instrument)
        currencies_found.append(currency)
    df["literal"] = literals
    df["instrumento"] = instruments
    df["moneda_raw"] = currencies_found
    return df


def normalize_dimensions(df: pd.DataFrame) -> pd.DataFrame:
    """Conserva códigos originales y agrega nombres de AFAP y moneda."""
    df = df.copy()
    afap_map = {
        "SURA": "AFAP SURA", "INTEGRACION": "INTEGRACION AFAP",
        "REPUBLICA": "REPUBLICA AFAP", "ITAU": "AFAP ITAU",
        "UNION_CAPITAL": "UNION CAPITAL AFAP", "TOTAL_SISTEMA": "TOTAL SISTEMA",
    }
    currency_map = {"UY": "UYU", "US": "USD", "UI": "UI", "UP": "UP", "UR": "UR"}
    df["afap_normalizada"] = df["afap"].map(afap_map)
    if df["afap_normalizada"].isna().any():
        unknown = df.loc[df["afap_normalizada"].isna(), "afap"].unique().tolist()
        raise ValueError(f"AFAP sin normalizar: {unknown}")
    df["moneda"] = df["moneda_raw"].map(currency_map)
    return df


def validate_portfolio_data(df_all: pd.DataFrame, df_detail: pd.DataFrame) -> None:
    """Controla estructura, entidades y porcentajes; falla ante errores críticos."""
    print("\n--- CONTROLES DE CALIDAD ---")
    detected_subfunds = set(df_all["subfondo"].dropna().unique())
    if detected_subfunds != EXPECTED_SUBFUNDS:
        raise ValueError(f"Subfondos inesperados: {detected_subfunds}")
    print("OK - Se detectaron los 3 subfondos esperados.")

    detected_afaps = set(df_all["afap"].dropna().unique())
    variable = detected_afaps & VARIABLE_AFAPS
    if len(variable) != 1 or detected_afaps != COMMON_AFAPS | variable:
        raise ValueError(f"Entidades inesperadas: {detected_afaps}")
    for subfondo, group in df_all.groupby("subfondo"):
        if set(group["afap"].dropna().unique()) != detected_afaps:
            raise ValueError(f"Entidades incompletas en {subfondo}")
    print("OK - Se detectaron todas las AFAP y el total del sistema.")

    invalid = df_all[df_all["valor_pct"].notna() & ~df_all["valor_pct"].between(0, 1)]
    if not invalid.empty:
        raise ValueError("Hay porcentajes fuera del rango 0%-100%.")
    print("OK - No hay porcentajes fuera del rango 0%-100%.")

    missing_instruments = df_detail[df_detail["instrumento"].isna()]
    if not missing_instruments.empty:
        print(f"ADVERTENCIA - Hay {len(missing_instruments)} registros de detalle sin instrumento.")
    else:
        print("OK - No hay registros de detalle sin instrumento.")


def validate_missing_percentages(
    df_all: pd.DataFrame
) -> None:
    """
    Controla porcentajes faltantes.

    - Detiene el pipeline si faltan totales generales.
    - Detiene el pipeline si faltan porcentajes de subtotales
      y la suma de los literales es inconsistente.
    - Informa los nulos de detalle y participación
      para su revisión posterior.
    """

    print("\n--- CONTROL DE PORCENTAJES FALTANTES ---")

    expected_subfunds = {
        "CRECIMIENTO",
        "ACUMULACION",
        "RETIRO",
    }

    expected_afaps = set(
        df_all["afap"].dropna().unique()
    )

    expected_combinations = {
        (subfondo, afap)
        for subfondo in expected_subfunds
        for afap in expected_afaps
    }

    # 1. Comprobar que exista un total general
    #    numérico por cada subfondo y entidad.

    totals = df_all[
        df_all["tipo_fila"] == "TOTAL_GENERAL"
    ].copy()

    total_counts = (
        totals[totals["valor_pct"].notna()]
        .groupby(["subfondo", "afap"])
        .size()
    )

    invalid_combinations = {
        combination
        for combination in expected_combinations
        if total_counts.get(combination, 0) != 1
    }

    if invalid_combinations:
        raise ValueError(
            "Faltan totales generales numéricos "
            "o existen totales duplicados en: "
            f"{sorted(invalid_combinations)}"
        )

    print(
        "OK - Las 15 combinaciones tienen "
        "un total general numérico."
    )

    # 2. Identificar subtotales sin porcentaje.

    subtotals = df_all[
        df_all["tipo_fila"] == "SUBTOTAL"
    ].copy()

    missing_subtotals = subtotals[
        subtotals["valor_pct"].isna()
    ]

    if missing_subtotals.empty:
        print(
            "OK - No hay subtotales "
            "con porcentajes faltantes."
        )
    else:
        print(
            f"ADVERTENCIA - Hay {len(missing_subtotals)} "
            "subtotales sin porcentaje."
        )

        print(
            missing_subtotals[
                [
                    "subfondo",
                    "afap",
                    "instrumento_raw",
                ]
            ].to_string(index=False)
        )

    # 3. Revisar si los subtotales numéricos
    #    siguen sumando aproximadamente el 100 %.

    subtotal_sums = (
        subtotals
        .groupby(["subfondo", "afap"])["valor_pct"]
        .sum(min_count=1)
    )

    invalid_sums = {
        combination: subtotal_sums.get(
            combination, float("nan")
        )
        for combination in expected_combinations
        if (
            pd.isna(subtotal_sums.get(combination))
            or abs(
                subtotal_sums.get(combination) - 1.0
            ) > 0.0002
        )
    }

    if invalid_sums:
        raise ValueError(
            "Los subtotales numéricos no suman "
            "aproximadamente 100 %: "
            f"{invalid_sums}"
        )

    print(
        "OK - Los subtotales numéricos "
        "suman aproximadamente 100 %."
    )

    # 4. Registrar nulos de detalle
    #    y participación.

    for row_type in ["DETALLE", "PARTICIPACION"]:
        missing = df_all[
            (df_all["tipo_fila"] == row_type)
            & df_all["valor_pct"].isna()
        ]

        print(
            f"{row_type}: {len(missing)} "
            "porcentajes faltantes."
        )

        if not missing.empty:
            print(
                missing[
                    [
                        "subfondo",
                        "afap",
                        "instrumento_raw",
                    ]
                ].to_string(index=False)
            )


def validate_total_percentages(df_all: pd.DataFrame) -> None:
    """Exige exactamente un TOTAL_GENERAL válido por subfondo y entidad."""
    print("\n--- CONTROL DE TOTALES ---")
    totals = df_all[df_all["tipo_fila"] == "TOTAL_GENERAL"].copy()
    counts = totals.groupby(["subfondo", "afap"]).size()
    if len(counts) != 15 or not counts.eq(1).all():
        raise ValueError(f"Se esperaban 15 totales únicos. Detectados:\n{counts.to_string()}")
    invalid = totals[totals["valor_pct"].isna() | (totals["valor_pct"] - 1).abs().gt(0.0001)]
    if not invalid.empty:
        raise ValueError(
            "Se encontraron totales distintos de 100% o vacíos:\n"
            + invalid[["subfondo", "afap", "valor_pct"]].to_string(index=False)
        )
    print("OK - Todos los totales por subfondo y entidad son iguales a 100%.")


def validate_literal_percentages(df_literals: pd.DataFrame) -> None:
    """Valida categorías por subfondo, sin fijar seis filas cuando la fuente agrega E."""
    print("\n--- CONTROL DE COMPOSICIÓN POR LITERAL ---")
    if df_literals["literal"].isna().any():
        raise ValueError("Hay subtotales sin categoría de literal.")
    detected = set(df_literals["literal"].unique())
    allowed = EXPECTED_LITERALS | {"LITERAL E"}
    if detected - allowed:
        raise ValueError(f"Categorías de literal inesperadas: {detected - allowed}")
    expected_by_subfund = {
        subfund: set(group["literal"])
        for subfund, group in df_literals.groupby("subfondo")
    }
    for subfund, categories in expected_by_subfund.items():
        if not EXPECTED_LITERALS <= categories:
            raise ValueError(f"Faltan categorías base en {subfund}: {EXPECTED_LITERALS - categories}")
    groups = df_literals.groupby(["subfondo", "afap"])
    if groups.ngroups != 15:
        raise ValueError(f"Se esperaban 15 combinaciones subfondo-entidad; hay {groups.ngroups}.")
    for (subfondo, afap), group in groups:
        expected = expected_by_subfund[subfondo]
        if group["literal"].duplicated().any() or set(group["literal"]) != expected:
            raise ValueError(f"Literales incompletos o duplicados: {subfondo}, {afap}")
    totals = groups["valor_pct"].sum(min_count=1)
    invalid = totals[totals.isna() | (totals - 1).abs().gt(0.0002)]
    if not invalid.empty:
        raise ValueError("La composición por literal no suma aproximadamente 100%:\n" + invalid.to_string())
    print("OK - Categorías por subfondo: " + "; ".join(
        f"{subfund}: {len(categories)}" for subfund, categories in expected_by_subfund.items()
    ))
    print("OK - Se detectaron las 15 combinaciones subfondo-entidad sin literales duplicados.")
    print("OK - La composición por literal suma aproximadamente 100%.")


def save_processed_portfolio(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\nDataset guardado en: {output_path}")


def _legacy_diagnostic():
    df_all = load_all_subfunds(PDF_PATH)
    df_detail = normalize_dimensions(enrich_detail_structure(get_portfolio_detail(df_all)))
    validate_portfolio_data(df_all, df_detail)
    validate_total_percentages(df_all)
    df_literals = get_portfolio_literal_totals(df_all)
    validate_literal_percentages(df_literals)
    df_detail["archivo_origen"] = PDF_PATH.name
    print("\nFilas de detalle:", len(df_detail))
    print("\nNormalización de AFAP:")
    print(df_detail[["afap", "afap_normalizada"]].drop_duplicates().to_string(index=False))
    print("\nNormalización de monedas:")
    print(df_detail[["moneda_raw", "moneda"]].drop_duplicates().to_string(index=False))


# Extracción completa. Las funciones anteriores conservan su contrato para
# pipeline.py: sus controles y salidas analíticas siguen siendo independientes.
def _report_lines(page, tolerance=2.0):
    """Agrupa palabras en líneas sin separar texto y cifras por leves desfases."""
    lines = []
    for word in sorted(page.extract_words(), key=lambda w: (w["top"], w["x0"])):
        if not lines or abs(word["top"] - lines[-1][0]) > tolerance:
            lines.append((word["top"], [word]))
        else:
            lines[-1][1].append(word)
    return [(top, sorted(words, key=lambda w: w["x0"])) for top, words in lines]


def _report_number(raw, percentage=False):
    """Lee porcentajes con coma/punto decimal e importes con miles coma/punto.

    En porcentajes no se admiten separadores de miles. En importes, grupos
    de tres cifras son miles; si hay decimales, usan el separador opuesto.
    Los textos no reconocidos fallan; nunca se convierten silenciosamente a cero.
    """
    if raw is None or not str(raw).strip() or str(raw).strip() in {"-", "—"}:
        return None
    value = str(raw).strip().removesuffix("%").strip()
    if percentage:
        if not re.fullmatch(r"-?\d+(?:[.,]\d+)?", value):
            raise ValueError(f"Formato porcentual no reconocido: {raw!r}")
        return float(value.replace(",", ".")) / 100
    if re.fullmatch(r"-?\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?", value):
        normalized = value.replace(",", "")
    elif re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?", value):
        normalized = value.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d+(?:[.,]\d{1,2})?", value):
        normalized = value.replace(",", ".")
    else:
        raise ValueError(f"Formato monetario no reconocido: {raw!r}")
    return float(normalized)


def _complete_base(pdf_path, fecha, page_number, line_number, top, words, fund):
    return {
        "fecha": fecha, "fondo": fund,
        "subfondo": fund if fund in EXPECTED_SUBFUNDS else None,
        "pagina": page_number, "fila_pdf": line_number,
        "fila_id": f"p{page_number:02d}_f{line_number:03d}",
        "y_pdf": round(top, 2),
        "texto_fila_raw": " ".join(w["text"] for w in words),
        "archivo_origen": Path(pdf_path).name,
    }


def _complete_composition(page, pdf_path, fecha, page_number, fund):
    columns = detect_columns(page)
    centers = sorted(columns.values())
    data_left = centers[0] - (centers[1] - centers[0]) / 2
    header_top = next(w["top"] for w in page.extract_words() if w["text"] == "SURA")
    records = []
    for line_number, (top, words) in enumerate(_report_lines(page), 1):
        if top <= header_top + 2:
            continue
        full_text = " ".join(w["text"] for w in words)
        if full_text.startswith("NOTA:"):
            break
        description, values = [], {}
        for word in words:
            text = word["text"]
            center = (word["x0"] + word["x1"]) / 2
            is_number = bool(re.fullmatch(r"-?[\d,.]+%?|[-—]", text))
            if center >= data_left and is_number:
                column = min(columns, key=lambda name: abs(columns[name] - center))
                if column in values:
                    raise ValueError(f"Dos valores en página {page_number}, fila {line_number}, {column}")
                values[column] = text
            else:
                description.append(text)
        label = " ".join(description).strip()
        if not label:
            raise ValueError(f"Fila sin concepto: página {page_number}, fila {line_number}")
        # No se exige un valor: se conservan también filas con todas las celdas vacías.
        monetary = "$" in label
        row_type = "TOTAL_MONETARIO" if monetary else classify_row(label)
        base = _complete_base(pdf_path, fecha, page_number, line_number, top, words, fund)
        for afap in sorted(columns, key=columns.get):
            raw = values.get(afap)
            if raw not in (None, "-", "—") and (raw.endswith("%") == monetary):
                raise ValueError(f"Unidad inesperada en {label}: {raw}")
            value = _report_number(raw, percentage=not monetary)
            records.append({
                **base, "seccion": "COMPOSICION", "afap": afap,
                "tipo_fila": row_type, "instrumento_raw": label,
                "tipo_valor": "IMPORTE" if monetary else "PORCENTAJE",
                "unidad": "$" if monetary else "PROPORCION",
                "valor_raw": raw, "valor_pct": None if monetary else value,
                "valor_importe": value if monetary else None,
                "columna_origen": afap,
            })
    if not records:
        raise ValueError(f"Página de composición sin datos: {page_number}")
    return records


def _complete_annex(page, pdf_path, fecha, page_number, fund):
    lines = _report_lines(page)
    header = next(((top, words) for top, words in lines
                   if {"MONEDA", "S/ACT", "SISTEMA"} <= {w["text"] for w in words}), None)
    if header is None:
        raise ValueError(f"Encabezado de anexo no reconocido: página {page_number}")
    header_top, header_words = header
    instrument_starts = sorted(w["x0"] for w in header_words if w["text"] == "INSTRUMENTO")
    if len(instrument_starts) != 2:
        raise ValueError(f"Columnas de instrumento no reconocidas: página {page_number}")
    instrument_left = instrument_starts[1] - 2
    currency_left = next(w["x0"] for w in header_words if w["text"] == "MONEDA") - 2
    percent_left = min(w["x0"] for w in header_words if w["text"] == "%") - 2
    system_left = next(w["x0"] for w in header_words if w["text"] == "TOT.") - 2
    category = None
    records = []
    for line_number, (top, words) in enumerate(lines, 1):
        if top <= header_top + 2:
            continue
        full_text = " ".join(w["text"] for w in words)
        if full_text.startswith("NOTA:"):
            break
        category_words, instrument_words, currency_words = [], [], []
        percentages = {}
        for word in words:
            x, text = word["x0"], word["text"]
            if x >= percent_left:
                col = "TOT_SISTEMA" if x >= system_left else "S_ACT_FAP"
                if col in percentages:
                    raise ValueError(f"Dos valores de anexo en página {page_number}, fila {line_number}")
                percentages[col] = text
            elif x >= currency_left:
                currency_words.append(text)
            elif x >= instrument_left:
                instrument_words.append(text)
            else:
                category_words.append(text)
        label = " ".join(category_words + instrument_words + currency_words)
        if not label:
            raise ValueError(f"Anexo sin concepto: página {page_number}, fila {line_number}")
        total = label.startswith("TOTAL INSTRUMENTOS")
        subtotal = label.startswith("SUB TOTAL")
        if category_words and not total:
            category = " ".join(category_words)
        first = _report_number(percentages.get("S_ACT_FAP"), percentage=True)
        second = _report_number(percentages.get("TOT_SISTEMA"), percentage=True)
        selected = "S_ACT_FAP" if first is not None else "TOT_SISTEMA"
        base = _complete_base(pdf_path, fecha, page_number, line_number, top, words, fund)
        records.append({
            **base, "seccion": "ANEXO_LITERAL_A", "afap": "TOTAL_SISTEMA",
            "tipo_fila": "TOTAL_ANEXO" if total else "SUBTOTAL_ANEXO" if subtotal else "DETALLE_ANEXO",
            "instrumento_raw": label, "literal": "LITERAL A",
            "tipo_instrumento": None if total else category,
            "instrumento": " ".join(instrument_words) if not (total or subtotal) else None,
            "moneda_raw": " ".join(currency_words) or None,
            "tipo_valor": "PORCENTAJE", "unidad": "PROPORCION",
            "valor_raw": percentages.get(selected),
            "valor_pct": first if first is not None else second,
            "valor_importe": None,
            "anexo_pct_s_act_fap": first, "anexo_pct_tot_sistema": second,
            "anexo_raw_s_act_fap": percentages.get("S_ACT_FAP"),
            "anexo_raw_tot_sistema": percentages.get("TOT_SISTEMA"),
            "columna_origen": "AMBAS" if first is not None and second is not None else selected,
        })
    if not records:
        raise ValueError(f"Anexo sin datos: página {page_number}")
    return records


def load_complete_report(pdf_path: Path) -> pd.DataFrame:
    """Todas las filas de datos, importes, FVP y anexos; rechaza páginas desconocidas.

    Una fila por entidad en composición y una fila por renglón del anexo.
    Encabezados, notas al pie y separadores no son observaciones de datos.
    Validado con cocf03d0124.pdf; otros formatos requieren control de cobertura.
    """
    pdf_path = Path(pdf_path)
    records = []
    with pdfplumber.open(pdf_path) as pdf:
        fecha = extract_report_date(pdf.pages[0].extract_text() or "")
        for page_number, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            fund = identify_section(text)
            if fund == "DESCONOCIDO":
                raise ValueError(f"Sección no reconocida en página {page_number}; no se omite silenciosamente.")
            normalized = _without_accents(text.upper())
            if "COMPOSICION DEL ACTIVO" in normalized:
                page_date = extract_report_date(text)
                if page_date != fecha:
                    raise ValueError(f"Fecha distinta en página {page_number}: {page_date}")
                records.extend(_complete_composition(page, pdf_path, fecha, page_number, fund))
            elif "DETALLE DE LOS INSTRUMENTOS" in normalized:
                match = re.search(r"\b\d{1,2}/\d{1,2}/(?:\d{4}|\d{2})\b", text)
                if not match:
                    raise ValueError(f"Fecha de anexo no reconocida: página {page_number}")
                raw_date = match.group()
                date_format = "%d/%m/%Y" if len(raw_date.rsplit("/", 1)[1]) == 4 else "%d/%m/%y"
                annex_date = pd.to_datetime(raw_date, format=date_format)
                if annex_date != fecha:
                    raise ValueError(
                        f"Fecha de anexo diferente: página {page_number}, "
                        f"anexo {annex_date:%d/%m/%Y}, reporte {fecha:%d/%m/%Y}"
                    )
                records.extend(_complete_annex(page, pdf_path, fecha, page_number, fund))
            else:
                raise ValueError(f"Formato de página no reconocido: {page_number}")
    df = pd.DataFrame(records)
    for col in ["literal", "instrumento", "moneda_raw"]:
        if col not in df:
            df[col] = None
    detail_mask = df["seccion"].eq("COMPOSICION") & df["tipo_fila"].eq("DETALLE")
    details = enrich_detail_structure(df.loc[detail_mask])
    df.loc[detail_mask, ["literal", "instrumento", "moneda_raw"]] = details[
        ["literal", "instrumento", "moneda_raw"]
    ]
    literal_mask = df["seccion"].eq("COMPOSICION") & df["tipo_fila"].eq("SUBTOTAL")
    df.loc[literal_mask, "literal"] = df.loc[literal_mask, "instrumento_raw"].str.upper().str.replace(
        "TOTAL ", "", regex=False).str.strip()
    df = normalize_dimensions(df)
    df["valor_importe"] = df["valor_importe"].astype("Float64")
    if df.duplicated(["archivo_origen", "fila_id", "afap"]).any():
        raise ValueError("Identificadores de fila y entidad duplicados.")
    return df


def save_complete_report(pdf_path: Path, output_path=None) -> pd.DataFrame:
    """Guarda el CSV completo sin aplicar filtros de detalle ni de subfondos."""
    df = load_complete_report(pdf_path)
    # Las reglas de composición se aplican a su ámbito original; nunca a
    # importes, anexos ni FVP. El cotejo manual de los nulos sigue pendiente.
    composition = df[
        df["seccion"].eq("COMPOSICION")
        & df["subfondo"].isin(EXPECTED_SUBFUNDS)
        & df["tipo_valor"].eq("PORCENTAJE")
    ]
    validate_portfolio_data(composition, get_portfolio_detail(composition))
    validate_total_percentages(composition)
    validate_literal_percentages(get_portfolio_literal_totals(composition))
    if output_path is None:
        fecha = pd.Timestamp(df["fecha"].iloc[0])
        output_path = Path("data/processed") / f"portfolio_composition_{fecha:%Y_%m}.csv"
    save_processed_portfolio(df, Path(output_path))
    print(df.groupby(["pagina", "seccion", "fondo"]).size().rename("registros").to_string())
    return df


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extrae todas las tablas y anexos del reporte BCU.")
    parser.add_argument("--pdf", type=Path, help="PDF local para extracción completa.")
    parser.add_argument("--output", type=Path, help="CSV destino; por defecto data/processed/portfolio_composition_YYYY_MM.csv.")
    args = parser.parse_args()
    if args.output and not args.pdf:
        parser.error("--output requiere --pdf")
    if args.pdf:
        save_complete_report(args.pdf, args.output)
    else:
        _legacy_diagnostic()
