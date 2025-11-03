import numpy as np
import matplotlib.pyplot as plt
import os

# Paramètres
binary_path = 'data_1752195397.bin'
CHANNELS = ['adc_15', 'adc_17', 'adc_19', 'adc_21', 'adc_23']
NUM_CHANNELS = 6  # 5 ADCs + 1 timestamp

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

# Plot des signaux temporels (code existant)
fig, axs = plt.subplots(5, 1, figsize=(10, 12), sharex=True)
pins = [15, 17, 19, 21, 23]
for i in range(5):
    # Fixed the title: it should use pins[i] not [i]
    axs[i].plot(time_s, adc_data[:, i])
    axs[i].set_title(f"ADC Pin {pins[i]}")
    axs[i].set_ylabel("Valeur ADC")
    axs[i].grid(True)

axs[-1].set_xlabel('Temps (s)')
plt.tight_layout()
plt.show()

# Calcul de la fréquence d'échantillonnage moyenne (code existant)
time_s = timestamps / 1e6  # conversion µs → s
delta_t = np.diff(time_s)

# fréquence instantanée par intervalle
frequencies = 1 / delta_t

# moyenne globale
mean_freq = np.mean(frequencies)

print(f"Fréquence d'échantillonnage moyenne : {mean_freq:.2f} Hz")

# Optionnel : visualiser la fréquence instantanée (code existant)
plt.figure(figsize=(10, 4))
plt.plot(frequencies)
plt.title("Fréquence d'échantillonnage instantanée")
plt.xlabel("Échantillon")
plt.ylabel("Fréquence (Hz)")
plt.grid(True)
plt.tight_layout()
plt.show()

# --- Transformées de Fourier (Amplitude et Phase) ---

# Calcul de la fréquence d'échantillonnage à partir des timestamps
if len(time_s) > 1:
    sample_rate = 1 / np.mean(np.diff(time_s))
else:
    sample_rate = 1 # Fallback, you might want to handle this case more robustly

print(f"\nFréquence d'échantillonnage utilisée pour FFT : {sample_rate:.2f} Hz")

fig_fft, axs_fft = plt.subplots(5, 2, figsize=(14, 12), sharex='col')

for i in range(5):
    signal = adc_data[:, i]
    N = len(signal) # Nombre de points du signal

    yf = np.fft.fft(signal)
    xf = np.fft.fftfreq(N, 1 / sample_rate)

    positive_frequencies = xf[:N // 2]
    amplitude = 2.0/N * np.abs(yf[0:N // 2])
    phase = np.unwrap(np.angle(yf[0:N // 2]))

    # Plot de l'amplitude
    axs_fft[i, 0].plot(positive_frequencies, amplitude)
    axs_fft[i, 0].set_title(f"Amplitude - ADC Pin {pins[i]}")
    axs_fft[i, 0].set_ylabel("Amplitude")
    axs_fft[i, 0].grid(True)
    # axs_fft[i, 0].set_xlim(0, sample_rate / 2) # Afficher jusqu'à la fréquence de Nyquist

    # Plot de la phase
    axs_fft[i, 1].plot(positive_frequencies, phase)
    axs_fft[i, 1].set_title(f"Phase - ADC Pin {pins[i]}")
    axs_fft[i, 1].set_ylabel("Phase (radians)")
    axs_fft[i, 1].grid(True)
    # axs_fft[i, 1].set_xlim(0, sample_rate / 2) # Afficher jusqu'à la fréquence de Nyquist

axs_fft[-1, 0].set_xlabel('Fréquence (Hz)')
axs_fft[-1, 1].set_xlabel('Fréquence (Hz)')

plt.tight_layout()
plt.show()



## Calcul des Différences Temporelles (Méthode de Phase FFT)

# Le signal de référence sera le premier canal (ADC Pin 15, index 0)
reference_signal = adc_data[:, 0]
reference_pin = pins[0]
N = len(reference_signal)

# Calcul FFT pour le signal de référence
yf_ref = np.fft.fft(reference_signal)
xf_all = np.fft.fftfreq(N, 1 / sample_rate) # Toutes les fréquences pour correspondance
positive_frequencies = xf_all[:N // 2]
phase_ref = np.unwrap(np.angle(yf_ref[:N // 2]))
amplitude_ref = 2.0/N * np.abs(yf_ref[0:N // 2])

# Filtrer les fréquences inférieures à 1kHz
min_freq_for_dominant = 300 # Hz
# Trouver les indices des fréquences >= 1kHz
freq_indices_above_1khz = np.where(positive_frequencies >= min_freq_for_dominant)

# Vérifier si des fréquences valides sont trouvées après le filtrage
if len(freq_indices_above_1khz[0]) == 0:
    print(f"Attention : Aucune fréquence au-dessus de {min_freq_for_dominant} Hz trouvée dans le signal de référence pour l'analyse de fréquence dominante. Le calcul de délai pourrait être imprécis.")
    # Si aucune fréquence >1kHz, on peut soit arrêter, soit choisir la plus haute fréquence disponible
    # Pour l'exemple, nous allons continuer, mais soyez conscient des limitations.
    dominant_frequency_ref = positive_frequencies[np.argmax(amplitude_ref)] # Prend la freq dominante globale
    print(f"Utilisation de la fréquence dominante globale ({dominant_frequency_ref:.2f} Hz) pour référence.")
else:
    # Appliquer le filtre aux amplitudes et fréquences du signal de référence
    amplitude_ref_filtered = amplitude_ref[freq_indices_above_1khz]
    frequencies_filtered = positive_frequencies[freq_indices_above_1khz]

    # Trouver la fréquence dominante parmi les fréquences filtrées du signal de référence
    dominant_freq_index_ref_filtered = np.argmax(amplitude_ref_filtered)
    dominant_frequency_ref = frequencies_filtered[dominant_freq_index_ref_filtered]
    dominant_phase_ref = phase_ref[freq_indices_above_1khz][dominant_freq_index_ref_filtered]

print(f"\n--- Calcul des différences temporelles (Méthode de Phase FFT > 1kHz) ---")
print(f"Signal de référence: ADC Pin {reference_pin}")
print(f"Fréquence dominante choisie pour la référence (> {min_freq_for_dominant} Hz): {dominant_frequency_ref:.2f} Hz")

# Liste pour stocker les délais temporels pour le graphique
time_delays_micro_s = []
labels = []

# Ajouter le délai du signal de référence à lui-même (0)
time_delays_micro_s.append(0.0)
labels.append(f"Pin {reference_pin} (Ref)")

# Comparer le signal de référence aux autres
for i in range(1, NUM_CHANNELS - 1): # Itérer sur les autres ADC pins
    current_signal = adc_data[:, i]
    current_pin = pins[i]

    yf_current = np.fft.fft(current_signal)
    phase_current = np.unwrap(np.angle(yf_current[:N // 2]))

    # Obtenir la phase du signal courant à la MÊME fréquence dominante que la référence
    # Trouver l'index de la fréquence dominante de référence dans les fréquences positives
    # Cela garantit que nous comparons les phases pour la même composante fréquentielle.
    # On cherche l'index exact dans `positive_frequencies`
    idx_at_dominant_freq = np.argmin(np.abs(positive_frequencies - dominant_frequency_ref))

    # Récupérer les phases des deux signaux à cette fréquence
    phase_ref_at_dom_freq = phase_ref[idx_at_dominant_freq]
    phase_current_at_dom_freq = phase_current[idx_at_dominant_freq]

    # Calculer la différence de phase
    delta_phi = phase_current_at_dom_freq - phase_ref_at_dom_freq

    # Calculer le délai temporel
    if dominant_frequency_ref > 1e-6:
        time_delay_s = -delta_phi / (2 * np.pi * dominant_frequency_ref)
        time_delay_micro_s = time_delay_s * 1e6
        print(f"  Délai (Pin {current_pin} vs Pin {reference_pin}): {time_delay_micro_s:.2f} µs")
    else:
        time_delay_micro_s = np.nan # Not a number if frequency is zero
        print(f"  Pour Pin {current_pin} vs Pin {reference_pin}: Fréquence dominante trop proche de zéro, délai non calculable.")

    time_delays_micro_s.append(time_delay_micro_s)
    labels.append(f"Pin {current_pin}")

# --- Affichage des résultats ---

# Plot du signal de référence
plt.figure(figsize=(10, 4))
plt.plot(time_s, reference_signal, label=f"ADC Pin {reference_pin} (Référence)")
plt.title(f"Signal de Référence (ADC Pin {reference_pin})")
plt.xlabel('Temps (s)')
plt.ylabel('Valeur ADC')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

# Diagramme en barres des différences temporelles
plt.figure(figsize=(10, 6))
# Créer une plage d'indices pour les positions des barres
x_pos = np.arange(len(labels))
plt.bar(x_pos, time_delays_micro_s, align='center', alpha=0.8)
plt.xticks(x_pos, labels, rotation=45, ha="right") # Rotation pour éviter le chevauchement des labels
plt.ylabel('Délai Temporel (µs)')
plt.title(f"Différence Temporelle de Chaque Signal par rapport à ADC Pin {reference_pin} (Méthode Phase FFT > 1kHz)")
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Ajouter des valeurs numériques au-dessus des barres
for index, value in enumerate(time_delays_micro_s):
    if not np.isnan(value):
        plt.text(index, value + (max(time_delays_micro_s)*0.05 if value >= 0 else min(time_delays_micro_s)*0.05),
                 f'{value:.2f}', ha='center', va='bottom' if value >= 0 else 'top')
plt.tight_layout()
plt.show()