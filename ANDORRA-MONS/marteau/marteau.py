import sounddevice as sd
import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks
import os
import csv
from datetime import datetime

# --- Config ---
sd.default.device = 6 # set the device to the default device, print(sd.query_devices()) to get the list of devices
DURATION = 60
FS = 48000
SENSITIVITY = 0.002251  # V/N
THRESHOLD_RELATIVE = 0.1  # seuil relatif

# Fenêtre autour des impacts
pre_impact_ms = 50
post_impact_ms = 100
pre_samples = int((pre_impact_ms / 1000) * FS)
post_samples = int((post_impact_ms / 1000) * FS)

# --- Création du dossier de sauvegarde ---
timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
output_dir = os.path.join("results", timestamp)
os.makedirs(output_dir, exist_ok=True)
csv_path = os.path.join(output_dir, "results.csv")

# --- Initialisation CSV ---
with open(csv_path, mode="w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Impact", "Time_s", "Peak_Force_N", "Energy_N2s", "Impulse_Ns",
                     "Impact_Duration_ms", "Rise_Time_ms", "Fall_Time_ms", "Dominant_Freq_Hz"])

# --- Acquisition ---
print("Recording...")
data = sd.rec(int(DURATION * FS), samplerate=FS, channels=1, dtype='float64')
sd.wait()
print("Recording finished.")

# --- Traitement signal ---
voltage_signal = data.flatten()
force_signal = voltage_signal / SENSITIVITY
time = np.linspace(0, DURATION, len(force_signal))

# --- Détection des impacts ---
max_force = np.max(force_signal)
peaks, _ = find_peaks(force_signal, height=max_force * THRESHOLD_RELATIVE, distance=FS * 0.05)

print(f"💥 {len(peaks)} impact(s) détecté(s)")

# --- Analyse des impacts ---
for i, peak_index in enumerate(peaks):
    start = max(0, peak_index - pre_samples)
    end = min(len(force_signal), peak_index + post_samples)
    windowed_force = force_signal[start:end]
    windowed_time = time[start:end]

    peak_force = force_signal[peak_index]
    peak_time = time[peak_index]

    ten_percent = 0.1 * peak_force
    ninety_percent = 0.9 * peak_force

    try:
        rise_indices = np.where((windowed_force >= ten_percent) & (windowed_force <= ninety_percent))[0]
        rise_time = (windowed_time[rise_indices[-1]] - windowed_time[rise_indices[0]]) * 1000 if len(rise_indices) > 1 else None
    except:
        rise_time = None

    try:
        fall_indices = np.where((windowed_force <= ninety_percent) & (windowed_force >= ten_percent))[0]
        fall_time = (windowed_time[fall_indices[-1]] - windowed_time[fall_indices[0]]) * 1000 if len(fall_indices) > 1 else None
    except:
        fall_time = None

    duration_mask = windowed_force > 0.2 * peak_force
    impact_duration = (windowed_time[duration_mask][-1] - windowed_time[duration_mask][0]) * 1000 if np.any(duration_mask) else 0

    energy_window = np.sum(windowed_force ** 2) / FS
    impulse = np.trapz(windowed_force, dx=1 / FS)

    local_fft = fft(windowed_force)
    N_local = len(windowed_force)
    xf_local = fftfreq(N_local, 1 / FS)[:N_local // 2]
    amp_spectrum_local = 2.0 / N_local * np.abs(local_fft[0:N_local // 2])
    dominant_freq = xf_local[np.argmax(amp_spectrum_local)]

    # Print
    print(f"\n🟢 Impact {i+1}")
    print(f"- Time: {peak_time:.4f} s")
    print(f"- Peak Force: {peak_force:.2f} N")
    print(f"- Energy: {energy_window:.4f} N²·s")
    print(f"- Impulse: {impulse:.4f} N·s")
    print(f"- Duration: {impact_duration:.1f} ms")
    print(f"- Rise Time: {rise_time:.1f} ms" if rise_time else "- Rise Time: N/A")
    print(f"- Fall Time: {fall_time:.1f} ms" if fall_time else "- Fall Time: N/A")
    print(f"- Dominant Freq: {dominant_freq:.1f} Hz")

    # Écriture CSV
    with open(csv_path, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            i + 1, f"{peak_time:.4f}", f"{peak_force:.2f}", f"{energy_window:.4f}",
            f"{impulse:.4f}", f"{impact_duration:.1f}",
            f"{rise_time:.1f}" if rise_time else "N/A",
            f"{fall_time:.1f}" if fall_time else "N/A",
            f"{dominant_freq:.1f}"
        ])

    # Plot force vs time
    plt.figure(figsize=(10, 3))
    plt.plot(windowed_time, windowed_force, label=f"Impact {i+1}")
    plt.axvline(peak_time, color='r', linestyle='--', label="Peak")
    plt.title(f"Impact {i+1} - Force vs Time")
    plt.xlabel("Time [s]")
    plt.ylabel("Force [N]")
    plt.grid()
    plt.legend()
    plt.tight_layout()
    plot_path = os.path.join(output_dir, f"impact_{i+1}_force.png")
    plt.savefig(plot_path)
    plt.close()

    # Plot spectre local
    plt.figure(figsize=(8, 3))
    plt.plot(xf_local, amp_spectrum_local)
    plt.title(f"Impact {i+1} - Local FFT")
    plt.xlabel("Frequency [Hz]")
    plt.ylabel("Amplitude")
    plt.grid()
    plt.tight_layout()
    fft_path = os.path.join(output_dir, f"impact_{i+1}_fft.png")
    plt.savefig(fft_path)
    plt.close()

# --- FFT globale ---
N = len(force_signal)
yf = fft(force_signal)
xf = fftfreq(N, 1 / FS)[:N // 2]
amplitude_spectrum = 2.0 / N * np.abs(yf[0:N // 2])

plt.figure(figsize=(10, 4))
plt.plot(xf, amplitude_spectrum)
plt.title("Global Frequency Spectrum (FFT)")
plt.xlabel("Frequency [Hz]")
plt.ylabel("Amplitude")
plt.grid()
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "global_fft.png"))
plt.close()

print(f"\n✅ Résultats sauvegardés dans: {output_dir}")
