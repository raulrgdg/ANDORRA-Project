from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# ========== CONFIGURA AQUÍ ==========
XLSX = Path("mun_e_v.xlsx")   # ruta al Excel
HOJA = "Tabelle1"             # hoja 
CALIBRES = [
    "9x19mm",
    "357 SIG",
    "357 Magnum",
    "5,56 x39 7N6 MSC",
    "5,56 x 45nn SS109",
    "FSP 5,56",
    "FSP 7,62",
    "FSP 12,7",
    "7,62 x 51 M80",
    "338 lapua",
    "12,7 x 99 mm",
    "12,7x108",
    "FSP 20",
    "14,5x114"
]

OUT_PNG = Path("energy_vs_momentum_total.png")
FIGSIZE = (8, 6)
# ====================================

# --- NUEVO: definición de categorías y colores ---
HANDGUNS = {"9x19mm", "357 SIG", "357 Magnum"}
FSP = {"FSP 5,56", "FSP 7,62", "FSP 12,7", "FSP 20"}

# Light rifles: 5.x y 7.62 (armas de asalto / intermedios y rifles de batalla ligeros)
RIFLES_LIGHT = {
    "5,56 x39 7N6 MSC", "5,56 x 45nn SS109", "7,62 x 51 M80"
}

# Heavy rifles / anti-material: .338 Lapua y 12.7
RIFLES_HEAVY = {
    "338 lapua", "12,7 x 99 mm", "12,7x108", "14,5x114"
}

def get_color(cal):
    """Devuelve color según la categoría del calibre."""
    if cal in HANDGUNS:
        return "blue"   # handguns
    if cal in FSP:
        return "grey"    # FSP
    if cal in RIFLES_LIGHT:
        return "purple"   # NUEVO: light rifles (5 & 7)
    if cal in RIFLES_HEAVY:
        return "red"     # heavy rifles / 12.7 / .338
    return None          # color por defecto de matplotlib si no coincide
# -------------------------------------

# --- Leer y limpiar ---
df = pd.read_excel(XLSX, sheet_name=HOJA)

# eliminar columnas 'Unnamed' vacías
df = df.loc[:, ~df.columns.astype(str).str.contains(r"^Unnamed", na=False)]
df.columns = [c.strip() for c in df.columns]

# comprobar columnas necesarias
for col in ("Mun", "E", "p"):
    if col not in df.columns:
        raise ValueError(f"Falta la columna '{col}' en la hoja '{HOJA}'. Columnas: {list(df.columns)}")

# propagar el nombre del calibre hacia abajo (bloques con filas vacías)
df["Mun"] = df["Mun"].ffill()

# limpiar nombres (quitar espacios y comas iniciales que a veces aparecen)
df["Mun"] = df["Mun"].astype(str).str.strip().str.replace(r"^[,\s]+", "", regex=True)

# convertir a numérico y quedarnos con filas válidas
df["E"] = pd.to_numeric(df["E"], errors="coerce")
df["p"] = pd.to_numeric(df["p"], errors="coerce")
df = df.dropna(subset=["E", "p"])

# lista de calibres disponibles
disponibles = sorted(df["Mun"].dropna().unique().tolist())

if not CALIBRES:
    print("No has indicado CALIBRES. Algunos disponibles son:")
    for c in disponibles[:40]:
        print(" -", c)
    print("\nEdita la lista CALIBRES al inicio del script y vuelve a ejecutar.")
else:
    # comprobar que existen
    faltan = [c for c in CALIBRES if c not in disponibles]
    if faltan:
        print("⚠️ No encontrados (revisa ortografía):")
        for f in faltan:
            print("  -", f)

    usados = [c for c in CALIBRES if c in disponibles]
    if not usados:
        raise ValueError("Ninguno de los calibres seleccionados existe con datos válidos.")

    plt.figure(figsize=FIGSIZE)

    for calibre in usados:
        sub = df[df["Mun"] == calibre].copy()
        sub = sub.sort_values("p")
        plt.plot(sub["p"].values, sub["E"].values, color=get_color(calibre))

    # --- Leyenda usando Line2D (más limpia que plot([],[],...)) ---
    legend_handles = [
        Line2D([0], [0], color='blue', lw=2, label='Handgun Ammunition'),
        Line2D([0], [0], color='purple', lw=2, label='Rifle Ammunition'),
        Line2D([0], [0], color='red', lw=2, label='Sniper & Anti-Materiel Ammunition'),
        Line2D([0], [0], color='grey', lw=2, label='FSP Ammunition'),
    ]
    plt.legend(handles=legend_handles)

    plt.xlabel("p (kg·m/s)")
    plt.ylabel("E (J)")
    plt.title("Energy vs Momentum")
    plt.xscale('log')
    plt.axvline(x=10, color='black', linestyle='--', linewidth=1)
    plt.axvline(x=55, color='black', linestyle='--', linewidth=1)
    plt.grid(True)
    plt.ylim(0,14000)
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150)
    plt.close()
    print(f"✅ Guardado en: {OUT_PNG.resolve()}")
