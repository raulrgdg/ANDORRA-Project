import plotly.graph_objects as go
import pandas as pd

csv_path = "seance_tir_4/tir4_plaque2.csv"
df = pd.read_csv(csv_path)

fig = go.Figure()
fig.add_trace(go.Scatter(x=df["time_s"], y=df["adc_value"], mode='lines', name='ADC'))

fig.update_layout(
    title="Signal ADC interactif",
    xaxis_title="Temps (s)",
    yaxis_title="Valeur ADC",
    template="plotly_dark"
)

fig.show()
