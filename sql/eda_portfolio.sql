
-- ============================================================
-- AFAP Investment Analytics
-- Análisis exploratorio: evolución por literal
-- ============================================================

-- Comparación entre enero y agosto de 2026
-- para el total del sistema.

WITH composicion AS (
    SELECT
        periodo,
        subfund_nombre,
        literal,
        valor_pct
    FROM vw_portfolio_literal
    WHERE afap_nombre = 'TOTAL SISTEMA'
      AND periodo IN ('2026-01', '2026-08')
)

SELECT
    subfund_nombre,
    literal,

    ROUND(
        MAX(valor_pct) FILTER (
            WHERE periodo = '2026-01'
        ) * 100,
        2
    ) AS enero_pct,

    ROUND(
        MAX(valor_pct) FILTER (
            WHERE periodo = '2026-08'
        ) * 100,
        2
    ) AS agosto_pct,

    ROUND(
        (
            MAX(valor_pct) FILTER (
                WHERE periodo = '2026-08'
            )
            -
            MAX(valor_pct) FILTER (
                WHERE periodo = '2026-01'
            )
        ) * 100,
        2
    ) AS variacion_pp

FROM composicion

GROUP BY
    subfund_nombre,
    literal

ORDER BY
    subfund_nombre,
    literal;


-- ============================================================
-- Evolución mensual por literal
-- Total del sistema AFAP
-- ============================================================

SELECT
    periodo,
    subfund_nombre,
    literal,
    ROUND(valor_pct * 100, 2) AS participacion_pct,

    ROUND(
        (
            valor_pct
            - LAG(valor_pct) OVER (
                PARTITION BY subfund_nombre, literal
                ORDER BY periodo
            )
        ) * 100,
        2
    ) AS variacion_mensual_pp

FROM vw_portfolio_literal

WHERE afap_nombre = 'TOTAL SISTEMA'

ORDER BY
    subfund_nombre,
    literal,
    periodo;


-- ============================================================
-- Comparación entre AFAP
-- Subfondo Retiro - Literal C
-- Enero vs. agosto de 2026
-- ============================================================

SELECT
    afap_nombre,

    ROUND(
        MAX(valor_pct) FILTER (
            WHERE periodo = '2026-01'
        ) * 100,
        2
    ) AS enero_pct,

    ROUND(
        MAX(valor_pct) FILTER (
            WHERE periodo = '2026-08'
        ) * 100,
        2
    ) AS agosto_pct,

    ROUND(
        (
            MAX(valor_pct) FILTER (
                WHERE periodo = '2026-08'
            )
            -
            MAX(valor_pct) FILTER (
                WHERE periodo = '2026-01'
            )
        ) * 100,
        2
    ) AS variacion_pp

FROM vw_portfolio_literal

WHERE subfund_nombre = 'RETIRO'
  AND literal = 'LITERAL C'
  AND periodo IN ('2026-01', '2026-08')

GROUP BY afap_nombre

ORDER BY afap_nombre;