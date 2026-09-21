from pathlib import Path

from data_loader import (
    get_portfolio_literal_totals,
    load_all_subfunds,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "cocf03d0826.pdf"
)


def main():
    df_all = load_all_subfunds(PDF_PATH)

    df_literals = get_portfolio_literal_totals(
        df_all
    )

    print(
        "\n=== COMPOSICIÓN POR LITERAL ===\n"
    )

    print(
        df_literals[
            [
                "subfondo",
                "afap",
                "literal",
                "valor_pct",
            ]
        ].to_string(index=False)
    )

    print(
        "\n=== CANTIDAD DE REGISTROS ==="
    )
    print(len(df_literals))

    print(
        "\n=== CATEGORÍAS DETECTADAS ==="
    )
    print(
        sorted(
            df_literals["literal"]
            .dropna()
            .unique()
        )
    )

    print(
        "\n=== SUMA POR SUBFONDO Y ENTIDAD ==="
    )

    totals = (
        df_literals
        .groupby(
            [
                "subfondo",
                "afap",
            ],
            as_index=False,
        )["valor_pct"]
        .sum()
    )

    totals["total_pct"] = (
        totals["valor_pct"] * 100
    )

    print(
        totals[
            [
                "subfondo",
                "afap",
                "total_pct",
            ]
        ].to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()