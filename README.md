# AFAP Investment Analytics – Uruguay

Proyecto de **ingeniería de datos y análisis financiero** enfocado en el sistema previsional administrado por las **Administradoras de Fondos de Ahorro Previsional (AFAP)** de Uruguay.

El proyecto utiliza información pública oficial emitida por la **Superintendencia de Servicios Financieros del Banco Central del Uruguay (BCU)** y busca transformar reportes financieros publicados en PDF, no diseñados como datasets estructurados, en **datasets históricos, trazables y preparados para el análisis.**

El objetivo central es construir un pipeline **ETL automatizado, reproducible, trazable y auditable**, integrando Python, SQL y Power BI y aplicando controles de calidad de datos (*Data Quality*) durante todo el proceso.

Actualmente se procesan datos correspondientes a:

- República AFAP
- AFAP SURA
- Integración AFAP
- AFAP Itaú
- Total del Sistema

---



## Objetivos del proyecto

1. **Automatización ETL**
  Construir un pipeline reproducible que descargue, extraiga, transforme, normalice y valide automáticamente reportes mensuales publicados por el BCU.
2. **Preservación de trazabilidad**
  Mantener los documentos originales en una capa *Raw* y conservar la referencia al archivo de origen de cada registro procesado.
3. **Principio de no invención de datos**
  Preservar los valores publicados por la fuente oficial sin completar valores faltantes mediante supuestos. Cuando una celda del documento original no contiene información, el dataset conserva dicha ausencia como `NaN`.
4. **Modelado analítico (Tidy Data)**
  Transformar matrices financieras diseñadas para lectura humana en estructuras tabulares normalizadas y preparadas para análisis con Python, SQL y herramientas de Business Intelligence.
5. **Data Quality**
  Incorporar controles automáticos sobre estructura, entidades, subfondos, porcentajes, duplicados, valores faltantes y consistencia de totales.
6. **Análisis y visualización**
  Construir métricas sobre composición de portafolio, instrumentos, monedas, concentración y, en etapas posteriores, rentabilidad y otras variables relevantes del sistema AFAP.
7. **Business Intelligence**
  Desarrollar un modelo analítico y un dashboard interactivo en Power BI para explorar la evolución del sistema y comparar administradoras y subfondos.

---



## Fuente de datos

La fuente principal del proyecto es el **Banco Central del Uruguay (BCU)**.

La primera fuente incorporada al pipeline corresponde a los reportes mensuales:

**Composición del Portafolio – Principales Variables**

Estos documentos presentan la composición porcentual de los activos administrados por las AFAP.

Actualmente se procesan los siguientes subfondos:

- Crecimiento
- Acumulación
- Retiro

La información permite analizar dimensiones como:

- AFAP
- Subfondo
- Instrumento financiero
- Literal regulatorio
- Moneda
- Participación porcentual
- Total del sistema
- Fecha del reporte

El proyecto está diseñado para incorporar progresivamente otras fuentes oficiales del BCU, incluyendo información de rentabilidad y otras variables relevantes para el análisis de inversiones.

---



## Arquitectura del proyecto

```text

afap-investment-analytics/

│

├── data/

│   ├── raw/              # PDFs originales descargados del BCU

│   └── processed/        # Datasets generados por el pipeline

│

├── docs/                 # Documentación

├── notebooks/            # Análisis exploratorio

├── powerbi/              # Dashboard y modelo Power BI

├── sql/                  # Modelo y consultas SQL

│

├── src/

│   ├── data_[loader.py](http://loader.py)

│   ├── download_[data.py](http://data.py)

│   ├── [pipeline.py](http://pipeline.py)

│   ├── pipeline_[range.py](http://range.py)

│   └── validate_[data.py](http://data.py)

│

├── .gitignore

├── requirements.txt

└── [README.md](http://README.md)

```

Los PDFs descargados y los datasets procesados no se almacenan en Git, ya que pueden reconstruirse mediante el pipeline.

---



## Arquitectura ETL

El flujo implementado actualmente es:

```text

Banco Central del Uruguay

          │

          ▼

Descubrimiento del reporte

          │

          ▼

Descarga automática del PDF

          │

          ▼

data/raw

          │

          ▼

Extracción con pdfplumber

          │

          ▼

Identificación de subfondos

          │

          ▼

Detección dinámica de columnas

          │

          ▼

Extracción de porcentajes

          │

          ▼

Transformación a formato Tidy / Long

          │

          ▼

Reconstrucción de dimensiones

          │

          ▼

Normalización

          │

          ▼

Controles de Data Quality

          │

          ▼

CSV mensual

          │

          ▼

Dataset histórico consolidado

```

---



## Extracción de PDFs

Uno de los principales desafíos técnicos del proyecto es que la información del BCU se publica originalmente en documentos PDF diseñados para lectura humana y no como datasets estructurados.

`data_loader.py` utiliza `pdfplumber` para recuperar texto y coordenadas de los elementos del documento.

A partir de esta información el pipeline:

- identifica las páginas correspondientes a cada subfondo;
- reconstruye las filas del reporte;
- detecta los porcentajes;
- asigna cada porcentaje a su AFAP correspondiente;
- transforma la matriz visual en registros analíticos;
- reconstruye literal, instrumento y moneda;
- normaliza las dimensiones.

---



## Detección dinámica de columnas

Durante la validación histórica se identificó que los documentos del BCU **no mantienen una geometría horizontal uniforme entre todos los períodos**.

Inicialmente, el extractor utilizaba posiciones horizontales fijas para identificar las columnas de cada AFAP.

Las pruebas sobre distintos períodos demostraron que esta estrategia podía provocar asignaciones incorrectas o pérdida de valores.

Para resolverlo se implementó una detección dinámica de los encabezados:

```text

SURA

INTEGRACIÓN

REPÚBLICA

ITAÚ

TOTAL DEL SISTEMA

```

El pipeline identifica sus posiciones en cada página y calcula automáticamente los límites correspondientes a cada columna.

Esto permite adaptar la extracción a diferentes geometrías de los documentos sin depender de coordenadas absolutas fijas.

---



## Ejecución del pipeline



### Procesar un mes

Ejemplo para julio de 2026:

```powershell

python src\[pipeline.py](http://pipeline.py) --year 2026 --month 7

```

El proceso:

1. localiza el reporte del período;
2. descarga el PDF si todavía no existe;
3. identifica los tres subfondos;
4. extrae y transforma los datos;
5. normaliza las dimensiones;
6. ejecuta controles de calidad;
7. guarda el dataset procesado.

El archivo generado se almacena como:

```text

data/processed/portfolio_composition_2026_07.csv

```

---



### Procesar un rango histórico

Ejemplo:

```powershell

python src\pipeline_[range.py](http://range.py) --start 2026-01 --end 2026-08

```

El script procesa automáticamente todos los períodos comprendidos en el rango y genera un histórico consolidado:

```text

data/processed/portfolio_composition_history.csv

```

---



## Modelo de datos actual

El dataset de composición del portafolio contiene las siguientes variables:

| Campo | Descripción |

|---|---|

| `fecha` | Fecha correspondiente al reporte del BCU |

| `subfondo` | Crecimiento, Acumulación o Retiro |

| `afap` | Identificador de la AFAP extraído del documento |

| `tipo_fila` | Clasificación del registro |

| `instrumento_raw` | Descripción original extraída del PDF |

| `valor_pct` | Participación porcentual almacenada como decimal |

| `literal` | Literal regulatorio |

| `instrumento` | Instrumento financiero |

| `moneda_raw` | Código de moneda extraído del documento |

| `afap_normalizada` | Nombre normalizado de la AFAP |

| `moneda` | Moneda normalizada |

| `archivo_origen` | Documento PDF del cual se obtuvo el registro |

Los porcentajes se almacenan en formato decimal.

Por ejemplo:

```text

0.36 % → 0.0036

```

---



## Data Quality

La calidad de los datos forma parte del pipeline y no se limita a una revisión posterior.

Actualmente se implementan controles sobre:

- presencia de los tres subfondos esperados;
- presencia de todas las AFAP y del Total del Sistema;
- porcentajes dentro del rango esperado;
- registros de detalle sin instrumento;
- totales de portafolio;
- filas completamente duplicadas;
- valores faltantes;
- consistencia estructural del histórico.

Los controles de calidad del histórico se encuentran implementados en:

```text

src/validate_[data.py](http://data.py)

```

---



## Tratamiento de valores faltantes

El proyecto aplica un **principio de no invención de datos**.

Los valores ausentes en los documentos originales no se imputan ni se reemplazan automáticamente por cero.

Cuando una determinada AFAP no presenta valor para una combinación de instrumento y moneda, el dataset conserva:

```text

NaN

```

Esto permite distinguir entre:

```text

0     → valor explícitamente informado como cero

NaN   → ausencia de valor en la fuente

```

Durante la validación del histórico enero–agosto de 2026 se identificaron **95 valores** `NaN` **en** `valor_pct`.

Se realizaron verificaciones manuales sobre una muestra de diferentes períodos contra los PDFs originales y se confirmó que los casos revisados correspondían a celdas efectivamente vacías en la fuente.

---



## Validación histórica

La primera serie histórica validada comprende:

```text

Enero 2026 → Agosto 2026

```

Se verificaron:

- 8 períodos mensuales;
- 3 subfondos;
- 4 AFAP;
- Total del Sistema;
- ausencia de filas completamente duplicadas;
- consistencia de los totales de portafolio;
- tratamiento de valores faltantes;
- trazabilidad mediante archivo de origen.

La validación permitió además detectar y corregir el problema de geometrías variables entre los PDFs del BCU mediante la implementación de detección dinámica de columnas.

---



## Tecnologías utilizadas



### Data Engineering

- Python
- pandas
- pdfplumber
- requests
- truststore



### Analytics

- SQL
- DuckDB *(previsto para la siguiente etapa)*
- Power BI



### Desarrollo

- Cursor
- Git
- GitHub
- Python virtual environments `.venv`)



### Entorno

- Windows 11
- Python 3.13

---



## Próximas etapas

El proyecto continuará evolucionando desde el pipeline actual de composición del portafolio hacia una solución integral de **Investment Analytics**.

Las próximas etapas incluyen:

1. incorporar series oficiales de rentabilidad de los subfondos;
2. analizar rentabilidad bruta y neta;
3. incorporar comisiones y otras variables relevantes;
4. ampliar progresivamente la serie histórica;
5. implementar una capa analítica utilizando SQL/DuckDB;
6. desarrollar análisis exploratorio;
7. diseñar KPIs financieros y de composición;
8. construir el modelo de datos para Power BI;
9. desarrollar el dashboard interactivo;
10. documentar metodología, supuestos y controles de calidad.

---



## Estado actual

**En desarrollo**

| Componente | Estado |

|---|---|

| Descarga automática de reportes | ✅ Implementado |

| Extracción de PDFs | ✅ Implementado |

| Procesamiento de subfondos | ✅ Implementado |

| Detección dinámica de columnas | ✅ Implementado |

| Transformación a Tidy Data | ✅ Implementado |

| Normalización de dimensiones | ✅ Implementado |

| Controles de Data Quality | ✅ Implementado |

| Histórico enero–agosto 2026 | ✅ Procesado |

| Validación contra PDFs originales | ✅ Realizada sobre muestras |

| Rentabilidad | ⏳ Próxima etapa |

| SQL / DuckDB | ⏳ Pendiente |

| Power BI | ⏳ Pendiente |

---



## Visión del proyecto

El objetivo final es construir una solución reproducible que permita transformar información financiera pública no estructurada en un modelo analítico capaz de responder preguntas sobre:

- composición de los portafolios;
- exposición por instrumento y moneda;
- diferencias entre AFAP;
- evolución temporal;
- concentración de inversiones;
- rentabilidad de los subfondos;
- relación entre composición, riesgo y rendimiento.

El proyecto combina **conocimiento financiero, ingeniería de datos y Business Intelligence**, utilizando exclusivamente información pública oficial y manteniendo trazabilidad desde el documento fuente hasta el indicador analítico.