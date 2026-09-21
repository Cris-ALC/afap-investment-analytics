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
-- 2. Casos cuyo total se aleja de 100 %
-- ============================================================

SELECT
    p.periodo,
    s.subfund_nombre AS subfondo,
    a.afap_nombre,
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
    a.afap_nombre
HAVING ABS(SUM(f.valor_pct) - 1) > 0.001
ORDER BY
    p.periodo,
    s.subfund_nombre,
    a.afap_nombre;


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