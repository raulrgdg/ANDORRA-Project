#!/usr/bin/env python3
# Use as: python plot_adc.py ./datos --outdir plots_ADC --max-n 10 --patron "data_*.bin"

import re
from pathlib import Path
import argparse
import numpy as np
import matplotlib.pyplot as plt

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
      - time_s: shape (N,) en segundos
      - adc_data: shape (N, 5)
      - timestamps_us: shape (N,) en microsegundos
    """
    data = np.fromfile(path, dtype=np.int32)
    if data.size % NUM_CHANNELS != 0:
        raise ValueError(f"El archivo {path} tiene tamaño {data.size} que no es múltiplo de {NUM_CHANNELS}.")
    data = data.reshape(-1, NUM_CHANNELS)
    adc_data = data[:, :5]
    timestamps_us = data[:, 5]
    time_s = timestamps_us * 1e-6
    return time_s, adc_data, timestamps_us

def plot_adc(time_s, adc_data, title: str, out_png: Path):
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

def plot_adc_single(time_s, adc_data, out_png):
    plt.figure(figsize=(10, 5))
    plt.plot(time_s, adc_data[:, 0])
    plt.title(f"ADC Pin {PINS[0]}")
    plt.ylabel("ADC value")
    plt.grid(True)
    plt.xlabel("Time (s)")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=150)
    plt.close()

def main():
    parser = argparse.ArgumentParser(
        description="Plotea ADC vs tiempo para todos los data_*.bin de una carpeta."
    )
    parser.add_argument("carpeta", type=str, help="Carpeta que contiene los .bin (p. ej. ./datos)")
    parser.add_argument("--max-n", type=int, default=None, help="Limitar a los primeros N archivos .bin (opcional)")
    parser.add_argument("--outdir", type=str, default="plots_ADC", help="Carpeta de salida para los PNG")
    parser.add_argument("--patron", type=str, default="data_*.bin", help="Patrón glob para buscar binarios")
    args = parser.parse_args()

    in_dir = Path(args.carpeta).expanduser().resolve()
    out_dir = Path(args.outdir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(
        (p for p in in_dir.glob(args.patron) if TS_RE.search(p.name)),
        key=lambda p: extract_timestamp_from_name(p)
    )

    if not files:
        raise SystemExit(f"No se encontraron archivos con patrón '{args.patron}' en {in_dir}")

    if args.max_n is not None:
        files = files[:args.max_n]

    print(f"Ploteando {len(files)} archivo(s) .bin en {in_dir}")
    for p in files:
        ts = extract_timestamp_from_name(p)
        if ts is None:
            print(f"  - Omitido (nombre no coincide): {p.name}")
            continue
        try:
            time_s, adc_data, _ = load_bin(p)
        except Exception as e:
            print(f"  - Error leyendo {p.name}: {e}")
            continue

        title = f"{p.name} (N={len(time_s)})"
        out_png = out_dir / f"data_{ts}.png"
        plot_adc_single(time_s, adc_data, out_png)
        print(f"  - OK plot: {out_png.name}")

    print(f"Listo.\nPNGs guardados en: {out_dir}")

if __name__ == "__main__":
    main()
