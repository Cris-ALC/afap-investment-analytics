from pathlib import Path
import requests
import truststore
import argparse

truststore.inject_into_ssl()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

BASE_URLS = [
    (
        "https://www.bcu.gub.uy/Servicios-Financieros-SSF/"
        "AFAPRentabilidades/Rentabilidad-Neta/"
    ),
    (
        "https://www.bcu.gub.uy/Servicios-Financieros-SSF/"
        "AFAPRentabilidades/"
    ),
]


def build_filename(year: int, month: int) -> str:
    """Construye el nombre del PDF mensual de rentabilidad neta."""
    yy = str(year)[-2:]
    mm = f"{month:02d}"

    return f"cocf02d{mm}{yy}.pdf"


def download_returns_report(year: int, month: int) -> Path:
    """
    Descarga el reporte mensual de Rentabilidad Neta del BCU.

    Prueba las distintas rutas históricas conocidas del BCU
    y devuelve la ruta local del PDF.
    """

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    filename = build_filename(year, month)
    output_path = RAW_DIR / filename

    if output_path.exists():
        print(f"PDF ya existe: {output_path}")
        return output_path

    for base_url in BASE_URLS:
        url = base_url + filename

        print(f"Probando: {url}")

        try:
            response = requests.get(
                url,
                timeout=30,
            )
        except requests.RequestException as error:
            print(f"Error de conexión: {error}")
            continue

        if response.status_code != 200:
            print(
                f"Ruta no disponible "
                f"(HTTP {response.status_code})"
            )
            continue

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        if (
            "pdf" not in content_type
            and not response.content.startswith(b"%PDF")
        ):
            print(
                "La respuesta existe, "
                "pero no parece ser un PDF."
            )
            continue

        output_path.write_bytes(response.content)

        print(f"PDF descargado: {output_path}")

        return output_path

    raise FileNotFoundError(
        "No fue posible localizar el reporte de "
        f"Rentabilidad Neta para {month:02d}/{year}."
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Descarga reportes mensuales "
            "de Rentabilidad Neta del BCU."
        )
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Año del reporte.",
    )

    parser.add_argument(
        "--month",
        type=int,
        required=True,
        choices=range(1, 13),
        help="Mes del reporte (1-12).",
    )

    args = parser.parse_args()

    download_returns_report(
        year=args.year,
        month=args.month,
    )