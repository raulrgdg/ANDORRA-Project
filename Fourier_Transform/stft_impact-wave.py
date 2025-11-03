# -- using venv: source /Users/raulrodriguez/Desktop/ANDORRAV2/venv/bin/activate --
# Code designed to compute the STFT of a given signal.
# Raúl Rodríguez || October 2025

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import stft, get_window

# =========================
# Configuration
# =========================
data = "hit10"
BIN_PATH = Path(f"/Users/raulrodriguez/Desktop/ANDORRAV2/Hammer/second-test_hammer/{data}.bin")

CHANNEL_INDEX = 0          # 0-4, choose which ADC is plotted. Now: channel 0 = Pin 15
XMAX_HZ = 0.5           # None -> full positive spectrum. 0-1 -> fraction of Nyquist. >1 -> absolute Hz cap
TIME_PLOT_SECONDS = None   # None -> full time trace
DETREND = True             # Remove global DC before STFT
OUT_PNG = Path(f"/Users/raulrodriguez/Desktop/ANDORRAV2/raul/fft/fft-hammer_second-session/stft_{data}.png")

NUM_CHANNELS_BIN = 6       # 5 ADC + 1 timestamp
PINS = [15, 17, 19, 21, 23]

# ---- STFT parameters (tune here) ----
WINDOW_SEC = 1e-3          # window length in seconds (e.g., 5 ms) --- ↓ si necesitas ver mejor el inicio del impacto (más resolución temporal). ↑ si necesitas distinguir frecuencias cercanas (más resolución en frecuencia).
OVERLAP = 0.75             # 75% overlap (0.5–0.875 habitual)
WINDOW_TYPE = "hann"       # 'hann' is a solid default for transients
BOUNDARY = None            # do not extend signal at edges
PADDED = False             # do not zero-pad the signal before STFT
DB_RANGE = 80.0            # dynamic range for spectrogram (dB) relative to vmax (p99)

# =========================
# Helpers
# =========================
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

def next_pow2(n):
    return 1 if n <= 1 else 2**int(np.ceil(np.log2(n)))

# =========================
# Load and prepare
# =========================
t, adc = load_bin(BIN_PATH)
fs = estimate_fs(t)
print(f"fs ≈ {fs:.3f} Hz")

CHANNEL_INDEX = int(np.clip(CHANNEL_INDEX, 0, adc.shape[1]-1))
y = adc[:, CHANNEL_INDEX].astype(np.float64)
label = f"ADC Pin {PINS[CHANNEL_INDEX]}" if CHANNEL_INDEX < len(PINS) else f"Channel {CHANNEL_INDEX}"

# Optional time cropping for plotting
if TIME_PLOT_SECONDS is not None:
    n_plot = int(min(len(y), max(1, TIME_PLOT_SECONDS * fs)))
    t_plot = t[:n_plot]
    y_plot = y[:n_plot]
else:
    t_plot = t
    y_plot = y

# Global detrend (remove DC)
if DETREND:
    y = y - np.mean(y)

# =========================
# STFT configuration derived from fs
# =========================
nperseg = max(16, int(round(WINDOW_SEC * fs)))  # lower-bound to be safe
nperseg = int(nperseg)

# avoid pathological tiny/huge windows
nperseg = int(np.clip(nperseg, 16, 131072))

noverlap = int(np.clip(int(OVERLAP * nperseg), 0, nperseg - 1))

# nfft = next power of two >= nperseg
nfft = next_pow2(nperseg)

# Create window
window = get_window(WINDOW_TYPE, nperseg, fftbins=True)

# =========================
# STFT compute
# =========================
# detrend='constant' removes local offset in each window; boundary/padded disabled to reflect true transient
f, tt, Zxx = stft(
    y,
    fs=fs,
    window=window,
    nperseg=nperseg,
    noverlap=noverlap,
    nfft=nfft,
    detrend='constant',
    return_onesided=True,
    boundary=BOUNDARY,
    padded=PADDED,
    axis=-1
)

# Magnitude (linear) -> dB
eps = np.finfo(float).eps
S_mag = np.abs(Zxx)
S_db = 20.0 * np.log10(S_mag + eps)

# Dynamic range for display
vmax = np.percentile(S_db, 99.0)
vmin = vmax - DB_RANGE

# Frequency limit
freq_limit = resolve_freq_max(XMAX_HZ, fs)

# =========================
# Plot
# =========================
plt.figure(figsize=(12, 6))

# (1) Time trace
plt.subplot(1, 2, 1)
plt.plot(t_plot, y_plot)
plt.title(f"ADC signal — {label}")
plt.xlabel("Time [s]")
plt.ylabel("ADC")

# (2) Spectrogram (STFT)
plt.subplot(1, 2, 2)
# pcolormesh expects edges; shading='gouraud' suaviza la rejilla
mesh = plt.pcolormesh(tt, f, S_db, shading='gouraud', vmin=vmin, vmax=vmax)
plt.title(f"Spectrogram (STFT) — {label}\nwindow={WINDOW_TYPE}, nperseg={nperseg}, overlap={int(100*OVERLAP)}%")
plt.xlabel("Time [s]")
plt.ylabel("Frequency [Hz]")
plt.ylim(0, freq_limit)
cbar = plt.colorbar(mesh)
cbar.set_label("Magnitude [dB]")

plt.tight_layout()
OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUT_PNG, dpi=150)
print(f"PNG saved to: {OUT_PNG}")
