-- ============================================================
-- AFAP Investment Analytics
-- Carga de dimensiones
-- ============================================================


-- ------------------------------------------------------------
-- DIMENSIÓN: PERÍODO
-- Alcance inicial del proyecto:
-- Enero 2024 - Agosto 2026
-- ------------------------------------------------------------

DELETE FROM dim_period;

INSERT INTO dim_period
SELECT
    CAST(
        strftime(period_start_date, '%Y%m')
        AS INTEGER
    ) AS period_id,

    strftime(
        period_start_date,
        '%Y-%m'
    ) AS periodo,

    period_start_date,

    year(period_start_date) AS anio,

    month(period_start_date) AS mes_numero,

    CASE month(period_start_date)
        WHEN 1 THEN 'Enero'
        WHEN 2 THEN 'Febrero'
        WHEN 3 THEN 'Marzo'
        WHEN 4 THEN 'Abril'
        WHEN 5 THEN 'Mayo'
        WHEN 6 THEN 'Junio'
        WHEN 7 THEN 'Julio'
        WHEN 8 THEN 'Agosto'
        WHEN 9 THEN 'Setiembre'
        WHEN 10 THEN 'Octubre'
        WHEN 11 THEN 'Noviembre'
        WHEN 12 THEN 'Diciembre'
    END AS mes_nombre,

    quarter(
        period_start_date
    ) AS trimestre,

    concat(
        year(period_start_date),
        '-T',
        quarter(period_start_date)
    ) AS anio_trimestre

FROM generate_series(
    DATE '2024-01-01',
    DATE '2026-08-01',
    INTERVAL '1 month'
) AS periods(period_start_date);