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
}


METRICS = {
    "Subfondo de CRECIMIENTO": (
        "SUBFONDO",
        "CRECIMIENTO",
    ),
    "Subfondo de ACUMULACIÓN": (
        "SUBFONDO",
        "ACUMULACION",
    ),
    "Subfondo de RETIRO": (
        "SUBFONDO",
        "RETIRO",
    ),
    "RENTABILIDAD NETA AGREGADA DEL FAP": (
        "FAP_AGREGADO",
        None,
    ),
    "RENTABILIDAD NETA RÉGIMEN ESPECIAL": (
        "REGIMEN_ESPECIAL",
        None,
    ),
}


def percentage_to_decimal(value):
    """
    Convierte un porcentaje textual a decimal.

    Ejemplos:
    0.11%  ->  0.0011
    -0.84% -> -0.0084
    """

    value = value.replace("%", "")
    value = value.replace(",", ".")

    return float(value) / 100

def detect_afaps(text):
    """
    Detecta las AFAP presentes en el encabezado del reporte
    respetando el orden en que aparecen en el PDF.
    """

    header_line = None

    for line in text.splitlines():
        if line.startswith(
            "RENTABILIDAD NETA POR SUBFONDOS"
        ):
            header_line = line
            break

    if header_line is None:
        raise ValueError(
            "No se encontró el encabezado de AFAP."
        )

    detected = []

    for raw_name, normalized_name in AFAP_VARIANTS.items():
        position = header_line.find(raw_name)

        if position != -1:
            detected.append(
                (
                    position,
                    normalized_name,
                )
            )

    detected.sort(
        key=lambda item: item[0]
    )

    afaps = [
        name
        for _, name in detected
    ]

    if len(afaps) != 4:
        raise ValueError(
            "Se esperaban 4 AFAP y se detectaron "
            f"{len(afaps)}: {afaps}"
        )

    return afaps

def extract_period(text):
    """
    Extrae el mes y año del reporte.
    Devuelve el período en formato YYYY-MM.
    """

    months = {
        "ENERO": 1,
        "FEBRERO": 2,
        "MARZO": 3,
        "ABRIL": 4,
        "MAYO": 5,
        "JUNIO": 6,
        "JULIO": 7,
        "AGOSTO": 8,
        "SETIEMBRE": 9,
        "SEPTIEMBRE": 9,
        "OCTUBRE": 10,
        "NOVIEMBRE": 11,
        "DICIEMBRE": 12,
    }

    pattern = (
        r"\b("
        + "|".join(months.keys())
        + r")\s+(\d{4})\b"
    )

    match = re.search(
        pattern,
        text.upper(),
    )

    if not match:
        raise ValueError(
            "No fue posible detectar "
            "el período del reporte."
        )

    month_name = match.group(1)
    year = int(match.group(2))
    month = months[month_name]

    return f"{year}-{month:02d}"

def extract_returns(pdf_path: Path):
    """
    Extrae las métricas de Rentabilidad Neta
    desde un reporte mensual del BCU.
    """

    records = []

    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(
            page.extract_text() or ""
            for page in pdf.pages
        )

    lines = text.splitlines()

    afap_order = detect_afaps(text)
    period = extract_period(text)

    for line in lines:

        for label, (
            metric_type,
            subfund,
        ) in METRICS.items():

            if line.startswith(label):

                percentages = re.findall(
                    r"-?\d+[.,]\d+%",
                    line,
                )

                if len(percentages) != 4:
                    raise ValueError(
                        "Se esperaban 4 porcentajes "
                        f"en la fila: {line}"
                    )

                for afap, value in zip(
                    afap_order,
                    percentages,
                ):
                    records.append(
                        {
                            "periodo": period,
                            "afap_raw": afap,
                            "tipo_metrica": metric_type,
                            "subfondo": subfund,
                            "rentabilidad_neta": (
                                percentage_to_decimal(
                                    value
                                )
                            ),
                            "archivo_origen": pdf_path.name,
                        }
                    )

    df = pd.DataFrame(records)

    if len(df) != 20:
        raise ValueError(
            "Se esperaban 20 registros "
            f"y se obtuvieron {len(df)}."
        )

    return df

if __name__ == "__main__":

    test_files = [
        "cocf02d0124.pdf",
        "cocf02d0824.pdf",
        "cocf02d0125.pdf",
        "cocf02d0825.pdf",
        "cocf02d0126.pdf",
        "cocf02d0826.pdf",
    ]

    print(
        "\n=== VALIDACIÓN RENTABILIDAD NETA ===\n"
    )

    for filename in test_files:

        pdf_path = RAW_DIR / filename

        try:
            df = extract_returns(pdf_path)

            afaps = ", ".join(
                df.afap_raw.unique()
            )

            print(
                f"{filename}: "
                f"{len(df)} registros | "
                f"AFAP: {afaps}"
            )

            print(
                df.head(1).to_string(
                    index=False
                )
            )

            print()

        except Exception as error:
            print(
                f"{filename}: ERROR -> {error}"
            )