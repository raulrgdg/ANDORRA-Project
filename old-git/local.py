import pandas as pd
import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt
from io import StringIO

# Données brutes fournies par l'utilisateur
data_string = """time_s,adc_23,adc_21,adc_19,adc_17,adc_15
31.500179767608643,12,11,11,11,10
31.50027322769165,12,11,11,11,10
31.500362396240234,12,11,11,11,11
31.50045585632324,12,11,19,26,77
31.500545740127563,7,10,191,128,6
31.50064849853516,60,28,37,47,48
31.50073456764221,52,10,61,17,12
31.500812292099,5,12,27,28,5
31.500905752182007,27,36,11,8,36
31.500998735427856,18,30,7,20,32
31.501098155975345,110,16,401,9,18
31.50118088722229,50,0,220,7,18
31.50127601623535,40,5,13,11,10
31.5013644695282,1,60,45,20,26
31.50145125389099,17,8,9,34,13
31.501546144485477,15,12,42,9,11
31.50164008140564,28,7,4,51,12
31.501733779907227,34,19,3,10,11
31.5018253326416,15,12,0,116,14
31.50191116333008,12,18,4,11,15
31.50202417373657,37,71,24,11,10
31.50209856033325,20,12,13,22,22
31.50218152999878,10,7,32,8,28
31.502269506454468,39,7,6,15,5
31.502368450164795,0,10,10,21,13
31.502458810806274,64,23,14,15,9
31.50253915786743,7,8,7,18,7
31.502643823623657,73,19,13,8,10
31.50272965431213,9,8,21,17,9
31.50281310081482,5,11,9,8,9
31.50291156768799,14,11,9,13,9
31.50301480293274,7,28,40,0,16
31.503090620040894,23,9,9,9,47
31.503181219100952,9,16,7,6,10
31.50328063964844,10,1,15,11,11
31.50337171554565,31,15,14,9,10
31.50346612930298,13,13,14,14,10
31.503555059432983,10,9,10,15,12
31.5036416053772,11,8,13,3,11
31.50374126434326,8,10,16,11,12
31.503828763961792,13,11,11,11,9
31.50390911102295,9,9,5,13,9
31.50402021408081,14,13,10,4,10
"""
df = pd.read_csv('seance_tir_4/tir2_plaque1_maxwindow.csv')

# Positions des capteurs en cm
sensor_positions = {
    'adc_17': (3, 3),
    'adc_23': (12, 3),
    'adc_15': (3, 12),
    'adc_21': (12, 12),
    'adc_19': (7.5, 7.5),  # centre
}

# Vitesse de propagation estimée (en m/s)
# C'est une valeur critique, à ajuster selon ta plaque.
wave_speed = 3200 # m/s (valeur typique pour l'onde de cisaillement dans l'acier)

# --- Détection des temps d'arrivée ---
arrival_times = {}
# Nombre de points pour estimer le bruit de fond au début
noise_estimation_window_points = 3
# Multiplicateur pour le seuil (le signal doit dépasser noise_std * threshold_multiplier)
threshold_multiplier = 5

plt.figure(figsize=(12, 8))

for i, sensor in enumerate(sensor_positions):
    signal = df[sensor].values
    time_s = df['time_s'].values

    # Estimer le niveau de bruit de fond
    noise_segment = signal[:noise_estimation_window_points]
    noise_mean = np.mean(noise_segment)
    noise_std = np.std(noise_segment)

    # Définir le seuil d'arrivée
    arrival_threshold = noise_mean + threshold_multiplier * noise_std
    if arrival_threshold < np.max(signal) * 0.1:
        arrival_threshold = np.max(signal) * 0.1

    # Trouver le premier point où le signal dépasse le seuil
    first_arrival_idx = np.where(signal > arrival_threshold)[0]

    if len(first_arrival_idx) > 0:
        arrival_times[sensor] = time_s[first_arrival_idx[0]]
        print(f"Capteur {sensor}: Temps d'arrivée détecté à {arrival_times[sensor]:.6f} s (valeur ADC: {signal[first_arrival_idx[0]]}, Seuil: {arrival_threshold:.2f})")

        # Pour visualisation
        color = plt.colormaps['tab10'](i) # Utilisation correcte de colormaps
        plt.plot(time_s, signal, label=f'Signal {sensor}', color=color)
        plt.axhline(y=arrival_threshold, color=color, linestyle='--', alpha=0.7)
        plt.plot(arrival_times[sensor], signal[first_arrival_idx[0]], 'o', color=color, markersize=8, label=f'ToA {sensor}')
    else:
        print(f"ATTENTION: Aucun temps d'arrivée détecté pour le capteur {sensor} avec le seuil {arrival_threshold:.2f}.")

plt.title('Détection des Temps d\'Arrivée (ToA) par seuil')
plt.xlabel('Temps (s)')
plt.ylabel('Valeur ADC')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# --- Localisation de l'impact par TDoA ---

if len(arrival_times) < 3: # Il faut au moins 3 capteurs pour trianguler, idéalement 4 ou 5
    print("Pas assez de temps d'arrivée détectés pour procéder à la localisation.")
else:
    # On utilise le capteur 'adc_19' (centre) comme référence
    ref_sensor = 'adc_19'
    if ref_sensor not in arrival_times:
        print(f"Le capteur de référence '{ref_sensor}' n'a pas détecté d'arrivée. Choisir un autre capteur de référence.")
        # Fallback pour choisir le premier capteur disponible comme référence
        ref_sensor = next(iter(arrival_times))
        print(f"Utilisation de '{ref_sensor}' comme capteur de référence.")

    ref_time = arrival_times[ref_sensor]
    tdoa = {sensor: arrival_times[sensor] - ref_time for sensor in arrival_times if sensor != ref_sensor}

    print("\nTemps d'arrivée (ToA) pour chaque capteur:")
    for sensor, time in arrival_times.items():
        print(f"  {sensor}: {time:.6f} s")

    print("\nDifférences de temps d'arrivée (TDoA) par rapport à", ref_sensor)
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
            expected_dt = (dist_curr - dist_ref) / (speed * 100) # cm -> m
            losses.append((expected_dt - dt_measured)**2)
        return np.sum(losses)

    # Optimisation de la position de l'impact
    res = minimize(
        loss_fn,
        x0=np.array([7.5, 7.5]),
        args=(tdoa, sensor_positions, wave_speed, ref_sensor),
        bounds=[(0, 15), (0, 15)]
    )
    impact_location = res.x

    print(f"\nLocalisation estimée de l'impact : X={impact_location[0]:.2f} cm, Y={impact_location[1]:.2f} cm")
    print(f"Méthode d'optimisation : {res.message}")
    if not res.success:
        print("Avertissement: L'optimisation n'a pas convergé correctement. La solution pourrait ne pas être optimale.")

    # --- Affichage graphique des résultats ---
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
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()