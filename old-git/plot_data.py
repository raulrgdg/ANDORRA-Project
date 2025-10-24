import pandas as pd
import matplotlib.pyplot as plt

CHANNELS = ['adc_23', 'adc_21', 'adc_19', 'adc_17', 'adc_15']
csv_path = 'seance_tir_4/tir1_plaque1_maxwindow.csv'  # à adapter si besoin

df = pd.read_csv(csv_path)

# Trouver le maximum global
max_val = None
max_idx = None
max_channel = None
for channel in CHANNELS:
    idx = df[channel].idxmax()
    val = df[channel].max()
    if (max_val is None) or (val > max_val):
        max_val = val
        max_idx = idx
        max_channel = channel

fig, axs = plt.subplots(5, 1, figsize=(10, 12), sharex=True)
pins = [23, 21, 19, 17, 15]
for i, channel in enumerate(CHANNELS):
    axs[i].plot(df['time_s'], df[channel])
    axs[i].set_title(f"ADC Pin {pins[i]}")
    axs[i].set_ylabel("Valeur ADC")
    axs[i].grid(True)

axs[-1].set_xlabel('Temps (s)')
plt.tight_layout()
plt.show()
