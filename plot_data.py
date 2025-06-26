import matplotlib.pyplot as plt
import numpy as np
import csv


def load_csv_and_plot():
    file_path = 'SEANCE_TIR_3/adc_data_20250612_094713.csv'
    timestamps = []
    values = []

    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Ignore l'en-tête
        for row in reader:
            try:
                t, v = float(row[0]), int(row[1])
                timestamps.append(t)
                values.append(v)
            except ValueError:
                continue

    timestamps = np.array(timestamps)
    values = np.array(values)

    print(f"📂 Données chargées depuis : {file_path}")
    print(f"Nombre d'échantillons : {len(values)}")

    # FFT
    if len(timestamps) > 1:
        sampling_interval = np.mean(np.diff(timestamps))
        fs = 1.0 / sampling_interval
        fft_vals = np.fft.fft(values - np.mean(values))
        fft_freqs = np.fft.fftfreq(len(values), d=sampling_interval)
        idx = fft_freqs >= 0
        fft_freqs = fft_freqs[idx]
        fft_magnitude = np.abs(fft_vals[idx]) * 2 / len(values)
    else:
        print("Pas assez de données pour une FFT.")
        fft_freqs = []
        fft_magnitude = []

    # Tracés
    fig, axs = plt.subplots(2, 1, figsize=(10, 6))

    axs[0].plot(timestamps, values)
    axs[0].set_title("Signal ADC (rechargé depuis CSV)")
    axs[0].set_xlabel("Temps (s)")
    axs[0].set_ylabel("Valeur ADC")
    axs[0].grid(True)

    axs[1].plot(fft_freqs, fft_magnitude)
    axs[1].set_title("Transformée de Fourier (FFT)")
    axs[1].set_xlabel("Fréquence (Hz)")
    axs[1].set_ylabel("Amplitude")
    axs[1].grid(True)

    plt.tight_layout()
    plt.savefig("plot_output.png")
    print("📊 Graphique sauvegardé dans : plot_output.png")

if __name__ == "__main__":
    load_csv_and_plot()
