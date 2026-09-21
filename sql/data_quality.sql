-- ============================================================
-- AFAP Investment Analytics
-- Controles de calidad del modelo dimensional
-- ============================================================


-- ============================================================
-- 1. DIM_PERIOD
-- ============================================================

SELECT
    COUNT(*) AS cantidad_periodos
FROM dim_period;

SELECT
    MIN(periodo) AS primer_periodo,
    MAX(periodo) AS ultimo_periodo
FROM dim_period;

SELECT
    anio,
    COUNT(*) AS cantidad_meses
FROM dim_period
GROUP BY anio
ORDER BY anio;


-- ============================================================
-- 2. DIM_AFAP
-- ============================================================

SELECT
    tipo_entidad,
    COUNT(*) AS cantidad
FROM dim_afap
GROUP BY tipo_entidad
ORDER BY tipo_entidad;


-- ============================================================
-- 3. DIM_SUBFUND
-- ============================================================

SELECT
    COUNT(*) AS cantidad_subfondos
FROM dim_subfund;


-- ============================================================
-- 4. DIM_CURRENCY
-- ============================================================

SELECT
    COUNT(*) AS cantidad_monedas
FROM dim_currency;


-- ============================================================
-- 5. DIM_INSTRUMENT
-- ============================================================

SELECT
    COUNT(*) AS cantidad_instrumentos,
    COUNT(DISTINCT instrumento) AS instrumentos_unicos
FROM dim_instrument;


-- ============================================================
-- 6. FACT_PORTFOLIO_COMPOSITION
-- ============================================================

SELECT
    COUNT(*) AS filas_portfolio,
    COUNT(DISTINCT period_id) AS periodos_con_datos,
    COUNT(DISTINCT afap_id) AS entidades,
    COUNT(DISTINCT subfund_id) AS subfondos,
    COUNT(DISTINCT instrument_id) AS instrumentos,
    COUNT(DISTINCT currency_id) AS monedas
FROM fact_portfolio_composition;


-- Nulos de la fact de composición

SELECT
    SUM(CASE WHEN period_id IS NULL THEN 1 ELSE 0 END)
        AS period_id_null,
    SUM(CASE WHEN afap_id IS NULL THEN 1 ELSE 0 END)
        AS afap_id_null,
    SUM(CASE WHEN subfund_id IS NULL THEN 1 ELSE 0 END)
        AS subfund_id_null,
    SUM(CASE WHEN instrument_id IS NULL THEN 1 ELSE 0 END)
        AS instrument_id_null,
    SUM(CASE WHEN currency_id IS NULL THEN 1 ELSE 0 END)
        AS currency_id_null,
    SUM(CASE WHEN valor_pct IS NULL THEN 1 ELSE 0 END)
        AS valor_pct_null
FROM fact_portfolio_composition;


-- Duplicados según la granularidad definida

SELECT
    period_id,
    afap_id,
    subfund_id,
    instrument_id,
    currency_id,
    COUNT(*) AS cantidad
FROM fact_portfolio_composition
GROUP BY
    period_id,
    afap_id,
    subfund_id,
    instrument_id,
    currency_id
HAVING COUNT(*) > 1;


-- Cobertura temporal de composición

SELECT
    p.periodo,
    COUNT(*) AS filas
FROM fact_portfolio_composition f
JOIN dim_period p
    ON f.period_id = p.period_id
GROUP BY p.periodo
ORDER BY p.periodo;


-- ============================================================
-- 7. FACT_RETURNS
-- ============================================================

SELECT
    COUNT(*) AS filas_returns,
    COUNT(DISTINCT period_id) AS periodos_con_datos,
    COUNT(DISTINCT afap_id) AS afaps
FROM fact_returns;


-- Nulos principales

SELECT
    SUM(CASE WHEN period_id IS NULL THEN 1 ELSE 0 END)
        AS period_id_null,
    SUM(CASE WHEN afap_id IS NULL THEN 1 ELSE 0 END)
        AS afap_id_null,
    SUM(CASE WHEN rentabilidad_neta IS NULL THEN 1 ELSE 0 END)
        AS rentabilidad_null
FROM fact_returns;


-- Validar comportamiento de subfund_id según tipo de métrica

SELECT
    tipo_metrica,
    COUNT(*) AS filas,
    SUM(
        CASE
            WHEN subfund_id IS NULL THEN 1
            ELSE 0
        END
    ) AS subfund_null
FROM fact_returns
GROUP BY tipo_metrica
ORDER BY tipo_metrica;


-- Duplicados según granularidad de rentabilidad

SELECT
    period_id,
    afap_id,
    tipo_metrica,
    subfund_id,
    COUNT(*) AS cantidad
FROM fact_returns
GROUP BY
    period_id,
    afap_id,
    tipo_metrica,
    subfund_id
HAVING COUNT(*) > 1;


-- Cobertura temporal de rentabilidad

SELECT
    p.periodo,
    COUNT(*) AS filas
FROM fact_returns f
JOIN dim_period p
    ON f.period_id = p.period_id
GROUP BY p.periodo
ORDER BY p.periodo;


-- ============================================================
-- 8. INTEGRIDAD REFERENCIAL
-- ============================================================

-- AFAP de composición sin dimensión

SELECT COUNT(*) AS portfolio_afap_sin_dimension
FROM fact_portfolio_composition f
LEFT JOIN dim_afap d
    ON f.afap_id = d.afap_id
WHERE d.afap_id IS NULL;


-- Períodos de composición sin dimensión

SELECT COUNT(*) AS portfolio_periodo_sin_dimension
FROM fact_portfolio_composition f
LEFT JOIN dim_period d
    ON f.period_id = d.period_id
WHERE d.period_id IS NULL;


-- Instrumentos sin dimensión

SELECT COUNT(*) AS portfolio_instrumento_sin_dimension
FROM fact_portfolio_composition f
LEFT JOIN dim_instrument d
    ON f.instrument_id = d.instrument_id
WHERE d.instrument_id IS NULL;


-- AFAP de rentabilidad sin dimensión

SELECT COUNT(*) AS returns_afap_sin_dimension
FROM fact_returns f
LEFT JOIN dim_afap d
    ON f.afap_id = d.afap_id
WHERE d.afap_id IS NULL;


-- Períodos de rentabilidad sin dimensión

SELECT COUNT(*) AS returns_periodo_sin_dimension
FROM fact_returns f
LEFT JOIN dim_period d
    ON f.period_id = d.period_id
WHERE d.period_id IS NULL;