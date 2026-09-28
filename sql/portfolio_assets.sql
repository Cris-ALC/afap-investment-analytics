-- Saldos de cierre: no sumar conceptos ni períodos distintos.
CREATE TABLE IF NOT EXISTS fact_portfolio_assets (
    period_id INTEGER NOT NULL REFERENCES dim_period(period_id),
    afap_id INTEGER NOT NULL REFERENCES dim_afap(afap_id),
    subfund_id INTEGER REFERENCES dim_subfund(subfund_id),
    fondo VARCHAR NOT NULL CHECK (fondo IN ('CRECIMIENTO','ACUMULACION','RETIRO','FVP')),
    concepto VARCHAR NOT NULL CHECK (concepto IN ('TOTAL_ACTIVOS','RESERVA_ESPECIAL','TOTAL_SUBFONDO')),
    fecha DATE NOT NULL,
    unidad VARCHAR NOT NULL,
    valor_importe DECIMAL(24,2) NOT NULL,
    concepto_raw VARCHAR NOT NULL,
    valor_raw VARCHAR NOT NULL,
    pagina INTEGER NOT NULL,
    fila_pdf INTEGER NOT NULL,
    fila_id VARCHAR NOT NULL,
    archivo_origen VARCHAR NOT NULL,
    PRIMARY KEY (period_id, afap_id, fondo, concepto),
    CHECK ((fondo = 'FVP' AND subfund_id IS NULL AND concepto = 'TOTAL_ACTIVOS')
        OR (fondo <> 'FVP' AND subfund_id IS NOT NULL))
);

CREATE OR REPLACE VIEW vw_portfolio_assets AS
SELECT p.period_id, p.periodo, a.afap_id, a.afap_nombre, a.tipo_entidad,
       f.subfund_id, s.subfund_nombre, f.fondo, f.concepto, f.fecha,
       f.unidad, f.valor_importe, f.concepto_raw, f.valor_raw,
       f.pagina, f.fila_pdf, f.fila_id, f.archivo_origen
FROM fact_portfolio_assets f
JOIN dim_period p ON f.period_id = p.period_id
JOIN dim_afap a ON f.afap_id = a.afap_id
LEFT JOIN dim_subfund s ON f.subfund_id = s.subfund_id;
