# code pour la lecture des données
# code pour plot les données
import struct
import matplotlib.pyplot as plt
import numpy as np

# Constants (must match the Arduino code)
COL_COUNT = 6  # 5 ADC pins + 1 timestamp
ELEMENT_SIZE = 4  # sizeof(int)
####WHITE FACE####
##################
##17#########15###
##################
##################
##21#########19###
##################
#####HIT FACE#####
##################
##15#########17###
##################
##################
##19#########21###
##################
# Load the binary file
file_path = "data_1752195401.bin"
with open(file_path, "rb") as f:
    data_bytes = f.read()

# Check if the file size is valid
num_elements = len(data_bytes) // ELEMENT_SIZE
num_rows = num_elements // COL_COUNT

# Trim extra bytes if any
trimmed_size = num_rows * COL_COUNT * ELEMENT_SIZE
data_bytes = data_bytes[:trimmed_size]
print(len(data_bytes))
print(trimmed_size)
# Unpack data
data = struct.unpack("<" + "i" * (num_rows * COL_COUNT), data_bytes)
data = np.array(data).reshape((num_rows, COL_COUNT))
print(data)
# Separate into signals and timestamps
timestamps = data[:, -1]  # Last column is micros()
adc_values = data[:, :-1]  # All but last column
print(timestamps)
print(adc_values)
# Normalize time to seconds from start
time_s = (timestamps - timestamps[0]) / 1e6

print("Mean")
print(np.mean(timestamps[1:] - timestamps[:-1]))

# Plot all ADC channels
plt.figure(figsize=(10, 6))
for i in range(COL_COUNT - 1):
    plt.plot(time_s, adc_values[:, i], label=f"ADC {i}")

plt.xlabel("Time (s)")
plt.ylabel("ADC Value")
plt.title("ADC Signals Over Time")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
