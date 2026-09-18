from pathlib import Path
from urllib.parse import urljoin
import re

import requests
from bs4 import BeautifulSoup


BCU_BASE_URL = "https://www.bcu.gub.uy"

COMPOSITION_PAGE_URL = (
    "https://www.bcu.gub.uy/"
    "Servicios-Financieros-SSF/Paginas/"
    "Composicion-del-Activo-de-los-Fondos-de-Ahorro-Previsional.aspx"
)

REPORT_FOLDER_URL = (
    "https://www.bcu.gub.uy/"
    "Servicios-Financieros-SSF/"
    "AFAPComposicionPortafolioPrincipalesVariables/"
)

RAW_DIR = Path("data/raw")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36"
    )
}


def build_report_filename(year: int, month: int) -> str:
    """
    Construye el nombre esperado del reporte BCU.

    Ejemplo:
    julio 2026 -> cocf03d0726.pdf
    """

    return f"cocf03d{month:02d}{year % 100:02d}.pdf"


def find_report_url(year: int, month: int) -> str:
    """
    Busca el enlace del reporte dentro del sitio del BCU.

    Si la página no expone el enlace correctamente,
    utiliza como respaldo la estructura oficial conocida
    de archivos del BCU.
    """

    filename = build_report_filename(year, month)

    print(
        f"Buscando en BCU: "
        f"{month:02d}/{year} - {filename}"
    )

    try:
        response = requests.get(
            COMPOSITION_PAGE_URL,
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Buscamos el archivo entre todos los links
        for link in soup.find_all("a", href=True):

            href = link["href"]

            if filename.lower() in href.lower():

                report_url = urljoin(
                    BCU_BASE_URL,
                    href
                )

                print("Reporte encontrado en la página del BCU.")

                return report_url

        # Segundo intento: buscar el nombre
        # directamente dentro del HTML
        match = re.search(
            rf"""[^"'<>]*{re.escape(filename)}""",
            response.text,
            flags=re.IGNORECASE,
        )

        if match:

            report_url = urljoin(
                BCU_BASE_URL,
                match.group(0)
            )

            print("Reporte encontrado en el código de la página.")

            return report_url

    except requests.RequestException as error:

        print(
            "No se pudo consultar correctamente "
            f"la página índice del BCU: {error}"
        )

    # Respaldo basado en la estructura oficial
    report_url = urljoin(
        REPORT_FOLDER_URL,
        filename
    )

    print(
        "Usando URL oficial esperada como respaldo."
    )

    return report_url


def download_portfolio_report(
    year: int,
    month: int,
    overwrite: bool = False,
) -> Path:
    """
    Busca y descarga el reporte mensual de composición
    del portafolio AFAP.

    Devuelve la ruta local del PDF.
    """

    filename = build_report_filename(
        year,
        month
    )

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = RAW_DIR / filename

    if output_path.exists() and not overwrite:

        print(
            f"El archivo ya existe: {output_path}"
        )

        return output_path

    report_url = find_report_url(
        year,
        month
    )

    print(f"Descargando: {report_url}")

    response = requests.get(
        report_url,
        headers=HEADERS,
        timeout=60,
    )

    if response.status_code == 404:

        raise FileNotFoundError(
            f"El BCU no tiene publicado el reporte "
            f"para {month:02d}/{year}."
        )

    response.raise_for_status()

    # Evitamos guardar una página HTML como si fuera PDF
    if b"%PDF-" not in response.content[:1024]:

        raise ValueError(
            "El archivo descargado no parece ser un PDF válido."
        )

    output_path.write_bytes(
        response.content
    )

    print(
        f"PDF guardado en: {output_path}"
    )

    return output_path