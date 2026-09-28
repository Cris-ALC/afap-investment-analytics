-- ============================================================
-- AFAP Investment Analytics
-- Modelo dimensional
-- ============================================================


-- ------------------------------------------------------------
-- DIMENSIÓN: PERÍODO
-- Una fila representa un mes calendario.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dim_period (
    period_id INTEGER PRIMARY KEY,
    periodo VARCHAR NOT NULL UNIQUE,
    period_start_date DATE NOT NULL,
    anio INTEGER NOT NULL,
    mes_numero INTEGER NOT NULL,
    mes_nombre VARCHAR NOT NULL,
    trimestre INTEGER NOT NULL,
    anio_trimestre VARCHAR NOT NULL
);


-- ------------------------------------------------------------
-- DIMENSIÓN: AFAP
-- Mantiene separadas las entidades publicadas por el BCU.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dim_afap (
    afap_id INTEGER PRIMARY KEY,
    afap_nombre VARCHAR NOT NULL UNIQUE,
    tipo_entidad VARCHAR NOT NULL
);


-- ------------------------------------------------------------
-- DIMENSIÓN: SUBFONDO
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dim_subfund (
    subfund_id INTEGER PRIMARY KEY,
    subfund_nombre VARCHAR NOT NULL UNIQUE
);


-- ------------------------------------------------------------
-- DIMENSIÓN: INSTRUMENTO
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dim_instrument (
    instrument_id INTEGER PRIMARY KEY,
    instrumento VARCHAR NOT NULL UNIQUE,
    literal VARCHAR
);


-- ------------------------------------------------------------
-- DIMENSIÓN: MONEDA
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dim_currency (
    currency_id INTEGER PRIMARY KEY,
    moneda VARCHAR NOT NULL UNIQUE
);


-- ------------------------------------------------------------
-- DIMENSIÓN: LITERAL
-- Categorías regulatorias de composición publicadas por el BCU.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dim_literal (
    literal_id INTEGER PRIMARY KEY,
    literal VARCHAR NOT NULL UNIQUE
);


-- ============================================================
-- TABLAS DE HECHOS
-- ============================================================


-- ------------------------------------------------------------
-- FACT: COMPOSICIÓN DEL PORTAFOLIO
-- Una fila representa la participación porcentual de un
-- instrumento/moneda para una AFAP, subfondo y período.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fact_portfolio_composition (
    period_id INTEGER NOT NULL,
    afap_id INTEGER NOT NULL,
    subfund_id INTEGER NOT NULL,
    instrument_id INTEGER NOT NULL,
    currency_id INTEGER,
    valor_pct DOUBLE,
    archivo_origen VARCHAR,

    FOREIGN KEY (period_id)
        REFERENCES dim_period(period_id),

    FOREIGN KEY (afap_id)
        REFERENCES dim_afap(afap_id),

    FOREIGN KEY (subfund_id)
        REFERENCES dim_subfund(subfund_id),

    FOREIGN KEY (instrument_id)
        REFERENCES dim_instrument(instrument_id),

    FOREIGN KEY (currency_id)
        REFERENCES dim_currency(currency_id)
);


-- ------------------------------------------------------------
-- FACT: COMPOSICIÓN POR LITERAL
-- Una fila representa la participación porcentual de una
-- categoría regulatoria para una entidad, subfondo y período.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fact_portfolio_literal (
    period_id INTEGER NOT NULL,
    afap_id INTEGER NOT NULL,
    subfund_id INTEGER NOT NULL,
    literal_id INTEGER NOT NULL,
    valor_pct DOUBLE,
    archivo_origen VARCHAR,

    FOREIGN KEY (period_id)
        REFERENCES dim_period(period_id),

    FOREIGN KEY (afap_id)
        REFERENCES dim_afap(afap_id),

    FOREIGN KEY (subfund_id)
        REFERENCES dim_subfund(subfund_id),

    FOREIGN KEY (literal_id)
        REFERENCES dim_literal(literal_id)
);


-- ------------------------------------------------------------
-- FACT: RENTABILIDAD NETA
-- Una fila representa una métrica de rentabilidad publicada
-- para una AFAP y período.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fact_returns (
    period_id INTEGER NOT NULL,
    afap_id INTEGER NOT NULL,
    tipo_metrica VARCHAR NOT NULL,
    subfund_id INTEGER,
    rentabilidad_neta DOUBLE NOT NULL,
    archivo_origen VARCHAR,

    FOREIGN KEY (period_id)
        REFERENCES dim_period(period_id),

    FOREIGN KEY (afap_id)
        REFERENCES dim_afap(afap_id),

    FOREIGN KEY (subfund_id)
        REFERENCES dim_subfund(subfund_id)
);

-- ------------------------------------------------------------
-- FACT: RENTABILIDAD BRUTA
-- Una fila representa una tasa de rentabilidad bruta publicada
-- para una AFAP/total del sistema, período y tipo de fondo.
--
-- tipo_tasa:
--   TRM = Tasa de Rentabilidad Real Mensual
--   TNA = Tasa de Rentabilidad Nominal Anual
--   TRA = Tasa de Rentabilidad Real Anual en UR
--
-- subfund_id se utiliza únicamente para:
--   CRECIMIENTO, ACUMULACION y RETIRO.
--
-- Para FAP y FONDO_VOLUNTARIO_PREVISIONAL,
-- subfund_id permanece NULL.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fact_gross_returns (
    period_id INTEGER NOT NULL,
    afap_id INTEGER NOT NULL,
    tipo_fondo VARCHAR NOT NULL,
    tipo_tasa VARCHAR NOT NULL,
    subfund_id INTEGER,
    rentabilidad_bruta DOUBLE NOT NULL,
    archivo_origen VARCHAR,

    FOREIGN KEY (period_id)
        REFERENCES dim_period(period_id),

    FOREIGN KEY (afap_id)
        REFERENCES dim_afap(afap_id),

    FOREIGN KEY (subfund_id)
        REFERENCES dim_subfund(subfund_id)
);