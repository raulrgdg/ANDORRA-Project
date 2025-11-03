import serial
import matplotlib.pyplot as plt
import numpy as np
import time
import os
from datetime import datetime
import csv

# Configuration
PORT = '/dev/ttyACM0'  # ⚠️ adapte ce port si besoin
BAUDRATE = 1000000000
DURATION_SECONDS = 5
MAX_VALID_ADC = 4095
SAVE_FOLDER = "adc_logs"

# Crée le dossier si inexistant
os.makedirs(SAVE_FOLDER, exist_ok=True)

def read_adc_data():
    ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    time.sleep(2)  # Laisse la Teensy démarrer

    print(f"Lecture des données ADC pendant {DURATION_SECONDS} secondes...")
    start_time = time.time()
    timestamps = []
    all_values = []  # liste de listes [ [v1,v2,v3,v4,v5], ... ]
    not_parsed = []

    while time.time() - start_time < DURATION_SECONDS:
        line = ser.readline()
        not_parsed.append((line, time.time() - start_time))

    for line, timestamp in not_parsed:
        line = line.decode('utf-8').strip()
        try:
            parts = line.split(",")
            if len(parts) != 5:
                continue  # ignore si pas 5 valeurs
            values = [int(p) for p in parts]
            if all(0 <= v <= MAX_VALID_ADC for v in values):
                all_values.append(values)
                timestamps.append(timestamp)
        except ValueError:
            continue  # ignore les lignes corrompues
    ser.close()
    return np.array(timestamps), np.array(all_values)

def plot_and_save(timestamps, all_values):
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Sauvegarde CSV
    csv_path = os.path.join(SAVE_FOLDER, f"adc_data_{timestamp_str}.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        header = ["time_s", "adc_23", "adc_21", "adc_19", "adc_17", "adc_15"]
        writer.writerow(header)
        for t, row in zip(timestamps, all_values):
            writer.writerow([t] + list(row))

    print(f"✅ Données sauvegardées dans : {csv_path}")

    # Tracé simple des signaux
    fig, axs = plt.subplots(5, 1, figsize=(10, 12))
    pins = [23, 21, 19, 17, 15]
    for i in range(5):
        axs[i].plot(timestamps, all_values[:, i])
        axs[i].set_title(f"ADC Pin {pins[i]}")
        axs[i].set_xlabel("Temps (s)")
        axs[i].set_ylabel("Valeur ADC")
        axs[i].grid(True)

    plt.tight_layout()
    fig_path = os.path.join(SAVE_FOLDER, f"adc_plot_{timestamp_str}.png")
    plt.savefig(fig_path)
    plt.show()

    print(f"📊 Graphiques sauvegardés dans : {fig_path}")

if __name__ == "__main__":
    timestamps, all_values = read_adc_data()
    print(f"Nombre d'échantillons valides : {len(all_values)}")
    plot_and_save(timestamps, all_values)
