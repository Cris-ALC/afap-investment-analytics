"""Cotización BCU DLS. USA CABLE a la fecha de cada reporte AFAP."""
import argparse
import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import os
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
URL = 'https://cotizaciones.bcu.gub.uy/wscotizaciones/servlet/awsbcucotizaciones'
CODE = '2224'
NAME = 'DLS. USA CABLE'
NS = {'c': 'Cotiza'}
MAX_AGE = 7


def report_dates(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    selected = [r for r in rows if r['tipo_valor'] == 'IMPORTE']
    dates = sorted({date.fromisoformat(r['fecha']) for r in selected})
    if not dates or len({d.strftime('%Y-%m') for d in dates}) != len(dates):
        raise ValueError('Se requiere una única fecha de saldo por mes.')
    if any(r['unidad'].strip() != '$' for r in selected):
        raise ValueError('Unidad monetaria inesperada; revisar el origen.')
    return dates


def parse_quotes(content):
    root = ET.fromstring(content)
    error = root.findtext('.//c:codigoerror', namespaces=NS)
    if error != '0':
        message = root.findtext('.//c:mensaje', namespaces=NS)
        raise ValueError(f'Respuesta BCU inválida ({error}): {message}')
    quotes = {}
    for item in root.findall('.//c:datoscotizaciones.dato', NS):
        def val(tag):
            return (item.findtext('c:' + tag, namespaces=NS) or '').strip()
        if val('Moneda') != CODE or ' '.join(val('Nombre').split()) != NAME:
            raise ValueError('La respuesta contiene otra serie cambiaria.')
        day = date.fromisoformat(val('Fecha'))
        buy, sell = Decimal(val('TCC')), Decimal(val('TCV'))
        if not buy.is_finite() or not sell.is_finite() or buy <= 0 or sell <= 0:
            raise ValueError('Cotización no positiva o no finita.')
        # Esta referencia es única; no sustituir por una pizarra comercial.
        if buy != sell:
            raise ValueError('TCC y TCV difieren. Revisar la metodología antes de convertir.')
        if day in quotes:
            raise ValueError('Cotización duplicada para la misma fecha.')
        quotes[day] = sell
    if not quotes:
        raise ValueError('El BCU no devolvió cotizaciones.')
    return quotes


def choose_quote(quotes, report_day):
    candidates = [day for day in quotes if day <= report_day]
    if not candidates:
        raise ValueError(f'No hay cotización anterior o igual a {report_day}.')
    day = max(candidates)
    lag = (report_day - day).days
    if lag > MAX_AGE:
        raise ValueError(f'Cotización demasiado antigua para {report_day}: {day}.')
    return day, quotes[day], lag


def fetch_quotes(report_day, raw_dir):
    import requests
    start = report_day - timedelta(days=MAX_AGE)
    body = f'''<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" xmlns:c="Cotiza">
      <s:Body><c:wsbcucotizaciones.Execute><c:Entrada>
      <c:Moneda><c:item>{CODE}</c:item></c:Moneda>
      <c:FechaDesde>{start.isoformat()}</c:FechaDesde>
      <c:FechaHasta>{report_day.isoformat()}</c:FechaHasta><c:Grupo>0</c:Grupo>
      </c:Entrada></c:wsbcucotizaciones.Execute></s:Body></s:Envelope>'''
    response = requests.post(URL, data=body.encode('utf-8'), headers={
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'Cotizaaction/AWSBCUCOTIZACIONES.Execute'}, timeout=(15, 45))
    response.raise_for_status()
    quotes = parse_quotes(response.content)
    if any(not start <= day <= report_day for day in quotes):
        raise ValueError('Respuesta BCU fuera del intervalo solicitado.')
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f'bcu_usd_cable_{report_day.isoformat()}.xml'
    path.write_bytes(response.content)
    return quotes, path


def build(portfolio, output, raw_dir, offline=False):
    dates = report_dates(portfolio)
    raw_dir, output = Path(raw_dir), Path(output)
    rows = []
    for report_day in dates:
        path = raw_dir / f'bcu_usd_cable_{report_day.isoformat()}.xml'
        if offline:
            quotes = parse_quotes(path.read_bytes())
        else:
            quotes, path = fetch_quotes(report_day, raw_dir)
        day, rate, lag = choose_quote(quotes, report_day)
        rows.append({
            'period_id': int(report_day.strftime('%Y%m')),
            'periodo': report_day.strftime('%Y-%m'),
            'fecha_reporte': report_day.isoformat(),
            'fecha_cotizacion': day.isoformat(),
            'tc_uyu_por_usd': str(rate),
            'dias_desfase': lag,
            'codigo_bcu': CODE,
            'serie_bcu': NAME,
            'campo_bcu': 'TCV (igual a TCC)',
            'unidad': 'UYU por USD',
            'fuente': URL,
            'archivo_origen': path.name,
        })
        print(f'OK - {report_day}: {rate} UYU/USD; cotización {day}; desfase {lag} días.', flush=True)
    # Publicar solamente después de verificar todo el histórico.
    output.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='',
                                         dir=output.parent, delete=False) as f:
            name = f.name
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        os.replace(name, output)
    finally:
        if name and Path(name).exists():
            Path(name).unlink()
    print(f'Cotizaciones guardadas: {output} | {len(rows)} meses.')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--portfolio', type=Path, default=ROOT / 'data/processed/portfolio_composition_history.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'powerbi/data_actualizada/fx_usd_monthly.csv')
    parser.add_argument('--raw-dir', type=Path, default=ROOT / 'data/raw/bcu_fx')
    parser.add_argument('--offline', action='store_true', help='Reutilizar las respuestas XML oficiales guardadas.')
    args = parser.parse_args()
    if not args.offline:
        try:
            import truststore
            truststore.inject_into_ssl()
        except ImportError:
            pass
    build(args.portfolio, args.output, args.raw_dir, args.offline)
