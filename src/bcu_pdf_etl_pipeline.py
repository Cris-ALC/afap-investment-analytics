import os
import re
import sys
import requests
import pdfplumber
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from bs4 import BeautifulSoup

# Configuración de logging para seguimiento en terminal
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Configuración de URLs base y directorios de almacenamiento
BASE_URL_BCU = "https://www.bcu.gub.uy"
PORTAL_PREVISIONAL = f"{BASE_URL_BCU}/Servicios-Financieros-SSF/Paginas/Estadisticas-del-Sistema-Previsional.aspx"
RAW_PDF_DIR = "./data/raw/pdfs"
PROCESSED_DIR = "./data/processed"

# Headers para simular peticiones de navegador estándar
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ==========================================
# 1. DESCARGA AUTOMÁTICA SEGÚN PERÍODO
# ==========================================

def generate_month_year_range(start_date: str, end_date: str):
    """
    Genera una lista de tuplas (año_4_dígitos, mes_2_dígitos) entre dos fechas YYYY-MM.
    Ejemplo: ('2026', '08')
    """
    dates = pd.date_range(start=start_date, end=end_date, freq='MS')
    return [(str(d.year), f"{d.month:02d}") for d in dates]

def download_bcu_pdfs_for_period(start_date: str, end_date: str) -> dict:
    """
    Scrapea la web del BCU y descarga los PDFs de Activos, Rentabilidad Bruta/Neta 
    y Principales Variables que coincidan con el período definido.
    """
    target_periods = generate_month_year_range(start_date, end_date)
    os.makedirs(RAW_PDF_DIR, exist_ok=True)
    
    downloaded_files = {
        'composicion_activo': [],
        'rentabilidad_bruta': [],
        'rentabilidad_neta': [],
        'principales_variables': []
    }
    
    logging.info(f"Buscando PDFs en BCU para el período {start_date} a {end_date}...")
    
    try:
        response = requests.get(PORTAL_PREVISIONAL, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Error al conectar con el sitio del BCU: {e}")
        return downloaded_files

    soup = BeautifulSoup(response.text, 'html.parser')
    links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].lower().endswith('.pdf')]
    
    for relative_url in links:
        full_url = relative_url if relative_url.startswith('http') else f"{BASE_URL_BCU}{relative_url}"
        filename = os.path.basename(full_url).lower()
        
        # Verificar si el archivo coincide con los meses/años buscados (patrones dMMYY o YYYYMM)
        for year, month in target_periods:
            short_year = year[-2:]
            period_pattern = f"{month}{short_year}"  # Ejemplo '0826'
            
            if period_pattern in filename:
                category = None
                if 'cocf03' in filename or 'composicion' in filename:
                    category = 'composicion_activo'
                elif 'cocf01' in filename or 'rentabilidad' in filename:
                    category = 'rentabilidad_bruta'
                elif 'esen07' in filename or 'variables' in filename:
                    category = 'principales_variables'
                elif 'neta' in filename:
                    category = 'rentabilidad_neta'
                
                if category:
                    target_path = os.path.join(RAW_PDF_DIR, f"{category}_{filename}")
                    
                    if not os.path.exists(target_path):
                        logging.info(f"[{category.upper()}] Descargando {filename}...")
                        try:
                            res = requests.get(full_url, headers=HEADERS, timeout=20)
                            with open(target_path, 'wb') as f:
                                f.write(res.content)
                            downloaded_files[category].append((target_path, f"{year}-{month}-01"))
                        except Exception as err:
                            logging.error(f"Fallo descarga {filename}: {err}")
                    else:
                        downloaded_files[category].append((target_path, f"{year}-{month}-01"))
                        
    return downloaded_files

# ==========================================
# 2. EXTRACCIÓN CON PDFPLUMBER Y MAPPING
# ==========================================

def parse_composicion_activo_pdf(pdf_path: str, fecha_corte: str) -> pd.DataFrame:
    """Extrae las tablas de composición de activo (cocf03) y las convierte a formato Long."""
    extracted_data = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 3:
                    continue
                
                df_raw = pd.DataFrame(table).fillna("").map(lambda x: str(x).strip().replace("\n", " "))
                
                for _, row in df_raw.iterrows():
                    rubro = str(row.iloc[0]).upper()
                    if any(term in rubro for term in ['TITULOS', 'BONOS', 'DEPOSITOS', 'FIDEICOMISOS', 'ACCIONES', 'DISPONIBILIDADES']):
                        # Mapeo de columnas a las AFAPs estándar
                        afap_mapping = {1: 'REPUBLICA AFAP', 2: 'AFAP SURA', 3: 'INTEGRACION AFAP', 4: 'CAPITAL AFAP'}
                        
                        for col_idx, afap_name in afap_mapping.items():
                            if col_idx < len(row):
                                val_str = str(row.iloc[col_idx]).replace(".", "").replace(",", ".")
                                try:
                                    monto = float(val_str)
                                except ValueError:
                                    monto = 0.0
                                    
                                extracted_data.append({
                                    'fecha': fecha_corte,
                                    'afap': afap_name,
                                    'subfondo': 'ACUMULACION',
                                    'tipo_instrumento': extract_instrument_type(rubro),
                                    'moneda': extract_currency(rubro),
                                    'monto_muyu': monto
                                })

    return pd.DataFrame(extracted_data)


def parse_principales_variables_pdf(pdf_path: str, fecha_corte: str) -> pd.DataFrame:
    """Extrae AUM, número de afiliados y cotizantes (esen07)."""
    metrics_data = []
    
    with pdfplumber.open(pdf_path) as pdf:
        text_full = " ".join([page.extract_text() or "" for page in pdf.pages])
        
        afaps = ['REPUBLICA', 'SURA', 'INTEGRACION', 'CAPITAL']
        for afap in afaps:
            pattern = re.compile(rf"{afap}.*?(\d+[\.,]\d+)", re.IGNORECASE)
            match = pattern.search(text_full)
            if match:
                aum_val = float(match.group(1).replace(".", "").replace(",", "."))
                metrics_data.append({
                    'fecha': fecha_corte,
                    'afap': f"{afap} AFAP" if afap != 'SURA' else 'AFAP SURA',
                    'aum_total_muyu': aum_val
                })
                
    return pd.DataFrame(metrics_data)

# Helpers de extracción semántica
def extract_currency(text: str) -> str:
    text = text.upper()
    if 'U.I.' in text or 'INDEXADA' in text: return 'UI'
    if 'U.S.D.' in text or 'DÓLAR' in text or 'DOLAR' in text: return 'USD'
    if 'U.R.' in text: return 'UR'
    return 'UYU'

def extract_instrument_type(text: str) -> str:
    text = text.upper()
    if 'GOBIERNO' in text or 'B.C.U' in text or 'DEUDA' in text: return 'RENTA FIJA SOBERANA'
    if 'FINANCIERO' in text or 'OBLIGACION' in text: return 'RENTA FIJA CORPORATIVA'
    if 'ACCION' in text: return 'RENTA VARIABLE'
    if 'DEPOSITO' in text or 'DISPONIBILIDAD' in text: return 'LIQUIDEZ Y DEPÓSITOS'
    return 'OTROS INSTRUMENTOS'

# ==========================================
# 3. PIPELINE Y EJECUCIÓN PRINCIPAL
# ==========================================

def run_bcu_pdf_pipeline(start_date: str, end_date: str):
    """Ejecuta la descarga, extracción y generación del esquema relacional."""
    
    files_dict = download_bcu_pdfs_for_period(start_date, end_date)
    
    fact_portfolio_list = []
    dim_stats_list = []
    
    for pdf_path, fecha in files_dict.get('composicion_activo', []):
        df_p = parse_composicion_activo_pdf(pdf_path, fecha)
        if not df_p.empty:
            fact_portfolio_list.append(df_p)
            
    for pdf_path, fecha in files_dict.get('principales_variables', []):
        df_v = parse_principales_variables_pdf(pdf_path, fecha)
        if not df_v.empty:
            dim_stats_list.append(df_v)
            
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    if fact_portfolio_list:
        df_fact_portfolio = pd.concat(fact_portfolio_list, ignore_index=True)
        total_aum = df_fact_portfolio.groupby(['fecha', 'afap'])['monto_muyu'].transform('sum')
        df_fact_portfolio['participacion_pct'] = np.where(total_aum > 0, df_fact_portfolio['monto_muyu'] / total_aum, 0.0)
        
        fact_path = os.path.join(PROCESSED_DIR, "fact_portfolio_monthly.csv")
        df_fact_portfolio.to_csv(fact_path, index=False)
        logging.info(f"Tabla de hechos guardada en: {fact_path} ({len(df_fact_portfolio)} registros)")
        
    if dim_stats_list:
        df_dim_stats = pd.concat(dim_stats_list, ignore_index=True)
        stats_path = os.path.join(PROCESSED_DIR, "dim_afap_stats.csv")
        df_dim_stats.to_csv(stats_path, index=False)
        logging.info(f"Tabla de variables/AUM guardada en: {stats_path}")


if __name__ == "__main__":
    # Captura de argumentos por consola (con valores por defecto si se ejecuta sin parámetros)
    start_period = sys.argv[1] if len(sys.argv) > 1 else "2026-01"
    end_period   = sys.argv[2] if len(sys.argv) > 2 else "2026-08"
    
    logging.info(f"Iniciando ejecucion para el rango: {start_period} -> {end_period}")
    run_bcu_pdf_pipeline(start_date=start_period, end_date=end_period)