import pandas as pd
import os

PRE_WINDOW_MS = 1   # ms avant le pic
POST_WINDOW_MS = 3 # ms après le pic
CHANNELS = ['adc_23', 'adc_21', 'adc_19', 'adc_17', 'adc_15']

csv_path = 'seance_tir_4/tir3_plaque1.csv'  # à adapter si besoin

df = pd.read_csv(csv_path)
times = df['time_s'].values
base = os.path.splitext(os.path.basename(csv_path))[0]
out_dir = os.path.dirname(csv_path)

# Chercher la valeur maximale sur tous les channels
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

print(f"Maximum trouvé: {max_val} sur {max_channel} à l'index {max_idx}")

# Extraire la fenêtre autour du maximum
if max_idx is not None:
    t0 = times[max_idx] - PRE_WINDOW_MS/1000
    t1 = times[max_idx] + POST_WINDOW_MS/1000
    window = df[(times >= t0) & (times <= t1)]
    out_path = os.path.join(out_dir, f"{base}_maxwindow.csv")
    window.to_csv(out_path, index=False)
    print(f"Fenêtre autour du maximum sauvegardée dans {out_path}")
else:
    print("Aucun maximum trouvé.")

