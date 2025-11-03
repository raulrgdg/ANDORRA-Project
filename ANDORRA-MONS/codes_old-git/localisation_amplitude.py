import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Positions des capteurs en cm
sensor_coords = {
    'adc_17': (3, 3),
    'adc_23': (12, 3),
    'adc_15': (3, 12),
    'adc_21': (12, 12),
    'adc_19': (7.5, 7.5),  # centre
}

# Chargement du CSV
df = pd.read_csv("seance_tir_4/tir3_plaque1_maxwindow.csv")  # ou remplacer par ton DataFrame directement

# On isole les colonnes utiles
adc_columns = list(sensor_coords.keys())
timestamps = df["time_s"].values
signals = df[adc_columns].values

# On remplace les valeurs manquantes par 0
signals = np.nan_to_num(signals)

# Trouver l'indice de l'impact basé sur l’amplitude maximale globale
impact_index = np.unravel_index(np.argmax(signals), signals.shape)[0]

# Définir une fenêtre autour du pic (ex: 5 échantillons avant/après)
window_before = 5
window_after = 10
start = max(0, impact_index - window_before)
end = min(len(df), impact_index + window_after)

# Extraire les signaux dans la fenêtre
window_signals = signals[start:end]

# Trouver les amplitudes maximales par capteur dans cette fenêtre
max_amplitudes = np.max(window_signals, axis=0)

# Convertir les coordonnées en array
sensor_positions = np.array([sensor_coords[ch] for ch in adc_columns])  # shape: (n_sensors, 2)

# Normalisation des amplitudes pour pondération
norm_amplitudes = max_amplitudes / (np.sum(max_amplitudes) + 1e-8)  # évite div by 0

# Localisation par interpolation pondérée
estimated_position = np.sum(sensor_positions * norm_amplitudes[:, np.newaxis], axis=0)

print(f"Position estimée par amplitude maximale : {estimated_position}")

# Affichage
plt.figure(figsize=(6,6))
plt.scatter(*sensor_positions.T, c='blue', label="Capteurs")
plt.scatter(*estimated_position, c='red', label="Impact estimé", marker='x', s=100)
plt.title("Localisation par interpolation d'amplitude")
for label, pos in zip(adc_columns, sensor_positions):
    plt.text(pos[0]+0.2, pos[1]+0.2, label, fontsize=9)
plt.legend()
plt.grid()
plt.axis("equal")
plt.show()
