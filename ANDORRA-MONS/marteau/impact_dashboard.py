import streamlit as st
from utils import record_signal, analyze_impacts
import matplotlib.pyplot as plt

st.set_page_config(page_title="Impact Analyzer", layout="centered")
st.title("🔨 Hammer Impact Analyzer")

# --- Sidebar Config ---
with st.sidebar:
    st.header("Paramètres d'acquisition")
    duration = st.slider("Durée d'acquisition (s)", 1, 10, 5)
    fs = st.number_input("Fréquence d’échantillonnage (Hz)", value=48000)
    device = st.number_input("ID de la carte son (input)", value=6)
    sensitivity = st.number_input("Sensibilité capteur (V/N)", value=0.002251, step=0.0001, format="%.6f")
    threshold = st.slider("Seuil relatif pour détection", 0.1, 0.9, 0.4)

if st.button("🎙️ Lancer l'enregistrement"):
    st.info("📡 Enregistrement en cours...")
    signal = record_signal(duration, fs, device)
    st.success("✅ Signal acquis")

    st.info("🧠 Traitement en cours...")
    results, plots, csv_path, output_dir = analyze_impacts(signal, fs, sensitivity, threshold)

    st.success(f"✅ {len(results)} impact(s) détecté(s)")

    for res, (fig1, fig2) in zip(results, plots):
        with st.expander(f"Impact {res['i']}"):
            st.markdown(f"""
            - ⏱️ Temps : `{res['time']:.4f} s`
            - 🏋️ Pic : `{res['peak']:.2f} N`
            - ⚡ Énergie : `{res['energy']:.4f} N²·s`
            - 💨 Impulsion : `{res['impulse']:.4f} N·s`
            - ⏲️ Durée : `{res['duration']:.1f} ms`
            - 🔼 Rise time : `{res['rise']:.1f} ms`
            - 🔽 Fall time : `{res['fall']:.1f} ms`
            - 🎵 Fréquence dominante : `{res['freq']:.1f} Hz`
            """)

            st.pyplot(fig1)
            st.pyplot(fig2)

    with open(csv_path, "rb") as f:
        st.download_button("⬇️ Télécharger le CSV", f, file_name="results.csv")

    st.success("📁 Résultats enregistrés dans : " + output_dir)
