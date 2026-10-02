# AFAP Investment Analytics | Uruguay

Proyecto personal de **análisis financiero e ingeniería de datos** que transforma reportes públicos del Banco Central del Uruguay (BCU), publicados en PDF, en un histórico estructurado y un dashboard interactivo de Power BI.

Permite analizar el posicionamiento de las AFAP, la composición de sus portafolios y la evolución de activos y rentabilidades, integrando Python, SQL, DuckDB y controles de calidad de datos.

**Python · SQL · DuckDB · Power BI · DAX**

**Cobertura:** enero de 2024 a agosto de 2026, con 32 períodos mensuales. La disponibilidad por entidad depende de los registros publicados en cada período.

## Ver el dashboard

- [Consultar el informe en PDF](docs/AFAP_Investment_Analytics.pdf)
- [Descargar el archivo Power BI](powerbi/AFAP_Monitor_vs_inic.pbix)
- [Consultar la metodología de activos en USD](docs/ACTIVOS_USD.md)
- [Consultar la integración con DuckDB](docs/INTEGRACION_DUCKDB.md)

El PDF permite consultar una selección estática de filtros. El archivo `.pbix` permite explorar el informe en Power BI Desktop. Para actualizar sus datos en otra computadora se deben revisar las rutas de origen de las consultas.

**Estado al 2 de octubre de 2026:** dashboard desarrollado y publicado en Power BI Service mediante una cuenta universitaria. El acceso público interactivo está pendiente de habilitación; no se ofrece todavía un enlace de acceso anónimo.

## Preguntas que responde

- ¿Qué posición ocupa una AFAP frente a sus competidoras para un mismo subfondo y mes?
- ¿Qué distancia tiene respecto del líder y del promedio simple de las AFAP?
- ¿Cómo se distribuye la cartera por literal e instrumento?
- ¿Cómo evolucionan los activos expresados en USD equivalentes?
- ¿Qué categorías ganan o pierden participación entre el inicio y el cierre del rango?
- ¿Cómo evolucionan las tasas netas publicadas y la rentabilidad bruta real mensual?

El análisis es descriptivo: la composición aporta contexto, pero no constituye una atribución causal de rentabilidad ni una evaluación integral del riesgo.

## Páginas del informe


| Página                | Indicadores y visualizaciones                                                                                                                                                                                      |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Resumen ejecutivo** | Rentabilidad neta al cierre, ranking, brechas frente al líder y al promedio, activos en USD, comparación entre AFAP, evolución frente al promedio y lectura ejecutiva dinámica.                                    |
| **Composición**       | Activos al cierre, variación de activos en el rango, literal de mayor peso, participación de los tres principales literales, principales instrumentos, evolución de activos y cambio de participación por literal. |
| **Rentabilidad**      | Rentabilidad neta al cierre, cambio de tasa en pb, brecha frente al promedio, TRM al cierre, evoluciones neta y bruta y comparaciones de subfondos, FAP y Régimen Especial.                                        |
| **Guía de lectura**   | Uso de filtros, interpretación de KPI, unidades, fuentes, criterios de cálculo y limitaciones.                                                                                                                     |


Los filtros principales son **Período, AFAP y Subfondo**. Los comparativos mantienen visibles las distintas AFAP; el gráfico de FAP y Régimen Especial no se filtra por subfondo.

## Fuentes y cobertura

La fuente es la información pública oficial del **Banco Central del Uruguay**, incluida la publicada por su Superintendencia de Servicios Financieros.


| Fuente                                             | Uso                                                              |
| -------------------------------------------------- | ---------------------------------------------------------------- |
| Composición del Portafolio - Principales Variables | Participaciones por literal e instrumento e importes de activos. |
| Reportes de rentabilidad neta                      | Tasas por subfondo, FAP agregado y Régimen Especial.             |
| Reportes de rentabilidad bruta                     | Series de tasas publicadas; el dashboard utiliza la TRM.         |
| Cotizaciones del BCU                               | Conversión de activos en pesos a USD equivalentes.               |


Se procesan los subfondos **Crecimiento, Acumulación y Retiro**, así como registros agregados cuando corresponden a la fuente. Las denominaciones incluyen República, SURA, Integración, Itaú y la denominación histórica Unión Capital. **Unión Capital e Itaú se conservan separadas en el modelo**; no se unen automáticamente sus series.

El Total del Sistema se utiliza cuando corresponde para controles y conciliaciones. No se suma a las AFAP individuales para evitar doble conteo.

## Arquitectura

El flujo integra descarga de reportes, extracción y normalización en Python, controles de calidad, consolidación histórica, carga en DuckDB, vistas SQL, exportación de tablas y visualización en Power BI.


| Carpeta o archivo           | Contenido                                                       |
| --------------------------- | --------------------------------------------------------------- |
| `data/raw/`                 | PDFs originales descargados del BCU.                            |
| `data/processed/`           | Datasets mensuales e históricos generados.                      |
| `docs/`                     | Documentación metodológica, controles e informe PDF.            |
| `notebooks/`                | Espacio para análisis exploratorio.                             |
| `powerbi/`                  | Informe `.pbix`, tema visual e iconos.                          |
| `powerbi/data_actualizada/` | Exportaciones generadas para el modelo de Power BI.             |
| `sql/`                      | Tablas, vistas analíticas, carga de dimensiones y controles.    |
| `src/`                      | Descarga, extracción, transformación, carga y validación.       |
| `src/diagnostics/`          | Controles y diagnósticos iniciales conservados como referencia. |
| `requirements.txt`          | Dependencias Python.                                            |


Los PDFs descargados, datasets generados, bases DuckDB, entorno virtual y respaldos locales están excluidos mediante `.gitignore`. El PDF de presentación en `docs/` y el archivo Power BI son entregables del proyecto.

## Extracción de PDFs y desafíos técnicos

Los reportes financieros están diseñados para lectura humana y no como tablas listas para analizar. El extractor de composición utiliza `pdfplumber` para recuperar texto y coordenadas, identificar subfondos, reconstruir filas y asignar valores a cada administradora.

Durante la validación histórica se detectó que los documentos no mantienen una geometría horizontal uniforme. Se reemplazó la asignación basada en posiciones fijas por **detección dinámica de encabezados y límites de columnas**, para reducir asignaciones incorrectas y pérdida de valores.

El procesamiento reconstruye las dimensiones de literal, instrumento y moneda, normaliza las denominaciones y conserva `archivo_origen` para facilitar el rastreo hasta el PDF. Los procesos de rentabilidad se organizan en scripts específicos para sus respectivas fuentes.

## Modelo de datos

La capa analítica utiliza dimensiones de período, AFAP, subfondo, literal, instrumento y moneda, junto con tablas de composición, activos y rentabilidades.


| Conjunto analítico          | Granularidad conceptual                                                  |
| --------------------------- | ------------------------------------------------------------------------ |
| Composición por literal     | Período, AFAP, subfondo y literal.                                       |
| Composición por instrumento | Período, AFAP, subfondo y categorías de detalle de instrumento y moneda. |
| Activos                     | Período, entidad, subfondo y concepto monetario.                         |
| Rentabilidad neta           | Período, AFAP, tipo de métrica y subfondo cuando corresponde.            |
| Rentabilidad bruta          | Período, entidad, fondo o subfondo y tipo de tasa.                       |


El dataset de composición conserva, entre otros, `fecha`, `subfondo`, `afap`, `tipo_fila`, `instrumento_raw`, `valor_pct`, `literal`, `instrumento`, `moneda_raw`, `afap_normalizada`, `moneda` y `archivo_origen`.

Las participaciones de composición se almacenan como fracciones: **0,36 % se almacena como 0,0036**. En rentabilidades se distingue entre columnas en fracción y en unidades porcentuales; las medidas DAX aplican la conversión correspondiente para evitar multiplicar o dividir por 100 dos veces.

## Criterios de cálculo e interpretación

- **Al cierre:** último mes seleccionado, manteniendo el contexto de entidad y subfondo. No se sustituye automáticamente por otro mes si faltan datos.
- **Evoluciones:** muestran los valores de cada mes incluido en el rango. Las tasas publicadas no se suman entre meses.
- **Ranking:** orden descendente de la tasa neta entre las AFAP con datos para el mismo subfondo y mes. Los empates comparten posición.
- **Promedio simple AFAP:** otorga igual peso a cada AFAP con datos, incluida la seleccionada. No representa un promedio ponderado por activos ni necesariamente una tasa oficial del sistema.
- **Brechas de rentabilidad:** diferencia entre tasas expresada en puntos básicos. **100 pb = 1 punto porcentual**.
- **Cambio de tasa en el rango:** diferencia entre la tasa publicada al cierre y al inicio. No es rentabilidad acumulada de la inversión durante el rango.
- **Cambio de participación:** diferencia entre participaciones finales e iniciales, expresada en puntos porcentuales. Pasar del 20 % al 25 % implica +5 pp.
- **Activos en USD:** conversión desde pesos con cotización BCU del cierre del reporte o una anterior admitida por el procedimiento documentado. Los importes se presentan en millones de USD equivalentes.
- **Variación de activos:** cambio del saldo entre extremos. Puede reflejar flujos, resultados de inversión y variación cambiaria; no equivale a rentabilidad.
- **TRM:** tasa de rentabilidad real mensual en UR publicada en los reportes de rentabilidad bruta. La tarjeta toma el mes de cierre y la evolución muestra cada mes.
- **Neta y bruta:** sus bases y horizontes pueden diferir. Su diferencia no se interpreta directamente como comisiones.
- **Concentración por literal:** el peso de los tres principales literales describe la distribución por categorías; no mide por sí solo concentración por emisor ni cumplimiento de límites.



## Calidad y validación

Los controles forman parte del proceso e incluyen estructura, entidades y subfondos esperados según el período, duplicados, valores faltantes, rangos de participaciones, totales y trazabilidad.

También se incorporaron conciliaciones de importes: activos menos reserva frente al total del subfondo, y Total del Sistema frente a la suma de AFAP. La documentación de controles se encuentra en `docs/` y las consultas de validación en `sql/`.

### Valores faltantes

Los valores ausentes en la fuente no se imputan ni se convierten automáticamente en cero. Se preservan como `NaN` o `NULL` según la capa. En Power BI, un indicador puede quedar vacío si falta un extremo del rango o si la selección no permite calcularlo.

### Validación inicial e histórico ampliado

La primera validación abarcó enero-agosto de 2026: ocho meses, tres subfondos, cuatro AFAP y Total del Sistema. En ese conjunto se identificaron **95 valores faltantes en** `valor_pct`. La revisión manual de una muestra confirmó celdas vacías en los PDFs originales.

Ese resultado corresponde a la etapa inicial y no debe interpretarse como el conteo de faltantes del histórico ampliado a 32 meses. Las verificaciones manuales se efectuaron sobre muestras, no sobre cada celda del universo.

## Ejecución

Entorno de desarrollo utilizado: **Windows 11 y Python 3.13**, con entorno virtual. Desde la raíz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```



### Composición de un mes

```powershell
python src\pipeline.py --year 2026 --month 7
```

El proceso descarga el reporte si corresponde, extrae los subfondos, transforma y normaliza la información, ejecuta controles y genera el archivo mensual:

```text
data/processed/portfolio_composition_2026_07.csv
```



### Composición de un rango

```powershell
python src\pipeline_range.py --start 2024-01 --end 2026-08
```

El histórico se consolida en:

```text
data/processed/portfolio_composition_history.csv
```

Estos comandos corresponden a composición; no ejecutan por sí solos todas las cargas del proyecto. Rentabilidad neta y bruta cuentan con sus propios procesos en `src/`. La carga de activos, dimensiones, hechos y exportaciones debe seguir la documentación de integración:

- [Integración con DuckDB](docs/INTEGRACION_DUCKDB.md)
- [Activos y conversión a USD](docs/ACTIVOS_USD.md)
- [Diagnósticos iniciales](src/diagnostics/README.md)

Las fuentes descargadas y los archivos generados deben reconstruirse antes de actualizar Power BI en un entorno nuevo. Algunas consultas pueden requerir adaptar rutas locales.

## Tecnologías


| Área                              | Herramientas                                      |
| --------------------------------- | ------------------------------------------------- |
| Extracción y transformación       | Python, pandas, pdfplumber, requests, truststore. |
| Almacenamiento y análisis         | DuckDB y SQL.                                     |
| Visualización y métricas          | Power BI, Power Query y DAX.                      |
| Desarrollo y control de versiones | Cursor, Git y entornos virtuales.                 |




## Estado y próximos pasos


| Componente                                          | Estado                              |
| --------------------------------------------------- | ----------------------------------- |
| Extracción, normalización y consolidación histórica | Implementado.                       |
| Cobertura enero de 2024-agosto de 2026              | Incorporada.                        |
| Rentabilidad neta y bruta                           | Incorporadas.                       |
| DuckDB, vistas SQL y exportaciones                  | Implementados.                      |
| Activos en USD equivalentes                         | Implementados.                      |
| Dashboard de cuatro páginas                         | Desarrollado.                       |
| Publicación en Power BI Service                     | Realizada con cuenta universitaria. |
| Acceso público interactivo                          | Pendiente de habilitación.          |


Antes de distribuir una nueva versión se revisan unidades, filtros, etiquetas y consistencia entre el `.pbix` y el PDF exportado.

Las siguientes ampliaciones contemplan facilitar el acceso público, actualizar la cobertura mensual y profundizar los análisis financieros. Comisiones, atribución de rentabilidad y evaluación de límites regulatorios requieren fuentes y metodología adicionales; no forman parte del alcance actual.

## Autoría y alcance

Desarrollado por iniciativa personal como proyecto de portfolio, utilizando exclusivamente información pública. No corresponde a un encargo laboral ni a una publicación oficial del BCU o de una AFAP.

