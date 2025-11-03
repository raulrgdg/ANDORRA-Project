# -- using venv: source /Users/raulrodriguez/Desktop/ANDORRAV2/venv/bin/activate --
# Code designed to compute the FFT of a given signal.
# Raúl Rodríguez || October 2025

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# =========================
# Configuration
# =========================
data = "shoot12_right"
BIN_PATH = Path(f"/Users/raulrodriguez/Desktop/ANDORRAV2/seance_tir_8/{data}.bin")

CHANNEL_INDEX = 0          # 0-4choose which ADC is plotted. Now: channel 0 = Pin 15
XMAX_HZ = 0.9             # None to use the full positive spectrum. 0-1 part of spectrum
TIME_PLOT_SECONDS = None   # None to show the full time trace
DETREND = True             # If True subtracts the signal’s mean before taking the FFT. Removes any DC component so the spectrum focuses on the oscillatory content rather than a large spike at 0 Hz.
OUT_PNG = Path(f"/Users/raulrodriguez/Desktop/ANDORRAV2/raul/fft/shooting-session8/fft_{data}-5.png")

NUM_CHANNELS_BIN = 6             # 5 ADC + 1 timestamp
PINS = [15, 17, 19, 21, 23]

def resolve_freq_max(xmax, fs):
    """Return the upper frequency limit while respecting Nyquist."""
    nyquist = fs / 2.0
    if xmax is None:
        return nyquist
    if 0 < xmax < 1:
        return xmax * nyquist
    return float(min(xmax, nyquist))

def load_bin(path: Path):
    """Load [adc_15, adc_17, adc_19, adc_21, adc_23, timestamp_us] as int32."""
    data = np.fromfile(path, dtype=np.int32)
    if data.size % NUM_CHANNELS_BIN != 0:
        raise ValueError(f"Size {data.size} is not a multiple of {NUM_CHANNELS_BIN}")
    data = data.reshape(-1, NUM_CHANNELS_BIN)
    adc = data[:, :5]                      # (N,5)
    t_us = data[:, 5].astype(np.float64)   # (N,)
    t_s = t_us * 1e-6
    return t_s, adc

def estimate_fs(time_s: np.ndarray) -> float:
    """Estimate sampling frequency using the median time step."""
    dt = np.median(np.diff(time_s))
    if dt <= 0 or not np.isfinite(dt):
        raise ValueError("time_s is not valid to estimate fs.")
    return 1.0 / dt

t, adc = load_bin(BIN_PATH)
fs = estimate_fs(t)
print(f"fs ≈ {fs:.3f} Hz")

CHANNEL_INDEX = int(np.clip(CHANNEL_INDEX, 0, adc.shape[1]-1))
y = adc[:, CHANNEL_INDEX].astype(np.float64)
label = f"ADC Pin {PINS[CHANNEL_INDEX]}" if CHANNEL_INDEX < len(PINS) else f"Channel {CHANNEL_INDEX}"

if TIME_PLOT_SECONDS is not None:
    n_plot = int(min(len(y), max(1, TIME_PLOT_SECONDS * fs)))
    t_plot = t[:n_plot]
    y_plot = y[:n_plot]
else:
    t_plot = t
    y_plot = y

if DETREND:
    y = y - np.mean(y)

N = len(y)
Y = np.fft.rfft(y, n=N)
freqs = np.fft.rfftfreq(N, d=1.0/fs)
magnitude = np.abs(Y) / N

plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plt.plot(t_plot, y_plot)
plt.title(f"ADC signal — {label}")
plt.xlabel("Time [s]")
plt.ylabel("ADC")

plt.subplot(1, 2, 2)
plt.plot(freqs, magnitude)
plt.title(f"Frequency Spectrum (FFT) — {label}")
plt.xlabel("Frequency [Hz]")
plt.ylabel(r"f($\epsilon$)")
freq_limit = resolve_freq_max(XMAX_HZ, fs)
plt.xlim(-1000, freq_limit)

plt.tight_layout()

plt.savefig(OUT_PNG, dpi=150)
print(f"PNG saved to: {OUT_PNG}")
