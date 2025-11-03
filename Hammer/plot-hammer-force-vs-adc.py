"""Plot ADC pin 15 samples from a binary capture alongside hammer force data."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Binary layout: 5 ADC channels followed by a timestamp (µs)
NUM_COLUMNS = 6
number= 1 #Hit number 

PIN_TO_COLUMN = {
    15: 0,
    17: 1,
    19: 2,
    21: 3,
    23: 4,
}

def _default_paths() -> tuple[Path, Path]:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    binary_default = repo_root / "Hammer" / "second-test_hammer" / f"hit{number}.bin"
    force_default = script_dir / "second-test_hammer" / "Hammer_Test_28OCT25" / f"Impact_0{number}"
    return binary_default, force_default


def load_adc_from_binary(binary_path: Path, pin: int) -> tuple[np.ndarray, np.ndarray]:
    """Return time axis (seconds) and ADC counts for the desired pin."""
    if pin not in PIN_TO_COLUMN:
        raise ValueError(f"Pin {pin} is not available in the binary file.")

    try:
        raw = np.fromfile(binary_path, dtype=np.int32)
    except OSError as exc:
        raise SystemExit(f"Could not read '{binary_path}': {exc}") from exc

    if raw.size % NUM_COLUMNS != 0:
        raise SystemExit(
            f"The file '{binary_path}' does not contain a valid number of samples "
            f"({raw.size} integers for {NUM_COLUMNS} columns)."
        )

    data = raw.reshape(-1, NUM_COLUMNS)
    adc_counts = data[:, PIN_TO_COLUMN[pin]]
    timestamps = data[:, -1] * 1e-6  # convert µs → s

    return timestamps, adc_counts


def load_force_samples(force_path: Path) -> np.ndarray:
    """Load hammer force values from text file (one value per line)."""
    try:
        return np.loadtxt(force_path, dtype=float)
    except OSError as exc:
        raise SystemExit(f"Could not read '{force_path}': {exc}") from exc


def build_force_time_axis(sample_count: int) -> np.ndarray:
    """Construct a 0-2s time axis matching the number of force samples."""
    if sample_count <= 0:
        raise ValueError("The force file does not contain valid samples.")
    if sample_count == 1:
        return np.array([0.0])
    return np.linspace(0, 1.33, num=sample_count, endpoint=True)


def parse_args() -> argparse.Namespace:
    binary_default, force_default = _default_paths()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--binary",
        type=Path,
        default=binary_default,
        help=f"Path to the binary file containing the ADC data (default: {binary_default})",
    )
    parser.add_argument(
        "--force",
        type=Path,
        default=force_default,
        help=f"Path to the text file containing the force measurements (default: {force_default})",
    )
    parser.add_argument(
        "--pin",
        type=int,
        default=15,
        choices=sorted(PIN_TO_COLUMN),
        help="ADC pin to plot from the binary file (default: 15).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    binary_path = args.binary
    force_path = args.force

    time_adc, adc_counts = load_adc_from_binary(binary_path, args.pin)
    force_samples = load_force_samples(force_path)
    time_force = build_force_time_axis(force_samples.size)
    force_newtons = force_samples / 0.00025

    fig, (ax_adc, ax_force) = plt.subplots(1, 2, figsize=(14, 5), sharey=False)

    ax_adc.plot(time_adc, adc_counts, linewidth=1)
    ax_adc.set_title(f"ADC(t)")
    ax_adc.set_xlabel("Time [s]")
    ax_adc.set_ylabel("ADC")
    ax_adc.grid(True, which="both", linestyle="--", linewidth=0.5)

    ax_force.plot(time_force, force_newtons, linewidth=1, color="tab:orange")
    ax_force.set_title(f"F(t)")
    ax_force.set_xlabel("Time [s]")
    ax_force.set_ylabel("Force [N]")
    ax_force.grid(True, which="both", linestyle="--", linewidth=0.5)

    fig.tight_layout()
    plt.savefig(f"/Users/raulrodriguez/Desktop/ANDORRAV2/Hammer/second-test_hammer/plot-force-adc_hit{number}-session2.png")
    plt.close()

if __name__ == "__main__":
    main()
