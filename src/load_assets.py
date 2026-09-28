"""Carga saldos monetarios conservando unidad y trazabilidad del PDF."""
from decimal import Decimal, InvalidOperation
import re
import unicodedata

import pandas as pd

SUBFUNDS = {"CRECIMIENTO", "ACUMULACION", "RETIRO"}


def concept(label, fondo):
    clean = unicodedata.normalize("NFKD", str(label))
    clean = "".join(c for c in clean if not unicodedata.combining(c))
    clean = re.sub(r"\s+", " ", clean).strip().upper()
    expected = {
        f"TOTAL ACTIVOS DEL SUBFONDO DE {fondo}($)": "TOTAL_ACTIVOS",
        f"TOTAL SUBFONDO DE {fondo} ($)": "TOTAL_SUBFONDO",
        "TOTAL RESERVA ESPECIAL ($)": "RESERVA_ESPECIAL",
    }
    if fondo == "FVP":
        expected = {f"TOTAL ACTIVOS DEL FONDO {name} PREVISIONAL{suffix} ($)": "TOTAL_ACTIVOS"
                    for name in ("VOLUNTARIO", "VOLUNARIO") for suffix in ("", " (FVP)")}
    if clean not in expected:
        raise ValueError(f"Concepto monetario no reconocido: {fondo}: {label!r}")
    return expected[clean]


def exact_amount(value, raw):
    try:
        result = Decimal(str(value))
        # La fuente actual publica pesos enteros, con coma o punto de miles.
        text = str(raw).strip()
        if not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+|\d{1,3}(?:\.\d{3})+)", text):
            raise ValueError(f"Importe original no reconocido: {raw!r}")
        original = Decimal(text.replace(",", "").replace(".", ""))
        if not result.is_finite() or result < 0 or result != original:
            raise ValueError(f"Importe no coincide con valor_raw: {value!r}, {raw!r}")
        return result
    except InvalidOperation as exc:
        raise ValueError(f"Importe inválido: {value!r}") from exc


def prepare_assets(connection, report):
    assets = report.loc[report.tipo_valor.eq("IMPORTE")].copy()
    if assets.empty or not assets.seccion.eq("COMPOSICION").all() or not assets.tipo_fila.eq("TOTAL_MONETARIO").all():
        raise ValueError("Faltan importes o aparecen fuera de composición / total monetario.")
    required = ["fecha", "fondo", "afap_normalizada", "unidad", "valor_importe",
                "valor_raw", "instrumento_raw", "pagina", "fila_pdf", "fila_id", "archivo_origen"]
    if assets[required].isna().any().any() or not assets.unidad.eq("$").all():
        raise ValueError("Importes con nulos o unidades no reconocidas.")
    if not set(assets.fondo) <= SUBFUNDS | {"FVP"}:
        raise ValueError("Fondo monetario desconocido.")
    if not assets.loc[assets.fondo.ne("FVP"), "subfondo"].equals(assets.loc[assets.fondo.ne("FVP"), "fondo"]):
        raise ValueError("Fondo y subfondo inconsistentes.")
    if assets.loc[assets.fondo.eq("FVP"), "subfondo"].notna().any():
        raise ValueError("FVP no debe asociarse a un subfondo.")
    assets["concepto"] = [concept(label, fund) for label, fund in zip(assets.instrumento_raw, assets.fondo)]
    assets["valor_importe"] = [exact_amount(v, r) for v, r in zip(assets.valor_importe, assets.valor_raw)]
    assets["fecha"] = pd.to_datetime(assets.fecha, errors="raise")
    assets["periodo"] = assets.fecha.dt.strftime("%Y-%m")
    keys = ["periodo", "fondo", "afap_normalizada", "concepto"]
    if assets.duplicated(keys).any():
        raise ValueError("Importes duplicados en período, fondo, entidad y concepto.")
    for period, group in assets.groupby("periodo"):
        if len(group) != 50 or group.fecha.nunique() != 1:
            raise ValueError(f"Cobertura monetaria incompleta o fechas diferentes: {period}.")
        entities = set(group.afap_normalizada)
        expected = {(f, a, c) for f in SUBFUNDS | {"FVP"} for a in entities
                    for c in (["TOTAL_ACTIVOS"] if f == "FVP" else ["TOTAL_ACTIVOS", "RESERVA_ESPECIAL", "TOTAL_SUBFONDO"])}
        actual = set(group[["fondo", "afap_normalizada", "concepto"]].itertuples(index=False, name=None))
        if len(entities) != 5 or "TOTAL SISTEMA" not in entities or actual != expected:
            raise ValueError(f"Combinaciones monetarias incompletas: {period}.")
    for table, left, right, key in [
        ("dim_period", "periodo", "periodo", "period_id"),
        ("dim_afap", "afap_normalizada", "afap_nombre", "afap_id"),
        ("dim_subfund", "subfondo", "subfund_nombre", "subfund_id"),
    ]:
        dim = connection.execute(f"SELECT {key}, {right} FROM {table}").df()
        assets = assets.merge(dim, left_on=left, right_on=right, how="left", validate="many_to_one")
        missing = assets[key].isna()
        if key == "subfund_id":
            missing &= assets.fondo.ne("FVP")
        if missing.any():
            raise ValueError(f"Falta correspondencia en {table}.")
        assets[key] = assets[key].astype("Int64")
    assets = assets.rename(columns={"instrumento_raw": "concepto_raw"})
    return assets[["period_id", "afap_id", "subfund_id", "fondo", "concepto", "fecha", "unidad",
                   "valor_importe", "concepto_raw", "valor_raw", "pagina", "fila_pdf", "fila_id", "archivo_origen"]]


def validate_assets(connection):
    # Comprobaciones sobre DECIMAL, sin redondear antes de comparar.
    recon = connection.execute("""
        SELECT period_id, fondo, afap_id,
          sum(CASE WHEN concepto='TOTAL_ACTIVOS' THEN valor_importe ELSE -valor_importe END) AS diferencia
        FROM fact_portfolio_assets WHERE fondo <> 'FVP'
        GROUP BY ALL
    """).df()
    system = connection.execute("""
        SELECT period_id, fondo, concepto,
          sum(CASE WHEN a.tipo_entidad='TOTAL_SISTEMA' THEN valor_importe ELSE -valor_importe END) AS diferencia
        FROM fact_portfolio_assets f JOIN dim_afap a USING(afap_id)
        GROUP BY ALL
    """).df()
    for title, frame in [("Activos - reserva - subfondo", recon), ("Sistema - AFAP", system)]:
        invalid = frame.loc[frame.diferencia.abs() > 1]
        if not invalid.empty:
            raise ValueError(f"{title}: diferencias mayores a $1:\n{invalid.to_string(index=False)}")
        print(f"OK - {title}: {len(frame)} conciliaciones, diferencia máxima ${frame.diferencia.abs().max():.0f}.")


def load_fact_portfolio_assets(connection, report):
    assets = prepare_assets(connection, report)
    connection.register("assets_df", assets)
    try:
        connection.execute("DELETE FROM fact_portfolio_assets")
        connection.execute("INSERT INTO fact_portfolio_assets SELECT * FROM assets_df")
    finally:
        connection.unregister("assets_df")
    validate_assets(connection)
    return len(assets)
