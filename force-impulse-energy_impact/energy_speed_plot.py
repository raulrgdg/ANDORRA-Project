import matplotlib.pyplot as plt

VELOCITIES = [800, 560, 282]
ENERGIES = [132.0, 106.0, 76.8]

plt.figure(figsize=(6, 4))
plt.plot(VELOCITIES, ENERGIES, marker='o')
plt.xlabel('Velocity (m/s)')
plt.xlim(0,800)
plt.ylabel('Energy (J)')
plt.ylim(0,150)
plt.title('Impact Energy vs Velocity')
plt.grid(True, alpha=0.3)
for v, e in zip(VELOCITIES, ENERGIES):
    plt.annotate(f"{e} J", (v, e), textcoords="offset points", xytext=(0, 8), ha='center')

plt.tight_layout()
plt.savefig('energy_vs_velocity.png', dpi=150)
