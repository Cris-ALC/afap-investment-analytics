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
        "AFAPRentabilidades/Rentabilidad-Bruta/"
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

    return f"cocf01d{mm}{yy}.pdf"


def download_returns_report(year: int, month: int) -> Path:
    """
    Descarga el reporte mensual de Rentabilidad Bruta del BCU.

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
        f"Rentabilidad Bruta para {month:02d}/{year}."
    )

def download_returns_range(
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
) -> None:
    """Descarga un rango mensual de reportes de Rentabilidad Bruta."""

    year = start_year
    month = start_month

    downloaded = 0
    errors = []

    while (year, month) <= (end_year, end_month):

        print(f"\n--- Rentabilidad Bruta {month:02d}/{year} ---")

        try:
            download_returns_report(
                year=year,
                month=month,
            )
            downloaded += 1

        except FileNotFoundError as error:
            print(f"ERROR: {error}")
            errors.append(f"{month:02d}/{year}")

        month += 1

        if month > 12:
            month = 1
            year += 1

    print("\n--- RESUMEN DE DESCARGA ---")
    print(f"Meses procesados: {downloaded + len(errors)}")
    print(f"Correctos: {downloaded}")
    print(f"Errores: {len(errors)}")

    if errors:
        print("Meses con error:")
        for period in errors:
            print(f"  - {period}")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Descarga reportes mensuales "
            "de Rentabilidad Bruta del BCU."
        )
    )

    parser.add_argument(
        "--year",
        type=int,
        help="Año del reporte.",
    )

    parser.add_argument(
        "--month",
        type=int,
        choices=range(1, 13),
        help="Mes del reporte (1-12).",
    )

    parser.add_argument(
        "--range",
        action="store_true",
        help="Descarga un rango mensual de reportes.",
    )

    parser.add_argument(
        "--start-year",
        type=int,
        help="Año inicial.",
    )

    parser.add_argument(
        "--start-month",
        type=int,
        choices=range(1, 13),
        help="Mes inicial.",
    )

    parser.add_argument(
        "--end-year",
        type=int,
        help="Año final.",
    )

    parser.add_argument(
        "--end-month",
        type=int,
        choices=range(1, 13),
        help="Mes final.",
    )

    args = parser.parse_args()

    if args.range:
        download_returns_range(
            start_year=args.start_year,
            start_month=args.start_month,
            end_year=args.end_year,
            end_month=args.end_month,
        )

    elif args.year and args.month:
        download_returns_report(
            year=args.year,
            month=args.month,
        )

    else:
        parser.error(
            "Usá --year y --month para un mes individual, "
            "o --range con el rango de fechas."
        )