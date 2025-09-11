import numpy as np
import matplotlib.pyplot as plt
import os
from scipy.optimize import minimize
import pandas as pd # Utilisé pour la moyenne glissante, bien que numpy puisse le faire aussi

# --- Paramètres de l'acquisition des données binaires ---
binary_path = 'data_1752195397.bin' # Assurez-vous que ce fichier est dans le même répertoire
NUM_ADC_CHANNELS = 5 # Le nombre de canaux ADC lus (adc_23, adc_21, adc_19, adc_17, adc_15)
NUM_TOTAL_COLUMNS = 6 # 5 ADCs + 1 timestamp
# Mappage des indices des colonnes ADC aux noms des capteurs
# Basé sur l'ordre de votre script de lecture binaire
ADC_CHANNEL_MAP = {
    0: 'adc_23',
    1: 'adc_21',
    2: 'adc_19', # Ce capteur central sera ignoré pour la localisation
    3: 'adc_17',
    4: 'adc_15',
}

# --- Positions des capteurs sur la plaque (en cm) ---
# Nous utilisons uniquement les 4 capteurs de coin pour la localisation
sensor_positions = {
    'adc_17': (3, 3),   # Bas-gauche
    'adc_23': (12, 3),  # Bas-droite
    'adc_15': (3, 12),  # Haut-gauche
    'adc_21': (12, 12), # Haut-droite
}

# --- Paramètres de l'algorithme de localisation ---
# Vitesse de propagation estimée (en m/s)
# C'est une valeur CRITIQUE. Ajustez-la précisément par calibration expérimentale.
# Pour l'acier, elle peut varier de 3000 à 6000 m/s selon le type d'onde.
wave_speed = 3200 # m/s (valeur typique pour l'onde de cisaillement dans l'acier)

# Paramètres pour la détection du Temps d'Arrivée (ToA)
# Fenêtre pour l'estimation du bruit de fond (nombre de points au début du signal)
noise_estimation_window_points = 50 # Augmenté pour une meilleure estimation avec plus de données
# Multiplicateur pour le seuil (le signal doit dépasser noise_std * threshold_multiplier)
threshold_multiplier = 5 # A ajuster si trop de faux positifs/négatifs
# Taille de la fenêtre pour la moyenne glissante (nombre de points)
moving_average_window = 10 # A ajuster pour lisser le signal sans trop le déformer

# --- 1. Lecture et préparation des données binaires ---
print(f"Lecture du fichier binaire : {binary_path}")
try:
    data = np.fromfile(binary_path, dtype=np.int32)
except FileNotFoundError:
    print(f"ERREUR : Le fichier '{binary_path}' n'a pas été trouvé. Veuillez vérifier le chemin.")
    exit()

# Vérification que la taille est bien multiple de NUM_TOTAL_COLUMNS
if data.size % NUM_TOTAL_COLUMNS != 0:
    print(f"ERREUR : Le fichier binaire a une taille incorrecte ({data.size} entiers). "
          f"Elle devrait être un multiple de {NUM_TOTAL_COLUMNS}.")
    exit()

# Reshape en lignes de NUM_TOTAL_COLUMNS
data_reshaped = data.reshape(-1, NUM_TOTAL_COLUMNS)

# Séparer les colonnes ADC et les timestamps
adc_data_raw = data_reshaped[:, :NUM_ADC_CHANNELS]
timestamps_us = data_reshaped[:, NUM_ADC_CHANNELS] # en microsecondes

# Convertir les timestamps en secondes
time_s = timestamps_us * 1e-6

print(f"Données lues : {adc_data_raw.shape[0]} échantillons.")
print(f"Fréquence d'échantillonnage moyenne : {np.mean(1/np.diff(time_s)):.2f} Hz")

# --- 2. Détection des Temps d'Arrivée (ToA) pour chaque capteur ---
arrival_times = {}
plt.figure(figsize=(14, 10)) # Figure plus grande pour la visualisation des signaux

for i, adc_col_name in ADC_CHANNEL_MAP.items():
    # Nous ignorons le capteur central 'adc_19' pour la localisation
    if adc_col_name not in sensor_positions:
        print(f"Ignorance du capteur {adc_col_name} (non utilisé pour la localisation des 4 coins).")
        continue

    signal_raw = adc_data_raw[:, i]

    # Appliquer une moyenne glissante pour lisser le signal
    # Utilisation de pd.Series.rolling pour faciliter le calcul de la moyenne glissante
    signal_smoothed = pd.Series(signal_raw).rolling(window=moving_average_window, min_periods=1, center=False).mean().values

    # Estimer le niveau de bruit de fond sur le signal BRUT (pour ne pas sous-estimer le bruit)
    noise_segment = signal_raw[:noise_estimation_window_points]
    noise_mean = np.mean(noise_segment)
    noise_std = np.std(noise_segment)

    # Définir le seuil d'arrivée sur le signal LISSÉ
    # Le seuil est la moyenne du bruit plus un multiple de son écart-type
    arrival_threshold = noise_mean + threshold_multiplier * noise_std

    # S'assurer que le seuil n'est pas trop bas si le bruit est quasi nul ou si le signal est très faible
    # On garantit un seuil minimum basé sur une fraction du pic max du signal lissé
    min_threshold_from_max = np.max(signal_smoothed) * 0.05 # Au moins 5% du max du signal lissé
    if arrival_threshold < min_threshold_from_max:
        arrival_threshold = min_threshold_from_max

    # Trouver le premier point où le signal LISSÉ dépasse le seuil
    first_arrival_idx = np.where(signal_smoothed > arrival_threshold)[0]

    if len(first_arrival_idx) > 0:
        toa_idx = first_arrival_idx[0]
        arrival_times[adc_col_name] = time_s[toa_idx]
        print(f"Capteur {adc_col_name}: Temps d'arrivée détecté à {arrival_times[adc_col_name]:.6f} s "
              f"(valeur ADC lissée: {signal_smoothed[toa_idx]:.2f}, Seuil: {arrival_threshold:.2f})")

        # Pour visualisation
        color = plt.colormaps['tab10'](list(sensor_positions.keys()).index(adc_col_name) % 10) # Assurer une couleur unique
        plt.plot(time_s, signal_raw, label=f'Signal brut {adc_col_name}', alpha=0.5, color=color)
        plt.plot(time_s, signal_smoothed, label=f'Signal lissé {adc_col_name} (MA={moving_average_window})', color=color, linestyle='--')
        plt.axhline(y=arrival_threshold, color=color, linestyle=':', alpha=0.7)
        plt.plot(arrival_times[adc_col_name], signal_smoothed[toa_idx], 'o', color='red', markersize=8, label=f'ToA {adc_col_name}')
    else:
        print(f"ATTENTION: Aucun temps d'arrivée détecté pour le capteur {adc_col_name} avec le seuil {arrival_threshold:.2f}.")

plt.title('Détection des Temps d\'Arrivée (ToA) par seuil sur signal lissé')
plt.xlabel('Temps (s)')
plt.ylabel('Valeur ADC')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# --- 3. Localisation de l'impact par TDoA ---

if len(arrival_times) < 3: # Il faut au moins 3 capteurs pour trianguler
    print("Pas assez de temps d'arrivée détectés pour procéder à la localisation (minimum 3 capteurs requis).")
else:
    # Choisir le capteur de référence comme celui avec le temps d'arrivée le plus précoce
    ref_sensor = min(arrival_times, key=arrival_times.get)
    ref_time = arrival_times[ref_sensor]

    tdoa = {sensor: arrival_times[sensor] - ref_time for sensor in arrival_times if sensor != ref_sensor}

    print("\nTemps d'arrivée (ToA) pour chaque capteur:")
    for sensor, time in arrival_times.items():
        print(f"  {sensor}: {time:.6f} s")

    print(f"\nDifférences de temps d'arrivée (TDoA) par rapport à {ref_sensor}:")
    for sensor, dt in tdoa.items():
        print(f"  {sensor} - {ref_sensor}: {dt*1e6:.2f} µs")

    # Fonction de perte à minimiser (erreur entre TDoA mesuré et TDoA théorique)
    def loss_fn(impact_coords, tdoa_data, sensor_pos_map, speed, reference_sensor_name):
        losses = []
        p_ref = np.array(sensor_pos_map[reference_sensor_name])
        for sensor_name, dt_measured in tdoa_data.items():
            p_curr = np.array(sensor_pos_map[sensor_name])
            # Calcul de la distance euclidienne de l'impact aux capteurs
            dist_curr = np.linalg.norm(impact_coords - p_curr)
            dist_ref = np.linalg.norm(impact_coords - p_ref)
            # TDoA théorique (en secondes)
            # Les positions sont en cm, la vitesse en m/s. On convertit les distances en mètres.
            expected_dt = (dist_curr - dist_ref) / (speed * 100) # (cm / (m/s * 100 cm/m)) = s
            losses.append((expected_dt - dt_measured)**2)
        return np.sum(losses)

    # Optimisation de la position de l'impact
    # Les bornes sont importantes pour maintenir la solution dans les limites de la plaque.
    res = minimize(
        loss_fn,
        x0=np.array([7.5, 7.5]), # Centre de la plaque de 15x15 cm
        args=(tdoa, sensor_positions, wave_speed, ref_sensor),
        bounds=[(0, 15), (0, 15)] # La plaque est de 15cm x 15cm
    )
    impact_location = res.x

    print(f"\nLocalisation estimée de l'impact : X={impact_location[0]:.2f} cm, Y={impact_location[1]:.2f} cm")
    print(f"Méthode d'optimisation : {res.message}")
    if not res.success:
        print("Avertissement: L'optimisation n'a pas convergé correctement. La solution pourrait ne pas être optimale.")

    # --- 4. Affichage graphique des résultats ---
    fig, ax = plt.subplots(figsize=(7, 7))
    for name, pos in sensor_positions.items():
        ax.plot(*pos, 'o', markersize=10, label=f'Capteur {name}', alpha=0.8)
        ax.text(pos[0]+0.3, pos[1], name, fontsize=9)

    ax.plot(*impact_location, 'rX', markersize=15, markeredgewidth=2, label='Impact estimé')
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 15)
    ax.set_title(f'Localisation de l\'Impact par TDoA (Vitesse = {wave_speed} m/s)')
    ax.set_xlabel('Position X (cm)')
    ax.set_ylabel('Position Y (cm)')
    ax.set_aspect('equal', adjustable='box') # Assure que les axes ont la même échelle
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()
