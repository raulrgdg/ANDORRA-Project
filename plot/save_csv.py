#!/usr/bin/env python3
# Use as: python export_csv.py ./datos --csvdir csv_ADC --max-n 10 --patron "data_*.bin"

import re
from pathlib import Path
import argparse
import numpy as np
import pandas as pd

# --- Parámetros fijos de formato del binario ---
NUM_CHANNELS = 6                 # 5 ADC + 1 timestamp
PINS = [15, 17, 19, 21, 23]      # etiquetas de los 5 canales ADC

# Regex para extraer el número después de "data_"
TS_RE = re.compile(r"data_(\d+)\.bin$", re.IGNORECASE)

def extract_timestamp_from_name(path: Path):
    m = TS_RE.search(path.name)
    return int(m.group(1)) if m else None

def load_bin(path: Path):
    """
    Carga el binario int32 con formato [adc_15, adc_17, adc_19, adc_21, adc_23, timestamp]
    Devuelve: (time_s, adc_data, timestamps_us)
    """
    data = np.fromfile(path, dtype=np.int32)
    if data.size % NUM_CHANNELS != 0:
        raise ValueError(f"El archivo {path} tiene tamaño {data.size} que no es múltiplo de {NUM_CHANNELS}.")
    data = data.reshape(-1, NUM_CHANNELS)
    adc_data = data[:, :5]
    timestamps_us = data[:, 5]
    time_s = timestamps_us * 1e-6
    return time_s, adc_data, timestamps_us

def df_from_adc(time_s, adc_data, timestamps_us) -> pd.DataFrame:
    """
    Construye un DataFrame con cabeceras de canales + timestamp_us.
    """
    cols = [f"adc_{p}" for p in PINS]  # ['adc_15', 'adc_17', ...]
    df = pd.DataFrame(adc_data, columns=cols)
    df["timestamp_us"] = timestamps_us
    df["time_s"] = time_s
    return df

def save_csv(df: pd.DataFrame, out_csv: Path):
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)

def main():
    parser = argparse.ArgumentParser(
        description="Guarda CSV para todos los data_*.bin de una carpeta."
    )
    parser.add_argument("carpeta", type=str, help="Carpeta que contiene los .bin (p. ej. ./datos)")
    parser.add_argument("--max-n", type=int, default=None, help="Limitar a los primeros N archivos .bin (opcional)")
    parser.add_argument("--csvdir", type=str, default="csv_ADC", help="Carpeta de salida para los CSV")
    parser.add_argument("--patron", type=str, default="data_*.bin", help="Patrón glob para buscar binarios")
    args = parser.parse_args()

    in_dir = Path(args.carpeta).expanduser().resolve()
    csv_dir = Path(args.csvdir).expanduser().resolve()
    csv_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(
        (p for p in in_dir.glob(args.patron) if TS_RE.search(p.name)),
        key=lambda p: extract_timestamp_from_name(p)
    )

    if not files:
        raise SystemExit(f"No se encontraron archivos con patrón '{args.patron}' en {in_dir}")

    if args.max_n is not None:
        files = files[:args.max_n]

    print(f"Exportando CSV de {len(files)} archivo(s) .bin en {in_dir}")
    for p in files:
        ts = extract_timestamp_from_name(p)
        if ts is None:
            print(f"  - Omitido (nombre no coincide): {p.name}")
            continue

        try:
            time_s, adc_data, timestamps_us = load_bin(p)
        except Exception as e:
            print(f"  - Error leyendo {p.name}: {e}")
            continue

        df = df_from_adc(time_s, adc_data, timestamps_us)
        out_csv = csv_dir / f"data_{ts}.csv"
        save_csv(df, out_csv)
        print(f"  - OK CSV: {out_csv.name}")

    print(f"Listo.\nCSV guardados en: {csv_dir}")

if __name__ == "__main__":
    main()
