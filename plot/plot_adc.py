#!/usr/bin/env python3
# Use as: python plot_adc.py ./data --outdir plots_ADC --max-n 10 --patron "data_*.bin"

import re
from pathlib import Path
import argparse
import numpy as np
import matplotlib.pyplot as plt

# --- Fixed binary layout parameters ---
NUM_CHANNELS = 6                 # 5 ADC samples + 1 timestamp
PINS = [15, 17, 19, 21, 23]      # labels for the five ADC channels

# Regex to extract the number following "data_"
TS_RE = re.compile(r"data_(\d+)\.bin$", re.IGNORECASE)

def extract_timestamp_from_name(path: Path):
    m = TS_RE.search(path.name)
    return int(m.group(1)) if m else None

def load_bin(path: Path):
    """
    Load the int32 binary formatted as [adc_15, adc_17, adc_19, adc_21, adc_23, timestamp].
    Returns: (time_s, adc_data, timestamps_us)
      - time_s: shape (N,) in seconds
      - adc_data: shape (N, 5)
      - timestamps_us: shape (N,) in microseconds
    """
    data = np.fromfile(path, dtype=np.int32)
    if data.size % NUM_CHANNELS != 0:
        raise ValueError(f"File {path} has size {data.size}, which is not a multiple of {NUM_CHANNELS}.")
    data = data.reshape(-1, NUM_CHANNELS)
    adc_data = data[:, :5]
    timestamps_us = data[:, 5]
    time_s = timestamps_us * 1e-6
    return time_s, adc_data, timestamps_us

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
        description="Plot ADC signals versus time for all data_*.bin files in a folder."
    )
    parser.add_argument("carpeta", type=str, help="Folder containing the .bin files (e.g., ./data)")
    parser.add_argument("--max-n", type=int, default=None, help="Limit processing to the first N .bin files (optional)")
    parser.add_argument("--outdir", type=str, default="plots_ADC", help="Output directory for the PNG files")
    parser.add_argument("--patron", type=str, default="data_*.bin", help="Glob pattern used to discover binary files")
    args = parser.parse_args()

    in_dir = Path(args.carpeta).expanduser().resolve()
    out_dir = Path(args.outdir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(
        (p for p in in_dir.glob(args.patron) if TS_RE.search(p.name)),
        key=lambda p: extract_timestamp_from_name(p)
    )

    if not files:
        raise SystemExit(f"No files matching pattern '{args.patron}' were found in {in_dir}")

    if args.max_n is not None:
        files = files[:args.max_n]

    print(f"Plotting {len(files)} .bin file(s) in {in_dir}")
    for p in files:
        ts = extract_timestamp_from_name(p)
        if ts is None:
            print(f"  - Skipped (name does not match): {p.name}")
            continue
        try:
            time_s, adc_data, _ = load_bin(p)
        except Exception as e:
            print(f"  - Error reading {p.name}: {e}")
            continue

        title = f"{p.name} (N={len(time_s)})"
        out_png = out_dir / f"data_{ts}.png"
        plot_adc_single(time_s, adc_data, out_png)
        print(f"  - OK plot: {out_png.name}")

    print(f"Done.\nPNGs saved to: {out_dir}")

if __name__ == "__main__":
    main()
