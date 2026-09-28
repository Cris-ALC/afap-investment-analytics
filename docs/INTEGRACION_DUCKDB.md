# Integración del histórico y los importes monetarios

Actualización del 28/09/2026. Probada con los dos históricos recibidos y una copia de la base DuckDB compartida.

## Instalar y ejecutar

1. Cerrar las conexiones a DuckDB. Extraer el ZIP en la raíz de `afap-investment-analytics`, combinando las carpetas `src`, `sql` y `docs`. Reemplaza `src/load_facts.py` y `src/export_powerbi.py`; agrega tres archivos de código/SQL y este documento. Conservar los dos históricos finales en `data/processed`.
2. Con `.venv` activo, ejecutar desde la raíz del proyecto:

```powershell
python src\migrate_portfolio.py
```

El comando lee `data/afap_analytics.duckdb` y genera **otro archivo**, `data/afap_analytics_actualizada.duckdb`. La base original se conserva. La salida debe ser nueva; si ya existe, elegir otro nombre con `--output-db data\afap_analytics_actualizada_2.duckdb`.

3. Exportar la base nueva a una carpeta de prueba:

```powershell
python src\export_powerbi.py --db data\afap_analytics_actualizada.duckdb --output powerbi\data_actualizada
```

4. Compartir la salida de ambos comandos. El siguiente paso es conectar Power BI a los CSV de `data_actualizada` y agregar la vista monetaria. La ejecución anterior no cambia el PBIX ni la carpeta de exportación usada por el dashboard actual.

**Para esta actualización usar `migrate_portfolio.py`.** El flujo anterior `database.py --rebuild` elimina y reconstruye la base y no es el procedimiento de migración. `database.py`, `load_dimensions.py` y sus SQL originales se conservan. La migración usa `sql/portfolio_assets.sql` y agrega Literal E con una clave nueva; no renumera las dimensiones existentes ni vuelve a cargar rentabilidad.

## Resultados esperados

| Objeto | Filas |
|---|---:|
| CSV reporte completo | 15.488 |
| fact_portfolio_composition / vw_portfolio_instrument | 4.765 |
| fact_portfolio_literal / vw_portfolio_literal | 2.900 |
| fact_portfolio_assets / vw_portfolio_assets | 1.600 |
| fact_returns / vw_returns | 120 |
| dim_literal | 7 |

Cobertura de composición: enero de 2024 a agosto de 2026, 32 meses. La rentabilidad conserva su cobertura anterior. Los instrumentos mantienen 344 porcentajes nulos y los literales, 44. No se sustituyen por cero. Los 1.600 importes son numéricos.

El reporte completo contiene otras filas (totales porcentuales, participaciones, composición FVP y anexos). Permanecen en el CSV original. Las 4.765 observaciones de instrumentos corresponden exclusivamente a `COMPOSICION / DETALLE / PORCENTAJE` de los tres subfondos.

## Modelo monetario

Una fila por período, AFAP, fondo y concepto. Conceptos: `TOTAL_ACTIVOS`, `RESERVA_ESPECIAL`, `TOTAL_SUBFONDO`. FVP tiene únicamente `TOTAL_ACTIVOS` y `subfund_id` nulo; la vista lo conserva mediante LEFT JOIN. Usar la columna `fondo` para identificar FVP.

Los importes se guardan como DECIMAL(24,2), con fecha, concepto original, importe original, unidad, página, fila y archivo. La unidad sigue siendo el símbolo `$` publicado; falta confirmar formalmente moneda y escala antes de rotular el dashboard. No deducir la moneda del total a partir de la moneda de un instrumento.

Son saldos de cierre: no sumar distintos meses, no sumar activos con reserva y saldo neto, ni sumar TOTAL SISTEMA junto con las AFAP. Para la primera tarjeta: un período, fondo CRECIMIENTO y concepto TOTAL_ACTIVOS, eligiendo TOTAL SISTEMA o las AFAP individuales por separado.

## Validaciones ejecutadas

- Igualdad de cobertura mensual entre históricos, ausencia de meses intermedios y duplicados. Coincidencia de los 2.900 subtotales con el CSV de literales, incluidos los nulos.
- 50 importes por mes, conceptos y entidades completos, valores originales consistentes, claves dimensionales válidas.
- 480 conciliaciones: activos menos reserva especial igual al saldo del subfondo. Diferencia absoluta máxima: $1.
- 320 conciliaciones: TOTAL SISTEMA frente a la suma de las AFAP por mes, fondo y concepto. Diferencia absoluta máxima: $1.
- Tolerancia de literales: 0,0002 en proporción (0,02 puntos porcentuales), con margen de 1e-12 para la representación binaria. No se amplió materialmente la tolerancia financiera.
- Rentabilidad y dimensiones anteriores preservadas; vistas anteriores conservadas y sin pérdida de registros.
- Reejecución sobre una copia ya migrada con resultados idénticos; rechazo de duplicados, importes nulos, entidades desconocidas, descuadres y sobrescritura del original. Ante errores de validación no se publica la base de salida.
- Exportación de las cuatro vistas y las seis dimensiones completada.

Estas pruebas verifican la integración y las conciliaciones del histórico recibido. No sustituyen una revisión celda a celda de los 32 PDF. Quedan pendientes el examen de los nulos no cotejados, la confirmación de unidades monetarias y la integración visual en Power BI.
