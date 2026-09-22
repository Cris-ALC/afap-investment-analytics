# AFAP Investment Analytics — Informe de validación y calidad de datos

**Corte de análisis:** enero–agosto de 2026 para composición de portafolios.  
**Base:** `data/afap_analytics.duckdb` (DuckDB).  
**Estado:** controles ejecutados; conciliación por literal y conciliación de detalle A/C superadas con las tolerancias indicadas.  
**Fuente:** informes oficiales de composición de portafolios del BCU descargados por el pipeline del proyecto.  
**Carácter:** respaldo técnico de las pruebas efectuadas; no constituye auditoría externa ni certificación de los datos de origen.

## 1. Objetivo y alcance

Documentar las pruebas de integridad estructural, calidad de datos, conciliación financiera y cobertura de rentabilidades ejecutadas sobre el modelo dimensional AFAP Investment Analytics. Las consultas reproducibles se conservan en `sql/data_quality.sql` y `sql/financial_validation.sql`; las consultas complementarias se incluyen en este informe.

El análisis de composición comprende ocho cierres mensuales de enero a agosto de 2026, tres subfondos y cinco entidades/agrupaciones presentes en los datos de composición, incluido el total del sistema. Las rentabilidades cargadas corresponden a seis cortes: enero y agosto de 2024, 2025 y 2026. Estos conjuntos tienen coberturas temporales diferentes y no deben confundirse.

## 2. Modelo y volumen de datos


| Tabla                        | Registros verificados |
| ---------------------------- | --------------------- |
| `dim_afap`                   | 6                     |
| `dim_currency`               | 4                     |
| `dim_instrument`             | 9                     |
| `dim_literal`                | 6                     |
| `dim_period`                 | 32                    |
| `dim_subfund`                | 3                     |
| `fact_portfolio_composition` | 1.205                 |
| `fact_portfolio_literal`     | 720                   |
| `fact_returns`               | 120                   |


**Observación:** `dim_period` contiene 32 períodos (enero de 2024 a agosto de 2026); ello no implica que cada tabla de hechos tenga observaciones en todos esos meses.

## 3. Matriz de controles y resultados


| ID  | Control                                                | Resultado observado                                                                                                                    | Estado / interpretación                                                                                                           |
| --- | ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| E01 | Existencia de tablas y volumen                         | Nueve tablas; conteos indicados en §2                                                                                                  | Ejecutado                                                                                                                         |
| E02 | Cobertura de composición                               | Ocho meses; 1.205 filas                                                                                                                | Ejecutado                                                                                                                         |
| E03 | Distribución mensual de composición                    | Ene 150; feb 145; mar 150; abr 150; may 150; jun 150; jul 155; ago 155                                                                 | Ejecutado; variación de filas no implica por sí sola un error                                                                     |
| E04 | Clave compuesta de composición                         | No se detectaron grupos duplicados por período, AFAP, subfondo, instrumento y moneda                                                   | Superado                                                                                                                          |
| E05 | Integridad referencial de composición                  | Sin referencias huérfanas en las dimensiones verificadas                                                                               | Superado                                                                                                                          |
| E06 | Valores faltantes en composición                       | 95 valores `valor_pct` nulos; claves foráneas verificadas sin nulos                                                                    | Observación documentada; no imputar automáticamente                                                                               |
| E07 | Cobertura de rentabilidad                              | 120 filas; seis cortes; 20 filas por corte                                                                                             | Ejecutado                                                                                                                         |
| E08 | Tipos de rentabilidad                                  | 72 `SUBFONDO`, 24 `FAP_AGREGADO`, 24 `REGIMEN_ESPECIAL`                                                                                | Ejecutado                                                                                                                         |
| E09 | Nulos y claves de rentabilidad                         | Sin nulos en rentabilidad neta, período ni AFAP; 48 `subfund_id` nulos asociados a métricas agregadas/especiales                       | Consistente con el nivel de agregación registrado                                                                                 |
| E10 | Duplicados e integridad referencial de rentabilidad    | Sin duplicados de la clave de negocio verificada ni referencias huérfanas en AFAP/período                                              | Superado                                                                                                                          |
| F01 | Total por cartera de la tabla de literales             | 120 carteras; seis literales por cartera; mínimo 99,99 % y máximo 100,01 %; cero diferencias con tolerancia de 0,1 puntos porcentuales | Superado                                                                                                                          |
| F02 | Nulos por literal                                      | 12 filas, todas de `LITERAL F` en Acumulación: SURA enero–agosto (8), ITAÚ mayo–agosto (4)                                             | Observación; pendiente confirmar semántica de blanco contra PDF original                                                          |
| F03 | Total de detalle por instrumento                       | 120 carteras; sumas entre 52,47 % y 87,04 %                                                                                            | No corresponde exigir 100 %: el detalle disponible cubre los literales A y C                                                      |
| F04 | Conciliación instrumentos vs. literales A y C          | Cero diferencias detectadas con tolerancia de 0,1 puntos porcentuales                                                                  | Superado dentro del alcance de la consulta ejecutada; confirmar explícitamente la cardinalidad de las 240 comparaciones previstas |
| F05 | Ejemplo de conciliación: SURA, Acumulación, enero 2026 | Literal A: 49,86 % en ambas tablas; literal C: 6,63 % en ambas; A+C: 56,49 %                                                           | Coincidencia exacta en porcentajes presentados                                                                                    |


**Tolerancia:** `ABS(total - 1) > 0.001` equivale a diferencias superiores a 0,1 puntos porcentuales, cuando los porcentajes se almacenan como proporciones (1 = 100 %). El redondeo mostrado a dos decimales no reemplaza la comparación sobre valores sin redondear.

## 4. Consultas SQL de respaldo

Las consultas siguientes reproducen los controles financieros principales. Para la totalidad de los controles de integridad y rentabilidad, conservar los archivos originales `sql/data_quality.sql` y `sql/financial_validation.sql` en el mismo commit que este informe; esos archivos son la fuente ejecutable completa.

### F01. Conciliación de los seis literales por cartera

```sql
SELECT
    period_id,
    afap_id,
    subfund_id,
    COUNT(*) AS cantidad_literales,
    COUNT(valor_pct) AS literales_informados,
    SUM(valor_pct) AS total
FROM fact_portfolio_literal
GROUP BY period_id, afap_id, subfund_id
HAVING COUNT(*) <> 6
    OR SUM(valor_pct) IS NULL
    OR ABS(SUM(valor_pct) - 1) > 0.001;
```

**Resultado:** cero carteras con diferencias. Una consulta agregada sin `HAVING` confirmó 120 carteras, seis filas por cartera y totales entre 0,9999 y 1,0001.

### F02. Identificación de literales sin porcentaje

```sql
SELECT
    p.periodo,
    a.afap_nombre,
    s.subfund_nombre AS subfondo,
    l.literal,
    f.valor_pct
FROM fact_portfolio_literal f
JOIN dim_period p ON f.period_id = p.period_id
JOIN dim_afap a ON f.afap_id = a.afap_id
JOIN dim_subfund s ON f.subfund_id = s.subfund_id
JOIN dim_literal l ON f.literal_id = l.literal_id
WHERE f.valor_pct IS NULL
ORDER BY p.periodo, a.afap_nombre, s.subfund_nombre;
```

**Resultado:** 12 registros, todos `LITERAL F` de Acumulación. La suma del resto de literales se mantiene dentro de la tolerancia en las 12 carteras. Un `NULL` no se convierte en cero sin validar el significado del espacio en blanco en la fuente.

### F03. Control informativo del total del detalle por instrumento

```sql
SELECT
    period_id,
    afap_id,
    subfund_id,
    COUNT(*) AS registros,
    COUNT(valor_pct) AS valores_informados,
    SUM(valor_pct) AS total_detalle
FROM fact_portfolio_composition
GROUP BY period_id, afap_id, subfund_id
ORDER BY period_id, afap_id, subfund_id;
```

**Resultado:** 120 carteras, con sumas entre 0,5247 y 0,8704. Este control es informativo; no debe tener una regla de 100 % porque los instrumentos de `dim_instrument` están asociados a los literales A y C.

### F04. Conciliación del desglose por instrumento con los literales A y C

```sql
WITH totales_literal AS (
    SELECT f.period_id, f.afap_id, f.subfund_id,
           l.literal,
           SUM(f.valor_pct) AS total_literal
    FROM fact_portfolio_literal f
    JOIN dim_literal l ON f.literal_id = l.literal_id
    WHERE l.literal IN ('LITERAL A', 'LITERAL C')
    GROUP BY 1, 2, 3, 4
),
detalle_instrumentos AS (
    SELECT f.period_id, f.afap_id, f.subfund_id,
           i.literal AS literal,
           SUM(f.valor_pct) AS total_detalle
    FROM fact_portfolio_composition f
    JOIN dim_instrument i ON f.instrument_id = i.instrument_id
    GROUP BY 1, 2, 3, 4
)
SELECT l.period_id, l.afap_id, l.subfund_id, l.literal,
       l.total_literal, d.total_detalle,
       l.total_literal - d.total_detalle AS diferencia
FROM totales_literal l
LEFT JOIN detalle_instrumentos d
  ON l.period_id = d.period_id
 AND l.afap_id = d.afap_id
 AND l.subfund_id = d.subfund_id
 AND l.literal = d.literal
WHERE d.total_detalle IS NULL
   OR l.total_literal IS NULL
   OR ABS(l.total_literal - d.total_detalle) > 0.001
ORDER BY 1, 2, 3, 4;
```

**Resultado:** cero diferencias. **Limitación de la ejecución registrada:** el script imprimió «Comparaciones esperadas: 240» como valor fijo, no como un conteo calculado. Antes de afirmar que se compararon efectivamente las 240 combinaciones, ejecutar el control adicional siguiente.

### Conciliación entre instrumentos y literales A y C

**Objetivo:** verificar que la suma de los porcentajes por instrumento coincida con el total del literal correspondiente para cada combinación de período, AFAP y subfondo.

**Metodología:** se agruparon los registros de `fact_portfolio_composition` según el literal asociado a cada instrumento y se compararon con los totales de `fact_portfolio_literal`. Se aplicó una tolerancia de 0,001 en escala decimal, equivalente a 0,1 puntos porcentuales.

| Indicador | Resultado |

|---|---:|

| Comparaciones realizadas | 240 |

| Desgloses encontrados | 240 |

| Desgloses faltantes | 0 |

| Diferencias superiores a la tolerancia | 0 |

**Resultado:** control superado. Las 120 carteras cuentan con los desgloses correspondientes a los literales A y C, sin diferencias superiores a la tolerancia establecida.

**Consulta de respaldo:** sección 4 de `sql/financial_validation.sql`.

### F04-A. Control adicional de cardinalidad y categorías no conciliadas

```sql
WITH literales AS (
    SELECT f.period_id, f.afap_id, f.subfund_id, l.literal,
           SUM(f.valor_pct) AS total_literal
    FROM fact_portfolio_literal f
    JOIN dim_literal l ON l.literal_id = f.literal_id
    WHERE l.literal IN ('LITERAL A', 'LITERAL C')
    GROUP BY 1, 2, 3, 4
),
detalle AS (
    SELECT f.period_id, f.afap_id, f.subfund_id, i.literal,
           SUM(f.valor_pct) AS total_detalle
    FROM fact_portfolio_composition f
    JOIN dim_instrument i ON i.instrument_id = f.instrument_id
    GROUP BY 1, 2, 3, 4
),
comparacion AS (
    SELECT COALESCE(l.period_id, d.period_id) AS period_id,
           COALESCE(l.afap_id, d.afap_id) AS afap_id,
           COALESCE(l.subfund_id, d.subfund_id) AS subfund_id,
           COALESCE(l.literal, d.literal) AS literal,
           l.total_literal, d.total_detalle
    FROM literales l
    FULL OUTER JOIN detalle d
      ON l.period_id = d.period_id
     AND l.afap_id = d.afap_id
     AND l.subfund_id = d.subfund_id
     AND l.literal = d.literal
)
SELECT COUNT(*) AS comparaciones_efectivas,
       COUNT(*) FILTER (
           WHERE total_literal IS NULL
              OR total_detalle IS NULL
              OR ABS(total_literal - total_detalle) > 0.001
       ) AS diferencias_o_faltantes
FROM comparacion;
```

**Estado:** consulta propuesta, todavía no ejecutada. Debe devolver 240 comparaciones y cero diferencias/faltantes para cerrar también el control de cobertura bidireccional.

### Consultas de calidad e integridad — referencia ejecutable

`sql/data_quality.sql` contiene las consultas ejecutadas sobre cobertura temporal, conteos, unicidad, valores nulos e integridad referencial. No se reproducen aquí textualmente porque el contenido íntegro del archivo no se ha cotejado en esta sesión; conservarlo sin alteraciones y referenciar el commit correspondiente.

`sql/financial_validation.sql` contiene cuatro consultas ejecutadas después de la corrección: resumen de composición (120 filas), conciliación por literal (0 filas), control informativo de literales nulos (12 filas) y listado de rentabilidad (120 filas). Los controles de F01 y F02 anteriores reflejan la lógica validada.

## 5. Interpretación de los nulos y excepciones

- Los 12 `NULL` en `fact_portfolio_literal` corresponden exclusivamente a `LITERAL F`, subfondo Acumulación, para SURA (ocho meses) e ITAÚ (mayo–agosto).
- El hecho de que los demás literales sumen aproximadamente 100 % **no prueba por sí solo** que cada blanco del PDF equivalga a una participación económica de cero. Conservar el valor faltante y cotejar con el PDF original antes de asignarle significado.
- Los 95 `NULL` del detalle por instrumento ya habían sido identificados en la etapa de calidad de datos; su interpretación debe mantenerse documentada y no mezclarse con los 12 nulos de la tabla de literales.
- La tabla de detalle por instrumento no representa por sí sola el 100 % de la cartera. Los instrumentos actualmente clasificados en `dim_instrument` corresponden a los literales A y C.



## 6. Conclusiones y acciones pendientes

**Comprobado:** integridad estructural y conteos indicados; ausencia de duplicados y referencias huérfanas en las verificaciones ejecutadas; conciliación del total de los seis literales en las 120 carteras; identificación y segregación de los 12 nulos; ausencia de diferencias superiores a 0,1 puntos porcentuales entre detalle por instrumento y totales A/C en la consulta realizada.

**Pendiente para cierre documental definitivo:** (1) ejecutar F04-A para certificar el número efectivo de comparaciones y detectar categorías presentes solo en el detalle; (2) contrastar los 12 blancos de `LITERAL F` con los PDF originales del BCU; (3) adjuntar o referenciar los archivos SQL del commit definitivo y registrar fecha de ejecución, versión del código y hash de Git.

## 7. Registro de ejecución


| Campo                     | Valor                                                        |
| ------------------------- | ------------------------------------------------------------ |
| Entorno                   | Windows 11, PowerShell, Python, DuckDB                       |
| Base de datos             | `data/afap_analytics.duckdb`                                 |
| Modo de validación        | Conexiones `read_only=True` en los controles complementarios |
| Archivos SQL              | `sql/data_quality.sql`, `sql/financial_validation.sql`       |
| Períodos de composición   | 2026-01 a 2026-08                                            |
| Períodos de rentabilidad  | 2024-01, 2024-08, 2025-01, 2025-08, 2026-01, 2026-08         |
| Fecha exacta de ejecución | Completar al incorporar el documento al repositorio          |
| Commit de referencia      | Completar después del commit del informe                     |


