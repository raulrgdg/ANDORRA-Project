import csv
from pathlib import Path

import matplotlib.pyplot as plt

# ==== Configure these paths and column names manually ====
CSV_FILE = Path("/Users/raulrodriguez/Work-Station/ANDORRAV2/raul/compression-test/Test de compression tubes composites carbon_1/Hexa-Tabla 1.csv")
DISPLACEMENT_COLUMN = "Ecrasement"          # Column name for displacement
FORCE_COLUMN = "Forcestandard"               # Column name for force
SECTION_AREA = 1.12/10000                       # Cross-sectional area (same units as force)
DELIMITER = ";"                         # CSV delimiter
OUTPUT_PREFIX = "compression_test_hexagon"  # Prefix for output images
# =========================================================


displacements = []
forces = []

def _to_float(value: str) -> float:
    return float(value.replace(" ", "").replace(",", "."))


with CSV_FILE.open(newline="") as handle:
    reader = csv.DictReader(handle, delimiter=DELIMITER)
    for row in reader:
        dis_raw = row.get(DISPLACEMENT_COLUMN, "")
        force_raw = row.get(FORCE_COLUMN, "")
        if not dis_raw or not force_raw:
            continue
        try:
            displacements.append(_to_float(dis_raw))
            forces.append(_to_float(force_raw))
        except ValueError:
            continue

max_force = max(forces)
print(f"Maximum force: {max_force:.3f} N")

# Force vs displacement plot
plt.figure(figsize=(7, 4))
plt.plot(displacements, forces)
plt.xlabel("Displacement (%)")
plt.ylabel("Force (N)")
plt.title("Compression Test: Force vs Displacement")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f"{OUTPUT_PREFIX}_force_displacement.png", dpi=150)

# Stress vs displacement plot
stresses = [(force / SECTION_AREA)/1000000 for force in forces]
plt.figure(figsize=(7, 4))
plt.plot(displacements, stresses, color="tab:red")
plt.xlabel("Displacement (%)")
plt.ylabel("Stress (MPa)")
plt.title("Compression Test: Stress vs Displacement")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f"{OUTPUT_PREFIX}_stress_displacement.png", dpi=150)
