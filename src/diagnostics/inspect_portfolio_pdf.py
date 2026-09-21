from pathlib import Path

import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "cocf03d0826.pdf"
)


def inspect_pdf():
    if not PDF_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró: {PDF_PATH}"
        )

    with pdfplumber.open(PDF_PATH) as pdf:
        print(
            f"\nPDF: {PDF_PATH.name}"
        )

        print(
            f"Páginas: {len(pdf.pages)}\n"
        )

        for page_number, page in enumerate(
            pdf.pages,
            start=1,
        ):
            print(
                "=" * 70
            )

            print(
                f"PÁGINA {page_number}"
            )

            print(
                "=" * 70
            )

            text = page.extract_text()

            if text:
                print(text)
            else:
                print(
                    "[Página sin texto extraíble]"
                )

            print()


if __name__ == "__main__":
    inspect_pdf()