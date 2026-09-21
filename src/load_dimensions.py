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

RETURNS_FILE = (
    PROCESSED_DIR
    / "returns_history_test.csv"
)


def validate_source_files():
    """
    Comprueba que existan los datasets procesados
    necesarios para construir las dimensiones.
    """

    required_files = [
        PORTFOLIO_FILE,
        LITERAL_FILE,
        RETURNS_FILE,
    ]

    for file_path in required_files:
        if not file_path.exists():
            raise FileNotFoundError(
                f"No se encontró: {file_path}"
            )


def load_dim_afap(connection):
    """
    Construye dim_afap a partir de las entidades
    existentes en los datasets procesados.
    """

    print(
        "\nCargando dim_afap..."
    )

    validate_source_files()

    # Leer datasets
    portfolio = pd.read_csv(
        PORTFOLIO_FILE
    )

    returns = pd.read_csv(
        RETURNS_FILE
    )

    # Obtener entidades de composición
    portfolio_afaps = (
        portfolio.afap_normalizada
        .dropna()
        .astype(str)
        .str.strip()
    )

    # Obtener entidades de rentabilidad
    returns_afaps = (
        returns.afap_raw
        .dropna()
        .astype(str)
        .str.strip()
    )

    # Combinar ambas fuentes
    afaps = pd.concat(
        [
            portfolio_afaps,
            returns_afaps,
        ],
        ignore_index=True,
    )

    afaps = (
        afaps
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    # Construir dimensión
    dim_afap = pd.DataFrame(
        {
            "afap_nombre": afaps
        }
    )

    dim_afap.insert(
        0,
        "afap_id",
        range(
            1,
            len(dim_afap) + 1
        ),
    )

    dim_afap["tipo_entidad"] = (
        dim_afap.afap_nombre.apply(
            lambda value: (
                "TOTAL_SISTEMA"
                if value == "TOTAL SISTEMA"
                else "AFAP"
            )
        )
    )

    # Limpiar dimensión antes de cargar
    connection.execute(
        "DELETE FROM dim_afap"
    )

    # Registrar DataFrame temporalmente
    connection.register(
        "dim_afap_df",
        dim_afap,
    )

    # Insertar en DuckDB
    connection.execute(
        """
        INSERT INTO dim_afap
        SELECT
            afap_id,
            afap_nombre,
            tipo_entidad
        FROM dim_afap_df
        """
    )

    connection.unregister(
        "dim_afap_df"
    )

    # Control
    result = connection.execute(
        """
        SELECT
            afap_id,
            afap_nombre,
            tipo_entidad
        FROM dim_afap
        ORDER BY afap_id
        """
    ).fetchall()

    print(
        f"Entidades cargadas: {len(result)}"
    )

    for row in result:
        print(
            f"  {row[0]} | "
            f"{row[1]} | "
            f"{row[2]}"
        )

    return dim_afap


def load_dim_subfund(connection):
    """
    Construye dim_subfund a partir de los subfondos
    existentes en los datasets procesados.
    """

    print(
        "\nCargando dim_subfund..."
    )

    validate_source_files()

    # Leer datasets
    portfolio = pd.read_csv(
        PORTFOLIO_FILE
    )

    returns = pd.read_csv(
        RETURNS_FILE
    )

    # Obtener subfondos de composición
    portfolio_subfunds = (
        portfolio.subfondo
        .dropna()
        .astype(str)
        .str.strip()
    )

    # Obtener subfondos de rentabilidad.
    # Los NULL correspondientes a métricas agregadas
    # se excluyen correctamente.
    returns_subfunds = (
        returns.subfondo
        .dropna()
        .astype(str)
        .str.strip()
    )

    # Combinar ambas fuentes
    subfunds = pd.concat(
        [
            portfolio_subfunds,
            returns_subfunds,
        ],
        ignore_index=True,
    )

    subfunds = (
        subfunds
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    # Construir dimensión
    dim_subfund = pd.DataFrame(
        {
            "subfund_nombre": subfunds
        }
    )

    dim_subfund.insert(
        0,
        "subfund_id",
        range(
            1,
            len(dim_subfund) + 1
        ),
    )

    # Limpiar dimensión antes de cargar
    connection.execute(
        "DELETE FROM dim_subfund"
    )

    # Registrar DataFrame temporalmente
    connection.register(
        "dim_subfund_df",
        dim_subfund,
    )

    # Insertar en DuckDB
    connection.execute(
        """
        INSERT INTO dim_subfund
        SELECT
            subfund_id,
            subfund_nombre
        FROM dim_subfund_df
        """
    )

    connection.unregister(
        "dim_subfund_df"
    )

    # Control
    result = connection.execute(
        """
        SELECT
            subfund_id,
            subfund_nombre
        FROM dim_subfund
        ORDER BY subfund_id
        """
    ).fetchall()

    print(
        f"Subfondos cargados: {len(result)}"
    )

    for row in result:
        print(
            f"  {row[0]} | {row[1]}"
        )

    return dim_subfund

def load_dim_currency(connection):
    """
    Construye dim_currency a partir de las monedas
    existentes en el dataset de composición.
    """

    print(
        "\nCargando dim_currency..."
    )

    if not PORTFOLIO_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró: {PORTFOLIO_FILE}"
        )

    portfolio = pd.read_csv(
        PORTFOLIO_FILE
    )

    currencies = (
        portfolio.moneda
        .dropna()
        .astype(str)
        .str.strip()
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    dim_currency = pd.DataFrame(
        {
            "moneda": currencies
        }
    )

    dim_currency.insert(
        0,
        "currency_id",
        range(
            1,
            len(dim_currency) + 1
        ),
    )

    connection.execute(
        "DELETE FROM dim_currency"
    )

    connection.register(
        "dim_currency_df",
        dim_currency,
    )

    connection.execute(
        """
        INSERT INTO dim_currency
        SELECT
            currency_id,
            moneda
        FROM dim_currency_df
        """
    )

    connection.unregister(
        "dim_currency_df"
    )

    result = connection.execute(
        """
        SELECT
            currency_id,
            moneda
        FROM dim_currency
        ORDER BY currency_id
        """
    ).fetchall()

    print(
        f"Monedas cargadas: {len(result)}"
    )

    for row in result:
        print(
            f"  {row[0]} | {row[1]}"
        )

    return dim_currency

def load_dim_instrument(connection):
    """
    Construye dim_instrument a partir de los instrumentos
    de detalle existentes en el dataset de composición.
    """

    print(
        "\nCargando dim_instrument..."
    )

    if not PORTFOLIO_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró: {PORTFOLIO_FILE}"
        )

    portfolio = pd.read_csv(
        PORTFOLIO_FILE
    )

    instruments = (
        portfolio
        .query("tipo_fila == 'DETALLE'")
        .loc[:, ["instrumento", "literal"]]
        .dropna(subset=["instrumento"])
        .drop_duplicates()
        .sort_values(
            by=["literal", "instrumento"]
        )
        .reset_index(drop=True)
    )

    # Validar que cada instrumento tenga
    # un único literal.
    literal_count = (
        instruments
        .groupby("instrumento")
        .literal
        .nunique()
    )

    if (literal_count > 1).any():
        raise ValueError(
            "Se encontraron instrumentos asociados "
            "a más de un literal."
        )

    instruments.insert(
        0,
        "instrument_id",
        range(
            1,
            len(instruments) + 1
        ),
    )

    connection.execute(
        "DELETE FROM dim_instrument"
    )

    connection.register(
        "dim_instrument_df",
        instruments,
    )

    connection.execute(
        """
        INSERT INTO dim_instrument
        SELECT
            instrument_id,
            instrumento,
            literal
        FROM dim_instrument_df
        """
    )

    connection.unregister(
        "dim_instrument_df"
    )

    result = connection.execute(
        """
        SELECT
            instrument_id,
            instrumento,
            literal
        FROM dim_instrument
        ORDER BY instrument_id
        """
    ).fetchall()

    print(
        f"Instrumentos cargados: {len(result)}"
    )

    for row in result:
        print(
            f"  {row[0]} | "
            f"{row[1]} | "
            f"{row[2]}"
        )

    return instruments

def load_dim_literal(connection):
    """
    Construye dim_literal a partir de las categorías
    existentes en el histórico de composición por literal.
    """

    print(
        "\nCargando dim_literal..."
    )

    if not LITERAL_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró: {LITERAL_FILE}"
        )

    portfolio_literal = pd.read_csv(
        LITERAL_FILE
    )

    literals = (
        portfolio_literal["literal"]
        .dropna()
        .astype(str)
        .str.strip()
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    # Control estructural.
    expected_literals = {
        "D. TRANSITORIA",
        "LITERAL A",
        "LITERAL B",
        "LITERAL C",
        "LITERAL D",
        "LITERAL F",
    }

    detected_literals = set(literals)

    if detected_literals != expected_literals:
        raise ValueError(
            "Categorías de literal inesperadas. "
            f"Detectadas: {detected_literals}"
        )

    dim_literal = pd.DataFrame(
        {
            "literal": literals
        }
    )

    dim_literal.insert(
        0,
        "literal_id",
        range(
            1,
            len(dim_literal) + 1
        ),
    )

    connection.execute(
        "DELETE FROM dim_literal"
    )

    connection.register(
        "dim_literal_df",
        dim_literal,
    )

    connection.execute(
        """
        INSERT INTO dim_literal
        SELECT
            literal_id,
            literal
        FROM dim_literal_df
        """
    )

    connection.unregister(
        "dim_literal_df"
    )

    result = connection.execute(
        """
        SELECT
            literal_id,
            literal
        FROM dim_literal
        ORDER BY literal_id
        """
    ).fetchall()

    print(
        f"Literales cargados: {len(result)}"
    )

    for row in result:
        print(
            f"  {row[0]} | {row[1]}"
        )

    return dim_literal