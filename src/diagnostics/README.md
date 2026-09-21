# Diagnostics

Esta carpeta contiene scripts auxiliares utilizados durante el desarrollo para

inspeccionar fuentes de datos, investigar anomalías y validar supuestos antes de incorporar controles definitivos al pipeline productivo.

Estos scripts no forman parte del ETL principal. Se conservan como herramientas de diagnóstico y como referencia reutilizable para futuros proyectos de datos.

## Objetivo

Durante el desarrollo de un pipeline de datos pueden aparecer resultados que

parecen errores, pero que en realidad pueden deberse a:

- cambios en la estructura de la fuente;
- diferencias de formato entre archivos;
- valores faltantes legítimos;
- errores de extracción;
- supuestos incorrectos sobre los datos;
- redondeos;
- diferencias entre datos de detalle, subtotales y totales.

Antes de modificar el pipeline productivo conviene aislar el problema mediante scripts pequeños de diagnóstico.

El flujo recomendado es:

```text

Fuente original

      ↓

Inspección

      ↓

Diagnóstico

      ↓

Validación del supuesto

      ↓

Corrección del ETL

      ↓

Control permanente de calidad

```

---

## Scripts disponibles

### `inspect_portfolio_pdf.py`

Herramienta utilizada para inspeccionar directamente la estructura de los PDF

de composición del portafolio publicados por el BCU.

Fue útil para analizar:

- distribución de páginas;
- encabezados;
- posiciones de columnas;
- nombres de AFAP;
- instrumentos;
- literales;
- porcentajes;
- cambios de layout entre períodos.

Este análisis permitió detectar que las coordenadas de las columnas podían

variar entre archivos, por lo que no era seguro depender exclusivamente de

posiciones fijas.

### `check_portfolio_totals.py`

Control utilizado para analizar las sumas obtenidas a partir del detalle de

instrumentos.

Permitió comprobar que el dataset de detalle no representa necesariamente el

100 % del portafolio, ya que la fuente contiene categorías adicionales que no

aparecen desagregadas a nivel de instrumento.

Este diagnóstico evitó incorporar al pipeline un control financiero incorrecto

que exigiera que el detalle de instrumentos sumara 100 %.

### `test_literal_totals.py`

Script utilizado para validar la extracción de la composición del portafolio a

nivel de literal.

Controla la estructura formada por:

- D. TRANSITORIA
- LITERAL A
- LITERAL B
- LITERAL C
- LITERAL D
- LITERAL F

La suma de estas categorías debe aproximarse al 100 % para cada combinación de:

```text

período + AFAP + subfondo

```

Se admite una pequeña tolerancia debido al redondeo de los porcentajes

publicados por la fuente.

---

## Principio de trabajo

Un control de calidad no debería incorporarse al pipeline únicamente porque

parece lógico desde el punto de vista técnico.

Primero debe comprobarse que representa correctamente la estructura y el

significado financiero de la fuente.

En este proyecto, por ejemplo:

```text

Detalle de instrumentos ≠ Portafolio completo

```

mientras que:

```text

D. TRANSITORIA

+ LITERAL A

+ LITERAL B

+ LITERAL C

+ LITERAL D

+ LITERAL F

≈ 100 %

```

La inspección de la fuente permitió distinguir ambos niveles y diseñar dos

tablas de hechos diferentes:

```text

fact_portfolio_composition

    → detalle disponible por instrumento

fact_portfolio_literal

    → composición completa por categoría

```

---

## Uso en futuros proyectos

Esta carpeta puede utilizarse como modelo cuando sea necesario investigar una

nueva fuente de datos.

Una práctica recomendable es crear scripts de diagnóstico para responder

preguntas concretas antes de modificar el ETL principal.

Ejemplos:

```text

inspect_[source.py](http://source.py)

check_[totals.py](http://totals.py)

check_[duplicates.py](http://duplicates.py)

check_missing_[values.py](http://values.py)

check_schema_[changes.py](http://changes.py)

test_[extraction.py](http://extraction.py)

```

Una vez comprendido y validado el comportamiento de los datos, los controles que deban ejecutarse permanentemente deberían trasladarse al pipeline o al sistema formal de validación.

Los scripts exploratorios pueden conservarse en `diagnostics/` como evidencia del proceso de análisis y como herramientas para futuras investigaciones.