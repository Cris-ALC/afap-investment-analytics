# Activos en millones de USD equivalentes

## Criterio adoptado

Convertir los saldos monetarios en pesos uruguayos enteros a USD equivalentes con la serie oficial BCU **DLS. USA CABLE (2224)** de la fecha del reporte. Si no hay cotización ese día, usar la última anterior, con límite de siete días corridos para detectar faltantes anormales. Guardar ambas fechas. No usar una cotización posterior, una tasa fija para todo el histórico ni un promedio mensual para estos saldos.

El campo utilizado es TCV. El proceso exige TCC = TCV en esta serie de referencia; si difieren, se detiene para revisar la metodología. No se aplica un margen comercial ni se estima un valor de liquidación. La conversión expresa todos los activos en USD, no la proporción de inversiones denominadas en USD.

La comprobación de moneda y escala se apoyó en los totales del PDF de diciembre de 2025 y el Reporte del Sistema Financiero BCU, diciembre 2025, página 31. Los tres saldos netos suman 1.049.405.220.042 pesos y los activos incluyendo reserva, 1.052.810.589.243 pesos. Redondeados a millones coinciden con 1.049.405 y 1.052.811 del reporte oficial. Esto respalda usar unidades de UYU en el histórico actual. Revisar la unidad si cambia el formato de la fuente.

Fuentes:
- https://www.bcu.gub.uy/Servicios-Financieros-SSF/Reportes%20del%20Sistema%20Financiero/RSF_IV_25.pdf
- https://www.bcu.gub.uy/Estadisticas-e-Indicadores/Paginas/Cotizaciones.aspx
- Contrato del servicio: https://cotizaciones.bcu.gub.uy/wscotizaciones/servlet/awsbcucotizaciones?wsdl
- Catálogo de series: https://cotizaciones.bcu.gub.uy/wscotizaciones/servlet/awsbcumonedas?wsdl

## Archivos

Extraer el paquete en la raíz del proyecto, combinando sus carpetas:

- `src/exchange_rates.py`: descarga y valida las cotizaciones para las fechas del CSV histórico.
- `data/raw/bcu_fx/`: respuestas XML oficiales, para reproducir el cálculo.
- `powerbi/data_actualizada/fx_usd_monthly.csv`: una cotización por mes, lista para importar.
- Este documento: metodología y medidas.

Para regenerar desde los XML guardados, sin descargar nuevamente:

```powershell
python src\exchange_rates.py --offline
```

Para actualizar con el servicio del BCU cuando se agreguen períodos:

```powershell
python src\exchange_rates.py
```

Requiere `requests`, ya utilizado por el proyecto. En Windows usa `truststore` si está instalado. No cambia DuckDB ni las exportaciones existentes. Si falla una fecha, conserva el CSV anterior y no publica uno incompleto; actualizar Power BI solo después de una ejecución exitosa.

## Importar en Power BI

1. Obtener datos → Texto/CSV → `powerbi/data_actualizada/fx_usd_monthly.csv` → Transformar datos.
2. Nombrar la consulta **fx_usd_monthly**. Eliminar el paso automático Tipo cambiado antes de asignar tipos.
3. `period_id`, `dias_desfase` y `codigo_bcu`: número entero. `fecha_reporte` y `fecha_cotizacion`: fecha. `tc_uyu_por_usd`: número decimal usando configuración regional Inglés (Estados Unidos). Resto: texto. No truncar la cotización a dos decimales.
4. Cerrar y aplicar. Esta tabla se utilizará como tabla de consulta **sin relaciones**, buscando por period_id en la medida. Si Power BI crea una relación automática para ella, eliminar solo esa relación. Las relaciones de activos con las dimensiones permanecen.

## Medidas

Crear cada medida por separado. Se utiliza la medida `Total activos subfondos` ya indicada, que requiere un solo mes, suma AFAP individuales, selecciona TOTAL_ACTIVOS y excluye FVP.

```dax
Tipo de cambio USD =
VAR PeriodoSeleccionado = SELECTEDVALUE(dim_period[period_id])
RETURN
    IF(
        NOT ISBLANK(PeriodoSeleccionado),
        LOOKUPVALUE(
            fx_usd_monthly[tc_uyu_por_usd],
            fx_usd_monthly[period_id], PeriodoSeleccionado
        )
    )
```

```dax
Total activos subfondos USD millones =
VAR TC = [Tipo de cambio USD]
RETURN
    IF(
        HASONEVALUE(dim_period[period_id]) && TC > 0,
        DIVIDE([Total activos subfondos], TC * 1000000),
        BLANK()
    )
```

```dax
Estado conversion USD =
SWITCH(
    TRUE(),
    NOT HASONEVALUE(dim_period[period_id]), "Seleccioná un único mes",
    ISBLANK([Tipo de cambio USD]), "Falta cotización BCU para el período",
    [Tipo de cambio USD] <= 0, "Cotización inválida",
    ISBLANK([Total activos subfondos]), "Sin activos para la selección",
    "Conversión disponible"
)
```

Usar campos de `dim_period`, `dim_afap` y `dim_subfund` en los segmentadores. No usar columnas de otras facts para filtrar activos.

Tarjeta: medida `Total activos subfondos USD millones`, dos decimales, unidades de visualización **Ninguna**, título **Total de activos — millones de USD equivalentes**. La medida ya divide por un millón: no volver a elegir Millones en el visual. Nota: “Conversión al tipo de cambio BCU DLS. USA CABLE de la fecha del reporte”. Mostrar `Estado conversion USD` como indicador auxiliar.

Una tarjeta con varios meses queda vacía. En un gráfico mensual, cada punto usa su propia cotización si el eje proviene de `dim_period`. Las variaciones en USD reflejan movimientos de activos y del tipo de cambio; no equivalen a rentabilidad. TOTAL SISTEMA queda excluido por la medida base para evitar duplicación.

El CSV y los cálculos se validan en Python. La evaluación de las medidas DAX y el formato visual deben confirmarse en el PBIX de la usuaria.

## Resultado de la preparación del 28/09/2026

- 32 cotizaciones mensuales desde enero de 2024 hasta agosto de 2026, descargadas del servicio oficial BCU y conservadas en XML.
- 30 coinciden con la fecha del reporte. Para 31/12/2024 y 31/12/2025 se aplicó 30/12/2024 (44,066 UYU/USD) y 30/12/2025 (39,041 UYU/USD), respectivamente.
- Las 1.600 filas monetarias tienen una cotización aplicable; el enlace por mes no pierde ni duplica registros.
- Se probó selección de la fecha exacta, último día anterior, rechazo de cotización futura o demasiado antigua, serie incorrecta, error del servicio y diferencia TCC/TCV.
- Se comprobó la conversión y reconversión con precisión decimal, sin modificar los valores fuente. La variación de tipos de cambio no se redondea antes del cálculo.
