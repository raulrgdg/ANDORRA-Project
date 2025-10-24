import serial
import matplotlib.pyplot as plt
import numpy as np
import time
import os
from datetime import datetime
import csv

# Configuration
PORT = '/dev/ttyACM0'  # Modifier selon ton système
BAUDRATE = 10000000
DURATION_SECONDS = 60
MAX_VALID_ADC = 4095
SAVE_FOLDER = "adc_logs"

# Assure-toi que le dossier de sauvegarde existe
os.makedirs(SAVE_FOLDER, exist_ok=True)

def read_adc_data():
    ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    time.sleep(2)  # Laisse le temps à la Teensy de redémarrer

    print(f"Lecture des données ADC pendant {DURATION_SECONDS} secondes...")
    start_time = time.time()
    timestamps = []
    values = []

    while time.time() - start_time < DURATION_SECONDS:
        line = ser.readline().decode('utf-8').strip()
        try:
            value = int(line)
            if 0 <= value <= MAX_VALID_ADC:
                values.append(value)
                timestamps.append(time.time() - start_time)
        except ValueError:
            continue  # Ignore les lignes corrompues

    ser.close()
    return np.array(timestamps), np.array(values)

def plot_and_save(timestamps, values):
    # Création timestamp unique pour les fichiers
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Sauvegarde CSV
    csv_path = os.path.join(SAVE_FOLDER, f"adc_data_{timestamp_str}.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "adc_value"])
        writer.writerows(zip(timestamps, values))

    print(f"✅ Données sauvegardées dans : {csv_path}")

    # FFT (suppose un échantillonnage à intervalles réguliers)
    if len(timestamps) > 1:
        sampling_interval = np.mean(np.diff(timestamps))
        fs = 1.0 / sampling_interval  # fréquence d'échantillonnage estimée
        fft_vals = np.fft.fft(values - np.mean(values))  # centrage
        fft_freqs = np.fft.fftfreq(len(values), d=sampling_interval)

        # On ne garde que la partie positive
        idx = fft_freqs >= 0
        fft_freqs = fft_freqs[idx]
        fft_magnitude = np.abs(fft_vals[idx]) * 2 / len(values)
    else:
        print("Pas assez de données pour une FFT.")
        fft_freqs = []
        fft_magnitude = []

    # Tracé
    fig, axs = plt.subplots(2, 1, figsize=(10, 6))

    axs[0].plot(timestamps, values)
    axs[0].set_title("Signal ADC (A17 / pin 41)")
    axs[0].set_xlabel("Temps (s)")
    axs[0].set_ylabel("Valeur ADC")
    axs[0].grid(True)

    axs[1].plot(fft_freqs, fft_magnitude)
    axs[1].set_title("Transformée de Fourier (FFT)")
    axs[1].set_xlabel("Fréquence (Hz)")
    axs[1].set_ylabel("Amplitude")
    axs[1].grid(True)

    plt.tight_layout()
    fig_path = os.path.join(SAVE_FOLDER, f"adc_plot_{timestamp_str}.png")
    plt.savefig(fig_path)
    plt.show()

    print(f"📊 Graphiques sauvegardés dans : {fig_path}")

if __name__ == "__main__":
    timestamps, values = read_adc_data()
    print(f"Nombre d'échantillons valides : {len(values)}")
    plot_and_save(timestamps, values)
