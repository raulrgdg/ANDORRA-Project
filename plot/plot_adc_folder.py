import os
import re
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import argparse
import pandas as pd  # <— NUEVO

# --- Parámetros fijos de formato del binario ---
NUM_CHANNELS = 6                 # 5 ADC + 1 timestamp
PINS = [15, 17, 19, 21, 23]      # etiquetas de los 5 canales ADC

# Regex para extraer el número después de "data_"
TS_RE = re.compile(r"data_(\d+)\.bin$", re.IGNORECASE)

def extract_timestamp_from_name(path: Path):
    m = TS_RE.search(path.name)
    return int(m.group(1)) if m else None

def load_bin(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Carga el binario int32 con formato [adc_15, adc_17, adc_19, adc_21, adc_23, timestamp]
    Devuelve: (time_s, adc_data, timestamps_us)
      - time_s: shape (N,) en segundos
      - adc_data: shape (N, 5)
      - timestamps_us: shape (N,) en microsegundos
    """
    data = np.fromfile(path, dtype=np.int32)
    if data.size % NUM_CHANNELS != 0:
        raise ValueError(f"El archivo {path} tiene tamaño {data.size} que no es múltiplo de {NUM_CHANNELS}.")
    data = data.reshape(-1, NUM_CHANNELS)

    adc_data = data[:, :5]          # 5 columnas ADC
    timestamps_us = data[:, 5]      # en microsegundos (µs)
    time_s = timestamps_us * 1e-6   # a segundos
    return time_s, adc_data, timestamps_us

def df_from_adc(time_s: np.ndarray, adc_data: np.ndarray, timestamps_us: np.ndarray) -> pd.DataFrame:
    """
    Construye un DataFrame con cabeceras de canales + timestamp_us + time_s.
    """
    cols = [f"adc_{p}" for p in PINS]  # ['adc_15', 'adc_17', ...]
    df = pd.DataFrame(adc_data, columns=cols)
    df["timestamp_us"] = timestamps_us
    return df

def save_csv(df: pd.DataFrame, out_csv: Path):
    """
    Guarda el DataFrame en CSV (sin índice).
    """
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)

def plot_adc(time_s: np.ndarray, adc_data: np.ndarray, title: str, out_png: Path):
    """
    Genera el plot de 5 subplots (uno por canal) vs tiempo y guarda PNG.
    """
    fig, axs = plt.subplots(5, 1, figsize=(10, 12), sharex=True)
    for i in range(5):
        axs[i].plot(time_s, adc_data[:, i])
        axs[i].set_title(f"ADC Pin {PINS[i]}")
        axs[i].set_ylabel("Valor ADC")
        axs[i].grid(True)

    axs[-1].set_xlabel("Tiempo (s)")
    fig.suptitle(title, y=0.995)
    plt.tight_layout(rect=[0, 0, 1, 0.98])
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150)
    plt.close(fig)

def main():
    parser = argparse.ArgumentParser(
        description="Plotea ADC vs tiempo y guarda CSV para todos los data_*.bin de una carpeta."
    )
    parser.add_argument("carpeta", type=str, help="Carpeta que contiene los .bin (p. ej. ./datos)")
    parser.add_argument("--max-n", type=int, default=None, help="Limitar a los primeros N archivos .bin (opcional)")
    parser.add_argument("--outdir", type=str, default="plots_ADC", help="Carpeta de salida para los PNG")
    parser.add_argument("--csvdir", type=str, default="csv_ADC", help="Carpeta de salida para los CSV")
    args = parser.parse_args()

    in_dir = Path(args.carpeta).expanduser().resolve()
    out_dir = Path(args.outdir).expanduser().resolve()
    csv_dir = Path(args.csvdir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)

    # Buscar archivos con patrón data_*.bin
    files = sorted(
        (p for p in in_dir.glob("data_1546300873_60_*.bin") if TS_RE.search(p.name)),
        key=lambda p: extract_timestamp_from_name(p)
    )

    if not files:
        raise SystemExit(f"No se encontraron archivos 'data_*.bin' en {in_dir}")

    # Si el usuario quiere limitar la cantidad
    if args.max_n is not None:
        files = files[:args.max_n]

    print(f"Procesando {len(files)} archivo(s) .bin en {in_dir}")
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

        # 1) Plot PNG
        title = f"{p.name} (N={len(time_s)})"
        out_png = out_dir / f"data_{ts}.png"
        #plot_adc(time_s, adc_data, title, out_png)

        # 2) Guardar CSV con pandas
        df = df_from_adc(time_s, adc_data, timestamps_us)
        out_csv = csv_dir / f"data_{ts}.csv"
        save_csv(df, out_csv)

        print(f"  - OK: {p.name} → {out_png.name}, {out_csv.name}")

    print(f"Listo.\nPNGs guardados en: {out_dir}\nCSV guardados en: {csv_dir}")

if __name__ == "__main__":
    main()
