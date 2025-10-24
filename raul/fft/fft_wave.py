#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# ===== AJUSTA ESTO =====
data='shoot20_9mm'
BIN_PATH = Path(f"/Users/raulrodriguez/Work-Station/ANDORRAV2/seance_tir_8/{data}.bin")
CHANNEL_INDEX = 0          # 0..4 para elegir cuál ADC graficar
XMAX_HZ = None            # None para no recortar eje X del espectro
TIME_PLOT_SECONDS = 0.02   # None para toda la señal en el gráfico temporal (p.ej. 0.02 = 20 ms)
DETREND = True             # quitar media DC antes de FFT
SAVE_PNG = True
OUT_PNG = Path(f"fft_{data}.png")
SHOW_PLOT = True
# =======================

NUM_CHANNELS_BIN = 6             # 5 ADC + 1 timestamp
PINS = [15, 17, 19, 21, 23]      # etiquetas para los canales

def load_bin(path: Path):
    """Carga [adc_15, adc_17, adc_19, adc_21, adc_23, timestamp_us] en int32."""
    data = np.fromfile(path, dtype=np.int32)
    if data.size % NUM_CHANNELS_BIN != 0:
        raise ValueError(f"Tamaño {data.size} no múltiplo de {NUM_CHANNELS_BIN}")
    data = data.reshape(-1, NUM_CHANNELS_BIN)
    adc = data[:, :5]                      # (N,5)
    t_us = data[:, 5].astype(np.float64)   # (N,)
    t_s = t_us * 1e-6
    return t_s, adc

def estimate_fs(time_s: np.ndarray) -> float:
    """Frecuencia de muestreo usando la mediana del paso temporal."""
    dt = np.median(np.diff(time_s))
    if dt <= 0 or not np.isfinite(dt):
        raise ValueError("time_s inválido para estimar fs.")
    return 1.0 / dt

# ============= CÓDIGO DIRECTO, SIN main() =============

# 1) Leer datos y estimar fs
t, adc = load_bin(BIN_PATH)
fs = estimate_fs(t)
print(f"fs ≈ {fs:.3f} Hz")

# 2) Seleccionar canal
CHANNEL_INDEX = int(np.clip(CHANNEL_INDEX, 0, adc.shape[1]-1))
y = adc[:, CHANNEL_INDEX].astype(np.float64)
label = f"ADC Pin {PINS[CHANNEL_INDEX]}" if CHANNEL_INDEX < len(PINS) else f"Canal {CHANNEL_INDEX}"

# 3) (Opcional) recorte temporal para el gráfico en el tiempo
if TIME_PLOT_SECONDS is not None:
    n_plot = int(min(len(y), max(1, TIME_PLOT_SECONDS * fs)))
    t_plot = t[:n_plot]
    y_plot = y[:n_plot]
else:
    t_plot = t
    y_plot = y

# 4) Preprocesado simple
if DETREND:
    y = y - np.mean(y)

# 5) FFT (mitad positiva) con normalización por N
N = len(y)
Y = np.fft.rfft(y, n=N)
freqs = np.fft.rfftfreq(N, d=1.0/fs)
magnitude = np.abs(Y) / N  # magnitud lineal sencilla

# 6) Graficar: señal temporal + espectro
plt.figure(figsize=(12, 5))

# Señal en el tiempo
plt.subplot(1, 2, 1)
plt.plot(t_plot, y_plot)
plt.title(f"Señal en el tiempo — {label}")
plt.xlabel("Tiempo [s]")
plt.ylabel("Amplitud")

# Espectro (FFT)
plt.subplot(1, 2, 2)
plt.plot(freqs, magnitude)
plt.title(f"Espectro de Frecuencias (FFT) — {label}")
plt.xlabel("Frecuencia [Hz]")
plt.ylabel("Magnitud")
if XMAX_HZ is not None:
    plt.xlim(0, float(XMAX_HZ))

plt.tight_layout()

if SAVE_PNG:
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_PNG, dpi=150)
    print(f"PNG guardado en: {OUT_PNG}")

if SHOW_PLOT:
    plt.show()
else:
    plt.close()
