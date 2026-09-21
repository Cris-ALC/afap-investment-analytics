import duckdb
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "afap_analytics.duckdb"
)


connection = duckdb.connect(
    str(DATABASE_PATH),
    read_only=True,
)

query = """
SELECT
    p.periodo,
    s.subfund_nombre AS subfondo,
    a.afap_nombre,
    COUNT(*) AS filas,
    COUNT(f.valor_pct) AS informados,
    ROUND(
        SUM(f.valor_pct) * 100,
        4
    ) AS total_pct
FROM fact_portfolio_composition f
JOIN dim_period p
    ON f.period_id = p.period_id
JOIN dim_afap a
    ON f.afap_id = a.afap_id
JOIN dim_subfund s
    ON f.subfund_id = s.subfund_id
GROUP BY
    p.periodo,
    s.subfund_nombre,
    a.afap_nombre
HAVING ABS(
    SUM(f.valor_pct) - 1
) > 0.001
ORDER BY
    p.periodo,
    s.subfund_nombre,
    a.afap_nombre
"""

result = connection.execute(
    query
).df()

print(
    "\n=== TOTALES DISTINTOS DE 100 % ===\n"
)

print(
    result.to_string(
        index=False
    )
)

print(
    f"\nCasos encontrados: {len(result)}"
)

connection.close()