from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

PORTFOLIO_FILE = (
    PROCESSED_DIR
    / "portfolio_composition_history.csv"
)

LITERAL_FILE = (
    PROCESSED_DIR
    / "portfolio_literal_history.csv"
)

def load_fact_portfolio_composition(connection):
    """
    Construye fact_portfolio_composition a partir
    del histórico procesado de composición.

    Granularidad:
    período + AFAP + subfondo + instrumento + moneda.
    """

    print(
        "\nCargando fact_portfolio_composition..."
    )

    if not PORTFOLIO_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró: {PORTFOLIO_FILE}"
        )

    portfolio = pd.read_csv(
        PORTFOLIO_FILE
    )

    # ----------------------------------------------------
    # Preparar período
    # ----------------------------------------------------

    portfolio["fecha"] = pd.to_datetime(
        portfolio["fecha"]
    )

    portfolio["periodo"] = (
        portfolio["fecha"]
        .dt.strftime("%Y-%m")
    )

    # ----------------------------------------------------
    # Incorporar claves de las dimensiones
    # ----------------------------------------------------

    dim_period = connection.execute(
        """
        SELECT
            period_id,
            periodo
        FROM dim_period
        """
    ).df()

    dim_afap = connection.execute(
        """
        SELECT
            afap_id,
            afap_nombre
        FROM dim_afap
        """
    ).df()

    dim_subfund = connection.execute(
        """
        SELECT
            subfund_id,
            subfund_nombre
        FROM dim_subfund
        """
    ).df()

    dim_instrument = connection.execute(
        """
        SELECT
            instrument_id,
            instrumento
        FROM dim_instrument
        """
    ).df()

    dim_currency = connection.execute(
        """
        SELECT
            currency_id,
            moneda
        FROM dim_currency
        """
    ).df()

    fact = (
        portfolio
        .merge(
            dim_period,
            on="periodo",
            how="left",
        )
        .merge(
            dim_afap,
            left_on="afap_normalizada",
            right_on="afap_nombre",
            how="left",
        )
        .merge(
            dim_subfund,
            left_on="subfondo",
            right_on="subfund_nombre",
            how="left",
        )
        .merge(
            dim_instrument,
            on="instrumento",
            how="left",
        )
        .merge(
            dim_currency,
            on="moneda",
            how="left",
        )
    )

    # ----------------------------------------------------
    # Validar claves dimensionales
    # ----------------------------------------------------

    required_keys = [
        "period_id",
        "afap_id",
        "subfund_id",
        "instrument_id",
    ]

    for key in required_keys:
        missing = fact[key].isna().sum()

        if missing > 0:
            raise ValueError(
                f"Se encontraron {missing} filas "
                f"sin correspondencia para {key}."
            )

    # currency_id puede ser NULL si la fuente
    # no informa moneda.

    # ----------------------------------------------------
    # Construir tabla final
    # ----------------------------------------------------

    fact_final = fact[
        [
            "period_id",
            "afap_id",
            "subfund_id",
            "instrument_id",
            "currency_id",
            "valor_pct",
            "archivo_origen",
        ]
    ].copy()

    # ----------------------------------------------------
    # Validar granularidad
    # ----------------------------------------------------

    duplicate_columns = [
        "period_id",
        "afap_id",
        "subfund_id",
        "instrument_id",
        "currency_id",
    ]

    duplicates = fact_final.duplicated(
        subset=duplicate_columns,
        keep=False,
    )

    if duplicates.any():
        raise ValueError(
            "Se encontraron duplicados en la "
            "granularidad de fact_portfolio_composition."
        )

    # ----------------------------------------------------
    # Cargar DuckDB
    # ----------------------------------------------------

    connection.execute(
        "DELETE FROM fact_portfolio_composition"
    )

    connection.register(
        "fact_portfolio_df",
        fact_final,
    )

    connection.execute(
        """
        INSERT INTO fact_portfolio_composition
        SELECT
            period_id,
            afap_id,
            subfund_id,
            instrument_id,
            currency_id,
            valor_pct,
            archivo_origen
        FROM fact_portfolio_df
        """
    )

    connection.unregister(
        "fact_portfolio_df"
    )

    # ----------------------------------------------------
    # Controles
    # ----------------------------------------------------

    loaded_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM fact_portfolio_composition
        """
    ).fetchone()[0]

    null_values = connection.execute(
        """
        SELECT COUNT(*)
        FROM fact_portfolio_composition
        WHERE valor_pct IS NULL
        """
    ).fetchone()[0]

    print(
        f"Filas cargadas: {loaded_count}"
    )

    print(
        f"valor_pct NULL: {null_values}"
    )

    if loaded_count != len(portfolio):
        raise ValueError(
            "La cantidad cargada en la fact no coincide "
            "con el dataset de origen."
        )

    return fact_final

def load_fact_portfolio_literal(connection):
    """
    Construye fact_portfolio_literal a partir del histórico
    procesado de composición por literal.

    Granularidad:
    período + AFAP + subfondo + literal.
    """

    print(
        "\nCargando fact_portfolio_literal..."
    )

    if not LITERAL_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró: {LITERAL_FILE}"
        )

    portfolio = pd.read_csv(
        LITERAL_FILE
    )

    # ----------------------------------------------------
    # Preparar período
    # ----------------------------------------------------

    portfolio["fecha"] = pd.to_datetime(
        portfolio["fecha"]
    )

    portfolio["periodo"] = (
        portfolio["fecha"]
        .dt.strftime("%Y-%m")
    )

    # ----------------------------------------------------
    # Obtener dimensiones necesarias
    # ----------------------------------------------------

    dim_period = connection.execute(
        """
        SELECT
            period_id,
            periodo
        FROM dim_period
        """
    ).df()

    dim_afap = connection.execute(
        """
        SELECT
            afap_id,
            afap_nombre
        FROM dim_afap
        """
    ).df()

    dim_subfund = connection.execute(
        """
        SELECT
            subfund_id,
            subfund_nombre
        FROM dim_subfund
        """
    ).df()

    dim_literal = connection.execute(
        """
        SELECT
            literal_id,
            literal
        FROM dim_literal
        """
    ).df()

    # ----------------------------------------------------
    # Incorporar claves dimensionales
    # ----------------------------------------------------

    fact = (
        portfolio
        .merge(
            dim_period,
            on="periodo",
            how="left",
        )
        .merge(
            dim_afap,
            left_on="afap_normalizada",
            right_on="afap_nombre",
            how="left",
        )
        .merge(
            dim_subfund,
            left_on="subfondo",
            right_on="subfund_nombre",
            how="left",
        )
        .merge(
            dim_literal,
            on="literal",
            how="left",
        )
    )

    # ----------------------------------------------------
    # Validar claves dimensionales
    # ----------------------------------------------------

    required_keys = [
        "period_id",
        "afap_id",
        "subfund_id",
        "literal_id",
    ]

    for key in required_keys:
        missing = fact[key].isna().sum()

        if missing > 0:
            raise ValueError(
                f"Se encontraron {missing} filas "
                f"sin correspondencia para {key}."
            )

    # ----------------------------------------------------
    # Construir tabla final
    # ----------------------------------------------------

    fact_final = fact[
        [
            "period_id",
            "afap_id",
            "subfund_id",
            "literal_id",
            "valor_pct",
            "archivo_origen",
        ]
    ].copy()

    # ----------------------------------------------------
    # Validar granularidad
    # ----------------------------------------------------

    duplicate_columns = [
        "period_id",
        "afap_id",
        "subfund_id",
        "literal_id",
    ]

    duplicates = fact_final.duplicated(
        subset=duplicate_columns,
        keep=False,
    )

    if duplicates.any():
        raise ValueError(
            "Se encontraron duplicados en la "
            "granularidad de fact_portfolio_literal."
        )

    # ----------------------------------------------------
    # Validar composición financiera
    # ----------------------------------------------------

    totals = (
        fact_final
        .groupby(
            [
                "period_id",
                "afap_id",
                "subfund_id",
            ],
            as_index=False,
        )["valor_pct"]
        .sum()
    )

    invalid_totals = totals[
        (totals["valor_pct"] - 1.0).abs()
        > 0.0002
    ]

    if not invalid_totals.empty:
        raise ValueError(
            "Se encontraron composiciones por literal "
            "que no suman aproximadamente 100%:\n"
            + invalid_totals.to_string(index=False)
        )

    # ----------------------------------------------------
    # Cargar DuckDB
    # ----------------------------------------------------

    connection.execute(
        "DELETE FROM fact_portfolio_literal"
    )

    connection.register(
        "fact_portfolio_literal_df",
        fact_final,
    )

    connection.execute(
        """
        INSERT INTO fact_portfolio_literal
        SELECT
            period_id,
            afap_id,
            subfund_id,
            literal_id,
            valor_pct,
            archivo_origen
        FROM fact_portfolio_literal_df
        """
    )

    connection.unregister(
        "fact_portfolio_literal_df"
    )

    # ----------------------------------------------------
    # Controles finales
    # ----------------------------------------------------

    loaded_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM fact_portfolio_literal
        """
    ).fetchone()[0]

    null_values = connection.execute(
        """
        SELECT COUNT(*)
        FROM fact_portfolio_literal
        WHERE valor_pct IS NULL
        """
    ).fetchone()[0]

    print(
        f"Filas cargadas: {loaded_count}"
    )

    print(
        f"valor_pct NULL: {null_values}"
    )

    if loaded_count != len(portfolio):
        raise ValueError(
            "La cantidad cargada en "
            "fact_portfolio_literal no coincide "
            "con el dataset de origen."
        )

    print(
        "Composición por literal: OK"
    )

    return fact_final

def load_fact_returns(connection):
    """
    Construye fact_returns a partir del histórico
    procesado de Rentabilidad Neta.

    Granularidad:
    período + AFAP + tipo_metrica + subfondo.
    """

    print(
        "\nCargando fact_returns..."
    )

    returns_file = (
        PROCESSED_DIR
        / "returns_history_test.csv"
    )

    if not returns_file.exists():
        raise FileNotFoundError(
            f"No se encontró: {returns_file}"
        )

    returns = pd.read_csv(
        returns_file
    )

    # ----------------------------------------------------
    # Normalizar período
    # ----------------------------------------------------

    returns["periodo"] = (
        pd.to_datetime(
            returns["periodo"]
        )
        .dt.strftime("%Y-%m")
    )

    # ----------------------------------------------------
    # Obtener dimensiones necesarias
    # ----------------------------------------------------

    dim_period = connection.execute(
        """
        SELECT
            period_id,
            periodo
        FROM dim_period
        """
    ).df()

    dim_afap = connection.execute(
        """
        SELECT
            afap_id,
            afap_nombre
        FROM dim_afap
        """
    ).df()

    dim_subfund = connection.execute(
        """
        SELECT
            subfund_id,
            subfund_nombre
        FROM dim_subfund
        """
    ).df()

    # ----------------------------------------------------
    # Incorporar claves dimensionales
    # ----------------------------------------------------

    fact = (
        returns
        .merge(
            dim_period,
            on="periodo",
            how="left",
        )
        .merge(
            dim_afap,
            left_on="afap_raw",
            right_on="afap_nombre",
            how="left",
        )
        .merge(
            dim_subfund,
            left_on="subfondo",
            right_on="subfund_nombre",
            how="left",
        )
    )

    # ----------------------------------------------------
    # Validar período y AFAP
    # ----------------------------------------------------

    for key in [
        "period_id",
        "afap_id",
    ]:
        missing = fact[key].isna().sum()

        if missing > 0:
            raise ValueError(
                f"Se encontraron {missing} filas "
                f"sin correspondencia para {key}."
            )

    # ----------------------------------------------------
    # Validar subfondos
    # ----------------------------------------------------
    # subfund_id debe existir solamente cuando
    # tipo_metrica == SUBFONDO.
    #
    # FAP_AGREGADO y REGIMEN_ESPECIAL no corresponden
    # a un subfondo específico y deben conservar NULL.
    # ----------------------------------------------------

    subfund_rows = fact.query(
        "tipo_metrica == 'SUBFONDO'"
    )

    missing_subfund = (
        subfund_rows.subfund_id
        .isna()
        .sum()
    )

    if missing_subfund > 0:
        raise ValueError(
            f"Se encontraron {missing_subfund} "
            "métricas de subfondo sin subfund_id."
        )

    non_subfund_rows = fact.query(
        "tipo_metrica != 'SUBFONDO'"
    )

    unexpected_subfund = (
        non_subfund_rows.subfund_id
        .notna()
        .sum()
    )

    if unexpected_subfund > 0:
        raise ValueError(
            "Se encontraron métricas agregadas "
            "asociadas incorrectamente a un subfondo."
        )

    # ----------------------------------------------------
    # Construir fact final
    # ----------------------------------------------------

    fact_final = fact[
        [
            "period_id",
            "afap_id",
            "tipo_metrica",
            "subfund_id",
            "rentabilidad_neta",
            "archivo_origen",
        ]
    ].copy()

    # ----------------------------------------------------
    # Validar granularidad
    # ----------------------------------------------------

    duplicate_columns = [
        "period_id",
        "afap_id",
        "tipo_metrica",
        "subfund_id",
    ]

    duplicates = fact_final.duplicated(
        subset=duplicate_columns,
        keep=False,
    )

    if duplicates.any():
        raise ValueError(
            "Se encontraron duplicados en la "
            "granularidad de fact_returns."
        )

    # ----------------------------------------------------
    # Cargar DuckDB
    # ----------------------------------------------------

    connection.execute(
        "DELETE FROM fact_returns"
    )

    connection.register(
        "fact_returns_df",
        fact_final,
    )

    connection.execute(
        """
        INSERT INTO fact_returns
        SELECT
            period_id,
            afap_id,
            tipo_metrica,
            subfund_id,
            rentabilidad_neta,
            archivo_origen
        FROM fact_returns_df
        """
    )

    connection.unregister(
        "fact_returns_df"
    )

    # ----------------------------------------------------
    # Controles finales
    # ----------------------------------------------------

    loaded_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM fact_returns
        """
    ).fetchone()[0]

    null_returns = connection.execute(
        """
        SELECT COUNT(*)
        FROM fact_returns
        WHERE rentabilidad_neta IS NULL
        """
    ).fetchone()[0]

    print(
        f"Filas cargadas: {loaded_count}"
    )

    print(
        f"Rentabilidades NULL: {null_returns}"
    )

    if loaded_count != len(returns):
        raise ValueError(
            "La cantidad cargada en fact_returns "
            "no coincide con el dataset de origen."
        )

    if null_returns != 0:
        raise ValueError(
            "Se encontraron rentabilidades NULL."
        )

    return fact_final