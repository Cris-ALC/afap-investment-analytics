
-- ============================================================
-- AFAP Investment Analytics
-- Vistas analíticas para Power BI
-- ============================================================

-- 1. Composición del portafolio por literal

CREATE OR REPLACE VIEW vw_portfolio_literal AS

SELECT
    p.period_id,
    p.periodo,
    a.afap_id,
    a.afap_nombre,
    a.tipo_entidad,
    s.subfund_id,
    s.subfund_nombre,
    l.literal_id,
    l.literal,
    f.valor_pct,
    f.archivo_origen

FROM fact_portfolio_literal f

JOIN dim_period p
    ON f.period_id = p.period_id

JOIN dim_afap a
    ON f.afap_id = a.afap_id

JOIN dim_subfund s
    ON f.subfund_id = s.subfund_id

JOIN dim_literal l
    ON f.literal_id = l.literal_id;

-- ============================================================
-- 2. Composición del portafolio por instrumento y moneda
-- ============================================================

CREATE OR REPLACE VIEW vw_portfolio_instrument AS

SELECT
    p.period_id,
    p.periodo,
    a.afap_id,
    a.afap_nombre,
    a.tipo_entidad,
    s.subfund_id,
    s.subfund_nombre,
    i.instrument_id,
    i.instrumento,
    i.literal,
    m.currency_id,
    m.moneda,
    f.valor_pct,
    f.archivo_origen

FROM fact_portfolio_composition f

JOIN dim_period p
    ON f.period_id = p.period_id

JOIN dim_afap a
    ON f.afap_id = a.afap_id

JOIN dim_subfund s
    ON f.subfund_id = s.subfund_id

JOIN dim_instrument i
    ON f.instrument_id = i.instrument_id

JOIN dim_currency m
    ON f.currency_id = m.currency_id;



-- ============================================================
-- 3. Rentabilidad neta por AFAP, tipo de métrica y subfondo
-- ============================================================

CREATE OR REPLACE VIEW vw_returns AS

SELECT
    p.period_id,
    p.periodo,
    a.afap_id,
    a.afap_nombre,
    a.tipo_entidad,

    -- NULL cuando la métrica no corresponde a un subfondo
    s.subfund_id,
    s.subfund_nombre,

    f.tipo_metrica,
    f.rentabilidad_neta,

    -- Valor expresado en puntos porcentuales
    f.rentabilidad_neta * 100 AS rentabilidad_neta_pct,

    f.archivo_origen

FROM fact_returns f

JOIN dim_period p
    ON f.period_id = p.period_id

JOIN dim_afap a
    ON f.afap_id = a.afap_id

LEFT JOIN dim_subfund s
    ON f.subfund_id = s.subfund_id;

-- ============================================================
-- 4. Rentabilidad bruta por AFAP, fondo y tipo de tasa
-- ============================================================

CREATE OR REPLACE VIEW vw_gross_returns AS

SELECT
    p.period_id,
    p.periodo,

    a.afap_id,
    a.afap_nombre,
    a.tipo_entidad,

    -- NULL para FAP y Fondo Voluntario Previsional
    s.subfund_id,
    s.subfund_nombre,

    f.tipo_fondo,
    f.tipo_tasa,

    f.rentabilidad_bruta,

    -- Valor expresado en puntos porcentuales
    f.rentabilidad_bruta * 100
        AS rentabilidad_bruta_pct,

    f.archivo_origen

FROM fact_gross_returns f

JOIN dim_period p
    ON f.period_id = p.period_id

JOIN dim_afap a
    ON f.afap_id = a.afap_id

LEFT JOIN dim_subfund s
    ON f.subfund_id = s.subfund_id;