"""Plot ADC samples from a text file against a 0-2s time axis."""

from pathlib import Path
import argparse

import matplotlib.pyplot as plt
import numpy as np


def load_adc_samples(file_path: Path) -> np.ndarray:
    """Load ADC samples from a plain text file (one value per line)."""
    try:
        return np.loadtxt(file_path, dtype=float)
    except OSError as exc:
        raise SystemExit(f"Error reading '{file_path}': {exc}") from exc


def build_time_axis(sample_count: int) -> np.ndarray:
    """Return a time axis from 0s to 2s matching the number of samples."""
    if sample_count <= 0:
        raise ValueError("El archivo no contiene muestras válidas.")
    if sample_count == 1:
        return np.array([0.0])
    return np.linspace(0.0, 2.0, num=sample_count, endpoint=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "archivo",
        nargs="?",
        default="./Hit-05",
        help="Ruta al archivo de texto con los valores ADC (default: Hammer/Hit 01)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    adc_path = Path(args.archivo)

    muestras = load_adc_samples(adc_path)
    tiempo = build_time_axis(len(muestras))

    fuerza= muestras/0.00025
    plt.figure()
    plt.plot(tiempo, fuerza,linestyle="-", linewidth=1)
    plt.title(f"Force(t) - {adc_path.name}")
    plt.xlabel("Tiempo [s]")
    plt.ylabel("force")
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
