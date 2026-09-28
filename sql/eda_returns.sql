
-- ============================================================
-- AFAP Investment Analytics
-- EDA: rentabilidad neta
-- ============================================================

-- 1. Cobertura temporal y tipos de rentabilidad

SELECT
    periodo,
    tipo_metrica,
    COUNT(*) AS registros,
    COUNT(DISTINCT afap_id) AS cantidad_afap,
    COUNT(DISTINCT subfund_id) AS cantidad_subfondos,
    COUNT(*) FILTER (
        WHERE rentabilidad_neta IS NULL
    ) AS rentabilidades_nulas

FROM vw_returns

GROUP BY
    periodo,
    tipo_metrica

ORDER BY
    periodo,
    tipo_metrica;


-- ============================================================
-- 2. Comparación de rentabilidad neta entre AFAP
-- Agosto de 2026, por subfondo
-- ============================================================

SELECT
    subfund_nombre,
    afap_nombre,
    ROUND(rentabilidad_neta_pct, 2)
        AS rentabilidad_neta_pct

FROM vw_returns

WHERE periodo = '2026-08'
  AND tipo_metrica = 'SUBFONDO'

ORDER BY
    subfund_nombre,
    afap_nombre;


-- ============================================================
-- 3. Evolución de la rentabilidad neta por AFAP y subfondo
-- ============================================================

SELECT
    periodo,
    afap_nombre,
    subfund_nombre,
    ROUND(rentabilidad_neta_pct, 2)
        AS rentabilidad_neta_pct

FROM vw_returns

WHERE tipo_metrica = 'SUBFONDO'

ORDER BY
    afap_nombre,
    subfund_nombre,
    periodo;   