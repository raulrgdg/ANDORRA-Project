import struct
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter
from scipy.optimize import least_squares

# --- Code pour le chargement des données et la détection T0 (copié du code précédent) ---
# Constantes (doivent correspondre au code Arduino)
COL_COUNT = 6  # 5 broches ADC + 1 horodatage
ELEMENT_SIZE = 4  # sizeof(int)

# Chargement du fichier binaire
file_path = "data_1752195406.bin"
try:
    with open(file_path, "rb") as f:
        data_bytes = f.read()

    num_elements = len(data_bytes) // ELEMENT_SIZE
    num_rows = num_elements // COL_COUNT
    trimmed_size = num_rows * COL_COUNT * ELEMENT_SIZE
    data_bytes = data_bytes[:trimmed_size]

    data = struct.unpack("<" + "i" * (num_rows * COL_COUNT), data_bytes)
    data = np.array(data).reshape((num_rows, COL_COUNT))

    timestamps = data[:, -1]  # Dernière colonne est micros()
    adc_values = data[:, :-1]  # Toutes les colonnes sauf la dernière

    time_s = (timestamps - timestamps[0]) / 1e6

    # Calcul de la fréquence d'échantillonnage réelle
    avg_sampling_period_us = np.mean(timestamps[1:] - timestamps[:-1])
    FS = 1e6 / avg_sampling_period_us # Fréquence d'échantillonnage en Hz

except FileNotFoundError:
    print(f"Erreur : Le fichier '{file_path}' n'a pas été trouvé.")
    print("Veuillez vous assurer que 'data_1752195397.bin' est dans le même répertoire que le script.")
    exit()
except Exception as e:
    print(f"Une erreur est survenue lors du chargement ou du traitement des données : {e}")
    exit()

print(f"Fréquence d'échantillonnage (FS) détectée : {FS:.2f} Hz")

# --- Paramètres de détection d'impact (à ajuster si besoin) ---
STA_WINDOW_LENGTH_S = 0.0005 # 2 ms
LTA_WINDOW_LENGTH_S = 0.005 # 15 ms
STA_LTA_THRESHOLD = 1.8 # Seuil pour le ratio STA/LTA

# Conversion des longueurs de fenêtres en nombre d'échantillons
STA_WINDOW_SAMPLES = int(STA_WINDOW_LENGTH_S * FS)
LTA_WINDOW_SAMPLES = int(LTA_WINDOW_LENGTH_S * FS)
STA_WINDOW_SAMPLES = max(1, STA_WINDOW_SAMPLES)
LTA_WINDOW_SAMPLES = max(1, LTA_WINDOW_SAMPLES)

# Paramètres pour l'affinage avec la dérivée (filtre de Savitzky-Golay)
SAVGOL_WINDOW_LENGTH = 31 # Doit être impair
SAVGOL_POLYORDER = 3
REFINEMENT_SEARCH_BACK_SAMPLES = int(0.001 * FS) # 1 ms en arrière
REFINEMENT_SEARCH_FORWARD_SAMPLES = int(0.0002 * FS) # 0.2 ms en avant
DERIVATIVE_THRESHOLD_FACTOR = 0.05 # Fraction de la dérivée max pour T0

# --- Fonctions d'aide (copiées) ---
def calculate_sta_lta(signal, sta_window, lta_window):
    signal = np.abs(signal).astype(float)
    sta = np.zeros_like(signal)
    lta = np.zeros_like(signal)
    for i in range(len(signal)):
        start_sta = max(0, i - sta_window + 1)
        sta[i] = np.mean(signal[start_sta : i + 1])
        start_lta = max(0, i - lta_window + 1)
        lta[i] = np.mean(signal[start_lta : i + 1])
    lta[lta == 0] = 1e-9
    sta_lta_ratio = sta / lta
    return sta_lta_ratio

def find_onset_sta_lta(sta_lta_ratio, threshold):
    for i in range(LTA_WINDOW_SAMPLES, len(sta_lta_ratio)):
        if sta_lta_ratio[i] > threshold:
            return i
    return -1

def refine_onset_derivative(signal, preliminary_onset_idx,
                            search_back_samples, search_forward_samples,
                            savgol_win_len, savgol_poly_order, deriv_threshold_factor):
    search_start_idx = max(0, preliminary_onset_idx - search_back_samples)
    search_end_idx = min(len(signal), preliminary_onset_idx + search_forward_samples)
    if search_start_idx >= search_end_idx:
        return preliminary_onset_idx

    segment = signal[search_start_idx : search_end_idx]
    if savgol_win_len % 2 == 0: savgol_win_len += 1
    if len(segment) < savgol_win_len:
        savgol_win_len = max(3, (len(segment) // 2) * 2 + 1)
        if savgol_win_len > len(segment):
             return preliminary_onset_idx

    try:
        smoothed_deriv = savgol_filter(segment, savgol_win_len, savgol_poly_order, deriv=1)
    except ValueError as e:
        print(f"Erreur du filtre Savitzky-Golay : {e}. Longueur segment : {len(segment)}, longueur fenêtre : {savgol_win_len}")
        return preliminary_onset_idx

    relative_prelim_idx = preliminary_onset_idx - search_start_idx
    search_range_for_peak = smoothed_deriv[ : min(len(smoothed_deriv), relative_prelim_idx + savgol_win_len // 2)]
    if len(search_range_for_peak) == 0:
        return preliminary_onset_idx

    max_deriv_in_range = np.max(search_range_for_peak)
    if max_deriv_in_range <= 0:
        return preliminary_onset_idx

    idx_max_deriv_in_segment = np.argmax(search_range_for_peak)
    deriv_threshold = max_deriv_in_range * deriv_threshold_factor

    onset_relative_idx = -1
    for i in range(idx_max_deriv_in_segment, -1, -1):
        if smoothed_deriv[i] < deriv_threshold:
            onset_relative_idx = i
            break

    if onset_relative_idx == -1:
        return preliminary_onset_idx

    refined_onset_idx = search_start_idx + onset_relative_idx
    return refined_onset_idx

# --- Boucle principale de détection pour obtenir detected_t0_times_s ---
detected_sta_lta_times_s = []
detected_t0_times_s = []

for i in range(adc_values.shape[1]):
    signal = adc_values[:, i]
    sta_lta_ratio = calculate_sta_lta(signal, STA_WINDOW_SAMPLES, LTA_WINDOW_SAMPLES)
    preliminary_onset_idx = find_onset_sta_lta(sta_lta_ratio, STA_LTA_THRESHOLD)

    if preliminary_onset_idx != -1:
        detected_sta_lta_times_s.append(time_s[preliminary_onset_idx])
        t0_idx = refine_onset_derivative(signal, preliminary_onset_idx,
                                         REFINEMENT_SEARCH_BACK_SAMPLES,
                                         REFINEMENT_SEARCH_FORWARD_SAMPLES,
                                         SAVGOL_WINDOW_LENGTH, SAVGOL_POLYORDER,
                                         DERIVATIVE_THRESHOLD_FACTOR)
        detected_t0_times_s.append(time_s[t0_idx])
    else:
        print(f"Aucun déclenchement STA/LTA détecté pour ADC {i} avec le seuil {STA_LTA_THRESHOLD}")
        detected_sta_lta_times_s.append(np.nan)
        detected_t0_times_s.append(np.nan)

print("\n--- Temps de début (Onset) détectés ---")
for i in range(adc_values.shape[1]):
    if not np.isnan(detected_t0_times_s[i]):
        print(f"ADC {i}: T0 affiné à {detected_t0_times_s[i]:.6f}s")
    else:
        print(f"ADC {i}: T0 non détecté.")
# --- Affichage des résultats ---
plt.figure(figsize=(12, 7))
ax = plt.gca() # Récupère les axes actuels pour tracer des lignes verticales

for i in range(adc_values.shape[1]):
    plt.plot(time_s, adc_values[:, i], label=f"ADC {i}")

# Tracer les temps détectés par STA/LTA
for i, t_sta_lta in enumerate(detected_sta_lta_times_s):
    if not np.isnan(t_sta_lta):
        ax.axvline(t_sta_lta, color=f'C{i}', linestyle='--', linewidth=1.5,
                   label=f'ADC {i} STA/LTA ({t_sta_lta:.4f}s)')

# Tracer les temps T0 affinés
for i, t0 in enumerate(detected_t0_times_s):
    if not np.isnan(t0):
        ax.axvline(t0, color=f'C{i}', linestyle='-', linewidth=2,
                   label=f'ADC {i} T0 ({t0:.4f}s)')

plt.xlabel("Temps (s)")
plt.ylabel("Valeur ADC")
plt.title("Signaux ADC avec détections STA/LTA et T0 affinées")
plt.legend(loc='upper left', bbox_to_anchor=(1, 1)) # Légende à l'extérieur pour la clarté
plt.grid(True)
plt.tight_layout(rect=[0, 0, 0.85, 1]) # Ajuster la mise en page pour laisser de la place à la légende
plt.show()

# Afficher les temps détectés dans la console
print("\n--- Temps de début (Onset) détectés ---")
for i in range(adc_values.shape[1]):
    if not np.isnan(detected_sta_lta_times_s[i]):
        print(f"ADC {i}: STA/LTA à {detected_sta_lta_times_s[i]:.6f}s, T0 affiné à {detected_t0_times_s[i]:.6f}s")
    else:
        print(f"ADC {i}: Aucun début détecté.")

# --- Implémentation de la localisation TDOA ---

# Dimensions de la plaque en cm
PLATE_WIDTH = 15
PLATE_HEIGHT = 15

# Coordonnées des capteurs en cm, mappées aux indices ADC
# Modifie ces coordonnées si ton arrangement réel est différent.
SENSOR_COORDS_ALL = np.array([
    [3, 12],   # Correspond à ADC 0
    [12, 12],  # Correspond à ADC 1
    [3, 3],  # Correspond à ADC 2
    [12, 3], # Correspond à ADC 3
    # [0, 0]    # Placeholder pour ADC 4 (si non utilisé ou bruité, son T0 sera NaN)
])

# Définis ici la position réelle de l'impact pour la comparaison (en cm)
ACTUAL_IMPACT_X = 7.5 # Exemple : centre de la plaque
ACTUAL_IMPACT_Y = 7.5
ACTUAL_IMPACT_LOCATION = np.array([ACTUAL_IMPACT_X, ACTUAL_IMPACT_Y])

# Vitesse de propagation de l'onde dans le matériau de la plaque (en cm/s)
# C'est une valeur CRUCIALE. Ajuste-la en fonction de ton matériau ou de tes mesures expérimentales.
# Par exemple, 3000 m/s = 300000 cm/s
V_WAVE = 300000.0 # cm/s


# Filtrer les capteurs avec des T0s non détectés et préparer les données pour la TDOA
valid_sensor_indices = [i for i, t0 in enumerate(detected_t0_times_s) if not np.isnan(t0)]

if len(valid_sensor_indices) < 3:
    print("\nErreur : Moins de 3 capteurs ont un T0 détecté. La localisation TDOA nécessite au moins 3 capteurs.")
    estimated_impact_location = None
else:
    # Préparer les coordonnées des capteurs et les T0s pour les capteurs valides
    active_sensor_coords = SENSOR_COORDS_ALL[valid_sensor_indices]
    active_t0_s = np.array(detected_t0_times_s)[valid_sensor_indices]

    # Choisir un capteur de référence (celui avec le temps d'arrivée le plus précoce)
    reference_sensor_idx_in_active = np.argmin(active_t0_s)
    T0_ref = active_t0_s[reference_sensor_idx_in_active]
    X_ref, Y_ref = active_sensor_coords[reference_sensor_idx_in_active]

    print(f"\nCapteur de référence pour TDOA: ADC {valid_sensor_indices[reference_sensor_idx_in_active]} (T0={T0_ref:.6f}s)")
    print(f"Capteurs utilisés pour la localisation TDOA: {[f'ADC {idx}' for idx in valid_sensor_indices]}")

    # Fonction de résidus pour l'optimisation des moindres carrés
    # Nous cherchons (xp, yp) qui minimise cette fonction
    def tdoa_residuals(impact_location, sensor_coords, arrival_times, wave_speed, ref_t0, ref_x, ref_y):
        xp, yp = impact_location
        residuals = []
        for i in range(len(sensor_coords)):
            xi, yi = sensor_coords[i]
            ti = arrival_times[i]

            # Distance de l'impact estimé au capteur actuel
            dist_i = np.sqrt((xp - xi)**2 + (yp - yi)**2)
            # Distance de l'impact estimé au capteur de référence
            dist_ref = np.sqrt((xp - ref_x)**2 + (yp - ref_y)**2)

            # Équation TDOA : (dist_i - dist_ref) - V_WAVE * (ti - ref_t0) = 0
            # On veut que cette différence soit proche de zéro
            residuals.append((dist_i - dist_ref) - wave_speed * (ti - ref_t0))
        return np.array(residuals)

    # Deviner une position initiale pour le solveur (ex: centre de la plaque)
    initial_guess = np.array([PLATE_WIDTH / 2, PLATE_HEIGHT / 2])

    # Exécuter l'optimisation des moindres carrés
    # Les bornes permettent de maintenir la solution à l'intérieur de la plaque
    bounds = ([0, 0], [PLATE_WIDTH, PLATE_HEIGHT])
    result = least_squares(tdoa_residuals, initial_guess,
                           args=(active_sensor_coords, active_t0_s, V_WAVE, T0_ref, X_ref, Y_ref),
                           bounds=bounds, # Contraintes pour rester dans les limites de la plaque
                           ftol=1e-6, xtol=1e-6, gtol=1e-6) # Tolérances de convergence

    estimated_impact_location = result.x
    print(f"\nLocalisation de l'impact réelle : ({ACTUAL_IMPACT_X:.2f} cm, {ACTUAL_IMPACT_Y:.2f} cm)")
    print(f"Localisation de l'impact estimée : ({estimated_impact_location[0]:.2f} cm, {estimated_impact_location[1]:.2f} cm)")

    # Calcul de l'erreur de localisation
    localization_error = np.sqrt(np.sum((estimated_impact_location - ACTUAL_IMPACT_LOCATION)**2))
    print(f"Erreur de localisation : {localization_error:.2f} cm")


# --- Affichage des résultats de localisation ---
plt.figure(figsize=(8, 8))
plt.title("Localisation de l'impact sur la plaque")
plt.xlabel("X (cm)")
plt.ylabel("Y (cm)")
plt.grid(True)
plt.xlim(0, PLATE_WIDTH)
plt.ylim(0, PLATE_HEIGHT)

# Tracer les bords de la plaque
plt.plot([0, PLATE_WIDTH, PLATE_WIDTH, 0, 0], [0, 0, PLATE_HEIGHT, PLATE_HEIGHT, 0], 'k-', label="Bords de la plaque")

# Tracer les emplacements des capteurs
sensor_names = [f"ADC {i}" for i in range(COL_COUNT - 1)]
for i, coord in enumerate(SENSOR_COORDS_ALL):
    plt.plot(coord[0], coord[1], 'o', markersize=8, label=f"Capteur {sensor_names[i]}")
    plt.text(coord[0] + 0.5, coord[1] + 0.5, sensor_names[i], fontsize=9)

# Tracer la localisation réelle de l'impact
plt.plot(ACTUAL_IMPACT_LOCATION[0], ACTUAL_IMPACT_LOCATION[1], 'X', markersize=12, color='red', label="Impact réel")

# Tracer la localisation estimée de l'impact
if estimated_impact_location is not None:
    plt.plot(estimated_impact_location[0], estimated_impact_location[1], '*', markersize=15, color='green', label="Impact estimé")
    plt.text(estimated_impact_location[0] + 0.5, estimated_impact_location[1] + 0.5, f"Est. ({estimated_impact_location[0]:.1f},{estimated_impact_location[1]:.1f})", fontsize=9, color='green')


plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.show()