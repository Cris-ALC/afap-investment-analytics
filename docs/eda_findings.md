# AFAP Investment Analytics

## Hallazgos del análisis exploratorio

### 1. Alcance

Se analiza la composición del portafolio del total del sistema AFAP entre enero y agosto de 2026, utilizando los datos procesados de los informes mensuales del BCU.

Las variaciones de participación se expresan en puntos porcentuales (pp).

### 2. Comparación entre enero y agosto

**Subfondo Acumulación**

- Literal A: 49,39 % → 49,71 % (+0,32 pp).
- Literal C: 5,82 % → 5,42 % (−0,40 pp).
- La composición presenta variaciones moderadas.

**Subfondo Crecimiento**

- Literal A: 58,89 % → 59,28 % (+0,39 pp).
- Literal C: 5,36 % → 5,99 % (+0,63 pp).
- Literal F: 2,06 % → 1,60 % (−0,46 pp).

**Subfondo Retiro**

- Literal A: 68,60 % → 66,30 % (−2,30 pp).
- Literal C: 13,68 % → 16,26 % (+2,58 pp).
- Se observan movimientos más amplios entre los literales A y C.



### 3. Evolución mensual del Literal C en Retiro

| Mes | Participación | Variación mensual |

|---|---:|---:|

| Enero | 13,68 % | — |

| Febrero | 13,74 % | +0,06 pp |

| Marzo | 14,34 % | +0,60 pp |

| Abril | 15,60 % | +1,26 pp |

| Mayo | 15,20 % | −0,40 pp |

| Junio | 16,03 % | +0,83 pp |

| Julio | 16,48 % | +0,45 pp |

| Agosto | 16,26 % | −0,22 pp |

El incremento no fue uniforme. Abril y junio registraron los mayores aumentos mensuales.

### 4. Limitaciones de interpretación

Los cambios en la participación de los literales no permiten identificar por sí solos si se deben a operaciones de compraventa, variaciones de precios o una combinación de ambos.

El análisis corresponde al total del sistema.

Las diferencias entre AFAP se estudiarán por separado.

### 5. Fuentes y reproducibilidad

- Fuente primaria: informes mensuales del BCU.
- Período: enero-agosto de 2026.
- Vista: `vw_portfolio_literal`.
- Consultas: `sql/eda_portfolio.sql`.



### 6. Comparación entre AFAP: Literal C del subfondo Retiro

Entre enero y agosto de 2026, la participación del Literal C en el subfondo Retiro presentó comportamientos diferentes entre administradoras.

| AFAP | Enero | Agosto | Variación |

|---|---:|---:|---:|

| ITAÚ | 15,51 % | 20,21 % | +4,70 pp |

| SURA | 14,87 % | 14,05 % | −0,82 pp |

| Integración | 18,61 % | 24,41 % | +5,80 pp |

| República | 12,22 % | 14,90 % | +2,68 pp |

| Total sistema | 13,68 % | 16,26 % | +2,58 pp |

Tres administradoras incrementaron su participación en el Literal C, mientras que SURA registró una reducción. El agregado del sistema aumentó 2,58 pp.

Las diferencias observadas describen cambios en la composición de las carteras, pero no permiten identificar por sí solas operaciones de compraventa ni evaluar el desempeño de las inversiones.

**Fuente:** `vw_portfolio_literal`, informes mensuales del BCU, enero y agosto de 2026.



### 8. Metodología de rentabilidad neta

La rentabilidad neta de cada subfondo corresponde a una tasa de rentabilidad real anual, calculada deduciendo de la rentabilidad bruta real anual una comisión equivalente sobre saldos.

La metodología fue modificada a partir de diciembre de 2023, conforme a la reforma previsional.

La rentabilidad neta agregada del FAP se calcula ponderando las tasas de sus subfondos según su participación en el fondo.

Para el análisis temporal se dispone de seis observaciones: enero y agosto de 2024, 2025 y 2026.

Las diferencias entre observaciones se expresarán en puntos porcentuales y no se interpretarán como rentabilidades obtenidas entre esas fechas.

Fuentes:

- BCU: Metodología de cálculo de rentabilidad bruta  y neta.

- BCU: Reporte del Sistema Financiero, IV trimestre   de 2023, apartado de metodología de rentabilidad neta de las AFAP.