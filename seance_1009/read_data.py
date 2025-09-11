import numpy as np
import matplotlib.pyplot as plt
import os

# Paramètres
binary_path = 'data_1546300840.bin'
CHANNELS = ['adc_15', 'adc_17', 'adc_19', 'adc_21', 'adc_23']
NUM_CHANNELS = 6  # 5 ADCs + 1 timestamp

# Choisir le canal à afficher (0-4 pour les 5 canaux ADC)
SELECTED_CHANNEL = 0  # Changez ce numéro selon le canal connecté (0=adc_15, 1=adc_17, 2=adc_19, 3=adc_21, 4=adc_23)


# Lire le fichier binaire
data = np.fromfile(binary_path, dtype=np.int32)

# Vérification que la taille est bien multiple de NUM_CHANNELS
assert data.size % NUM_CHANNELS == 0, f"Le fichier binaire a une taille incorrecte ({data.size} entiers)."

# Reshape en lignes de 6 colonnes
data = data.reshape(-1, NUM_CHANNELS)

print(data)

# save data in csv
np.savetxt('data.csv', data, delimiter=',')

# Séparer les colonnes
adc_data = data[:, :5]
timestamps = data[:, 5]  # en microsecondes

# Convertir les timestamps en secondes
time_s = timestamps * 1e-6

print(adc_data)
print(timestamps)
print(time_s)

# Plot - seulement le canal sélectionné
pins = [15, 17, 19, 21, 23]
plt.figure(figsize=(10, 6))
plt.plot(time_s, adc_data[:, SELECTED_CHANNEL])
plt.title(f"ADC Pin {pins[SELECTED_CHANNEL]} - Canal {SELECTED_CHANNEL}")
plt.xlabel('Temps (s)')
plt.ylabel("Valeur ADC")
plt.grid(True)
plt.tight_layout()
plt.show()




# timestamps est un array 1D avec les timestamps en microsecondes
time_s = timestamps / 1e6  # conversion µs → s
delta_t = np.diff(time_s)

# fréquence instantanée par intervalle
frequencies = 1 / delta_t

# moyenne globale
mean_freq = np.mean(frequencies)

print(f"Fréquence d'échantillonnage moyenne : {mean_freq:.2f} Hz")

# Optionnel : visualiser la fréquence instantanée
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 4))
plt.plot(frequencies)
plt.title("Fréquence d'échantillonnage instantanée")
plt.xlabel("Échantillon")
plt.ylabel("Fréquence (Hz)")
plt.grid(True)
plt.tight_layout()
plt.show()
