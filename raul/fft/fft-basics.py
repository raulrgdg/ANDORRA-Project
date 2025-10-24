import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq

# --- Parámetros ---
fs = 5  # frecuencia de muestreo en Hz
T = 20   # duración de la señal en segundos
t = np.linspace(0, T, int(fs*T), endpoint=False)

# --- Señal: mezcla de dos senoidales ---
y = np.sin(2 * np.pi *t) 

# --- FFT ---
N = len(y)
Y = fft(y)
freqs = fftfreq(N, 1/fs)

# --- Magnitud normalizada ---
magnitude = np.abs(Y) / N

# --- Solo mitad positiva del espectro ---
idx = np.where(freqs >= 0)
freqs = freqs[idx]
magnitude = magnitude[idx]

# --- Graficar señal temporal ---
plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.plot(t, y)
plt.title("Señal en el tiempo")
plt.xlabel("Tiempo [s]")
plt.ylabel("Amplitud")

# --- Graficar espectro FFT ---
plt.subplot(1, 2, 2)
plt.plot(freqs, magnitude)
plt.title("Espectro de Frecuencias (FFT)")
plt.xlabel("Frecuencia [Hz]")
plt.ylabel("Magnitud")
  # limitar el eje X para ver mejor los picos

plt.tight_layout()
plt.show()
