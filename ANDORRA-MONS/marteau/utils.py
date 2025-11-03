import os
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.fft import fft, fftfreq
import csv

def record_signal(duration, fs, device):
    import sounddevice as sd
    sd.default.device = device
    data = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float64')
    sd.wait()
    return data.flatten()

def analyze_impacts(force_signal, fs, sensitivity, threshold_rel=0.4, pre_ms=50, post_ms=100):
    time = np.linspace(0, len(force_signal) / fs, len(force_signal))
    force_signal = force_signal / sensitivity

    pre_samples = int((pre_ms / 1000) * fs)
    post_samples = int((post_ms / 1000) * fs)

    max_force = np.max(force_signal)
    peaks, _ = find_peaks(force_signal, height=max_force * threshold_rel, distance=fs * 0.05)

    results = []
    plots = []

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_dir = os.path.join("results", timestamp)
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "results.csv")

    with open(csv_path, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Impact", "Time_s", "Peak_Force_N", "Energy_N2s", "Impulse_Ns",
                         "Impact_Duration_ms", "Rise_Time_ms", "Fall_Time_ms", "Dominant_Freq_Hz"])

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

        energy_window = np.sum(windowed_force ** 2) / fs
        impulse = np.trapz(windowed_force, dx=1 / fs)

        local_fft = fft(windowed_force)
        N_local = len(windowed_force)
        xf_local = fftfreq(N_local, 1 / fs)[:N_local // 2]
        amp_spectrum_local = 2.0 / N_local * np.abs(local_fft[0:N_local // 2])
        dominant_freq = xf_local[np.argmax(amp_spectrum_local)]

        # Save to CSV
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
        fig1, ax1 = plt.subplots(figsize=(6, 2))
        ax1.plot(windowed_time, windowed_force)
        ax1.set_title(f"Impact {i+1} - Force")
        ax1.set_xlabel("Time [s]")
        ax1.set_ylabel("Force [N]")
        ax1.grid()
        fig1.tight_layout()

        # Plot FFT
        fig2, ax2 = plt.subplots(figsize=(6, 2))
        ax2.plot(xf_local, amp_spectrum_local)
        ax2.set_title(f"Impact {i+1} - FFT")
        ax2.set_xlabel("Freq [Hz]")
        ax2.set_ylabel("Amplitude")
        ax2.grid()
        fig2.tight_layout()

        results.append({
            "i": i + 1,
            "time": peak_time,
            "peak": peak_force,
            "energy": energy_window,
            "impulse": impulse,
            "duration": impact_duration,
            "rise": rise_time,
            "fall": fall_time,
            "freq": dominant_freq
        })

        plots.append((fig1, fig2))

    return results, plots, csv_path, output_dir
