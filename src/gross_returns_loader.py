from pathlib import Path
import re

import pandas as pd
import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"


AFAP_VARIANTS = {
    "AFAP SURA S.A.": "AFAP SURA",
    "INTEGRACIÓN AFAP S.A.": "INTEGRACION AFAP",
    "INTEGRACION AFAP S.A.": "INTEGRACION AFAP",
    "REPUBLICA AFAP S.A.": "REPUBLICA AFAP",
    "REPÚBLICA AFAP S.A.": "REPUBLICA AFAP",
    "AFAP ITAÚ S.A.": "AFAP ITAU",
    "AFAP ITAU S.A.": "AFAP ITAU",
    "UNIÓN CAPITAL AFAP S.A.": "UNION CAPITAL AFAP",
    "UNION CAPITAL AFAP S.A.": "UNION CAPITAL AFAP",
    "RENTABILIDADES DEL REGIMEN": "TOTAL SISTEMA",
}


FUND_TYPES = {
    "CRECIMIENTO": "CRECIMIENTO",
    "ACUMULACIÓN": "ACUMULACION",
    "ACUMULACION": "ACUMULACION",
    "RETIRO": "RETIRO",
    "FAP": "FAP",
    "FONDO VOLUNTARIO PREVISIONAL": "FONDO_VOLUNTARIO_PREVISIONAL",
}


RATE_TYPES = [
    "TRM",
    "TNA",
    "TRA",
]


def percentage_to_decimal(value):
    """
    Convierte un porcentaje textual a decimal.

    Ejemplos:
    0.73%  ->  0.0073
    -0.47% -> -0.0047
    """

    value = value.replace("%", "")
    value = value.replace(",", ".")

    return float(value) / 100


def extract_period_from_filename(pdf_path: Path):
    """
    Extrae el período desde el nombre del archivo.

    Ejemplo:
    cocf01d0826.pdf -> 2026-08
    """

    match = re.search(
        r"cocf01d(\d{2})(\d{2})\.pdf$",
        pdf_path.name,
        re.IGNORECASE,
    )

    if not match:
        raise ValueError(
            "No fue posible detectar el período "
            f"desde el archivo: {pdf_path.name}"
        )

    month = int(match.group(1))
    year = 2000 + int(match.group(2))

    if month < 1 or month > 12:
        raise ValueError(
            f"Mes inválido en {pdf_path.name}: {month}"
        )

    return f"{year}-{month:02d}"


def detect_fund_type(text):
    """
    Detecta qué fondo representa una página
    del reporte de Rentabilidad Bruta.
    """

    upper_text = text.upper()

    # Debe evaluarse primero porque la página
    # también contiene las palabras RENTABILIDAD BRUTA.
    if "FONDO VOLUNTARIO PREVISIONAL" in upper_text:
        return "FONDO_VOLUNTARIO_PREVISIONAL"

    for raw_name, normalized_name in FUND_TYPES.items():

        if raw_name == "FONDO VOLUNTARIO PREVISIONAL":
            continue

        pattern = rf"(?m)^\s*{re.escape(raw_name)}\s*$"

        if re.search(pattern, upper_text):
            return normalized_name

    raise ValueError(
        "No fue posible detectar el fondo "
        "de la página."
    )


def detect_entity(line):
    """
    Identifica la AFAP o el total del sistema
    correspondiente a una fila.
    """

    upper_line = line.upper()

    for raw_name, normalized_name in AFAP_VARIANTS.items():
        if raw_name.upper() in upper_line:
            return normalized_name

    return None


def extract_gross_returns(pdf_path: Path):
    """
    Extrae Rentabilidad Bruta desde un reporte
    mensual del BCU.

    Granularidad:
    período + entidad + fondo + tipo_tasa.
    """

    records = []

    period = extract_period_from_filename(
        pdf_path
    )

    with pdfplumber.open(pdf_path) as pdf:

        for page_number, page in enumerate(
            pdf.pages,
            start=1,
        ):

            text = page.extract_text() or ""

            if not text.strip():
                raise ValueError(
                    f"Página {page_number} sin texto "
                    f"en {pdf_path.name}."
                )

            fund_type = detect_fund_type(text)

            for line in text.splitlines():

                entity = detect_entity(line)

                if entity is None:
                    continue

                percentages = re.findall(
                    r"-?\d+[.,]\d+%",
                    line,
                )

                if len(percentages) != 3:
                    raise ValueError(
                        "Se esperaban 3 porcentajes "
                        f"en la fila: {line}"
                    )

                for rate_type, value in zip(
                    RATE_TYPES,
                    percentages,
                ):
                    records.append(
                        {
                            "periodo": period,
                            "afap_raw": entity,
                            "tipo_fondo": fund_type,
                            "tipo_tasa": rate_type,
                            "rentabilidad_bruta": (
                                percentage_to_decimal(
                                    value
                                )
                            ),
                            "archivo_origen": (
                                pdf_path.name
                            ),
                        }
                    )

    df = pd.DataFrame(records)

    if df.empty:
        raise ValueError(
            f"No se extrajeron registros de {pdf_path.name}."
        )

    duplicates = df.duplicated(
        subset=[
            "periodo",
            "afap_raw",
            "tipo_fondo",
            "tipo_tasa",
        ]
    )

    if duplicates.any():
        raise ValueError(
            "Se encontraron duplicados en "
            f"{pdf_path.name}."
        )

    return df


if __name__ == "__main__":

    test_files = [
        "cocf01d0124.pdf",
        "cocf01d0824.pdf",
        "cocf01d0125.pdf",
        "cocf01d0825.pdf",
        "cocf01d0126.pdf",
        "cocf01d0826.pdf",
    ]

    print(
        "\n=== VALIDACIÓN RENTABILIDAD BRUTA ===\n"
    )

    for filename in test_files:

        pdf_path = RAW_DIR / filename

        try:
            df = extract_gross_returns(
                pdf_path
            )

            print(
                f"{filename}: "
                f"{len(df)} registros | "
                f"período {df['periodo'].iloc[0]}"
            )

            print(
                "Fondos:",
                ", ".join(
                    df["tipo_fondo"].unique()
                ),
            )

            print(
                "Entidades:",
                ", ".join(
                    df["afap_raw"].unique()
                ),
            )

            print()

        except Exception as error:
            print(
                f"{filename}: ERROR -> {error}"
            )