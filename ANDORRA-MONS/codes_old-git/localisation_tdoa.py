import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from scipy.optimize import minimize
import matplotlib.pyplot as plt

# Charger les données depuis un CSV (remplace "data.csv" par ton vrai fichier)
df = pd.read_csv("seance_tir_4/tir3_plaque1_maxwindow.csv")

# Positions des capteurs en cm
sensor_positions = {
    'adc_17': (3, 3),
    'adc_23': (12, 3),
    'adc_15': (3, 12),
    'adc_21': (12, 12),
    'adc_19': (7.5, 7.5),  # centre
}

# Détection des premiers pics pour chaque capteur
peak_times = {}
for sensor in sensor_positions:
    signal = df[sensor].values
    peaks, _ = find_peaks(signal, height=np.max(signal)*0.05)
    if len(peaks) > 0:
        peak_times[sensor] = df['time_s'].iloc[peaks[0]]

# Calcul des différences de temps d'arrivée (TDoA) par rapport au capteur central
ref_sensor = 'adc_19'
ref_time = peak_times[ref_sensor]
tdoa = {sensor: peak_times[sensor] - ref_time for sensor in peak_times if sensor != ref_sensor}

# Vitesse de propagation estimée (en m/s)
wave_speed = 2000  # à ajuster selon ta plaque

# Fonction de perte à minimiser
def loss_fn(x, tdoa, sensor_positions, wave_speed):
    losses = []
    for sensor, dt in tdoa.items():
        p1 = np.array(sensor_positions[sensor])
        p0 = np.array(sensor_positions[ref_sensor])
        expected_dt = (np.linalg.norm(x - p1) - np.linalg.norm(x - p0)) / (wave_speed * 0.01)  # cm -> m
        losses.append((expected_dt - dt)**2)
    return np.sum(losses)

# Optimisation de la position de l'impact
res = minimize(
    loss_fn,
    x0=np.array([7.5, 7.5]),
    args=(tdoa, sensor_positions, wave_speed),
    bounds=[(0, 15), (0, 15)]
)
impact_location = res.x

# Affichage
fig, ax = plt.subplots(figsize=(6, 6))
for name, pos in sensor_positions.items():
    ax.plot(*pos, 'bo')
    ax.text(pos[0]+0.2, pos[1], name)

ax.plot(*impact_location, 'rx', markersize=12, label='Impact estimé')
ax.set_xlim(0, 15)
ax.set_ylim(0, 15)
ax.set_title('Localisation estimée par TDoA')
ax.set_xlabel('X (cm)')
ax.set_ylabel('Y (cm)')
ax.grid(True)
ax.legend()
plt.tight_layout()
plt.show()
