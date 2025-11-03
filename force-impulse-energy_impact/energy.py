# This code is a very first ¡draft! to compute the impulse and energy given a shock impat wave. 
# Raúl Rodr-iguez || September 2025
import numpy as np
import os
import matplotlib.pyplot as plt

parent_path = '/Users/raulrodriguez/Work-Station/ANDORRAV2/raul/plot/data_sh_5'
data_name='data_1546301780.bin'
data_path= os.path.join(parent_path, data_name)


def energy_from_adc(adc, fs=None, v_imp=1.0, k_adc2F=1.0,
                      k_umbral=3.0, margen_ms=2.0,
                      n_ini=0, n_fin=None, usar_abs=False,
                      offset_adc=None, clip_below_offset=True,
                      timestamps=None):
    """
    adc:      array with ADC values
    fs:       Hz (sampling freq.). Optional if timestamps provided.
    v_imp:    m/s (impact velocity)
    k_adc2F:  N/ADC (conversion factor ADC -> Force)
    k_umbral: multiplier on baseline noise to define the threshold
    margen_ms: time window before/after the detected impact (ms)
    usar_abs: if True integrates |F| (not recommended)
    offset_adc: ADC value to treat as zero (if None, estimate from data)
    clip_below_offset: if True ignores contributions under the offset
    timestamps: array of timestamps (in seconds) aligned with ADC samples
    """
    if fs is None and timestamps is None:
        raise ValueError("Provide either fs or timestamps for integration timing")

    if n_fin is None:
        n_fin = len(adc)
    x = np.asarray(adc[n_ini:n_fin]).astype(float)
    N = len(x)

    if timestamps is not None:
        t = np.asarray(timestamps[n_ini:n_fin]).astype(float)
        if t.size != N:
            raise ValueError("timestamps length must match sliced ADC data")
        if N < 2 or np.any(np.diff(t) <= 0):
            raise ValueError("timestamps must be strictly increasing")
        dt_vec = np.diff(t)
        dt = float(np.mean(dt_vec))
        t_rel = t - t[0]
    else:
        dt = 1.0/float(fs)
        t_rel = None

    # Baseline using an initial "rest" segment (used to estimate the offset)
    muestras_base = int(round(0.05/dt)) if dt > 0 else 1
    n_base = max(1, min(N, muestras_base))
    base = offset_adc if offset_adc is not None else np.median(x[:n_base])
    xr = x - base
    xr_int = np.clip(xr, 0.0, None) if clip_below_offset else xr

    # Noise-based threshold
    ruido = np.std(xr[:n_base]) if n_base < N else np.std(xr)
    umbral = k_umbral * max(ruido, 1e-1)

    # Indices above the threshold (absolute value to capture peaks)
    idx = np.where(np.abs(xr) >= umbral)[0]
    if idx.size == 0:
        return dict(W=0.0, J=0.0, i0=None, i1=None)

    i0, i1 = idx[0], idx[-1]

    # Margins around detected impact
    muestras_margen = int(round((margen_ms/1000.0)/dt)) if dt > 0 else 0
    m = max(0, muestras_margen)
    i0 = max(0, i0 - m)
    i1 = min(N-1, i1 + m)

    # Force window
    F = k_adc2F * xr_int[i0:i1+1]
    if usar_abs:
        F = np.abs(F)

    # Impulse J (trapezoid)
    if t_rel is not None:
        t_slice = t_rel[i0:i1+1]
        J = np.trapz(F, x=t_slice)   # N·s
    else:
        J = np.trapz(F, dx=dt)   # N·s

    # Energy W ≈ v_imp * J
    W = 0.5 * v_imp * J            # Joule if k_adc2F and v_imp are in SI

    return dict(W=W, J=J, i0=i0+n_ini, i1=i1+n_ini, offset=base, dt=dt, n_base=n_base, n_base_end=max(n_ini, n_ini + n_base - 1))

CHANNELS = ['adc_15', 'adc_17', 'adc_19', 'adc_21', 'adc_23']
NUM_CHANNELS = 6  # 5 ADCs + 1 timestamp

data = np.fromfile(data_path, dtype=np.int32)
data = data.reshape(-1, NUM_CHANNELS)

# Extract columns
adc_data = data[:, 0] # Just channel 15
timestamps = data[:, 5]  # in microseconds
time_s = timestamps / 1e6  # convert µs → s
delta_t = np.diff(time_s)

result = energy_from_adc(
    adc=adc_data,
    v_imp=820,
    k_adc2F=1,
    k_umbral=3, # Factor that multiplies the offset to define the threshold of 'impact zone'
    margen_ms=0.1,
    n_ini=0,
    n_fin=None,
    usar_abs=True,
    offset_adc=None, # Offset is estimated automatically from the initial portion of the signal
    clip_below_offset=True,
    timestamps=time_s,
)

print(f"Samples delta_t: {len(delta_t)}")
print(f"W = {result['W']}")
print(f"J = {result['J']}")
print(f"i0 = {result['i0']}")
print(f"i1 = {result['i1']}")
print(f"offset = {result['offset']}")
print(f"dt = {result['dt']}")

# Reference plot: ADC vs time
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(time_s, adc_data, label='ADC')

i0 = result.get('i0')
i1 = result.get('i1')
if i0 is not None and 0 <= i0 < len(time_s):
    ax.axvline(time_s[i0], color='red', linestyle='--', label='i0')
if i1 is not None and 0 <= i1 < len(time_s):
    ax.axvline(time_s[i1], color='green', linestyle='--', label='i1')

offset_val = result.get('offset')
if offset_val is not None:
    ax.axhline(offset_val, color='orange', linestyle=':', label='offset')

ax.set_xlabel('Time (s)')
ax.set_ylabel('ADC value')
ax.set_title('ADC vs Time with integration limits')
ax.legend(loc='best')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(f'integral_adc_{data_name}.png', dpi=150)
plt.close(fig)
