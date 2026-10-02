# CSV completo del informe AFAP — 27/09/2026

## Archivos y alcance

- `data_loader.py`: conserva las funciones usadas por el pipeline existente y agrega `load_complete_report(pdf_path)` y `save_complete_report(pdf_path, output_path=None)`.
- `portfolio_composition_2024_01.csv`: resultado de la extracción completa de `cocf03d0124.pdf` adjunto, fecha de corte 31/01/2024.
- `pipeline_range.py` fue revisado, sin modificaciones. Importa `run_portfolio_pipeline` desde `pipeline.py`, que no se recibió. La integración con el pipeline mensual queda pendiente de revisar ese archivo.

## Ejecutar en el proyecto

Guardar la versión anterior del código con Git o una copia y colocar el `data_loader.py` actualizado en `src/`. Con el entorno virtual activado, ejecutar desde la raíz del proyecto:

```powershell
python src\data_loader.py --pdf data\raw\cocf03d0124.pdf
```

Genera `data/processed/portfolio_composition_2024_01.csv` con todas las tablas de datos. Si ya existe, lo reemplaza. Para revisar primero en otro destino:

```powershell
python src\data_loader.py --pdf data\raw\cocf03d0124.pdf --output data\processed\revision\portfolio_composition_2024_01.csv
```

Este comando usa el PDF local y no descarga archivos. Sin `--pdf`, se mantiene el diagnóstico anterior. El nombre mensual conserva el patrón existente `YYYY_MM`, con guion bajo entre año y mes.

## Cobertura comprobada


| Página    | Fondo       | Bloque                         | Filas del PDF | Registros CSV |
| --------- | ----------- | ------------------------------ | ------------- | ------------- |
| 1         | Crecimiento | Composición y totales          | 22            | 110           |
| 2         | Crecimiento | Anexo Literal A                | 22            | 22            |
| 3         | Acumulación | Composición y totales          | 22            | 110           |
| 4         | Acumulación | Anexo Literal A                | 22            | 22            |
| 5         | Retiro      | Composición y totales          | 22            | 110           |
| 6         | Retiro      | Anexo Literal A                | 24            | 24            |
| 7         | FVP         | Composición y total de activos | 9             | 45            |
| **Total** |             |                                | **143**       | **443**       |


Las tablas de composición producen una observación por fila y entidad: cuatro AFAP y TOTAL SISTEMA, incluso si una celda está vacía. Los anexos producen una observación por fila física, con las dos columnas porcentuales separadas. Encabezados, notas al pie y líneas separadoras no se convierten en observaciones. `texto_fila_raw` conserva el texto completo de cada fila de datos.

## Campos para distinguir magnitudes y evitar duplicaciones


| Campo                                                      | Uso                                                                                                                                              |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `seccion`                                                  | `COMPOSICION` o `ANEXO_LITERAL_A`.                                                                                                               |
| `fondo`                                                    | CRECIMIENTO, ACUMULACION, RETIRO o FVP.                                                                                                          |
| `subfondo`                                                 | Solo los tres subfondos; vacío para FVP.                                                                                                         |
| `tipo_fila`                                                | DETALLE, SUBTOTAL, TOTAL_GENERAL, PARTICIPACION, TOTAL_MONETARIO, DETALLE_ANEXO, SUBTOTAL_ANEXO o TOTAL_ANEXO.                                   |
| `tipo_valor`                                               | PORCENTAJE o IMPORTE.                                                                                                                            |
| `valor_pct`                                                | Proporción decimal: 2,13 % se guarda como 0.0213. En anexos toma S/ACT FAP si tiene valor; en otro caso, TOT. SISTEMA. No suma las dos columnas. |
| `valor_importe`                                            | Importe nominal extraído sin dividir entre 100. Vacío en filas porcentuales.                                                                     |
| `unidad`                                                   | PROPORCION o `$`, conservando el símbolo de la fuente. El archivo no atribuye una moneda distinta ni una escala en miles/millones al importe.    |
| `valor_raw`                                                | Valor tal como aparece en el PDF.                                                                                                                |
| `anexo_pct_s_act_fap`, `anexo_pct_tot_sistema`             | Ambas columnas originales del anexo en escala decimal; se conservan también sus textos originales.                                               |
| `columna_origen`                                           | Entidad en composición; S_ACT_FAP, TOT_SISTEMA o AMBAS en anexos.                                                                                |
| `tipo_instrumento`                                         | Categoría heredada dentro del bloque del anexo.                                                                                                  |
| `moneda_raw`, `moneda`                                     | Moneda del instrumento, cuando corresponde. No representan la moneda de los totales monetarios.                                                  |
| `pagina`, `fila_pdf`, `fila_id`, `y_pdf`, `archivo_origen` | Trazabilidad. La clave del CSV es archivo + fila_id + AFAP.                                                                                      |


Los 50 importes incluyen 45 observaciones de activos, reserva especial y saldo del subfondo (3 conceptos × 3 subfondos × 5 entidades), y 5 importes de activos del FVP. Son conceptos distintos: no sumarlos indiscriminadamente.

## Validaciones realizadas

- Las 7 páginas están representadas; se compararon las 434 celdas numéricas del cuerpo de las tablas con las extraídas, página por página. En los anexos se contabilizaron las dos columnas porcentuales.
- Se mantuvieron los valores de las 285 observaciones porcentuales que producía el extractor original para los tres subfondos.
- Pasaron los controles originales de entidades, porcentajes, 15 totales al 100 % y composición por literal, aplicados únicamente a la composición porcentual de los tres subfondos.
- Se comprobaron activos menos reserva especial igual a saldo de subfondo, con tolerancia de $1 por redondeo, para las 15 combinaciones.
- Se probó una fila con sus cinco celdas vacías: conserva las cinco observaciones nulas.
- Por ejemplo, el activo del subfondo Crecimiento / TOTAL SISTEMA se conservó como `101513938450`, en las unidades monetarias publicadas.

Estas pruebas cubren el PDF de enero de 2024 recibido. El código rechaza páginas, fechas o formatos numéricos que no reconoce; no acredita la compatibilidad de todos los diseños históricos. No se realizó el cotejo individual de las 12 celdas pendientes ni se imputaron ceros.

## Integración pendiente

El `pipeline.py` actual podría volver a guardar únicamente el detalle al ejecutar el comando mensual o el rango. Debe revisarse su código para que guarde el reporte completo al final de su procesamiento y conserve las salidas analíticas necesarias. No se cambió `load_all_subfunds` para evitar alterar silenciosamente los controles existentes.

Antes de cargar este CSV ampliado en las tablas de hechos actuales, adaptar el cargador: para el detalle original usar `seccion == COMPOSICION`, `tipo_fila == DETALLE` y los tres subfondos; mantener importes, FVP y anexos diferenciados. Anexos, subtotales y detalles se superponen: no sumar todos sus porcentajes. Tampoco sumar TOTAL SISTEMA junto con las AFAP ni saldos de varios meses como un solo activo.

Próximo paso: incorporar el `pipeline.py` vigente y conectar el guardado completo. Después retomar las 12 celdas y la ampliación histórica.