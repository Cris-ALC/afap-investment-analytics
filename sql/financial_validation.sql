-- ============================================================
-- AFAP Investment Analytics
-- Controles financieros / funcionales
-- ============================================================


-- ============================================================
-- 1. Composición por período, subfondo y entidad
-- ============================================================

SELECT
    p.periodo,
    s.subfund_nombre AS subfondo,
    a.afap_nombre,
    a.tipo_entidad,
    COUNT(*) AS cantidad_registros,
    COUNT(f.valor_pct) AS valores_informados,
    SUM(f.valor_pct) AS total_composicion
FROM fact_portfolio_composition f
JOIN dim_period p
    ON f.period_id = p.period_id
JOIN dim_afap a
    ON f.afap_id = a.afap_id
JOIN dim_subfund s
    ON f.subfund_id = s.subfund_id
GROUP BY
    p.periodo,
    s.subfund_nombre,
    a.afap_nombre,
    a.tipo_entidad
ORDER BY
    p.periodo,
    s.subfund_nombre,
    a.afap_nombre;

-- ============================================================
-- 2. Conciliación financiera por literal
-- ============================================================

SELECT
    p.periodo,
    s.subfund_nombre AS subfondo,
    a.afap_nombre,
    COUNT(*) AS cantidad_literales,
    ROUND(SUM(f.valor_pct) * 100, 2)
        AS total_porcentaje
FROM fact_portfolio_literal f
JOIN dim_period p
    ON f.period_id = p.period_id
JOIN dim_afap a
    ON f.afap_id = a.afap_id
JOIN dim_subfund s
    ON f.subfund_id = s.subfund_id
GROUP BY
    p.periodo,
    s.subfund_nombre,
    a.afap_nombre
HAVING
    COUNT(*) <> 6
    OR SUM(f.valor_pct) IS NULL
    OR ABS(SUM(f.valor_pct) - 1) > 0.001
ORDER BY
    p.periodo,
    s.subfund_nombre,
    a.afap_nombre;

-- ============================================================
-- 2.1. Control informativo de literales sin porcentaje
-- ============================================================

SELECT
    p.periodo,
    a.afap_nombre,
    s.subfund_nombre AS subfondo,
    l.literal,
    f.valor_pct
FROM fact_portfolio_literal f
JOIN dim_period p
    ON f.period_id = p.period_id
JOIN dim_afap a
    ON f.afap_id = a.afap_id
JOIN dim_subfund s
    ON f.subfund_id = s.subfund_id
JOIN dim_literal l
    ON f.literal_id = l.literal_id
WHERE f.valor_pct IS NULL
ORDER BY
    p.periodo,
    a.afap_nombre,
    s.subfund_nombre;

-- ============================================================
-- 3. Rentabilidad por período y AFAP
-- ============================================================

SELECT
    p.periodo,
    a.afap_nombre,
    f.tipo_metrica,
    s.subfund_nombre AS subfondo,
    f.rentabilidad_neta
FROM fact_returns f
JOIN dim_period p
    ON f.period_id = p.period_id
JOIN dim_afap a
    ON f.afap_id = a.afap_id
LEFT JOIN dim_subfund s
    ON f.subfund_id = s.subfund_id
ORDER BY
    p.periodo,
    a.afap_nombre,
    f.tipo_metrica,
    s.subfund_nombre;

-- ============================================================
-- 4. Conciliación de instrumentos contra literales A y C
-- ============================================================

WITH detalle AS (
    SELECT
        f.period_id,
        f.afap_id,
        f.subfund_id,
        i.literal,
        SUM(f.valor_pct) AS total_instrumentos
    FROM fact_portfolio_composition f
    JOIN dim_instrument i
        ON f.instrument_id = i.instrument_id
    GROUP BY 1, 2, 3, 4
),
literales AS (
    SELECT
        f.period_id,
        f.afap_id,
        f.subfund_id,
        l.literal,
        SUM(f.valor_pct) AS total_literal
    FROM fact_portfolio_literal f
    JOIN dim_literal l
        ON f.literal_id = l.literal_id
    WHERE l.literal IN ('LITERAL A', 'LITERAL C')
    GROUP BY 1, 2, 3, 4
)
SELECT
    COUNT(*) AS comparaciones,
    COUNT(d.total_instrumentos) AS desgloses_encontrados,
    COUNT(*) FILTER (
        WHERE d.total_instrumentos IS NULL
    ) AS desgloses_faltantes,
    COUNT(*) FILTER (
        WHERE d.total_instrumentos IS NOT NULL
          AND ABS(
              l.total_literal - d.total_instrumentos
          ) > 0.001
    ) AS diferencias
FROM literales l
LEFT JOIN detalle d
    ON l.period_id = d.period_id
    AND l.afap_id = d.afap_id
    AND l.subfund_id = d.subfund_id
    AND l.literal = d.literal;