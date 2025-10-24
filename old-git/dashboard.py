import os
import csv
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.patheffects as patheffects

# 👉 Adapte ce chemin vers le fichier CSV que tu veux analyser
CSV_FILE = "adc_logs/adc_data_20250702_191259.csv"

# Coordonnées fictives des capteurs sur la plaque (en cm)
# Coin haut gauche, haut droit, bas gauche, bas droit, centre
SENSOR_POSITIONS = {
    "adc_23": (-10, 10),
    "adc_21": (10, 10),
    "adc_19": (-10, -10),
    "adc_17": (10, -10),
    "adc_15": (0, 0),
}
SENSOR_ORDER = ["adc_23", "adc_21", "adc_19", "adc_17", "adc_15"]

def load_data(csv_path):
    times = []
    values = []
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            times.append(float(row["time_s"]))
            values.append([int(row[f]) for f in SENSOR_ORDER])
    return np.array(times), np.array(values)

def plot_dashboard(timestamps, all_values):
    # Trouver l'index du pic global
    total_signal = np.sum(all_values, axis=1)
    peak_idx = np.argmax(total_signal)
    peak_time = timestamps[peak_idx]

    # Extraire valeurs au pic
    peak_values = all_values[peak_idx]
    print(f"📈 Pic détecté à t = {peak_time:.4f}s")
    print("Valeurs ADC au pic :", dict(zip(SENSOR_ORDER, peak_values)))

    # Normalisation pour couleur et taille
    norm_values = (peak_values - np.min(peak_values)) / (np.ptp(peak_values) + 1e-9)

    # Use a consistent color for each sensor
    sensor_cmap = plt.get_cmap("tab10")
    sensor_colors = {sensor: sensor_cmap(i) for i, sensor in enumerate(SENSOR_ORDER)}

    fig, ax = plt.subplots(figsize=(8,8))
    ax.set_title(f"Impact detected at t={peak_time:.3f}s", fontsize=16)
    ax.set_xlabel("X (cm)", fontsize=13)
    ax.set_ylabel("Y (cm)", fontsize=13)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_aspect("equal")

    # Draw a plate outline for context
    plate_x = [-12, 12, 12, -12, -12]
    plate_y = [12, 12, -12, -12, 12]
    ax.plot(plate_x, plate_y, color='gray', linestyle='-', linewidth=1, alpha=0.3)

    # Afficher les capteurs
    scatters = []
    for i, sensor in enumerate(SENSOR_ORDER):
        x, y = SENSOR_POSITIONS[sensor]
        val = peak_values[i]
        norm = norm_values[i]
        color = plt.cm.inferno(norm)
        size = 600 * (0.3 + norm)
        s = ax.scatter(x, y, s=size, c=[color], label=f"{sensor}: {val}", edgecolors="black", linewidths=2, zorder=3)
        scatters.append(s)
        ax.text(x, y, f"{val}", ha="center", va="center", color="white", fontsize=13, weight="bold", zorder=4, path_effects=[patheffects.withStroke(linewidth=2, foreground="black")])

    # Add colorbar for value scale
    sm = plt.cm.ScalarMappable(cmap="inferno", norm=plt.Normalize(vmin=np.min(peak_values), vmax=np.max(peak_values)))
    cbar = plt.colorbar(sm, ax=ax, pad=0.02, fraction=0.04)
    cbar.set_label('ADC Value at Peak', fontsize=12)

    # Move legend outside the plot
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=11, title="Sensors", title_fontsize=12, frameon=True)
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    plt.show()

    # --- Time series plots ---
    fig2, axs = plt.subplots(5,1, figsize=(12,13), sharex=True)
    fig2.suptitle("Évolution des signaux ADC (pic en rouge)", fontsize=16)
    peak_window = 0.05  # seconds around the peak to highlight
    for i, sensor in enumerate(SENSOR_ORDER):
        axs[i].plot(timestamps, all_values[:, i], color=sensor_colors[sensor], label=sensor)
        axs[i].axvline(peak_time, color="r", linestyle="--", label="Pic")
        axs[i].axvspan(peak_time-peak_window, peak_time+peak_window, color="red", alpha=0.1)
        axs[i].set_ylabel(sensor, fontsize=11)
        axs[i].grid(True, linestyle='--', alpha=0.5)
        axs[i].legend(loc="upper right", fontsize=10)
    axs[-1].set_xlabel("Temps (s)", fontsize=13)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.show()

if __name__ == "__main__":
    timestamps, all_values = load_data(CSV_FILE)
    plot_dashboard(timestamps, all_values)
