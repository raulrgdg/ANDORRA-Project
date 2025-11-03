import matplotlib.pyplot as plt
import pandas as pd

# === Charger les données depuis un fichier CSV ===
file_path = "seance_tir_4/tir1_plaque1.csv"  # Remplace par le nom réel de ton fichier
df = pd.read_csv(file_path)

# Vérification rapide du contenu
print(df.head())

# === Extraire les colonnes ===
time_s = df["time_s"]
adc_columns = [col for col in df.columns if col.startswith("adc_")]
adc_values = df[adc_columns]

# === Calculer la fréquence moyenne d’échantillonnage ===
deltas = time_s.diff().dropna()
mean_delta = deltas.mean()
print(f"Fréquence d'échantillonnage moyenne : {1/mean_delta:.1f} Hz")

# === Tracer les signaux ADC ===
plt.figure(figsize=(10, 6))
for col in adc_columns:
    plt.plot(time_s, df[col], label=col)

plt.xlabel("Temps (s)")
plt.ylabel("Valeur ADC")
plt.title("Signaux ADC dans le temps")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
